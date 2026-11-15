"""Shared, outcome-free feature transformations and saved-model inference."""
from __future__ import annotations
import numpy as np
import pandas as pd
import xgboost as xgb

ACTION_SUFFIXES = ['alpha'] + [f'w_load_{i}' for i in range(3)] + [f'threshold_{i}' for i in range(3)]
ACTION_COLUMNS = ['candidate_' + s for s in ACTION_SUFFIXES]
DERIVED_COLUMNS = ['candidate_delta_' + s for s in ACTION_SUFFIXES] + [f'candidate_cpu_margin_{i}' for i in range(3)]

def transform(frame: pd.DataFrame, kind: str = 'identity') -> pd.DataFrame:
    if kind == 'identity':
        return frame.copy()
    if kind != 'action_deltas_v1':
        raise ValueError(f'Unknown feature transform: {kind}')
    out = frame.copy()
    for suffix in ACTION_SUFFIXES:
        scale = 100.0 if suffix.startswith('threshold') else 1.0
        out['candidate_delta_' + suffix] = (out['candidate_' + suffix] - out['previous_' + suffix]) / scale
    for i in range(3):
        out[f'candidate_cpu_margin_{i}'] = (out[f'candidate_threshold_{i}'] - out['state_avg_edge_cpu']) / 100.0
    return out

def predict(booster: xgb.Booster, spec: dict, frame: pd.DataFrame) -> np.ndarray:
    matrix = transform(frame, spec.get('feature_transform', 'identity'))[spec['features']].astype(np.float32)
    if not np.isfinite(matrix.to_numpy()).all():
        raise ValueError('Nonfinite predictor input')
    prediction = booster.predict(xgb.DMatrix(matrix), iteration_range=(0, int(spec['best_iteration']) + 1))
    if spec.get('residual_feature'):
        prediction = prediction + frame[spec['residual_feature']].to_numpy()
    return np.clip(prediction, 0, 1 if spec['target'] == 'failure_rate' else None)
