# 02 · Step by step

This runbook takes the assignment from an empty AWS account to the finished report. Every step that
produces evidence saves it under `results/`, so the results are recorded as you go. Tick the boxes as you
complete them.

Conventions:

- 💻 means the command runs on your **laptop**, from the repository root.
- ☁️ means it runs on the **EMR primary node**, from `~/MAE-CDE-hbase`.

---

## Step 0 · Prerequisites

- [x] Personal AWS account, signed in to the console, region chosen (see [01_emr_setup.md](01_emr_setup.md#step-1--choose-the-region))
- [x] EC2 key pair downloaded and protected with `chmod 400` (see [01_emr_setup.md](01_emr_setup.md#step-2--create-the-ec2-key-pair))
- [x] 💻 Unit tests pass: `python3 -m unittest discover -s tests -v`

## Step 1 · (Optional) Rehearse locally with Docker

This step is free and takes about 5 minutes. It runs the same scripts against HBase 2.6.4 in Docker. See
[local/README.md](../local/README.md). Write the rehearsal outputs outside `results/`, which is reserved
for the EMR run.

## Step 2 · Create the EMR cluster

Follow [01_emr_setup.md](01_emr_setup.md) in the AWS console.

- [x] Network checked: default VPC and a public subnet with a `0.0.0.0/0 → igw-…` route (guide step 3)
- [x] Cluster created with that VPC and subnet (guide step 4)
- [x] Status is **Waiting** (guide step 5), and an SSH rule for **My IP** exists on the primary security
      group (guide step 6)
- [x] `ssh` works and `echo "status" | hbase shell -n` shows 1 active master and 1 server (guide step 7).
      2026-10-24, `us-east-2`: `HBase 2.6.4-amzn-2`, `1 active master, 0 backup masters, 1 servers, 0
      dead`, Thrift listening on `*:9090`
- [x] Idle time set to **3 hours** (**Properties → Cluster termination and node replacement → Edit**).
      With HBase, auto-termination does not count SSH or shell use as activity (guide 4.5)
- [ ] **Capacity** shows *1 Primary, 1 Core*, with no Task (guide troubleshooting)
- [x] Write down the cluster ID (`j-…`) and the primary public DNS: `j-00430072CCSGFQ8WWNLK`,
      `ec2-3-146-152-59.us-east-2.compute.amazonaws.com`

```bash
# 💻 keep these handy for the next steps
export KEY=~/.ssh/emr-hbase-key.pem
export PRIMARY=ec2-xx-xx-xx-xx.compute-1.amazonaws.com
```

## Step 3 · Copy the repository to the primary node

```bash
# 💻 package the repository without the local venv/.git and send it
# (--no-xattrs and COPYFILE_DISABLE=1 keep macOS metadata out, so Linux tar extracts without warnings)
COPYFILE_DISABLE=1 tar czf /tmp/mae-cde-hbase.tgz --no-xattrs --exclude .venv --exclude .git --exclude local --exclude .DS_Store .
scp -i "$KEY" /tmp/mae-cde-hbase.tgz hadoop@"$PRIMARY":~
ssh -i "$KEY" hadoop@"$PRIMARY" 'mkdir -p MAE-CDE-hbase && tar xzf mae-cde-hbase.tgz -C MAE-CDE-hbase'
ssh -i "$KEY" hadoop@"$PRIMARY"
```

If you have pushed the repository to GitHub, cloning it on the primary node works too:
☁️ `sudo dnf install -y git && git clone https://github.com/<user>/MAE-CDE-hbase.git`.

- [x] ☁️ `cd ~/MAE-CDE-hbase && ls` shows `src/`, `hbase/`, `data/`, …

## Step 4 · Prepare the node, create the table and load the data

```bash
# ☁️ Python venv + happybase, checks that Thrift listens on 9090 and that happybase connects
bash infra/setup_primary.sh
source .venv/bin/activate

# ☁️ record the environment for the report
hbase version 2>/dev/null | sed -n 1p | tee results/raw/00_hbase_version.txt

# ☁️ create table 'emp' (idempotent: re-running it leaves an existing table untouched)
hbase shell -n hbase/01_create_table.hbase 2>/dev/null

# ☁️ load the 300 employees through Thrift
python3 src/load_hbase.py --method thrift
# expected: 300 rows and 1187 cells written to 'emp' via Thrift (localhost:9090)
```

- [x] `setup_primary.sh` ends with "Setup complete". 2026-10-24: Python 3.9.25, happybase 1.2.0, Thrift
      listening on 9090, and the connection test shows `[]` (no tables yet)
- [x] The table was created (`Created table emp`) and `describe` shows the `personal` and `professional`
      families
- [x] The load reports **300 rows and 1187 cells**. That is 1200 minus the 13 cells left empty on
      purpose.

<details>
<summary>Fallback when Thrift or happybase is not available</summary>

```bash
# ☁️ generate a script of put commands (standard library only, no venv needed) and run it
python3 src/load_hbase.py --method shell-script
hbase shell -n hbase/generated/load_data.hbase 2>/dev/null | tail -3      # ends with: 300 row(s)
```
</details>

## Step 5 · HBase shell: Activity A and the HBase side of Activity B

```bash
# ☁️ Activity A: describe, count, sample rows, get, and per-column counts
hbase shell -n hbase/02_verify.hbase 2>/dev/null | tee results/raw/02_verify.txt

# ☁️ Activity A.2: full scan 'emp' (also the input of the fallback reader)
hbase shell -n hbase/03_full_scan.hbase 2>/dev/null > results/raw/scan_emp.txt
tail -3 results/raw/scan_emp.txt                       # 300 row(s)

# ☁️ Activity B as far as HBase can go by itself: filtered counts, range scans, get
hbase shell -n hbase/04_activity_b_queries.hbase 2>/dev/null | tee results/raw/04_activity_b_queries.txt
```

- [x] `02_verify.txt`: `count 'emp'` = 300, and the per-column counts show which cells are missing (name
      300, city 297, designation 298, salary 292)
- [x] `scan_emp.txt` ends with `300 row(s)`
- [x] `04_activity_b_queries.txt` contains the counts per city and designation

[03_hbase_commands.md](03_hbase_commands.md) explains what each command shows and why some HBase counts
differ from the Python ones.

The HBase shell wraps long lines to the terminal width **only when it prints to the terminal**: see the
`describe` output in step 4. With `> file` or `| tee`, stdout is not a terminal, so the saved files keep
one cell per line, which is what the parsers expect.

## Step 6 · Python: retrieve from HBase and compute the indicators

```bash
# ☁️ main method: happybase over Thrift
python3 src/analyze.py --source thrift
```

<details>
<summary>Fallback: parse the scan export from step 5 instead</summary>

```bash
# ☁️ standard library only
python3 src/analyze.py --source shell --scan-file results/raw/scan_emp.txt
```
</details>

- [x] The console shows the total (300), the largest city, the salary statistics and the city with the
      highest average salary
- [x] `results/` now contains `emp_snapshot.csv`, `extraction_metadata.json`, `01`–`05_*.csv` and
      `results.md`
- [x] (Optional, recommended) Also run the fallback with a separate output folder and confirm both
      methods agree:
      `python3 src/analyze.py --source shell --scan-file results/raw/scan_emp.txt --outdir /tmp/shell_check && diff results/01_employees_by_city.csv /tmp/shell_check/01_employees_by_city.csv && echo identical`

## Step 7 · Bring the results back, fill the report, commit

```bash
# 💻 copy results/ from the primary node into the local repository. results/README.md is excluded
#    because the copy on the cluster is older than your local one, which holds the run log.
ssh -i "$KEY" hadoop@"$PRIMARY" 'cd MAE-CDE-hbase && tar czf - --exclude README.md results' | tar xzf -

# 💻 fill the result tables of deliverable/REPORT.md from results/
python3 src/build_report.py

# 💻 record the run
git add results deliverable/REPORT.md
git commit -m "Add results of the EMR run"
```

- [x] Fill in the cluster ID, release and HBase version in section 1 of `deliverable/REPORT.md`, and in
      the run log in `results/README.md`
- [x] No `_Pendiente_` placeholders remain in sections 2–4 of the report

## Step 8 · Terminate the cluster

In the console: **Amazon EMR → Clusters → `practica2-hbase` → Terminate** (see
[01_emr_setup.md](01_emr_setup.md#terminate-the-cluster)).

- [ ] The cluster status is **Terminated**, so billing has stopped. Do not rely on auto-termination: with
      HBase it is only a safety net

## Step 9 · Interpretation and submission

- [x] Write the interpretation (5–10 lines, in Spanish) in section 5 of `deliverable/REPORT.md`, based on
      the tables in section 4
- [ ] Review the conceptual answers in section 6
- [ ] Export the report to PDF, using either method:
  - VS Code with the *Markdown PDF* extension: open `deliverable/REPORT.md` → `Markdown PDF: Export (pdf)`
  - pandoc: `pandoc deliverable/REPORT.md -o deliverable/REPORT.pdf`
- [ ] Submit the PDF, plus the repository (or a zip) with `src/`, `hbase/` and `results/`
