#!/usr/bin/env bash
# Prepare the EMR primary node: Python virtual environment and HBase/Thrift checks.
#
# Run it ON THE PRIMARY NODE, from the repository root:
#   bash infra/setup_primary.sh
set -euo pipefail
cd "$(dirname "$0")/.."
PORT="${HBASE_THRIFT_PORT:-9090}"

# True if something listens on $PORT (awk reads all input, so no SIGPIPE under pipefail).
thrift_listening() {
  ss -ltn 2>/dev/null | awk -v port=":${PORT}" '$4 ~ port"$" {found = 1} END {exit !found}'
}

echo "== HBase version =="
hbase version 2>/dev/null | sed -n 1p || echo "hbase command not found: is HBase installed on this cluster?"

echo "== Python =="
python3 --version

echo "== Python virtual environment (.venv) =="
if ! python3 -m venv .venv 2>/dev/null; then
  sudo dnf install -y python3-pip || sudo yum install -y python3-pip
  python3 -m venv --clear .venv
fi
.venv/bin/python -m pip install --quiet --upgrade pip
.venv/bin/python -m pip install --quiet -r requirements.txt
.venv/bin/python -c "import happybase; print('happybase', happybase.__version__)"

echo "== HBase Thrift server (port ${PORT}) =="
if ! thrift_listening; then
  echo "Thrift is not listening on ${PORT}; trying to start it..."
  sudo systemctl start hbase-thrift 2>/dev/null \
    || sudo -u hbase /usr/lib/hbase/bin/hbase-daemon.sh start thrift
  sleep 10
fi
if thrift_listening; then
  echo "Thrift is listening on ${PORT}"
else
  echo "Thrift is still not listening on ${PORT}. Use the HBase shell fallback (docs/02_step_by_step.md)."
  exit 1
fi

echo "== happybase connection test =="
.venv/bin/python - "$PORT" <<'PY'
import sys
import happybase

conn = happybase.Connection("localhost", int(sys.argv[1]))
print("Tables visible through Thrift:", [t.decode() for t in conn.tables()])
conn.close()
PY
echo "Setup complete. Activate the environment with: source .venv/bin/activate"
