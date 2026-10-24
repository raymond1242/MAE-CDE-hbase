# Practice 2: Processing Data Stored in HBase

**Course:** Ciencia de Datos Escalable · **Environment:** Amazon EMR with HBase · **Author:** Raymond Negron \
**Repository:** https://github.com/raymond1242/MAE-CDE-hbase \
**Report (Spanish):** [deliverable/REPORT.md](deliverable/REPORT.md)

This project retrieves employee records stored in the HBase table `emp` on Amazon EMR and computes
summary indicators with Python. It keeps the two kinds of work separate:

- **HBase** handles storage and retrieval: `put`, `get`, `scan`, `count`, and server-side filters.
- **Python** handles the analysis: type conversion, cleaning, grouping, percentages, and average, minimum
  and maximum.

## Results (EMR run)

The run took place on 2026-10-24 on cluster `j-00430072CCSGFQ8WWNLK` (`emr-7.14.0`, HBase 2.6.4,
`us-east-2`). Python read 300 rows from HBase through Thrift (happybase).

| Question | Result |
|---|---|
| Employees per city | Lima 67 · Bogota 56 · Santiago 56 · Quito 45 · Buenos Aires 44 · Madrid 29 · no city 3 |
| Share per city | Lima 22.33% · Bogota 18.67% · Santiago 18.67% · Quito 15.00% · Buenos Aires 14.67% · Madrid 9.67% · no city 1.00% |
| Average / min / max salary (USD) | 48 647.18 / 18 000 / 129 000. Computed over 284 valid salaries; 16 missing or invalid values were excluded |
| Employees per designation | Data Analyst 72 · Software Engineer 63 · Administrative Assistant 48 · Data Scientist 39 · Project Manager 33 · Accountant 28 · Director 15 · none 2 |
| City with the highest average salary | Madrid: 57 676.92 USD, from 26 valid salaries |

The full tables are in [results/](results/). The interpretation and the conceptual answers are in the
[report](deliverable/REPORT.md).

## Deliverables

| Required deliverable | Where |
|---|---|
| Code used to retrieve and process the data | [src/](src/) (Python) and [hbase/](hbase/) (HBase shell scripts) |
| Results table with the requested indicators | Section 4 of the [report](deliverable/REPORT.md); CSV files in [results/](results/) |
| Interpretation (5–10 lines) | Section 5 of the [report](deliverable/REPORT.md) |
| Answers to the conceptual questions | Section 6 of the [report](deliverable/REPORT.md) |
| Generative AI usage log (prompts used) | [deliverable/AI_USAGE.md](deliverable/AI_USAGE.md) |

## How the data is retrieved from HBase

```
data/employees.csv ──(src/load_hbase.py)──▶ HBase table 'emp' on EMR
                                                │
                ┌───────────────────────────────┴──────────────────────────────┐
                │ Python + happybase via Thrift (port 9090)   ← main method    │
                │ HBase shell `scan 'emp'` export, parsed     ← fallback       │
                └───────────────────────────────┬──────────────────────────────┘
                                                ▼
                     src/analyze.py ──▶ results/*.csv, results/results.md
                                                ▼
                  src/build_report.py ──▶ deliverable/REPORT.md
```

Both retrieval methods were run on the same table, and they produce byte-identical results.

## Repository structure

```
.
├── src/                         # Python code
│   ├── config.py                # table name, family:qualifier mapping, Thrift host/port
│   ├── generate_dataset.py      # builds data/employees.csv (seed 42)
│   ├── load_hbase.py            # loads the CSV into HBase (Thrift, or a generated put script)
│   ├── hbase_readers.py         # retrieves the rows from HBase (Thrift or shell export)
│   ├── indicators.py            # cleaning rules and indicator computation
│   ├── analyze.py               # retrieve → compute → write results/
│   └── build_report.py          # fills the result tables of the report
├── hbase/                       # HBase shell scripts (hbase shell -n <file>)
│   ├── 01_create_table.hbase
│   ├── 02_verify.hbase          # Activity A
│   ├── 03_full_scan.hbase       # scan 'emp' export
│   └── 04_activity_b_queries.hbase
├── data/                        # synthetic dataset and data dictionary
├── results/                     # outputs of the EMR run (CSV tables + raw HBase shell evidence)
├── deliverable/                 # REPORT.md and AI_USAGE.md (Spanish), each with its PDF
├── docs/                        # EMR console guide, step-by-step runbook, HBase command reference
├── infra/setup_primary.sh       # prepares the EMR primary node (Python venv, Thrift check)
├── local/                       # optional: HBase 2.6 in Docker for a free local rehearsal
├── tests/                       # unit tests (no cluster needed)
└── requirements.txt             # happybase + thriftpy2
```

## How to reproduce

The full procedure is in [docs/02_step_by_step.md](docs/02_step_by_step.md). To create the cluster, see
[docs/01_emr_setup.md](docs/01_emr_setup.md). Once the cluster is running, the commands on the EMR
primary node, from the repository root, are:

```bash
bash infra/setup_primary.sh && source .venv/bin/activate
hbase shell -n hbase/01_create_table.hbase
python3 src/load_hbase.py --method thrift
hbase shell -n hbase/02_verify.hbase 2>/dev/null | tee results/raw/02_verify.txt
hbase shell -n hbase/03_full_scan.hbase 2>/dev/null > results/raw/scan_emp.txt
hbase shell -n hbase/04_activity_b_queries.hbase 2>/dev/null | tee results/raw/04_activity_b_queries.txt
python3 src/analyze.py --source thrift
```

Requirements:

- Python 3.9 or later. The analysis uses only the standard library; `happybase` is needed only for the
  Thrift connection.
- Unit tests, which need no cluster: `python3 -m unittest discover -s tests -v`.

## Rules followed

- Results are computed from the data read back from HBase, never from the CSV directly.
- No `drop` or `truncate` anywhere. Table creation is idempotent.
- Missing and invalid values are handled with explicit rules. Every affected row is logged in
  [results/05_data_quality.csv](results/05_data_quality.csv).
