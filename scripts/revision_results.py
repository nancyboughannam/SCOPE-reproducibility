"""Recompute the manuscript's three additional studies from archived measurements."""
from pathlib import Path

import numpy as np
import pandas as pd

from verify_results import check_holm, stats

RESULTS = Path(__file__).resolve().parents[1] / "results"
METRICS = ["failure_pct", "service_seconds", "changes", "total_movement", "max_step"]


def check_summary(actual, path, index):
    expected = pd.read_csv(path).set_index(index).sort_index()
    pd.testing.assert_frame_equal(
        actual.sort_index()[expected.columns], expected,
        check_dtype=False, check_exact=False, rtol=1e-9, atol=1e-11,
    )
    print(actual.to_string(), end="\n\n")


def prediction_noise():
    folder = RESULTS / "prediction_noise"
    rows = pd.read_csv(folder / "per_run.csv").set_index(["noise_level", "iteration"])
    design = pd.MultiIndex.from_product(
        [[0, 1, 2], range(3401, 3411)], names=rows.index.names
    )
    pd.testing.assert_index_equal(rows.sort_index().index, design)
    if not rows.groupby("iteration").workload_sha256.nunique().eq(1).all():
        raise ValueError("Workloads differ across noise levels in a paired iteration.")
    groups = rows.groupby("noise_level")
    summary = groups[METRICS].mean().add_prefix("mean_")
    summary["n"] = groups.size()
    summary["largest_observed_step"] = groups.max_step.max()
    print("Table 9. Prediction noise at 1,800 vehicles")
    check_summary(summary, folder / "level_summary.csv", "noise_level")

    contrasts = pd.read_csv(folder / "paired_differences.csv")
    baseline = rows.loc[0].sort_index()
    for row in contrasts.itertuples():
        difference = rows.loc[row.noise_level, row.metric].sort_index() - baseline[row.metric]
        if row.unit == "ms":
            difference *= 1000
        np.testing.assert_allclose(
            stats(difference),
            [row.mean_difference, row.ci95_low, row.ci95_high, row.p_two_sided],
            rtol=1e-9, atol=1e-11,
        )
    check_holm(contrasts.rename(columns={"p_two_sided": "p_raw"}).assign(family_tests=4))
    print(contrasts[["noise_level", "metric", "mean_difference", "unit", "p_holm"]].to_string(index=False))


def control_loop_latency():
    folder = RESULTS / "control_loop_latency"
    rows = pd.read_csv(folder / "updates.csv")
    design = pd.MultiIndex.from_product(
        [range(3401, 3404), range(70, 3600, 60)], names=["iteration", "simulated_seconds"]
    )
    pd.testing.assert_index_equal(rows.set_index(design.names).sort_index().index, design)
    mask = rows.simulated_seconds >= 180
    np.testing.assert_array_equal(rows.post_warmup, mask)
    np.testing.assert_allclose(rows.local_control_loop_ns / 1e6, rows.local_control_loop_ms)
    primary = rows[mask]
    samples = {"pooled_post_warmup": primary, "pooled_all_updates": rows}
    for seed, group in primary.groupby("iteration"):
        samples[f"{seed}_post_warmup"] = group
    measures = []
    for name, group in samples.items():
        loop = group.local_control_loop_ms
        optimizer = group.optimizer_ms
        measures.append(dict(
            sample=name, n=len(group), loop_median_ms=loop.median(),
            loop_p95_ms=loop.quantile(.95), loop_max_ms=loop.max(),
            optimizer_median_ms=optimizer.median(), optimizer_p95_ms=optimizer.quantile(.95),
        ))
    print("Section 5.1.3. Measured local control-loop latency (milliseconds)")
    check_summary(pd.DataFrame(measures).set_index("sample"), folder / "summary.csv", "sample")


def reconfiguration_budget():
    folder = RESULTS / "reconfiguration_budget"
    rows = pd.read_csv(folder / "per_run.csv").set_index(["r_max", "iteration"])
    design = pd.MultiIndex.from_product(
        [[.10, .15, .20, .30], range(3301, 3304)], names=rows.index.names
    )
    pd.testing.assert_index_equal(rows.sort_index().index, design)
    groups = rows.groupby("r_max")
    summary = groups[METRICS].mean().add_suffix("_mean").join(groups[METRICS].std().add_suffix("_sd"))
    summary["iterations"] = groups.size()
    summary["largest_individual_step"] = groups.max_step.max()
    print("Appendix Table A.9. Hard reconfiguration budget at 1,800 vehicles")
    check_summary(summary, folder / "summary.csv", "r_max")


if __name__ == "__main__":
    prediction_noise()
    control_loop_latency()
    reconfiguration_budget()
