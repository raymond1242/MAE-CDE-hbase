"""Central project configuration.

If your HBase table uses different column family or qualifier names, change
only COLUMN_MAP (and document the difference in the report). The rest of the
code works with the logical field names (name, city, designation, salary).
"""
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
RESULTS_DIR = REPO_ROOT / "results"

TABLE_NAME = os.environ.get("HBASE_TABLE", "emp")

# logical field -> (column family, qualifier)
COLUMN_MAP = {
    "name": ("personal", "name"),
    "city": ("personal", "city"),
    "designation": ("professional", "designation"),
    "salary": ("professional", "salary"),
}
FIELDS = list(COLUMN_MAP)

# HBase Thrift server (on EMR it runs on the primary node, port 9090).
THRIFT_HOST = os.environ.get("HBASE_THRIFT_HOST", "localhost")
THRIFT_PORT = int(os.environ.get("HBASE_THRIFT_PORT", "9090"))

# Minimum number of valid salaries for a city's average to be considered
# representative when answering "which city has the highest average salary?".
MIN_SALARIES_PER_CITY = 5

# Label used to group records with no city or no designation.
MISSING_LABEL = "UNKNOWN"


def column_name(field):
    """Return 'family:qualifier' for a logical field."""
    family, qualifier = COLUMN_MAP[field]
    return f"{family}:{qualifier}"
