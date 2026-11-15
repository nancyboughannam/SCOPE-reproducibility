"""Evaluate the six frozen predictors and export the ORIGINAL corrected Table 4."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from xgboost import XGBRegressor

ROOT=Path(__file__).resolve().parents[1]


def main():
    models=ROOT/'FLaskAPIs/scope_candidate_xgboost_results'
    data=ROOT/'FLaskAPIs/scope_candidate_dataset'
    manifest=json.loads((models/'model_manifest.json').read_text())
    for split,digest in manifest['split_sha256'].items():
        assert hashlib.sha256((data/f'candidate_dataset_{split}.csv').read_bytes()).hexdigest()==digest
    frames={s:pd.read_csv(data/f'candidate_dataset_{s}.csv') for s in ['train','validation','test']}
    for a,b in [('train','validation'),('train','test'),('validation','test')]:
        assert not set(frames[a].run_id)&set(frames[b].run_id), 'Run leakage'
    assert set(frames['test'].run_id)=={'iteration_3006','iteration_3007'}
    predictions=pd.read_csv(models/'test_predictions.csv')
    archived=pd.read_csv(models/'model_metrics.csv')
    rows=[]
    for spec in manifest['models']:
        app=spec['app_id']; target=spec['target']
        f=frames['test'][frames['test'].app_id==app]
        saved=predictions[predictions.app_id==app]
        assert len(f)==len(saved)==550
        keys=['run_id','num_devices','window_id','app_id']
        assert f[keys].reset_index(drop=True).equals(saved[keys].reset_index(drop=True)), 'Test row alignment changed'
        model=XGBRegressor();model.load_model(models/spec['model_file'])
        y=f[spec['target_column']].to_numpy()
        pred=np.clip(model.predict(f[spec['features']]),0,1 if target=='failure_rate' else None)
        np.testing.assert_allclose(pred,saved['predicted_'+target],rtol=1e-6,atol=1e-7)
        state=saved['state_only_predicted_'+target]
        values=[mean_absolute_error(y,pred),mean_absolute_error(y,state),np.sqrt(mean_squared_error(y,pred)),r2_score(y,pred)]
        original=archived[(archived.app_id==app)&(archived.target==target)&(archived.split=='test')]
        c=original[original.model_type=='candidate_aware_xgboost'].iloc[0]
        s=original[original.model_type=='state_only_xgboost'].iloc[0]
        np.testing.assert_allclose(values,[c.mae,s.mae,c.rmse,c.r2],rtol=2e-5,atol=1e-7)
        rows.append(dict(application=['Traffic Management','Danger Assessment','Infotainment'][app],
                         target=target,rows=550,candidate_mae=values[0],state_mae=values[1],rmse=values[2],r2=values[3]))
    out=ROOT/'outputs'/('table4_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    out.mkdir(parents=True)
    table=pd.DataFrame(rows);table.to_csv(out/'table4.csv',index=False)
    lines=[r'\begin{tabular}{llrrrr}',r'Application & Target & Candidate MAE & State MAE & RMSE & $R^2$ \\',r'\hline']
    for row in rows:
        label='Failure rate' if row['target']=='failure_rate' else 'Normalized service time'
        lines.append(f"{row['application']} & {label} & {row['candidate_mae']:.6f} & {row['state_mae']:.6f} & {row['rmse']:.6f} & {row['r2']:.4f} "+r'\\')
    lines.append(r'\end{tabular}')
    (out/'table4.tex').write_text('\n'.join(lines)+'\n')
    print(table.to_string(index=False));print('TABLE 4 VERIFIED: '+str(out))
    print('Candidate predictions recomputed from frozen models. State-only values checked from archived held-out predictions; use the separate train command to refit those controls.')


if __name__=='__main__':main()
