# Local rehearsal with Docker (optional)

A single-container HBase 2.6.4 in standalone mode, with the Thrift server, so you can run every script for
free before using EMR. HBase 2.6.4 is the same version as `emr-7.14.0`. This is only for practice: the
deliverable must use the EMR run.

```bash
# 💻 from the repository root
docker compose -f local/docker-compose.yml up -d --build     # first build downloads HBase (~355 MB)
docker exec hbase-local bash -c 'echo status | hbase shell -n'   # wait until it shows "1 active master"
```

The repository is mounted at `/repo` inside the container, so the HBase scripts run unchanged. Python
runs on your laptop against `localhost:9090`. Send its outputs to a scratch folder so `results/` stays
reserved for EMR:

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

docker exec -w /repo hbase-local hbase shell -n hbase/01_create_table.hbase 2>/dev/null
.venv/bin/python src/load_hbase.py --method thrift
docker exec -w /repo hbase-local hbase shell -n hbase/02_verify.hbase 2>/dev/null
docker exec -w /repo hbase-local hbase shell -n hbase/03_full_scan.hbase 2>/dev/null > /tmp/scan_emp.txt
docker exec -w /repo hbase-local hbase shell -n hbase/04_activity_b_queries.hbase 2>/dev/null

.venv/bin/python src/analyze.py --source thrift --outdir /tmp/rehearsal
python3 src/analyze.py --source shell --scan-file /tmp/scan_emp.txt --outdir /tmp/rehearsal_shell
```

The HBase web UI is at http://localhost:16010.

To stop the container:

- `docker compose -f local/docker-compose.yml down` stops it and keeps the local data.
- `docker compose -f local/docker-compose.yml down -v` also deletes the local volume. It only affects this
  practice container.
