# Observed-outcome benchmark

The benchmark scores the 2005–2024 UK wheat harvests. It compares the yield two years earlier with the median of five prior years ending two years before each forecast year. Both use earlier year values from the same revised historical release.

| Scored cases | Baseline mean loss | Candidate mean loss | Candidate wins | Baseline wins | Ties |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 20 | 0.757330 | 0.522835 | 12 | 4 | 4 |

**Metric:** MAE in tonnes/ha. Lower is better. See [aggregate results](observed-results.json) for the largest regression and breakdowns.

The five-year median reduced average error, although the two-year baseline won on some years. This is a UK annual benchmark. It does not validate farm-level satellite predictions or crop stress detection.

## Reproduce

Save [FAOSTAT wheat yield via Our World in Data](https://ourworldindata.org/grapher/wheat-yields.csv) as `wheat.csv`. The input file SHA-256 is `511cca58ee7e657e38f9880106ca74f3c352d953b9ef813cc41874e04173cb68`. The workbook requires `xlrd`; all benchmarks use `pandas` and `numpy`.

```sh
python replay/observed_backtest.py wheat.csv --output /tmp/observed-results.json
diff -u replay/observed-results.json /tmp/observed-results.json
```
