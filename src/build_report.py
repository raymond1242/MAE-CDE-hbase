"""Fill the result tables of deliverable/REPORT.md from the files in results/.

The report keeps its hand-written text (interpretation, conceptual answers).
Only the blocks between <!-- BEGIN:name --> and <!-- END:name --> markers are
replaced, so this can be re-run after every new analysis. The generated
answer lines are in Spanish because the report is the Spanish deliverable.

Usage:
    python3 src/build_report.py
    python3 src/build_report.py --results-dir results --report deliverable/REPORT.md
"""
import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path

from config import MIN_SALARIES_PER_CITY, MISSING_LABEL, REPO_ROOT, RESULTS_DIR

_BLOCK_RE = re.compile(r"(<!-- BEGIN:(?P<name>[a-z_]+) -->\n).*?(\n<!-- END:(?P=name) -->)", re.S)
_PROMPT_RE = re.compile(r"^hbase:\d+:\d+> (?P<cmd>.+)$")
_ROWS_RE = re.compile(r"^(?P<n>\d+) row\(s\)")
_EXACT_COUNT_RE = re.compile(r"^count .*COLUMNS => \['(?P<col>[^']+)'\].*'binary:(?P<value>[^']+)'")


def pending(step):
    return f"_Pendiente: ejecute {step} de `docs/02_step_by_step.md` y vuelva a correr `python3 src/build_report.py`._"


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def md_table(rows, columns):
    lines = ["| " + " | ".join(columns) + " |", "|" + "---|" * len(columns)]
    lines += ["| " + " | ".join(str(r.get(c, "")) or "—" for c in columns) + " |" for r in rows]
    return "\n".join(lines)


def command_row_counts(path):
    """[(command, rows)] for every shell command that printed 'N row(s)'."""
    results, command = [], None
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.rstrip("\n")
            prompt = _PROMPT_RE.match(line)
            if prompt:
                command = prompt.group("cmd").strip()
                continue
            rows = _ROWS_RE.match(line)
            if rows and command:
                results.append((command, int(rows.group("n"))))
                command = None
    return results


def block_source(d):
    path = d / "extraction_metadata.json"
    if not path.exists():
        return pending("el paso 6")
    info = json.loads(path.read_text(encoding="utf-8"))
    location = info.get("server") or info.get("file", "")
    return md_table([
        {"item": "method", "value": info["method"]},
        {"item": "server / file", "value": f"`{location}`"},
        {"item": "table", "value": f"`{info.get('table', '')}`"},
        {"item": "rows_read", "value": info["rows_read"]},
        {"item": "extracted_at (UTC)", "value": info["extracted_at"]},
        {"item": "python", "value": info.get("python", "")},
    ], ["item", "value"])


def block_verification(d):
    path = d / "raw" / "02_verify.txt"
    if not path.exists():
        return pending("el paso 5")
    counts = [{"command": f"`{cmd}`", "rows": n} for cmd, n in command_row_counts(path) if cmd.startswith("count")]
    return md_table(counts, ["command", "rows"])


def block_by_city(d):
    path = d / "01_employees_by_city.csv"
    if not path.exists():
        return pending("el paso 6")
    rows = read_csv(path)
    top = next(r for r in rows if r["city"] != MISSING_LABEL)
    return (md_table(rows, ["city", "employees", "percentage"]) +
            f"\n\n**Respuesta:** {top['city']} concentra más empleados ({top['employees']}, "
            f"{top['percentage']}% del total). `{MISSING_LABEL}` agrupa los registros sin ciudad.")


def block_salary_summary(d):
    path = d / "02_salary_summary.csv"
    if not path.exists():
        return pending("el paso 6")
    rows = read_csv(path)
    s = {r["metric"]: r["value"] for r in rows}
    return (md_table(rows, ["metric", "value"]) +
            f"\n\n**Respuesta:** salario promedio {s['avg_salary']}, mínimo {s['min_salary']} y máximo "
            f"{s['max_salary']} USD, calculados sobre {s['valid_salaries']} salarios válidos de "
            f"{s['total_records']} registros ({s['missing_salaries']} faltantes y {s['invalid_salaries']} "
            f"inválidos excluidos; {s['fixed_salaries']} corregidos al quitar espacios).")


