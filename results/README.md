# Results

The files in this folder are produced on the EMR cluster (steps 4–6 of
[docs/02_step_by_step.md](../docs/02_step_by_step.md)) and copied back to the laptop in step 7. Never edit
them by hand: rerun the scripts instead.

| File | Produced by | Content |
|---|---|---|
| `raw/00_hbase_version.txt` | `hbase version` | HBase version of the cluster |
| `raw/02_verify.txt` | `hbase/02_verify.hbase` | Activity A: describe, count, sample rows, per-column counts |
| `raw/scan_emp.txt` | `hbase/03_full_scan.hbase` | Full `scan 'emp'` (evidence and fallback input) |
| `raw/04_activity_b_queries.txt` | `hbase/04_activity_b_queries.hbase` | Activity B queries answered by HBase alone |
| `emp_snapshot.csv` | `src/analyze.py` | Rows exactly as read from HBase (empty field means absent cell) |
| `extraction_metadata.json` | `src/analyze.py` | Method, server, table, row count and timestamp of the extraction |
| `01_employees_by_city.csv` | `src/analyze.py` | Q1–Q2: employees and percentage per city |
| `02_salary_summary.csv` | `src/analyze.py` | Q3: average, min, max (plus median, stdev, data-quality counts) |
| `03_employees_by_designation.csv` | `src/analyze.py` | Q4: employees and percentage per designation |
| `04_salary_by_city.csv` | `src/analyze.py` | Q5: salary statistics and ranking per city |
| `05_data_quality.csv` | `src/analyze.py` | Every missing, invalid or normalized value and how it was treated |
| `results.md` | `src/analyze.py` | All the tables above in Markdown |

## Run log

| Date (UTC) | Cluster ID | Release / HBase | Extraction method | Notes |
|---|---|---|---|---|
| 2026-10-24 | `j-04022101QBEOJ3O1HYPY` (`hbase-practice-2`) | emr-7.14.0 / HBase 2.6.4 | — | `us-east-2`. Terminated with errors 32 s after creation; never reached *Waiting*. Not used |
| 2026-10-24 | `j-00430072CCSGFQ8WWNLK` | emr-7.14.0 / HBase 2.6.4-amzn-2 | thrift (happybase), extracted 06:32:20 UTC | `us-east-2`, idle timeout raised. Cluster checks OK: 1 active master, 1 RegionServer, Thrift on `*:9090`. 300 rows / 1187 cells loaded via Thrift. The shell-export reader gives byte-identical results, and the HBase snapshot equals `data/employees.csv` |
