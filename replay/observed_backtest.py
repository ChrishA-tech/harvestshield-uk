"""Evaluate two fixed rules against recorded outcomes."""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def score(frame, loss="absolute"):
    difference=frame[["baseline", "candidate"]].sub(frame["actual"], axis=0)
    errors=difference.abs() if loss=="absolute" else difference.pow(2)
    gap=errors["candidate"]-errors["baseline"]
    if frame.empty or not np.isfinite(errors.to_numpy()).all():
        raise ValueError("No finite scores for the requested benchmark")
    worst=gap.idxmax()
    return {
        "cases":len(frame),
        "baseline_loss":round(float(errors["baseline"].mean()), 6),
        "candidate_loss":round(float(errors["candidate"].mean()), 6),
        "candidate_wins":int((gap < -1e-9).sum()),
        "baseline_wins":int((gap > 1e-9).sum()),
        "ties":int((gap.abs() <= 1e-9).sum()),
        "largest_candidate_disadvantage":round(float(gap.loc[worst]), 6),
        "worst_case":str(worst),
    }


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input",type=Path)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    try:
        result=evaluate(args.input)
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    except (OSError, ValueError, KeyError, ImportError) as error:
        parser.exit(2,f"Observed benchmark failed: {error}\n")


def evaluate(path):
    data=pd.read_csv(path)
    values=data.loc[data.Code.eq("GBR") & data.Year.ge(1961)].set_index("Year")["Wheat yield"].sort_index()
    if values.index.has_duplicates or len(values)!=values.index.max()-values.index.min()+1:
        raise ValueError("Expected one observed UK yield per year")
    panel=pd.DataFrame({"actual":values,"baseline":values.shift(2),
                        "candidate":values.shift(2).rolling(5).median()})
    test=panel.loc[2005:2024].dropna()
    if len(test)!=20:
        raise ValueError("Expected all 20 held-out harvests")
    return {"source":"FAOSTAT via Our World in Data, UK wheat yield","metric":"MAE in tonnes/ha",
            "baseline":"Yield two years earlier","candidate":"Median of five years through t-2",
            "holdout":[2005,2024],"metrics":score(test),
            "by_period":{"2005–2014":score(test.loc[:2014]),"2015–2024":score(test.loc[2015:])}}


if __name__=="__main__":
    main()
