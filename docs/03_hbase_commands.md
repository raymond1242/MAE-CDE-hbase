# 03 · HBase shell commands used

All commands live in the scripts under [`hbase/`](../hbase/) and run non-interactively:

```bash
hbase shell -n hbase/<script>.hbase 2>/dev/null
```

- `-n` (non-interactive) stops at the first error with a non-zero exit code.
- `2>/dev/null` hides the Java logging noise.
- When it runs a file, the shell echoes each command with its prompt (`hbase:012:0> count 'emp'`), so
  the saved output shows which command produced each result.

The sample outputs below come from the local rehearsal on HBase 2.6.4 with the same dataset, so the EMR
run should print the same numbers.

## Table creation: `01_create_table.hbase`

```ruby
create 'emp', {NAME => 'personal', VERSIONS => 1}, {NAME => 'professional', VERSIONS => 1} unless exists 'emp'
```

- A table is declared only with its **column families**. Qualifiers (`name`, `city`, `designation`,
  `salary`) are created implicitly by the first `put` that uses them.
- `VERSIONS => 1` keeps only the latest value of each cell. Reloading the data overwrites cells instead of
  piling up versions.
- `unless exists 'emp'` makes the script safe to re-run. The project never uses `drop` or `truncate`.

## Activity A: `02_verify.hbase` and `03_full_scan.hbase`

| Command | What it shows |
|---|---|
| `describe 'emp'` | The table is ENABLED, with families `personal` and `professional` and their settings (VERSIONS, TTL, BLOOMFILTER…). No qualifiers are listed, because HBase has no schema below the family. |
| `count 'emp'` | 300 rows. HBase counts by scanning, since it keeps no row counter. |
| `scan 'emp', {LIMIT => 3}` | The first 3 rows, one line per cell: `row column=family:qualifier, timestamp=…, value=…` |
| `get 'emp', 'E0001'` | One row, read directly by its key |
| `count 'emp', {COLUMNS => ['professional:salary']}` | Only rows that **have** that cell: 292, so 8 rows have no salary. Same idea for the other columns: name 300, city 297, designation 298. |
| `scan 'emp'` (03) | The full table, about 1,190 lines. This is the evidence for A.2 and the input of the fallback reader. |

```
hbase:016:0> get 'emp', 'E0001'
COLUMN  CELL
 personal:city timestamp=2026-10-24T04:29:31.595, value=Quito
 personal:name timestamp=2026-10-24T04:29:31.595, value=Sofia Gonzalez
 professional:designation timestamp=2026-10-24T04:29:31.595, value=Data Analyst
 professional:salary timestamp=2026-10-24T04:29:31.595, value=33800
1 row(s)
```

## Activity B: `04_activity_b_queries.hbase`

| Question | What HBase can do by itself | What Python adds (`src/indicators.py`) |
|---|---|---|
| Q1 employees per city | One `count` per city with `SingleColumnValueFilter` | Normalizes `LIMA`/`' lima '`, finds the distinct cities, groups missing values as `UNKNOWN` |
| Q2 % per city | Only the total (`count 'emp'`) | `count / total × 100` |
| Q3 avg/min/max salary | Returns the raw text values | Converts them to numbers, excludes missing/invalid values, computes the statistics |
| Q4 employees per designation | One `count` per designation | Same grouping as Q1 |
| Q5 city with the highest average | Nothing, because there is no grouping or averaging | Groups, averages, applies a minimum sample size, ranks |

### Filtered counts (Q1, Q4)

```ruby
count 'emp', {COLUMNS => ['personal:city'],
              FILTER => "SingleColumnValueFilter('personal', 'city', =, 'binary:Lima', true, true)"}
```

- The filter runs **on the RegionServer**, so only matching rows travel to the client.
- `binary:Lima` compares the bytes exactly.
- The first `true` (`filterIfMissing`) drops rows that have no `personal:city`. Without it, a row with no
  city would pass every city filter.
- The second `true` tests only the latest version of the cell.

The result is 64 for Lima, while Python counts 67. The difference is the rows stored as `LIMA` and
`' lima '`. A case-insensitive substring filter finds all 67:

```ruby
scan 'emp', {COLUMNS => ['personal:city'], FILTER => "ValueFilter(=, 'substring:lima')"}
```

### Text comparison is not numeric (Q3)

```ruby
scan 'emp', {COLUMNS => ['professional:salary'],
             FILTER => "SingleColumnValueFilter('professional', 'salary', >, 'binary:90000', true, true)"}
```

```
 E0009 column=professional:salary, ..., value=98000
 E0078 column=professional:salary, ..., value=pending
 E0166 column=professional:salary, ..., value=N/A
 ...
9 row(s)
```

HBase compares salaries as byte strings:

- `pending` and `N/A` sort after `90000`, because letters come after digits, so they are returned.
- `105000` sorts before `90000`, because `'1' < '9'`, so salaries of 100,000 or more are missed.

There are 8 numeric salaries above 90,000, but the filter returns 9 rows, 5 of them not numbers. This is
why salaries are converted to numbers in Python before computing statistics. (HBase's
`AggregateImplementation` coprocessor can average only cells stored as 8-byte longs, not text.)

### `get` vs `scan` (conceptual question 2)

```ruby
get  'emp', 'E0042'                                       # one known row, direct lookup by key
scan 'emp', {STARTROW => 'E0100', STOPROW => 'E0105'}     # contiguous key range: E0100 … E0104
```

Because row keys are stored sorted and zero-padded, the range scan reads only those 5 rows instead of the
whole table.

## Other useful commands (not needed for the deliverable)

| Command | Use |
|---|---|
| `list` | All tables |
| `status` | Cluster health: active master, number of RegionServers |
| `scan 'emp', {COLUMNS => ['personal:name'], LIMIT => 5}` | Projection: read only one column |
| `scan 'emp', {FILTER => "PrefixFilter('E01')"}` | Rows whose key starts with `E01` |
| `get 'emp', 'E0001', 'professional:salary'` | A single cell |
| `exists 'emp'` | Whether the table exists |
