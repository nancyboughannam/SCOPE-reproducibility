"""Export the three-seed lambda calibration as mean +/- sample SD (not CI)."""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data',type=Path,default=ROOT/'results/lambda_calibration')
    args=p.parse_args()
    status=json.loads((args.data/'completion.json').read_text())
    plan=json.loads((args.data/'study.json').read_text())
    assert status['complete'] and status['completed']==status['expected']==27
    assert plan['iterations']==[3301,3302,3303] and plan['r_max']==.15
    frame=pd.read_csv(args.data/'lambda_metrics.csv')
    frame=frame[(frame.application=='ALL_APPS')&(frame.variant=='adaptive')]
    columns=['failure_pct','service_seconds','changes','total_movement','max_step']
    rows=[]
    for case in ['steady','burst']:
        for value in [0.,.01,.05]:
            group=frame[(frame['case']==case)&(frame.lambda_value==value)]
            assert set(group.iteration)=={3301,3302,3303} and len(group)==3
            row=dict(scenario=case,lambda_value=value,n=3)
            for name in columns:
                assert np.isfinite(group[name]).all()
                row[name+'_mean']=group[name].mean(); row[name+'_sd']=group[name].std(ddof=1)
            rows.append(row)
    out=ROOT/'outputs'/('calibration_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    out.mkdir(parents=True)
    pd.DataFrame(rows).to_csv(out/'lambda_calibration_table.csv',index=False)
    lines=[r'\begin{tabular}{llrrrrr}',r'Case & $\lambda$ & Failure (\%) & Service (s) & Updates & Total movement & Maximum step \\',r'\hline']
    for row in rows:
        cells=[row['scenario'],f"{row['lambda_value']:.2f}"]
        for name in columns:
            digits=2 if name=='changes' else 4
            cells.append(f"${row[name+'_mean']:.{digits}f} \\pm {row[name+'_sd']:.{digits}f}$")
        lines.append(' & '.join(cells)+r' \\')
    lines.append(r'\end{tabular}')
    (out/'lambda_calibration_table.tex').write_text('\n'.join(lines)+'\n')
    print('CALIBRATION TABLE: '+str(out))
    print('Means +/- sample SD across three development seeds. Movement includes warm-up. No new parameter selection.')


if __name__=='__main__':main()
