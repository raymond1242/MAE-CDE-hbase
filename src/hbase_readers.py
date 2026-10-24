"""Mechanisms for retrieving the records of the HBase table.

Every reader returns (records, info):
  records  list of dicts {"row_key": str, "name": str|None, "city": ..., ...}
           None means the cell does not exist in HBase.
  info     dict with extraction metadata (for traceability).

1. read_via_thrift: direct connection from Python with happybase. happybase
   talks to the HBase Thrift server, which in turn uses the native Java
   client. Only the 4 required columns are requested (server-side projection).

2. read_via_shell_export: fallback when Thrift is not available. The output
   of `scan 'emp'` from the HBase shell is exported to a text file and parsed
   here line by line.

3. read_snapshot: re-reads a CSV snapshot that was already extracted from
   HBase with one of the methods above (to re-process without the cluster).
"""
import csv
import re

from config import COLUMN_MAP, FIELDS, TABLE_NAME

_COLUMN_TO_FIELD = {f"{family}:{qualifier}": field for field, (family, qualifier) in COLUMN_MAP.items()}


def _empty_record(row_key):
    return {"row_key": row_key, **{field: None for field in FIELDS}}


def read_via_thrift(host, port, table_name=TABLE_NAME, transport="buffered", protocol="binary",
                    batch_size=500, timeout_ms=60000):
    import happybase  # lazy import: the other readers do not need this dependency

    conn = happybase.Connection(host=host, port=port, timeout=timeout_ms,
                                transport=transport, protocol=protocol)
    try:
        if table_name.encode() not in conn.tables():
            raise SystemExit(f"Table '{table_name}' does not exist in HBase ({host}:{port})")
        table = conn.table(table_name)
        families = sorted(table.families())
        columns = [col.encode() for col in _COLUMN_TO_FIELD]

        records = []
        # scan() is lazy: happybase fetches rows from the server in batches of
        # batch_size instead of loading the whole table in a single response.
        for row_key, data in table.scan(columns=columns, batch_size=batch_size):
            record = _empty_record(row_key.decode("utf-8"))
            for col, value in data.items():
                record[_COLUMN_TO_FIELD[col.decode()]] = value.decode("utf-8")
            records.append(record)
    finally:
        conn.close()

    info = {
        "method": "thrift (happybase)",
        "server": f"{host}:{port}",
        "transport": f"{transport}/{protocol}",
        "table": table_name,
        "table_families": [f.decode() for f in families],
        "requested_columns": list(_COLUMN_TO_FIELD),
        "rows_read": len(records),
    }
    return records, info


# Cell line printed by the HBase shell scan, for example:
#  E0001     column=personal:city, timestamp=2026-10-23T22:15:30.123, value=Lima
_CELL_RE = re.compile(
    r"^\s*(?P<row>\S+)\s+column=(?P<column>[^,]+),\s*timestamp=(?P<ts>[^,]+),\s*value=(?P<value>.*)$"
)
_ROW_COUNT_RE = re.compile(r"^\s*(?P<n>\d+) row\(s\)")
_HEX_ESCAPE_RE = re.compile(r"\\x([0-9A-Fa-f]{2})")


def decode_shell_bytes(text):
    """Undo Bytes.toStringBinary: the shell prints non-printable bytes
    (including the bytes of UTF-8 characters such as 'á') as \\xNN."""
    raw = bytearray()
    pos = 0
    for match in _HEX_ESCAPE_RE.finditer(text):
        raw += text[pos:match.start()].encode("latin-1")
        raw.append(int(match.group(1), 16))
        pos = match.end()
    raw += text[pos:].encode("latin-1")
    return raw.decode("utf-8", errors="replace")


def read_via_shell_export(path, table_name=TABLE_NAME):
    records = {}
    ignored_columns = set()
    reported_rows = None
    n_cells = 0

    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.rstrip("\n")
            match = _CELL_RE.match(line)
            if match:
                row_key = decode_shell_bytes(match.group("row"))
                column = decode_shell_bytes(match.group("column"))
                record = records.setdefault(row_key, _empty_record(row_key))
                field = _COLUMN_TO_FIELD.get(column)
                if field is None:
                    ignored_columns.add(column)
                else:
                    record[field] = decode_shell_bytes(match.group("value"))
                n_cells += 1
                continue
            count = _ROW_COUNT_RE.match(line)
            if count:
                reported_rows = int(count.group("n"))

    if not records:
        raise SystemExit(f"No cells found in {path}. Is it the output of scan '{table_name}'?")
    if reported_rows is not None and reported_rows != len(records):
        raise SystemExit(
            f"The shell reported {reported_rows} rows but {len(records)} were parsed: "
            f"check whether the row keys contain spaces"
        )

    info = {
        "method": "HBase shell export (scan)",
        "file": str(path),
        "table": table_name,
        "cells_read": n_cells,
        "rows_reported_by_shell": reported_rows,
        "rows_read": len(records),
        "ignored_columns": sorted(ignored_columns),
    }
    return sorted(records.values(), key=lambda r: r["row_key"]), info


def write_snapshot(records, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["row_key", *FIELDS])
        writer.writeheader()
        for record in records:
            writer.writerow({k: ("" if v is None else v) for k, v in record.items()})


def read_snapshot(path):
    with open(path, newline="", encoding="utf-8") as f:
        records = [{k: (v if v != "" else None) for k, v in row.items()} for row in csv.DictReader(f)]
    return records, {"method": "CSV snapshot previously extracted from HBase", "file": str(path),
                     "rows_read": len(records)}
