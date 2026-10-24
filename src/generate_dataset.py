"""Generate the synthetic employee dataset (data/employees.csv).

The dataset is reproducible: it uses a fixed seed, so two runs with the same
parameters produce exactly the same file.

It deliberately includes some data quality problems (missing or invalid
salaries, cities with inconsistent case/whitespace, absent cells) to
demonstrate the explicit handling the assignment requires.

Usage:
    python3 src/generate_dataset.py                # 300 rows, seed 42
    python3 src/generate_dataset.py --rows 500 --seed 7 --out data/other.csv
"""
import argparse
import csv
import random

from config import DATA_DIR

# city -> (sampling weight, salary factor reflecting cost of living)
CITIES = {
    "Lima": (0.24, 0.92),
    "Bogota": (0.20, 0.88),
    "Santiago": (0.16, 1.05),
    "Quito": (0.14, 0.85),
    "Buenos Aires": (0.14, 0.95),
    "Madrid": (0.12, 1.20),
}

# designation -> (sampling weight, base annual salary in USD)
DESIGNATIONS = {
    "Data Analyst": (0.22, 42000),
    "Software Engineer": (0.22, 55000),
    "Administrative Assistant": (0.16, 24000),
    "Data Scientist": (0.12, 62000),
    "Accountant": (0.12, 38000),
    "Project Manager": (0.10, 72000),
    "Director": (0.06, 95000),
}

# ASCII only: HBase stores bytes and the shell prints non-ASCII characters as
# \xNN escape sequences, which makes scan output hard to read.
FIRST_NAMES = [
    "Jose", "Maria", "Luis", "Ana", "Carlos", "Lucia", "Jorge", "Sofia",
    "Miguel", "Valeria", "Pedro", "Camila", "Diego", "Daniela", "Andres",
    "Gabriela", "Fernando", "Paula", "Ricardo", "Carmen", "Javier", "Elena",
    "Raul", "Isabel", "Manuel", "Rosa", "Pablo", "Laura", "Hector", "Natalia",
]
LAST_NAMES = [
    "Garcia", "Rodriguez", "Martinez", "Lopez", "Gonzalez", "Perez",
    "Sanchez", "Ramirez", "Torres", "Flores", "Rivera", "Gomez", "Diaz",
    "Cruz", "Morales", "Reyes", "Gutierrez", "Ortiz", "Chavez", "Ruiz",
    "Mendoza", "Vargas", "Castillo", "Rojas", "Herrera", "Medina", "Aguilar",
    "Silva", "Navarro", "Vega",
]

# Injected quality problems: (kind, number of affected rows).
SALARY_ANOMALIES = [
    ("missing", 8),        # the professional:salary cell does not exist
    ("N/A", 3),
    ("pending", 2),
    ("negative", 2),
    ("zero", 1),
    ("whitespace", 2),     # " 48500 ": valid once whitespace is stripped
]
CITY_VARIANTS = ["LIMA", "LIMA", " lima ", "bogota", "Santiago "]
MISSING_CITY_ROWS = 3
MISSING_DESIGNATION_ROWS = 2


def weighted_choice(rng, options):
    names = list(options)
    weights = [options[name][0] for name in names]
    return rng.choices(names, weights=weights, k=1)[0]


def base_rows(rng, n_rows):
    rows = []
    for i in range(1, n_rows + 1):
        city = weighted_choice(rng, CITIES)
        designation = weighted_choice(rng, DESIGNATIONS)
        base_salary = DESIGNATIONS[designation][1]
        city_factor = CITIES[city][1]
        salary = round(base_salary * city_factor * rng.uniform(0.85, 1.20), -2)
        rows.append({
            # Zero-padded key: HBase sorts rows lexicographically, so this
            # keeps E0010 after E0009.
            "row_key": f"E{i:04d}",
            "name": f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}",
            "city": city,
            "designation": designation,
            "salary": str(int(salary)),
        })
    return rows


def inject_anomalies(rng, rows):
    """Modify randomly chosen (distinct) rows and return a summary."""
    n_needed = (sum(n for _, n in SALARY_ANOMALIES) + len(CITY_VARIANTS)
                + MISSING_CITY_ROWS + MISSING_DESIGNATION_ROWS)
    if n_needed > len(rows):
        raise ValueError(f"At least {n_needed} rows are needed to inject the anomalies")
    targets = iter(rng.sample(range(len(rows)), n_needed))
    summary = []

    for kind, count in SALARY_ANOMALIES:
        for _ in range(count):
            row = rows[next(targets)]
            original = row["salary"]
            row["salary"] = {
                "missing": "",
                "N/A": "N/A",
                "pending": "pending",
                "negative": f"-{original}",
                "zero": "0",
                "whitespace": f" {original} ",
            }[kind]
            summary.append((row["row_key"], "salary", kind))

    for variant in CITY_VARIANTS:
        row = rows[next(targets)]
        row["city"] = variant
        summary.append((row["row_key"], "city", f"variant {variant!r}"))

    for _ in range(MISSING_CITY_ROWS):
        row = rows[next(targets)]
        row["city"] = ""
        summary.append((row["row_key"], "city", "missing"))

    for _ in range(MISSING_DESIGNATION_ROWS):
        row = rows[next(targets)]
        row["designation"] = ""
        summary.append((row["row_key"], "designation", "missing"))

    return sorted(summary)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--rows", type=int, default=300, help="number of employees (default 300)")
    parser.add_argument("--seed", type=int, default=42, help="random seed (default 42)")
    parser.add_argument("--out", default=str(DATA_DIR / "employees.csv"), help="output CSV file")
    args = parser.parse_args()

    rng = random.Random(args.seed)
    rows = base_rows(rng, args.rows)
    anomalies = inject_anomalies(rng, rows)

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["row_key", "name", "city", "designation", "salary"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"{len(rows)} rows written to {args.out} (seed {args.seed})")
    print(f"{len(anomalies)} anomalies injected:")
    for row_key, field, kind in anomalies:
        print(f"  {row_key}  {field:<12} {kind}")


if __name__ == "__main__":
    main()
