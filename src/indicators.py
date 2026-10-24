"""Data cleaning and indicator computation (the processing done by Python).

HBase only stores bytes: it does not know that 'salary' is a number or that
'LIMA' and 'Lima' are the same city. Those decisions are made here, with
explicit rules and a log of every value that was fixed or discarded.
"""
import re
import statistics
from collections import Counter

from config import MIN_SALARIES_PER_CITY, MISSING_LABEL

# Plain decimal number with '.' as the decimal separator. Ambiguous formats
# ("4,250" may mean 4250 or 4.25 depending on the locale), scientific
# notation, "nan" and "inf" are rejected.
_PLAIN_NUMBER_RE = re.compile(r"^[+-]?\d+(\.\d+)?$")


def parse_salary(raw):
    """Convert the HBase text to a number. Returns (value|None, status, reason).

    status is one of: ok, fixed (usable after cleaning), missing, invalid.
    """
    if raw is None:
        return None, "missing", "cell professional:salary does not exist"
    text = raw.strip()
    if text == "":
        return None, "missing", "empty value"
    if not _PLAIN_NUMBER_RE.match(text):
        return None, "invalid", "not a number"
    value = float(text)
    if value <= 0:
        return None, "invalid", "not positive"
    if text != raw:
        return value, "fixed", "surrounding whitespace removed"
    return value, "ok", ""


def _grouping_key(value):
    return " ".join(value.split()).casefold()


def canonical_labels(values):
    """Group case/whitespace variants ('LIMA', ' lima ', 'Lima').

    Returns {original value: canonical label}. The canonical label is the most
    frequent variant of the group (with extra whitespace removed).
    """
    present = [v for v in values if v is not None and v.strip() != ""]
    variants_by_key = {}
    for value in present:
        variants_by_key.setdefault(_grouping_key(value), Counter())[" ".join(value.split())] += 1
    canonical = {key: variants.most_common(1)[0][0] for key, variants in variants_by_key.items()}
    return {value: canonical[_grouping_key(value)] for value in present}


def clean_records(records):
    """Return (cleaned records, data quality issues found)."""
    city_labels = canonical_labels([r["city"] for r in records])
    designation_labels = canonical_labels([r["designation"] for r in records])
    issues = []
    cleaned = []

    for r in records:
        salary, status, reason = parse_salary(r["salary"])
        if status != "ok":
            issues.append({
                "row_key": r["row_key"], "field": "salary", "original_value": r["salary"],
                "problem": reason,
                "treatment": "numeric value used" if salary is not None else "excluded from salary statistics",
            })

        categories = {}
        for field, labels in (("city", city_labels), ("designation", designation_labels)):
            raw = r[field]
            if raw is None or raw.strip() == "":
                categories[field] = MISSING_LABEL
                issues.append({
                    "row_key": r["row_key"], "field": field, "original_value": raw,
                    "problem": "missing value", "treatment": f"grouped as {MISSING_LABEL}",
                })
            else:
                categories[field] = labels[raw]
                if labels[raw] != raw:
                    issues.append({
                        "row_key": r["row_key"], "field": field, "original_value": raw,
                        "problem": "inconsistent case/whitespace",
                        "treatment": f"normalized to {labels[raw]!r}",
                    })

        cleaned.append({
            "row_key": r["row_key"],
            "name": r["name"],
            "city": categories["city"],
            "designation": categories["designation"],
            "salary": salary,
            "salary_status": status,
        })
    return cleaned, issues


def _salary_stats(salaries):
    if not salaries:
        return {"valid_salaries": 0, "avg_salary": None, "min_salary": None, "max_salary": None}
    return {
        "valid_salaries": len(salaries),
        "avg_salary": round(statistics.mean(salaries), 2),
        "min_salary": min(salaries),
        "max_salary": max(salaries),
    }


def employees_by(cleaned, field):
    """Employee count and share of the total per city or per designation.

    Sorted by count (descending); the UNKNOWN group always goes last.
    """
    total = len(cleaned)
    counts = Counter(r[field] for r in cleaned)
    ordered = sorted(counts.items(), key=lambda kv: (kv[0] == MISSING_LABEL, -kv[1], kv[0]))
    return [{field: group, "employees": n, "percentage": round(100 * n / total, 2)} for group, n in ordered]


def salary_summary(cleaned):
    salaries = [r["salary"] for r in cleaned if r["salary"] is not None]
    statuses = Counter(r["salary_status"] for r in cleaned)
    summary = {
        "total_records": len(cleaned),
        "missing_salaries": statuses["missing"],
        "invalid_salaries": statuses["invalid"],
        "fixed_salaries": statuses["fixed"],
        **_salary_stats(salaries),
    }
    if salaries:
        summary["median_salary"] = round(statistics.median(salaries), 2)
        summary["stdev_salary"] = round(statistics.stdev(salaries), 2) if len(salaries) > 1 else 0.0
    return summary


def salary_by_city(cleaned, min_salaries=MIN_SALARIES_PER_CITY):
    """Salary statistics per city and ranking by average salary.

    Only cities (other than UNKNOWN) with at least min_salaries valid salaries
    are ranked; an average computed from very few values is not comparable.
    """
    by_city = {}
    for r in cleaned:
        by_city.setdefault(r["city"], []).append(r["salary"])

    rows = []
    for city, values in by_city.items():
        stats = _salary_stats([v for v in values if v is not None])
        rows.append({
            "city": city,
            "employees": len(values),
            **stats,
            "meets_minimum": city != MISSING_LABEL and stats["valid_salaries"] >= min_salaries,
            "rank": None,
        })

    ranked = sorted((r for r in rows if r["meets_minimum"]), key=lambda r: -r["avg_salary"])
    for position, row in enumerate(ranked, start=1):
        row["rank"] = position
    return sorted(rows, key=lambda r: (r["rank"] is None, r["rank"] or 0, r["city"]))


def compute_all(records):
    cleaned, issues = clean_records(records)
    by_city_salary = salary_by_city(cleaned)
    ranked = [r for r in by_city_salary if r["rank"] is not None]
    return {
        "cleaned": cleaned,
        "issues": issues,
        "by_city": employees_by(cleaned, "city"),
        "by_designation": employees_by(cleaned, "designation"),
        "salary_summary": salary_summary(cleaned),
        "salary_by_city": by_city_salary,
        "top_city": ranked[0] if ranked else None,
    }