def block_by_designation(d):
    path = d / "03_employees_by_designation.csv"
    if not path.exists():
        return pending("el paso 6")
    rows = read_csv(path)
    top = next(r for r in rows if r["designation"] != MISSING_LABEL)
    return (md_table(rows, ["designation", "employees", "percentage"]) +
            f"\n\n**Respuesta:** el cargo más frecuente es {top['designation']} ({top['employees']} empleados, "
            f"{top['percentage']}%).")


def block_salary_by_city(d):
    path = d / "04_salary_by_city.csv"
    if not path.exists():
        return pending("el paso 6")
    rows = read_csv(path)
    columns = ["rank", "city", "employees", "valid_salaries", "avg_salary", "min_salary", "max_salary",
               "meets_minimum"]
    ranked = [r for r in rows if r["rank"]]
    if not ranked:
        answer = f"ninguna ciudad tiene al menos {MIN_SALARIES_PER_CITY} salarios válidos."
    else:
        top = ranked[0]
        answer = (f"sí hay registros suficientes (mínimo {MIN_SALARIES_PER_CITY} salarios válidos por ciudad). "
                  f"La ciudad con mayor salario promedio es {top['city']} ({top['avg_salary']} USD, "
                  f"{top['valid_salaries']} salarios válidos).")
    return md_table(rows, columns) + f"\n\n**Respuesta:** {answer}"


def block_data_quality(d):
    path = d / "05_data_quality.csv"
    if not path.exists():
        return pending("el paso 6")
    groups = Counter((r["field"], r["problem"], r["treatment"]) for r in read_csv(path))
    rows = [{"field": f, "problem": p, "treatment": t, "rows": n} for (f, p, t), n in sorted(groups.items())]
    return md_table(rows, ["field", "problem", "treatment", "rows"]) + \
        "\n\nDetalle fila por fila: [`results/05_data_quality.csv`](../results/05_data_quality.csv)."


def block_hbase_vs_python(d):
    path = d / "raw" / "04_activity_b_queries.txt"
    by_city, by_designation = d / "01_employees_by_city.csv", d / "03_employees_by_designation.csv"
    if not path.exists() or not by_city.exists() or not by_designation.exists():
        return pending("los pasos 5 y 6")
    python_counts = {("personal:city", r["city"]): r["employees"] for r in read_csv(by_city)}
    python_counts.update({("professional:designation", r["designation"]): r["employees"]
                          for r in read_csv(by_designation)})

    exact, other = [], []
    for cmd, n in command_row_counts(path):
        match = _EXACT_COUNT_RE.match(cmd)
        if match:
            python_n = int(python_counts.get((match.group("col"), match.group("value")), 0))
            exact.append({"column": match.group("col"), "value": match.group("value"),
                          "hbase_exact_filter": n, "python_normalized": python_n, "difference": python_n - n})
        else:
            other.append({"command": f"`{cmd}`", "rows": n})
    return (md_table(exact, ["column", "value", "hbase_exact_filter", "python_normalized", "difference"]) +
            "\n\nOtras consultas de HBase y filas devueltas:\n\n" + md_table(other, ["command", "rows"]))


BLOCKS = {
    "source": block_source,
    "verification": block_verification,
    "by_city": block_by_city,
    "salary_summary": block_salary_summary,
    "by_designation": block_by_designation,
    "salary_by_city": block_salary_by_city,
    "data_quality": block_data_quality,
    "hbase_vs_python": block_hbase_vs_python,
}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--results-dir", default=str(RESULTS_DIR))
    parser.add_argument("--report", default=str(REPO_ROOT / "deliverable" / "REPORT.md"))
    args = parser.parse_args()

    results_dir, report = Path(args.results_dir), Path(args.report)
    text = report.read_text(encoding="utf-8")
    filled = []

    def replace(match):
        name = match.group("name")
        if name not in BLOCKS:
            return match.group(0)
        filled.append(name)
        return match.group(1) + BLOCKS[name](results_dir) + match.group(3)

    report.write_text(_BLOCK_RE.sub(replace, text), encoding="utf-8")
    print(f"Updated {len(filled)} blocks in {report}: {', '.join(filled)}")


if __name__ == "__main__":
    main()
