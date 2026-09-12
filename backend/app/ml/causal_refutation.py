"""Offline refutations of the randomized simulator's average abandonment effect.

These are custom permutation/bootstrap tests, not calls to DoWhy. Passing them
does not establish causal validity on observational Nessie or bank data.
"""
import json
import numpy as np

from app.ml.simulator import generate_synthetic_data


def refute(rows=6000, seed=4100, repetitions=300):
    records = [row for row in generate_synthetic_data(rows, seed) if not row["fraud"]]
    treatment = np.array([row["treatment"] == "verify" for row in records])
    abandoned = np.array([not row["observed_completed"] for row in records], dtype=float)
    rng = np.random.default_rng(seed)

    def effect(t, y):
        return float(y[t].mean() - y[~t].mean())

    estimate = effect(treatment, abandoned)
    placebo = np.array([effect(rng.permutation(treatment), abandoned) for _ in range(repetitions)])
    bootstrap, subsets = [], []
    for _ in range(repetitions):
        ix = rng.integers(0, len(records), size=len(records))
        bootstrap.append(effect(treatment[ix], abandoned[ix]))
        ix = rng.choice(len(records), size=int(.8 * len(records)), replace=False)
        subsets.append(effect(treatment[ix], abandoned[ix]))
    noise = rng.normal(size=(len(records), 1))
    design = np.column_stack([np.ones(len(records)), treatment, noise])
    noise_effect = float(np.linalg.lstsq(design, abandoned, rcond=None)[0][1])
    return {
        "source": "synthetic randomized legitimate purchases",
        "estimator": "difference in means; treatment assignment probability = 0.5",
        "framework": "custom numpy permutation/bootstrap; DoWhy not installed or used",
        "seed": seed, "n": len(records), "repetitions": repetitions,
        "abandonment_ate_verify_minus_allow": estimate,
        "bootstrap_95_ci": np.quantile(bootstrap, [.025, .975]).tolist(),
        "placebo_mean_effect": float(placebo.mean()),
        "placebo_95_interval": np.quantile(placebo, [.025, .975]).tolist(),
        "permutation_p_value": float((1 + np.sum(np.abs(placebo) >= abs(estimate))) / (repetitions + 1)),
        "random_common_cause_effect": noise_effect,
        "subset_80_percent_95_interval": np.quantile(subsets, [.025, .975]).tolist(),
        "caveats": [
            "Simulator generates the relationship being tested; this is a pipeline sanity check.",
            "Average treatment effects do not validate individual treatment-effect estimates.",
            "Real observational logs require confounder adjustment, overlap and measured propensities.",
            "Unobserved confounding is absent from assignment in this randomized experiment.",
        ],
    }


if __name__ == "__main__":
    print(json.dumps(refute(), indent=2, allow_nan=False))
