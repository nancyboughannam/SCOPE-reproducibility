#!/usr/bin/env python3
"""Isolated, resumable sensitivity study of the final SCOPE controller's interval.

No repository files, source-study results or trained models are modified.
Only a copied Java constant becomes a validated JVM property (default: 60 s).
The original implementation couples its planning and telemetry windows. This
study retains that behavior and its frozen 60-second-trained predictors.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from contextlib import contextmanager
import csv
from datetime import datetime, timezone
import difflib
import fcntl
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import statistics
import subprocess
import sys
import time
import urllib.request
import zipfile

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE / 'support'))
import run_deadline_pilot as core

WORKFLOW = 'scope_delta_t_fixed_model_v1'
REPO = BASE.parent
DEFAULT_OUTPUT = REPO / 'ThreeBrains/sim_results/v5_delta_t_3601_3610'
JAVA_SOURCE = Path('runtime/src/edu/boun/edgecloudsim/applications/sample_app5/VehicularEdgeOrchestrator.java')
SCALES = [.9, .8, .8, .8, 75., 75., 75.]
METRICS = ['failure_pct', 'service_seconds']
SOURCE_WORKFLOWS = ['scope_confirmatory_v1', 'exp3_guard_ablation_v1']
JAVA_OLD = '    private static final double DELTA_T = 60.0;'
JAVA_NEW = '''    // Registered interval sensitivity: default preserves the final 60 s controller.
    private static final double DELTA_T = checkedPlanningInterval();

    private static double checkedPlanningInterval() {
        double value = Double.parseDouble(System.getProperty("scope.planningIntervalSeconds", "60"));
        if (!Double.isFinite(value) || (value != 15.0 && value != 30.0
                && value != 60.0 && value != 90.0)) {
            throw new IllegalArgumentException("Planning interval must be 15, 30, 60 or 90 seconds");
        }
        return value;
    }'''


def protocol(profile):
    smoke = profile == 'smoke'
    return dict(workflow=WORKFLOW, profile=profile,
        purpose='workflow validation only' if smoke else 'post-confirmation sensitivity of the frozen final controller; not interval selection',
        intervals_seconds=[15, 30, 60, 90], reference_interval_seconds=60,
        iterations=[3691] if smoke else list(range(3601, 3611)),
        cases=[dict(name='steady_900', load=900, burst=False),
               dict(name='steady_1800', load=1800, burst=False),
               dict(name='shift_1200', load=1200, burst=True)],
        minutes=8 if smoke else 60, warmup_minutes=3, activity_start_seconds=10,
        shift_seconds=240 if smoke else 1200,
        recovery_seconds=360 if smoke else 2400, rate_multiplier=1.5,
        lambda_value=.01, r_max=.15, routing_schema=core.SCHEMA,
        seed_base=20260828, training_window_seconds=60, retraining=False,
        window_semantics='Native reporting counters reset at every planner call; count and lag-count features therefore change scale with the interval. No rate rescaling, rolling-window redesign or interval-specific retraining is performed.',
        movement_semantics='Rmax 0.15 and lambda 0.01 apply per update, not per second. Short intervals offer more decisions and a larger possible cumulative movement budget per simulated hour.',
        inference=dict(primary_metrics=METRICS, replicates='simulation iterations, not tasks or windows',
            confidence_intervals='two-sided pointwise 95% Student t intervals across seeds; paired intervals for differences',
            comparisons='each of 15, 30 and 90 seconds minus 60, in each of three cases, for both primary metrics',
            multiplicity='one prespecified Holm family of 18 two-sided paired t tests; confidence intervals remain unadjusted',
            secondary='per-application metrics and configuration movement are descriptive',
            stopping='Complete all registered jobs regardless of performance; safe interruption is not a statistical stopping rule'),
        interpretation='Sensitivity of this frozen controller with coupled planning/measurement windows. Does not isolate adaptation speed, validate predictors at other horizons, establish a universal optimum or justify retuning the completed main study.')


def jobs(plan):
    return [dict(key=f"{case['name']}_dt{dt}_i{i}", case=case['name'], load=case['load'],
                 burst=case['burst'], interval_seconds=dt, iteration=i)
            for i in plan['iterations'] for case in plan['cases'] for dt in plan['intervals_seconds']]


def times(plan, job):
    dt = job['interval_seconds']
    return list(range(plan['activity_start_seconds'] + dt, plan['minutes'] * 60, dt))


def patch_java(text):
    core.require(text.count(JAVA_OLD) == 1, 'Unsupported Java source; expected the audited 60-second constant exactly once')
    return text.replace(JAVA_OLD, JAVA_NEW, 1)


def non_nested(source, out):
    core.require(source != out and source not in out.parents and out not in source.parents,
                 'Source and output must be separate, non-nested directories')


def default_source():
    # Both studies use identical SCOPE code, inputs and models. EXP3 is not run.
    for name in ['v5_exp3_guard_off_3401_3410', 'v5_final_3401_3410']:
        p = REPO / 'ThreeBrains/sim_results' / name
        if (p / JAVA_SOURCE).is_file():
            return p
    raise RuntimeError('Cannot locate the frozen final runtime. Use --source-study /full/path/to/v5_final_3401_3410. A review ZIP alone omits the runtime and cannot be used.')


def bundle_hashes():
    names = ['run_delta_t_study.py', 'support/run_deadline_pilot.py', 'audited_source_hashes.json',
             'plot_delta_t_results.m', 'figure_delta_t.tex', 'START_HERE.txt']
    return {n: core.sha(BASE / n) for n in names}


def load_plan(out):
    core.require((out / 'study.json').is_file(), 'Run prepare first for this output')
    plan = core.read(out / 'study.json')
    core.require(plan.get('workflow') == WORKFLOW, 'This is not a Delta T study output')
    core.require((out / 'study_checksum.txt').read_text().strip() == core.sha(out / 'study.json'),
                 'Registered protocol changed. Preserve it and prepare a new output.')
    return plan


def validate(out, plan):
    core.require(plan['output'] == str(out), 'Resume in the original output location')
    core.require(core.versions() == plan['package_versions'], 'Python package versions changed; use the original virtual environment')
    core.verify(BASE, plan['runner_hashes'])
    core.verify(out, plan['input_hashes'])
    core.require(core.sha(Path(plan['java'])) == plan['java_sha256'], 'Java executable changed; prepare a new output')


def environment(out, folder, plan):
    e = core.env()
    e.update(SCOPE_RESULTS_DIR=str(out / 'models'),
        SCOPE_CANDIDATE_DATASET=str(out / 'dataset/candidate_dataset_train.csv'),
        SCOPE_DIAGNOSTIC_DIR=str(folder / 'diagnostics'), SCOPE_ABLATION_RESULTS_DIR=str(folder / 'scope'),
        SCOPE_HARD_STABILITY='1', SCOPE_LAMBDA=str(plan['lambda_value']),
        SCOPE_R_MAX=str(plan['r_max']), SCOPE_PORT='5002', SCOPE_W_FAILURE='.5', SCOPE_W_SERVICE='.5')
    return e


def prepare(out, args):
    if (out / 'study.json').exists():
        plan = load_plan(out); validate(out, plan)
        core.require(args.profile is None or args.profile == plan['profile'], 'Profile differs; use a different output')
        if args.source_study:
            core.require(str(args.source_study.expanduser().resolve()) == plan['source_study'], 'Source differs')
        print('Already prepared: ' + str(out), flush=True)
        return
    core.require(not any(p.name != '.runner.lock' for p in out.iterdir()),
                 'Incomplete preparation retained. Use a new empty --output directory.')
    source = (args.source_study or default_source()).expanduser().resolve()
    non_nested(source, out)
    audit = core.read(BASE / 'audited_source_hashes.json')
    plan = protocol(args.profile or 'full')
    core.require(core.versions() == audit['package_versions'],
                 'Use the .venv-revision environment from the final study; dependency versions differ')
    core.port_available()
    core.require((source / '.runner.lock').is_file(), 'Source study lock is missing. Use the original complete study folder, not an extracted review ZIP.')
    with (source / '.runner.lock').open('r') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_SH | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError('Stop the source study before copying its frozen inputs') from exc
        old = core.read(source / 'study.json')
        core.require(old.get('workflow') in SOURCE_WORKFLOWS and old.get('profile') == 'full', 'Expected the full final study or its EXP3 routing ablation')
        core.require((source / 'study_checksum.txt').read_text().strip() == core.sha(source / 'study.json'), 'Source protocol checksum differs')
        core.require(old['lambda_value'] == .01 and old['r_max'] == .15 and old['routing_schema'] == core.SCHEMA, 'Source controller settings differ')
        core.require(not set(plan['iterations']) & set(old['iterations']), 'Sensitivity and final study seeds overlap')
        core.verify(source, audit['hashes'])
        core.write(out / 'preparing.json', dict(source=str(source), profile=plan['profile']))
        # Copy only audited files. Ignore unrelated files in the user's repository.
        for name in audit['hashes']:
            core.check_stop(out)
            target = out / name; target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source / name, target)
        core.verify(out, audit['hashes'])
        for name in ['study.json', 'study_checksum.txt']:
            target = out / 'source_provenance' / name; target.parent.mkdir(exist_ok=True)
            shutil.copy2(source / name, target)
        plan.update(source_study=str(source), source_study_sha256=core.sha(source / 'study.json'),
                    audited_source_hashes=audit['hashes'])
    manifest = core.read(out / 'models/model_manifest.json')
    core.require(manifest['routing_schema'] == core.SCHEMA and manifest['telemetry_schema'] == 'vm_percent_all_vms_v1', 'Model schema differs')
    # Fresh seeds must not occur in ANY model split or static calibration.
    core.require(not set(plan['iterations']) & set(range(3001, 3011)) and
                 not set(plan['iterations']) & {3201, 3202, 3301, 3302, 3303}, 'Sensitivity overlaps model/development seeds')
    original = (out / JAVA_SOURCE).read_text()
    revised = patch_java(original)
    (out / 'source_provenance/original_VehicularEdgeOrchestrator.java').write_text(original)
    (out / JAVA_SOURCE).write_text(revised)
    (out / 'source_provenance/interval.patch').write_text(''.join(difflib.unified_diff(
        original.splitlines(True), revised.splitlines(True), fromfile='original/'+str(JAVA_SOURCE), tofile='isolated/'+str(JAVA_SOURCE))))
    java = core.select_java(args.java)
    print('Compiling isolated Java classes with ' + java, flush=True)
    classes = out / 'runtime/classes'; classes.mkdir()
    libraries = os.pathsep.join(map(str, sorted((out / 'runtime/lib').glob('*.jar'))))
    core.managed([java, '-m', 'jdk.compiler/com.sun.tools.javac.Main', '-classpath', libraries,
        '-sourcepath', out / 'runtime/src', '-d', classes,
        out / 'runtime/src' / (core.MAIN.replace('.', '/') + '.java')], out / 'compile.log', out)
    plan.update(java=java, java_sha256=core.sha(Path(java)), python=sys.executable,
                package_versions=core.versions(), output=str(out), created=datetime.now(timezone.utc).isoformat(),
                runner_hashes=bundle_hashes())
    core.managed([sys.executable, '-c', 'import ml_optimizer_service as s; assert len(s.MODELS)==6; assert len(s.CANDIDATE_CATALOGUE)==1408; print("Six frozen models and 1408 catalogue entries verified")'],
                 out / 'preflight.log', out, cwd=out / 'runtime/services', environ=environment(out, out / 'preflight', plan))
    for name in plan['runner_hashes']:
        dest = out / 'setup' / name; dest.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(BASE / name, dest)
    (out / 'matlab').mkdir()
    shutil.copy2(BASE / 'plot_delta_t_results.m', out / 'matlab/plot_delta_t_results.m')
    shutil.copy2(BASE / 'figure_delta_t.tex', out / 'matlab/figure_delta_t.tex')
    plan['input_hashes'] = {str(p.relative_to(out)):core.sha(p)
        for d in ['runtime', 'inputs', 'models', 'dataset', 'source_provenance', 'setup', 'matlab']
        for p in sorted((out / d).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
    core.write(out / 'study.json', plan)
    (out / 'study_checksum.txt').write_text(core.sha(out / 'study.json') + '\n')
    print(f"PREPARED: {len(jobs(plan))} scenarios; intervals 15, 30, 60, 90 seconds.\n"
          f"Frozen models; lambda=0.01; Rmax=0.15; profile={plan['profile']}.\n{out}\n"
          'No simulation started. Source code, models and results were not replaced.', flush=True)


@contextmanager
def service(out, folder, plan):
    core.port_available(); server = None
    with (folder / 'service.log').open('w') as log:
        try:
            server = subprocess.Popen([sys.executable, '-u', str(out / 'runtime/services/scope_lambda_service.py')],
                cwd=out / 'runtime/services', env=environment(out, folder, plan), stdout=log, stderr=log, start_new_session=True)
            end = time.monotonic() + 60
            while True:
                core.check_stop(out)
                core.require(server.poll() is None, 'Service exited: ' + str(folder / 'service.log'))
                try:
                    with urllib.request.urlopen('http://127.0.0.1:5002/health', timeout=1) as response:
                        health = json.load(response)
                except (OSError, ValueError):
                    core.require(time.monotonic() < end, 'Service readiness timeout'); time.sleep(.2); continue
                core.require(health['routing_schema'] == core.SCHEMA and health['lambda'] == .01
                    and health['r_max'] == .15 and health['hard_stability_enabled']
                    and health.get('lambda_check_wrapper') == 1 and health.get('freeze_after_seconds') is None
                    and health['normalization'] == core.read(out / 'models/model_manifest.json')['normalization'],
                    'Service settings differ from the registered controller')
                core.write(folder / 'health.json', health)
                break
            yield server
        finally:
            core.terminate(server)


def decision_records(folder):
    return sorted([json.loads(line) for p in (folder / 'diagnostics').rglob('*.jsonl')
                   for line in p.read_text().splitlines()], key=lambda r:r['request']['timestamp'])


def inspect(folder, plan, job):
    log = (folder / 'java.log').read_text()
    core.require(log.count('Scenario finished at ') == 1 and 'Simulation finished at ' in log, 'Incomplete Java scenario')
    core.require(not any(s in log for s in ['Exception', 'ERROR', 'unexpected error', 'Training-data write failed']), 'Java reported errors')
    core.require('ROUTING_SCHEMA=' + core.SCHEMA in log and
                 f"Optimizer Loop. Delta T = {job['interval_seconds']}.0" in log, 'Routing or planning interval differs')
    fingerprints = re.findall(r'WORKLOAD_AUDIT .*sha256=([a-f0-9]{64})', log)
    core.require(len(fingerprints) == 1, 'Missing workload fingerprint')
    expected = times(plan, job)
    # Do not use the old parse_windows helper: it assumes every window is 60 s.
    logged_times = [float(x) for x in re.findall(r'PERF_WINDOW \| Policy=SCOPE \| Time=([\d.]+)', log)]
    core.require(logged_times == expected, 'Missing or mistimed reporting windows')
    records = decision_records(folder)
    core.require([r['request']['timestamp'] for r in records] == expected, 'Missing, repeated or mistimed decisions')
    previous = core.INITIAL; trace = []
    for r in records:
        q, settings = r['request'], r['settings']
        a = [r['current']['configuration'][k] for k in core.COLS]
        b = [r['selected']['configuration'][k] for k in core.COLS]
        core.require(q['policy'] == 'SCOPE' and q['iteration'] == job['iteration'] and q['num_devices'] == job['load']
                     and q['simulation_seed'] == plan['seed_base'] + job['iteration']
                     and q['routing_schema'] == core.SCHEMA and q['telemetry_schema'] == 'vm_percent_all_vms_v1', 'Decision identity/schema differs')
        core.require(settings['lambda'] == .01 and settings['r_max'] == .15 and settings['hard_stability_enabled']
                     and settings.get('selection_mode') == 'adaptive' and settings.get('freeze_after_seconds') is None, 'Objective/freeze settings differ')
        core.require(all(abs(x-y) <= 1e-9 for x,y in zip(a, previous)), 'Java did not apply the preceding configuration')
        move = sum(abs(x-y)/scale for x,y,scale in zip(a,b,SCALES))/7
        core.require(abs(move-r['selected']['reconfiguration_cost']) <= 1e-9 and move <= .15+1e-9, 'Movement bound or measurement differs')
        trace.append(dict(timestamp=q['timestamp'], movement=move, **dict(zip(core.COLS, b))))
        previous = b
    metrics = {app:core.generic(folder / 'java' / f"SIMRESULT_ITS_SCENARIO_SCOPE_{job['load']}DEVICES_{app}_GENERIC.log") for app in core.APPS}
    # Whole-run movement includes warmup; keep the post-warmup summary as well.
    post = [r for r in trace if r['timestamp'] >= plan['warmup_minutes'] * 60]
    return dict(spec=job, workload_sha256=fingerprints[0], metrics=metrics, decisions=trace,
        decision_epochs=len(trace), total_movement=sum(r['movement'] for r in trace),
        max_step=max((r['movement'] for r in trace), default=0), changes=sum(r['movement']>1e-9 for r in trace),
        postwarmup_total_movement=sum(r['movement'] for r in post), postwarmup_changes=sum(r['movement']>1e-9 for r in post))


def simulate(out, plan, job):
    saved = core.complete(out, job['key'])
    if saved:
        core.require(saved['result']['spec'] == job, 'Completed job belongs to different settings')
        print('SKIP ' + job['key'] + ' (verified complete)', flush=True)
        return saved['result']
    core.check_stop(out); core.port_available()
    folder = core.attempt(out, job['key']); (folder / 'java').mkdir()
    text = (out / 'inputs/base.properties').read_text()
    settings = dict(simulation_time=plan['minutes'], warm_up_period=plan['warmup_minutes'],
        min_number_of_mobile_devices=job['load'], max_number_of_mobile_devices=job['load'],
        mobile_device_counter_size=1, orchestrator_policies='SCOPE', file_log_enabled='true', deep_file_log_enabled='false')
    for k,v in settings.items():
        pattern = r'(?m)^' + re.escape(k) + r'=.*$'
        core.require(len(re.findall(pattern, text)) == 1, 'Missing/duplicate configuration key: ' + k)
        text = re.sub(pattern, k + '=' + str(v), text)
    (folder / 'config.properties').write_text(text)
    # VehicularMainApp loads these models beside the scenario config, even for SCOPE.
    (folder / 'weka').symlink_to(out / 'inputs/weka', target_is_directory=True)
    cmd = [plan['java'], '-Xmx2g', '-Dscope.optimizer.failFast=true', '-Dscope.deadlineTierGuard=true',
        '-Dscope.auditWorkload=true', '-Dscope.logPerformanceWindows=true',
        '-Dscope.planningIntervalSeconds=' + str(job['interval_seconds']),
        '-Dscope.trainingData.path=' + str(folder / 'candidate_windows.csv')]
    if job['burst']:
        cmd += ['-Dscope.workload.shiftSeconds=' + str(plan['shift_seconds']),
                '-Dscope.workload.recoverySeconds=' + str(plan['recovery_seconds']),
                '-Dscope.workload.rateMultiplier=' + str(plan['rate_multiplier'])]
    cmd += ['-cp', core.cp(out), core.MAIN, str(folder / 'config.properties'),
            str(out / 'inputs/edge_devices.xml'), str(out / 'inputs/applications.xml'), str(folder / 'java'), str(job['iteration'])]
    core.write(folder / 'command.json', cmd); core.write(folder / 'settings.json', job)
    print('RUN ' + job['key'] + ' | ' + str(folder / 'java.log'), flush=True)
    with service(out, folder, plan) as server:
        core.managed(cmd, folder / 'java.log', out, cwd=out, environ=core.env(), peer=server)
    result = inspect(folder, plan, job)
    core.receipt(out, job['key'], folder, result)
    m = result['metrics']['ALL_APPS']
    print(f"DONE {job['key']}: failures={m['failure_pct']:.4f}%, service={m['service_seconds']:.6f}s; changes={result['changes']}", flush=True)
    return result


def interval(values):
    from scipy.stats import t
    core.require(values and all(math.isfinite(v) for v in values), 'Nonfinite/empty statistical sample')
    n = len(values); mean = statistics.mean(values)
    # A single smoke run does not have a zero-width confidence interval.
    half = float(t.ppf(.975, n-1))*statistics.stdev(values)/math.sqrt(n) if n > 1 else None
    return dict(n=n, mean=mean, lower=mean-half if half is not None else None, upper=mean+half if half is not None else None)


def paired(values):
    from scipy.stats import t
    row = interval(values)
    if len(values) < 2:
        p = None
    else:
        sd = statistics.stdev(values)
        p = (1. if row['mean'] == 0 else 0.) if sd == 0 else float(2*t.sf(abs(row['mean'])/(sd/math.sqrt(len(values))),len(values)-1))
    return dict(**row, p_raw=p)


def holm(rows):
    usable = [r for r in rows if r['p_raw'] is not None]; running = 0.
    for j,r in enumerate(sorted(usable, key=lambda r:r['p_raw'])):
        running = max(running, min(1., (len(usable)-j)*r['p_raw']))
        r.update(p_holm=running, family_tests=len(usable))
    return rows


def write_csv(path, rows, fields):
    temp = path.with_suffix('.tmp')
    with temp.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields); writer.writeheader(); writer.writerows(rows)
    temp.replace(path)


def summarize(out, plan):
    metrics, traces, means, contrasts, checks = [], [], [], [], []
    fingerprints = {}; lookup = {}; groups = defaultdict(list); completed = 0
    for job in jobs(plan):
        receipt = core.complete(out, job['key'])
        if receipt is None:
            continue
        folder = out / receipt['attempt']; result = inspect(folder, plan, job)
        core.require(result == receipt['result'], 'Saved result differs from raw evidence')
        pair = (job['case'], job['iteration'])
        expected = fingerprints.setdefault(pair, result['workload_sha256'])
        core.require(expected == result['workload_sha256'], 'Paired workload hashes differ; do not compare these runs')
        checks.append(dict(job=job['key'], workload_sha256=expected))
        meta = dict(job=job['key'], scenario=job['case'], load=job['load'], iteration=job['iteration'], interval_seconds=job['interval_seconds'])
        for app,m in result['metrics'].items():
            metrics.append(dict(**meta, application=app, **m))
            for metric in METRICS:
                groups[(job['case'],job['load'],job['interval_seconds'],app,metric)].append(m[metric])
        lookup[(job['case'],job['iteration'],job['interval_seconds'])] = result['metrics']['ALL_APPS']
        for d in result['decisions']:
            traces.append(dict(**meta, **d))
        for metric in ['decision_epochs','total_movement','max_step','changes','postwarmup_total_movement','postwarmup_changes']:
            groups[(job['case'],job['load'],job['interval_seconds'],'CONTROLLER',metric)].append(result[metric])
        completed += 1
    for (case,load,dt,app,metric), values in sorted(groups.items()):
        means.append(dict(scenario=case,load=load,interval_seconds=dt,application=app,metric=metric,**interval(values)))
    complete = completed == len(jobs(plan))
    if complete:
        for case in plan['cases']:
            for dt in plan['intervals_seconds']:
                if dt == 60:
                    continue
                for metric in METRICS:
                    values = [lookup[(case['name'],i,dt)][metric]-lookup[(case['name'],i,60)][metric] for i in plan['iterations']]
                    contrasts.append(dict(scenario=case['name'],load=case['load'],interval_seconds=dt,reference_seconds=60,
                        metric=metric,**paired(values),p_holm=None,family_tests=0))
        holm(contrasts)
        core.require(len(contrasts) == 18, 'Unexpected comparison family')
    write_csv(out/'study_metrics.csv',metrics,['job','scenario','load','iteration','interval_seconds','application','completed','failed','pending','failure_pct','service_seconds','processing_seconds','network_seconds','qoe_completed_pct','qoe_all_pct','vm_capacity_failures','mobility_failures','network_failures'])
    write_csv(out/'decision_metrics.csv',traces,['job','scenario','load','iteration','interval_seconds','timestamp','movement',*core.COLS])
    write_csv(out/'mean_metrics.csv',means,['scenario','load','interval_seconds','application','metric','n','mean','lower','upper'])
    write_csv(out/'paired_comparisons.csv',contrasts,['scenario','load','interval_seconds','reference_seconds','metric','n','mean','lower','upper','p_raw','p_holm','family_tests'])
    core.write(out/'pair_checks.json',checks)
    core.write(out/'completion.json',dict(complete=complete,completed=completed,expected=len(jobs(plan)),
        profile=plan['profile'],iterations=plan['iterations'],matched_workload_groups=len(fingerprints),
        model_retraining=False,note='Complete all registered runs before paper figures. Failure denominator: completed + failed. Service time is conditional on completion.'))
    print(f'Completed {completed}/{len(jobs(plan))} scenarios. Summaries: {out}',flush=True)


def package(out, plan):
    summarize(out, plan)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    target = out.parent / (out.name + '_review_' + stamp + '.zip')
    with zipfile.ZipFile(target, 'x', zipfile.ZIP_DEFLATED) as z:
        for p in sorted(out.rglob('*')):
            rel = p.relative_to(out)
            if not p.is_file() or p.is_symlink() or '__pycache__' in rel.parts or p.name=='.runner.lock':
                continue
            if rel.parts[0] == 'runtime' and rel.parts[1] in ['classes','lib']:
                continue
            if 'weka' in rel.parts:
                continue
            z.write(p, Path(out.name)/rel)
    print('Review ZIP: ' + str(target), flush=True)
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=['prepare','run','status','stop','summarize','package'])
    parser.add_argument('--source-study',type=Path,help='Original final output, including runtime (not a review ZIP)')
    parser.add_argument('--output',type=Path,default=DEFAULT_OUTPUT)
    parser.add_argument('--profile',choices=['full','smoke'])
    parser.add_argument('--java',help='Path to JDK 21+ bin/java')
    parser.add_argument('--iteration',type=int,help='Run one registered iteration; a later run resumes the rest')
    args = parser.parse_args(); out = args.output.expanduser().resolve()
    core.require(args.iteration is None or args.stage=='run', '--iteration is valid only with run')
    if args.stage in ['status','stop']:
        plan = load_plan(out)
        if args.stage == 'stop':
            (out/'STOP_REQUESTED').touch(); print('Stop requested. Wait for STOPPED before resuming.')
        else:
            count = sum((out/'jobs'/j['key']/'complete.json').exists() for j in jobs(plan))
            print(f'Receipts: {count}/{len(jobs(plan))} (run/summarize verifies their bytes).\n{out}')
        return
    if args.stage == 'prepare':
        source = (args.source_study or default_source()).expanduser().resolve()
        non_nested(source,out); out.mkdir(parents=True,exist_ok=True)
    core.require(out.is_dir(), 'Run prepare first')
    signal.signal(signal.SIGINT,core.signal_stop); signal.signal(signal.SIGTERM,core.signal_stop)
    with (out/'.runner.lock').open('a+') as lock:
        try:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError('Another runner owns this output; do not run two batches together') from exc
        (out/'STOP_REQUESTED').unlink(missing_ok=True)
        try:
            if args.stage == 'prepare':
                prepare(out,args); return
            plan = load_plan(out); validate(out,plan)
            core.require(args.profile is None or args.profile==plan['profile'], 'Profile differs')
            if args.stage == 'package':
                package(out,plan); return
            if args.stage == 'summarize':
                summarize(out,plan); return
            core.require(args.iteration is None or args.iteration in plan['iterations'], 'Iteration not registered')
            for job in jobs(plan):
                if args.iteration is not None and args.iteration!=job['iteration']:
                    continue
                simulate(out,plan,job)
            summarize(out,plan)
            if all((out/'jobs'/j['key']/'complete.json').exists() for j in jobs(plan)):
                print('RUN COMPLETE. In MATLAB: cd to this output\'s matlab folder; plot_delta_t_results',flush=True)
        except core.Stopped:
            print('STOPPED safely. Completed jobs retained; repeat run to resume.',flush=True)
            raise SystemExit(130)
        except Exception as exc:
            print('STOPPED ON ERROR: '+str(exc)+'\nCompleted jobs and the failed attempt are retained.',file=sys.stderr,flush=True)
            raise


if __name__ == '__main__':
    main()
