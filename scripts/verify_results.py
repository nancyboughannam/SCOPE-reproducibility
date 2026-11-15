"""Independently recompute archived means, intervals and paired tests from seed rows."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from scipy.stats import t

ROOT = Path(__file__).resolve().parents[1]


def stats(values):
    v = np.asarray(values, dtype=float)
    assert len(v) == 10 and np.isfinite(v).all(), 'Expected ten finite independent seeds'
    mean = v.mean(); se = v.std(ddof=1) / np.sqrt(len(v))
    half = t.ppf(.975, len(v)-1) * se
    p = (1. if mean == 0 else 0.) if se == 0 else 2*t.sf(abs(mean/se), len(v)-1)
    return [mean, mean-half, mean+half, p]


def match(row, values, paired=False):
    actual = stats(values)
    expected = [row['mean'], row['lower'], row['upper']]
    if paired: expected.append(row['p_raw'])
    assert row['n'] == 10
    np.testing.assert_allclose(actual[:len(expected)], expected, rtol=1e-8, atol=2e-12)


def paired_values(a, b, metric):
    assert a.iteration.is_unique and b.iteration.is_unique
    x = a.set_index('iteration')[metric].sort_index()
    y = b.set_index('iteration')[metric].sort_index()
    assert x.index.equals(y.index) and len(x) == 10
    return x.to_numpy()-y.to_numpy()


def check_holm(frame):
    families = frame.groupby('family') if 'family' in frame else [('all', frame)]
    for _, group in families:
        ordered = group.sort_values('p_raw')
        expected = np.maximum.accumulate(np.minimum(1., ordered.p_raw.to_numpy()*np.arange(len(group),0,-1)))
        assert (ordered.family_tests == len(group)).all()
        np.testing.assert_allclose(expected, ordered.p_holm, rtol=1e-8, atol=2e-12)


def main_study(name):
    folder = ROOT / 'results' / name
    rows = pd.read_csv(folder/'study_metrics.csv')
    means = pd.read_csv(folder/'mean_metrics.csv')
    assert len(rows) == 1600 and rows.job.nunique() == 400
    assert not rows.duplicated(['job','application']).any()
    assert set(rows.iteration) == set(range(3401,3411))
    assert set(rows.query("group == 'main'").label) == {'SCOPE','AI_BASED','EXP3_MC','RAIDER_TRAX','RANDOM','SCOPE_STATIC'}
    controls = rows[(rows.group=='main') & (rows.load==1800) & rows.label.isin(['SCOPE','SCOPE_STATIC'])].copy()
    controls['group'] = 'ablation'
    display = pd.concat([rows, controls])
    groups = {k:g for k,g in display.groupby(['group','label','load','application'])}
    for _, row in means.iterrows():
        g = groups[(row['group'],row.label,row.load,row.application)]
        assert g.iteration.is_unique
        match(row, g[row.metric])
    pairs = pd.read_csv(folder/'paired_comparisons.csv')
    data = rows[rows.application=='ALL_APPS']
    for _, row in pairs.iterrows():
        _, comparator = row.comparison.split(' minus ')
        ga = 'adaptation' if row.family=='adaptation' else 'main'
        gb = row.family
        a = data[(data.group==ga)&(data.label=='SCOPE')&(data.load==row.load)]
        b = data[(data.group==gb)&(data.label==comparator)&(data.load==row.load)]
        match(row, paired_values(a,b,row.metric), True)
    check_holm(pairs)
    phases = pd.read_csv(folder/'phase_metrics.csv')
    for _, row in pd.read_csv(folder/'phase_means.csv').iterrows():
        g = phases[(phases.label==row.label)&(phases.phase==row.phase)]
        assert g.iteration.is_unique
        match(row,g[row.metric])
    print(f'{name}: {len(means)} means/intervals, {len(pairs)} paired tests, Holm families and phase summaries verified.')


def delta_study():
    folder=ROOT/'results/delta_t'
    rows=pd.read_csv(folder/'study_metrics.csv')
    assert len(rows)==480 and set(rows.iteration)==set(range(3601,3611))
    assert not rows.duplicated(['scenario','interval_seconds','iteration','application']).any()
    groups={k:g for k,g in rows.groupby(['scenario','interval_seconds','application'])}
    decisions=pd.read_csv(folder/'decision_metrics.csv')
    controllers=[]
    for (scenario,dt,iteration),g in decisions.groupby(['scenario','interval_seconds','iteration']):
        post=g[g.timestamp>=180]
        controllers.append(dict(scenario=scenario,interval_seconds=dt,iteration=iteration,
            decision_epochs=len(g),total_movement=g.movement.sum(),max_step=g.movement.max(),
            changes=(g.movement>1e-9).sum(),postwarmup_total_movement=post.movement.sum(),
            postwarmup_changes=(post.movement>1e-9).sum()))
    controller_groups={k:g for k,g in pd.DataFrame(controllers).groupby(['scenario','interval_seconds'])}
    means=pd.read_csv(folder/'mean_metrics.csv')
    for _,row in means.iterrows():
        g=(controller_groups[(row.scenario,row.interval_seconds)] if row.application=='CONTROLLER'
           else groups[(row.scenario,row.interval_seconds,row.application)])
        match(row,g[row.metric])
    pairs=pd.read_csv(folder/'paired_comparisons.csv')
    assert len(pairs)==18
    for _,row in pairs.iterrows():
        a=groups[(row.scenario,row.interval_seconds,'ALL_APPS')]
        b=groups[(row.scenario,row.reference_seconds,'ALL_APPS')]
        match(row,paired_values(a,b,row.metric),True)
    check_holm(pairs)
    print(f'delta_t: {len(means)} means/intervals and all 18 paired/Holm comparisons verified.')


def guard_comparison():
    folder=ROOT/'results/v5_guard_off'
    pairs=pd.read_csv(folder/'exp3_guard_pairs.csv')
    for name,col in [('v5_guard_off','guard_off'),('v5_guard_on','guard_on')]:
        metrics=pd.read_csv(ROOT/'results'/name/'study_metrics.csv')
        metrics=metrics[(metrics.group=='main')&(metrics.label=='EXP3_MC')].set_index(['load','iteration','application'])
        for _,row in pairs.iterrows():
            assert np.isclose(metrics.loc[(row.load,row.iteration,row.application),row.metric],row[col],rtol=1e-10,atol=1e-12)
    contrasts=pd.read_csv(folder/'exp3_guard_contrasts.csv')
    for _,row in contrasts.iterrows():
        g=pairs[(pairs.load==row.load)&(pairs.metric==row.metric)&(pairs.application=='ALL_APPS')]
        match(row,g.guard_off-g.guard_on,True)
    check_holm(contrasts)
    print('EXP3 routing comparison: paired raw values and all ten Holm tests verified.')


def lambda_calibration():
    folder=ROOT/'results/lambda_calibration'
    data=pd.read_csv(folder/'lambda_metrics.csv')
    assert len(data)==108 and data.job.nunique()==27
    assert not data.duplicated(['job','application']).any()
    assert set(data.iteration)=={3301,3302,3303}
    data=data[data.application=='ALL_APPS']
    summaries=pd.read_csv(folder/'calibration_means.csv')
    for _,row in summaries.iterrows():
        g=data[(data['case']==row['case'])&(data.variant==row.variant)&(data.lambda_value==row.lambda_value)]
        assert len(g)==3 and g.iteration.is_unique and row['n']==3
        v=g[row.metric].to_numpy();mean=v.mean();half=t.ppf(.975,2)*v.std(ddof=1)/np.sqrt(3)
        np.testing.assert_allclose([mean,mean-half,mean+half],[row['mean'],row.lower,row.upper],rtol=1e-8,atol=1e-12)
    print(f'lambda calibration: all 27 scenarios and {len(summaries)} three-seed summary intervals verified.')


if __name__=='__main__':
    main_study('v5_guard_on'); main_study('v5_guard_off')
    delta_study(); guard_comparison(); lambda_calibration()
