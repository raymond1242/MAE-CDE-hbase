# Practice 2: Processing Data Stored in HBase

Course: *Ciencia de Datos Escalable* · Environment: Amazon EMR with HBase

This repository contains everything needed to complete the assignment reproducibly. That includes the
dataset, the HBase table definition, the scripts that load and query the table, the Python code that
retrieves the data from HBase and computes the indicators, the results, and the final report.

The assignment asks for two things to be kept apart:

- **HBase** handles storage and retrieval: `put`, `get`, `scan`, `count`, and server-side filters.
- **Python** handles the analysis: type conversion, cleaning, grouping, percentages, and
  average/min/max.

The code and the report follow that split.

## Data flow

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
                  src/build_report.py ──▶ deliverable/REPORT.md (Spanish)
```

## Repository structure

```
.
├── data/
│   ├── employees.csv            # synthetic dataset (300 employees, seed 42)
│   └── README.md                # data dictionary and injected data-quality issues
├── deliverable/
│   └── REPORT.md                # the report to submit (Spanish): answers, tables, interpretation
├── docs/
│   ├── 01_emr_setup.md          # create the minimal EMR cluster in the AWS console and connect
│   ├── 02_step_by_step.md       # full runbook, from the cluster to the final report
│   └── 03_hbase_commands.md     # every HBase shell command used and what it shows
├── hbase/                       # HBase shell scripts (run with: hbase shell -n <file>)
│   ├── 01_create_table.hbase
│   ├── 02_verify.hbase          # Activity A
│   ├── 03_full_scan.hbase       # scan 'emp' export (evidence + fallback input)
│   └── 04_activity_b_queries.hbase
├── infra/
│   └── setup_primary.sh         # run on the primary node: Python venv + Thrift checks
├── local/                       # optional: HBase 2.6 in Docker to rehearse for free
├── results/                     # outputs of the EMR run (CSV tables + raw shell evidence)
├── src/
│   ├── config.py                # table name, column mapping, Thrift host/port
│   ├── generate_dataset.py      # rebuilds data/employees.csv
│   ├── load_hbase.py            # loads the CSV into HBase (Thrift or generated put script)
│   ├── hbase_readers.py         # retrieves rows from HBase (Thrift, shell export, snapshot)
│   ├── indicators.py            # cleaning rules and indicator computation
│   ├── analyze.py               # retrieve, compute, write results/
│   └── build_report.py          # fills the result tables in deliverable/REPORT.md
├── tests/                       # unit tests (no cluster needed)
└── requirements.txt             # happybase + thriftpy2
```

## Quick start

The full procedure, with explanations and fallbacks, is in
[docs/02_step_by_step.md](docs/02_step_by_step.md). In short:

```bash
# In the AWS console: create the cluster (docs/01_emr_setup.md), then SSH to the primary node

# On the EMR primary node, from the repository root
bash infra/setup_primary.sh && source .venv/bin/activate
hbase shell -n hbase/01_create_table.hbase
python3 src/load_hbase.py --method thrift
hbase shell -n hbase/02_verify.hbase 2>/dev/null | tee results/raw/02_verify.txt
hbase shell -n hbase/03_full_scan.hbase 2>/dev/null > results/raw/scan_emp.txt
hbase shell -n hbase/04_activity_b_queries.hbase 2>/dev/null | tee results/raw/04_activity_b_queries.txt
python3 src/analyze.py --source thrift

# Back on your laptop: fetch results/ and fill the report, then terminate the cluster in the console
python3 src/build_report.py
```

## Deliverables

| Required deliverable | Where |
|---|---|
| Code used to retrieve and process the data | `src/`, `hbase/` |
| Results table with the requested indicators | `results/01…05_*.csv` and section 4 of `deliverable/REPORT.md` |
| Short interpretation (5–10 lines) | section 5 of `deliverable/REPORT.md` |
| Answers to the conceptual questions | section 6 of `deliverable/REPORT.md` |

The tables are CSV files, which work well for machine-readable results and open in Excel or pandas. The
answers and interpretation are written in Markdown. For submission, export `deliverable/REPORT.md` to
PDF (see step 9 of the runbook) so the grader gets one document with every table already in it.

## Requirements

- A personal AWS account with permission to create EMR clusters (everything is done in the web console).
- Python 3.9 or later. The EMR 7.x primary node ships Python 3.9, and the analysis uses only the
  standard library. `happybase` is needed only for the Thrift connection.
- Optional: Docker for the local rehearsal.

Run the unit tests (no cluster needed) with:

```bash
python3 -m unittest discover -s tests -v
```

## Rules this project follows

- Results are computed from data read back from HBase, never from the CSV directly.
- No `drop` or `truncate` anywhere. Table creation is idempotent and loading only overwrites the same
  cells.
- Missing and invalid values are handled with explicit rules, and every affected row is logged in
  `results/05_data_quality.csv`.
