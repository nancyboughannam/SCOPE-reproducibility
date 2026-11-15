"""Regression checks for preservation boundaries and the frozen paper protocol."""
from pathlib import Path
import json
import pytest
import reproduce


def test_protected_output_rejected():
    for path in [reproduce.ROOT,reproduce.ROOT.parent,reproduce.ROOT/'results/new_run',
                 reproduce.ROOT/'FLaskAPIs/new_run']:
        with pytest.raises(RuntimeError): reproduce.safe_output(path)


def test_new_output_keeps_archive_separate(tmp_path):
    assert reproduce.safe_output(tmp_path/'new_run') == tmp_path/'new_run'
    assert reproduce.safe_output(reproduce.ROOT/'reruns'/'new_run') == reproduce.ROOT/'reruns'/'new_run'


def test_full_protocol_counts_and_random():
    plan=reproduce.confirmation.protocol('full')
    jobs=reproduce.confirmation.evaluation_specs(plan)
    assert len(jobs)==400
    assert sum(j['label']=='RANDOM' for j in jobs)==50
    assert set(plan['iterations'])==set(range(3401,3411))
    assert not set(plan['iterations'])&set(plan['tuning_iterations'])
    assert plan['lambda_value']==.01 and plan['r_max']==.15


def test_frozen_runtime_mapping_matches_independent_audit():
    root=reproduce.ROOT
    mapping=json.loads((root/'provenance/runtime_files.json').read_text())
    audit=json.loads((root/'experiments/delta_t/audited_source_hashes.json').read_text())['hashes']
    assert set(mapping)==set(audit) and len(mapping)==94
    for dest,source in mapping.items():
        assert reproduce.core.sha(root/source)==audit[dest]


def test_smoke_uses_distinct_seeds():
    smoke=reproduce.confirmation.protocol('smoke')
    full=reproduce.confirmation.protocol('full')
    assert len(reproduce.confirmation.evaluation_specs(smoke))==22
    assert not set(smoke['iterations'])&set(full['iterations'])
