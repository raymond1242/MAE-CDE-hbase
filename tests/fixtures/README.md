# Test fixtures

`scan_sample.txt` is real output of `hbase shell -n` running `scan 'fx'` on HBase 2.6.4
(the local Docker environment in `local/`). The table `fx` was built to cover the parser's
edge cases: a value with surrounding whitespace (`' lima '`), an absent cell (T0002 has no
salary), a UTF-8 value escaped as `\xC3\xA1`, a value with a quote and a comma, and an extra
qualifier (`personal:nickname`) that the analysis must ignore.
