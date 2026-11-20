#!/usr/bin/env python3
"""Portable entry point for the frozen SCOPE publication experiments."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import fcntl
import json
import os
import platform
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'FLaskAPIs'))
import run_deadline_pilot as core
import run_confirmatory_study as confirmation
import run_lambda_check as calibration


def stamp():
    return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')


def revision():
    if (ROOT / '.git').exists():
        try:
            return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,
                                           text=True,stderr=subprocess.DEVNULL).strip()
        except (OSError,subprocess.CalledProcessError):
            pass
    marker=ROOT/'REVISION.txt'
    return marker.read_text().strip() if marker.exists() else 'unknown; identify by artifact hashes'


def verify_bytes():
    entries = json.loads((ROOT / 'provenance/artifact_hashes.json').read_text())
    core.verify(ROOT, entries)
    print(f'VERIFIED: {len(entries)} archived code, model, data and figure files.', flush=True)


def command(script, *args):
    child = subprocess.Popen([sys.executable, str(ROOT / script), *map(str, args)],
                             cwd=ROOT, env=core.env())
    try:
        code = child.wait()
    except KeyboardInterrupt:
        # The child received the same Terminal signal and owns Java/Flask cleanup.
        print('\nWaiting for the active runner to stop safely...', flush=True)
        child.wait()
        raise SystemExit(130)
    if code:
        raise SystemExit(130 if code in (130, -2) else code)


def safe_output(path):
    path = path.expanduser().resolve()
    if path == ROOT or path in ROOT.parents or (ROOT in path.parents and ROOT / 'reruns' not in path.parents):
        raise RuntimeError('Use a new folder under reruns/, or a separate folder outside this repository.')
    return path


def make_source(out):
    """Materialize byte-identical inputs; archived study metadata is provenance."""
    audit = core.read(ROOT / 'experiments/delta_t/audited_source_hashes.json')
    mapping = core.read(ROOT / 'provenance/runtime_files.json')
    if (out / 'study.json').exists():
        core.verify(out, audit['hashes'])
        return
    out.mkdir(parents=True, exist_ok=True)
    core.require(not any(out.iterdir()), 'Incomplete source preparation; choose another output root.')
    for target, source in mapping.items():
        dest = out / target
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / source, dest)
    for name in ['study.json', 'study_checksum.txt']:
        shutil.copy2(ROOT / 'results/v5_guard_off' / name, out / name)
    (out / '.runner.lock').touch()
    core.verify(out, audit['hashes'])


def prepare_main(out, profile, java):
    if (out / 'study.json').exists():
        plan = confirmation.load_plan(out)
        confirmation.validate(out, plan)
        core.require(plan['profile'] == profile, 'Profile differs; use a separate output.')
        core.require(core.sha(Path(plan['java'])) == plan['java_sha256'], 'Java executable changed; use a new output.')
        if java:
            core.require(core.select_java(java) == plan['java'], 'Selected Java differs from the prepared study.')
        return
    out.mkdir(parents=True, exist_ok=True)
    core.require(not any(out.iterdir()), 'Incomplete main preparation retained; choose another output root.')
    mapping = core.read(ROOT / 'provenance/runtime_files.json')
    for target, source in mapping.items():
        dest = out / target
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / source, dest)
    # Frozen simulation services are unchanged; additional files implement orchestration.
    for p in (ROOT / 'FLaskAPIs').glob('*.py'):
        if not p.name.startswith('test_'):
            shutil.copy2(p, out / 'runtime/services' / p.name)
    shutil.copytree(ROOT / 'FLaskAPIs/confirmatory_matlab', out / 'matlab')
    classes = out / 'runtime/classes'
    classes.mkdir()
    java = core.select_java(java)
    libraries = os.pathsep.join(map(str, sorted((out / 'runtime/lib').glob('*.jar'))))
    core.managed([java, '-m', 'jdk.compiler/com.sun.tools.javac.Main', '-classpath', libraries,
                  '-sourcepath', out / 'runtime/src', '-d', classes,
                  out / 'runtime/src' / (core.MAIN.replace('.', '/') + '.java')],
                 out / 'compile.log', out)
    plan = confirmation.protocol(profile)
    plan['shortlist'] = confirmation.choose_shortlist(out, plan)
    archived = core.read(ROOT / 'results/v5_guard_on/study.json')
    for load, values in plan['shortlist'].items():
        core.require(values == archived['shortlist'][load], 'Static shortlist changed at load ' + load)
    plan.update(output=str(out), java=java, python=sys.executable, git_head=revision(),
                python_version=sys.version, platform=platform.platform(), architecture=platform.machine(),
                java_sha256=core.sha(Path(java)), package_versions=core.versions(),
                imported_calibration_jobs=[], created=stamp(),
                purpose='Reproduction of the frozen paper protocol using archived models; no model fitting or parameter selection on evaluation seeds.',
                source_study_sha=core.sha(ROOT / 'results/v5_guard_on/study.json'),
                runner_hashes={n:core.sha(ROOT / 'FLaskAPIs' / n) for n in confirmation.CODE})
    env = confirmation.service_environment(out, out / 'preflight', plan,
        confirmation.spec('main', 'SCOPE', plan['loads'][0], plan['iterations'][0]))
    core.managed([sys.executable, '-c', 'import ml_optimizer_service as s; import exp3_mc_service as e; assert len(s.MODELS)==6; assert s.NORMALIZATION==e.NORMALIZATION; print("Frozen models and normalization verified")'],
                 out / 'preflight.log', out, cwd=out / 'runtime/services', environ=env)
    for port in [5002, 5003]:
        confirmation.free_port(port)
    plan['input_hashes'] = {str(p.relative_to(out)): core.sha(p)
        for d in ['runtime','inputs','models','dataset'] for p in (out / d).rglob('*')
        if p.is_file() and '__pycache__' not in p.parts}
    core.write(out / 'study.json', plan)
    (out / 'study_checksum.txt').write_text(core.sha(out / 'study.json') + '\n')
    (out / '.runner.lock').touch()
    print(f'PREPARED main: {len(confirmation.evaluation_specs(plan))} evaluations plus '
          f'{len(confirmation.tuning_specs(plan))} static-calibration jobs.', flush=True)


def prepare_lambda(out, profile, java):
    selected_profile = 'smoke' if profile == 'smoke' else 'pilot'
    if (out / 'study.json').exists():
        plan = calibration.load_plan(out)
        calibration.validate_runtime(out, plan)
        core.require(plan['profile'] == selected_profile, 'Calibration profile differs.')
        core.require(core.sha(Path(plan['java'])) == plan['java_sha256'], 'Java changed; use a new output.')
        return
    out.mkdir(parents=True, exist_ok=True)
    core.require(not any(out.iterdir()), 'Incomplete lambda preparation retained; choose a new output.')
    for target, source in core.read(ROOT / 'provenance/runtime_files.json').items():
        dest = out / target; dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / source, dest)
    for p in (ROOT / 'FLaskAPIs').glob('*.py'):
        if not p.name.startswith('test_'): shutil.copy2(p, out / 'runtime/services' / p.name)
    shutil.copytree(ROOT / 'FLaskAPIs/lambda_check_matlab', out / 'matlab')
    classes = out / 'runtime/classes'; classes.mkdir()
    java = core.select_java(java)
    libraries = os.pathsep.join(map(str, sorted((out / 'runtime/lib').glob('*.jar'))))
    core.managed([java, '-m', 'jdk.compiler/com.sun.tools.javac.Main', '-classpath', libraries,
                  '-sourcepath', out / 'runtime/src', '-d', classes,
                  out / 'runtime/src' / (core.MAIN.replace('.', '/') + '.java')],
                 out / 'compile.log', out)
    plan = calibration.protocol(selected_profile)
    plan.update(output=str(out), java=java, java_sha256=core.sha(Path(java)),
        python=sys.executable, python_version=sys.version, platform=platform.platform(), git_head=revision(),
        package_versions=core.versions(), created=stamp(),
        source_study_sha=core.sha(ROOT / 'results/lambda_calibration/study.json'),
        runner_hashes={n:core.sha(ROOT / 'FLaskAPIs' / n) for n in calibration.CODE_FILES})
    plan['input_hashes']={str(p.relative_to(out)):core.sha(p)
        for d in ['runtime','inputs','models','dataset'] for p in (out / d).rglob('*')
        if p.is_file() and '__pycache__' not in p.parts}
    core.write(out / 'study.json', plan)
    (out / 'study_checksum.txt').write_text(core.sha(out / 'study.json')+'\n')
    (out / '.runner.lock').touch()
    print(f'PREPARED lambda calibration: {len(calibration.job_specs(plan))} scenarios; all settings retained.', flush=True)


def prepare(args, out):
    verify_bytes()
    audit = core.read(ROOT / 'experiments/delta_t/audited_source_hashes.json')
    core.require(core.versions() == audit['package_versions'], 'Dependency versions differ. Run bash SETUP.sh.')
    make_source(out / 'frozen_source')
    if args.study in ['all', 'lambda']:
        prepare_lambda(out / 'lambda_calibration', args.profile, args.java)
    if args.study in ['all', 'main']:
        prepare_main(out / 'guard_on', args.profile, args.java)
    if args.study in ['all', 'delta']:
        extra = ['--java', args.java] if args.java else []
        command('experiments/delta_t/run_delta_t_study.py', 'prepare',
                '--source-study', out / 'frozen_source', '--output', out / 'delta_t',
                '--profile', args.profile, *extra)
    print('PREPARED. Run the same command with run to start/resume.', flush=True)


def run(args, out):
    core.write(out / 'suite_completion.json', dict(complete=False, profile=args.profile,
               study=args.study, started=stamp(), output=str(out)))
    prepare(args, out)
    if args.study in ['all', 'lambda']:
        command('FLaskAPIs/run_lambda_check.py', 'run', '--output', out / 'lambda_calibration')
    if args.study in ['all', 'main']:
        command('FLaskAPIs/run_confirmatory_study.py', 'run', '--output', out / 'guard_on')
        extra = ['--java', args.java] if args.java else []
        command('FLaskAPIs/run_exp3_guard_ablation.py', 'prepare',
                '--source-study', out / 'guard_on', '--output', out / 'main', *extra)
        command('FLaskAPIs/run_exp3_guard_ablation.py', 'run', '--output', out / 'main')
    if args.study in ['all', 'delta']:
        command('experiments/delta_t/run_delta_t_study.py', 'run', '--output', out / 'delta_t')
    core.write(out / 'suite_completion.json', dict(complete=True, profile=args.profile,
               study=args.study, finished=stamp(), output=str(out)))
    print('SIMULATIONS COMPLETE: ' + str(out), flush=True)
    if args.profile == 'full':
        print("In MATLAB: RUN_MATLAB('rerun', '" + str(out).replace("'", "''") + "')", flush=True)
    else:
        print('Smoke results validate execution only and cannot be used as paper figures.', flush=True)


def package(args, out):
    source = ROOT / 'results' if args.source == 'archived' else out
    core.require(source.is_dir(), 'Results folder does not exist: ' + str(source))
    if args.source == 'archived':
        verify_bytes()
    else:
        completion = core.read(source / 'suite_completion.json')
        core.require(completion['complete'], 'Complete the selected simulation suite before packaging.')
    dest = ROOT / 'packages'
    dest.mkdir(exist_ok=True)
    target = dest / ('scope_' + args.source + '_review_' + stamp() + '.zip')
    figures = []
    for p in (ROOT / 'outputs').glob('figures_*/SOURCE.json'):
        info = core.read(p)
        if info['source'] == args.source and Path(info['data_root']).resolve() == source.resolve():
            figures.append(p.parent)
    with zipfile.ZipFile(target, 'x', zipfile.ZIP_DEFLATED) as z:
        z.writestr('REPRODUCTION_SOURCE.json',json.dumps(dict(code_revision=revision(),
            artifact_manifest_sha256=core.sha(ROOT/'provenance/artifact_hashes.json'),
            source=args.source, data_root=str(source), created=stamp()),indent=2)+'\n')
        for p in sorted(source.rglob('*')):
            rel = p.relative_to(source)
            if not p.is_file() or p.is_symlink() or any(x in rel.parts for x in ['runtime','weka','frozen_source','__pycache__']) or p.name in ['.runner.lock','.suite.lock']:
                continue
            z.write(p, Path('results') / rel)
        if figures:
            for p in sorted(sorted(figures)[-1].rglob('*')):
                if p.is_file(): z.write(p, Path('matlab_figures') / p.relative_to(sorted(figures)[-1]))
        for p in [ROOT / 'README.md', ROOT / 'CITATION.cff', ROOT / 'requirements-reproducibility.txt',
                  ROOT / 'provenance/artifact_hashes.json']:
            z.write(p, p.relative_to(ROOT))
    print('REVIEW ZIP: ' + str(target), flush=True)
    if not figures:
        print('No newly generated MATLAB figure folder matched this data source; archived PDF figures are included only for archived packages.', flush=True)
    if sys.platform == 'darwin':
        subprocess.run(['open', '-R', str(target)], check=False)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage', choices=['verify','prepare','run','status','package','table4','table5','revision-results','calibration-table','train'])
    p.add_argument('--study', choices=['all','main','delta','lambda'], default='all')
    p.add_argument('--profile', choices=['full','smoke'], default='full')
    p.add_argument('--output', type=Path)
    p.add_argument('--java', help='Full path to the JDK 21+ java executable')
    p.add_argument('--source', choices=['archived','rerun'], default='archived')
    args = p.parse_args()
    out = safe_output(args.output or ROOT / 'reruns' / ('paper' if args.profile == 'full' else 'smoke'))
    if args.stage == 'verify':
        verify_bytes()
        command('scripts/verify_results.py')
        command('scripts/revision_results.py')
        return
    if args.stage in ('table4', 'table5'):
        verify_bytes()
        command('scripts/table4.py', args.stage)
        return
    if args.stage == 'revision-results':
        verify_bytes()
        command('scripts/revision_results.py')
        return
    if args.stage == 'calibration-table':
        if args.source == 'archived': verify_bytes()
        source = ROOT / 'results/lambda_calibration' if args.source == 'archived' else out / 'lambda_calibration'
        command('scripts/calibration_table.py', '--data', source); return
    if args.stage == 'train':
        verify_bytes()
        target = ROOT / 'reruns' / ('predictor_training_' + stamp())
        command('FLaskAPIs/train_candidate_xgboost.py', '--data-dir',
                ROOT / 'FLaskAPIs/scope_candidate_dataset', '--output-dir', target,
                '--telemetry-schema', 'vm_percent_all_vms_v1')
        print('Fresh model fit saved separately: ' + str(target)); return
    if args.stage == 'package':
        package(args, out); return
    if args.stage == 'status':
        for name in ['lambda_calibration','guard_on','main','delta_t']:
            folder = out / name
            done = len(list((folder / 'jobs').glob('*/complete.json')))
            print(f'{name}: {done} completed-job receipts; folder {folder}')
        return
    out.mkdir(parents=True, exist_ok=True)
    with (out / '.suite.lock').open('a+') as lock:
        try: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError: raise RuntimeError('Another process is running this suite.')
        metadata = out / 'suite.json'
        settings = dict(profile=args.profile, study=args.study, output=str(out))
        if metadata.exists():
            core.require(core.read(metadata) == settings, 'Suite settings changed; use a different output root.')
        else: core.write(metadata, settings)
        if args.stage == 'prepare': prepare(args, out)
        else: run(args, out)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\nStop requested. Wait for the child runner to print STOPPED; repeat the command to resume.', flush=True)
        raise SystemExit(130)
    except (RuntimeError, FileNotFoundError) as exc:
        print('ERROR: ' + str(exc), file=sys.stderr)
        raise SystemExit(1)
