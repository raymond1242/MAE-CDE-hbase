#!/bin/bash
set -euo pipefail

start-hbase.sh
hbase-daemon.sh start thrift
echo "HBase started: Thrift on port 9090, web UI on http://localhost:16010"
exec tail -F "$HBASE_HOME"/logs/hbase-*-master-*.log "$HBASE_HOME"/logs/hbase-*-thrift-*.log
