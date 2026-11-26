# HarvestShield UK decision replay

[Open the interactive portfolio dashboard](https://chrisha-tech.github.io/replay/?project=harvestshield-uk).

Canopy and yield values are simulated. When the feed is degraded the candidate uses weather only. Satellite vision accuracy requires independent field labels and farm- and season-held-out evaluation.

## Reproduce

From the repository root, use Python 3.10+:

```sh
python replay/replay.py --output replay/example.json
python -m unittest discover -s replay -v
```

The committed HTML is a portable snapshot of the bundled report. Open `replay/index.html` directly. The dashboard supports group and scenario filters, case-level scores and CSV export.

## Error analysis on the bundled scenarios

Scores are in **Tonnes/ha absolute error**. Lower is better. Candidate regressions count cases where its score is higher.

| Scenario | Cases | Baseline mean | Candidate mean | Candidate regressions |
| --- | ---: | ---: | ---: | ---: |
| Typical | 30 | 0.541 | 0.228 | 4 |
| Weather stress | 27 | 0.501 | 0.256 | 9 |
| Feed degraded | 27 | 0.550 | 0.550 | 0 |

The largest regression was 0.563 at case 84 (Northern, Typical). The scenarios test software behaviour. They cannot establish real-world accuracy or savings.

## Replay an external archive

Supply a CSV with columns `period,group,scenario,baseline,candidate,actual`. Sort and align predictions and outcomes upstream. Each period/group pair must be unique. Supply genuinely out-of-sample predictions computed from information available at the decision time. The CLI validates input and scores cases. It does not train or backtest the source model for you.

For cost replay, put the realised policy costs in baseline and candidate, and a numeric placeholder in actual. For spill replay, use probabilities in [0,1] and binary outcomes. Other projects use predictions and observed numeric outcomes in the units above.

```sh
python replay/replay.py --input archive.csv --source "Archive name and holdout period" --output report.json
```

## Observed-outcome benchmark

See the [measured benchmark](OBSERVED_BACKTEST.md) for public observations, evaluation rules and results. The interactive synthetic scenarios are separate.
