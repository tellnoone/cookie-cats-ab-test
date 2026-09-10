"""
SIMULATED DATA ONLY (ANALYSIS_PLAN.md section 7).

Nothing here is a finding about Cookie Cats.

Five metrics tested at alpha = 0.05 when NONE of them has a real effect, with
and without correction. This is the arithmetic behind section 2's insistence on
exactly one primary metric.

Also shown: what correction COSTS. Bonferroni and Benjamini-Hochberg are applied
to a scenario where some metrics do move, so the loss of power is visible rather
than assumed away.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.proportion import proportions_ztest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import ALPHA, FIGURES, ROOT, SEED, TABLES, Report  # noqa: E402

say = Report(TABLES / "sim_multiple_comparisons.txt")
rng = np.random.default_rng(SEED)

N_SIMS = 5_000
N_PER_ARM = 20_000
BASELINE = 0.19
K = 5

say.head("SIMULATION: MULTIPLE COMPARISONS  (simulated data -- NOT Cookie Cats)")
say()
say("  " + "*" * 70)
say("  *  Every number below is generated in this script. None of it is a     *")
say("  *  result about Cookie Cats.                                           *")
say("  " + "*" * 70)
say()
say(f"  Simulations     : {N_SIMS:,d}")
say(f"  Metrics tested  : {K}")
say(f"  Users per arm   : {N_PER_ARM:,d}")
say(f"  Baseline        : {BASELINE:.0%}")
say(f"  alpha           : {ALPHA}")
say()

# ---------------------------------------------------------------------------
# The arithmetic, before any simulation
# ---------------------------------------------------------------------------
say.head("1. THE ARITHMETIC")
say()
say("  If all 5 null hypotheses are true and the tests are independent, the")
say("  chance of at least one false positive is:")
say()
say(f"    1 - (1 - {ALPHA})^{K}  =  1 - {1-ALPHA}^{K}  =  {1-(1-ALPHA)**K:.4f}")
say()
say(f"  So {1-(1-ALPHA)**K:.1%}, not 5%. Testing five metrics at 0.05 each means")
say("  roughly a 1-in-4 chance of finding a 'winner' that does not exist.")
say()
say(f"  {'k metrics':>11s}{'P(>=1 false positive)':>24s}")
for k in (1, 2, 3, 5, 10, 20):
    say(f"  {k:>11d}{1-(1-ALPHA)**k:>23.1%}")
say()

# ---------------------------------------------------------------------------
# 2. Simulate it: all nulls true
# ---------------------------------------------------------------------------
say.head("2. SIMULATED: five metrics, NO real effects anywhere")
say()


def simulate(effects: np.ndarray, n_sims: int) -> np.ndarray:
    """Return (n_sims, K) p-values for K binary metrics with given true effects."""
    pv = np.empty((n_sims, len(effects)))
    for i in range(n_sims):
        for j, eff in enumerate(effects):
            xc = rng.binomial(N_PER_ARM, BASELINE)
            xt = rng.binomial(N_PER_ARM, BASELINE + eff)
            _, p = proportions_ztest([xt, xc], [N_PER_ARM, N_PER_ARM],
                                     alternative="two-sided")
            pv[i, j] = p
    return pv


null_effects = np.zeros(K)
pv_null = simulate(null_effects, N_SIMS)

any_raw = (pv_null < ALPHA).any(axis=1)
bonf = np.array([multipletests(row, alpha=ALPHA, method="bonferroni")[0].any()
                 for row in pv_null])
bh = np.array([multipletests(row, alpha=ALPHA, method="fdr_bh")[0].any()
               for row in pv_null])

say(f"  P(at least one 'significant' metric):")
say()
say(f"    uncorrected        : {any_raw.mean():>7.2%}   "
    f"(theory {1-(1-ALPHA)**K:.2%})")
say(f"    Bonferroni         : {bonf.mean():>7.2%}   (target <= {ALPHA:.0%})")
say(f"    Benjamini-Hochberg : {bh.mean():>7.2%}   (target <= {ALPHA:.0%})")
say()
say("  Per-metric false-positive rate (each should be ~5%):")
for j in range(K):
    say(f"    metric {j+1} : {(pv_null[:, j] < ALPHA).mean():.2%}")
say()
say("  Each individual test is perfectly well calibrated. The problem is not")
say("  any one test -- it is the decision rule 'ship if ANY metric wins', which")
say("  is a different and much less stringent test than it appears to be.")
say()

# ---------------------------------------------------------------------------
# 3. What correction costs
# ---------------------------------------------------------------------------
say.head("3. WHAT CORRECTION COSTS (two metrics genuinely move)")
say()
say("  Correction is not free. Here metrics 1 and 2 have a true +1.0pp effect")
say("  and metrics 3-5 are null. Power is the chance of detecting a REAL effect.")
say()

mixed = np.array([0.010, 0.010, 0.0, 0.0, 0.0])
pv_mixed = simulate(mixed, N_SIMS)

rej_raw = pv_mixed < ALPHA
rej_bonf = np.array([multipletests(r, alpha=ALPHA, method="bonferroni")[0]
                     for r in pv_mixed])
rej_bh = np.array([multipletests(r, alpha=ALPHA, method="fdr_bh")[0]
                   for r in pv_mixed])

say(f"  {'metric':>8s}{'true effect':>14s}{'uncorrected':>14s}"
    f"{'Bonferroni':>13s}{'BH':>9s}")
for j in range(K):
    kind = "real" if mixed[j] > 0 else "null"
    say(f"  {j+1:>8d}{mixed[j]*100:>11.1f}pp{rej_raw[:, j].mean():>13.2%}"
        f"{rej_bonf[:, j].mean():>13.2%}{rej_bh[:, j].mean():>9.2%}"
        f"   <- {kind}")
say()
true_idx, null_idx = [0, 1], [2, 3, 4]
say("  Averaged over the metrics that genuinely moved (POWER, higher is better):")
say(f"    uncorrected        : {rej_raw[:, true_idx].mean():.2%}")
say(f"    Bonferroni         : {rej_bonf[:, true_idx].mean():.2%}")
say(f"    Benjamini-Hochberg : {rej_bh[:, true_idx].mean():.2%}")
say()
say("  Averaged over the null metrics (FALSE POSITIVES, lower is better):")
say(f"    uncorrected        : {rej_raw[:, null_idx].mean():.2%}")
say(f"    Bonferroni         : {rej_bonf[:, null_idx].mean():.2%}")
say(f"    Benjamini-Hochberg : {rej_bh[:, null_idx].mean():.2%}")
say()
say("  This is the trade, and it is why BH is usually preferred to Bonferroni")
say("  for a family of reported metrics: it controls the false DISCOVERY rate")
say("  rather than the family-wise error rate, giving up less power for a")
say("  slightly weaker guarantee.")
say()
say("  But note what neither correction can do: recover the clarity of having")
say("  said in advance which metric decides. That is the point of section 2")
say("  naming a single primary metric -- correction is damage control, and")
say("  pre-specification is prevention.")
say()

# ---------------------------------------------------------------------------
# Plot
# ---------------------------------------------------------------------------
fig, axes = plt.subplots(1, 3, figsize=(15.5, 4.7))

ax = axes[0]
ks = np.arange(1, 21)
ax.plot(ks, (1 - (1 - ALPHA) ** ks) * 100, "o-", lw=2, color="#b3452c", ms=4)
ax.axhline(5, ls="--", color="#333", lw=1.2, label="nominal 5%")
ax.axvline(K, ls=":", color="#1f4e79", lw=1.4, label=f"{K} metrics")
ax.set_xlabel("number of metrics tested at alpha = 0.05")
ax.set_ylabel("P(at least one false positive), %")
ax.set_title("Family-wise error inflation\n(all nulls true)")
ax.legend(fontsize=8)
ax.grid(alpha=0.25)
ax.set_xticks([1, 5, 10, 15, 20])

ax = axes[1]
labels = ["uncorrected", "Bonferroni", "BH"]
vals = [any_raw.mean() * 100, bonf.mean() * 100, bh.mean() * 100]
bars = ax.bar(labels, vals, color=["#b3452c", "#1f4e79", "#2e7d32"], alpha=0.88)
ax.axhline(ALPHA * 100, ls="--", color="#333", lw=1.3, label="target 5%")
for b, v in zip(bars, vals):
    ax.text(b.get_x() + b.get_width() / 2, v + 0.5, f"{v:.1f}%",
            ha="center", fontsize=9)
ax.set_ylabel("P(>=1 false positive), %")
ax.set_title(f"{K} null metrics, {N_SIMS:,d} sims\ncorrection restores the rate")
ax.legend(fontsize=8)
ax.grid(alpha=0.25, axis="y")

ax = axes[2]
x = np.arange(2)
w = 0.26
power_v = [rej_raw[:, true_idx].mean() * 100, rej_bonf[:, true_idx].mean() * 100,
           rej_bh[:, true_idx].mean() * 100]
fp_v = [rej_raw[:, null_idx].mean() * 100, rej_bonf[:, null_idx].mean() * 100,
        rej_bh[:, null_idx].mean() * 100]
for i, (lab, colour) in enumerate(zip(labels, ["#b3452c", "#1f4e79", "#2e7d32"])):
    ax.bar(x + (i - 1) * w, [power_v[i], fp_v[i]], w, label=lab, color=colour,
           alpha=0.88)
ax.set_xticks(x)
ax.set_xticklabels(["power\n(real effects)", "false positives\n(null metrics)"])
ax.set_ylabel("%")
ax.set_title("The cost of correcting\npower falls as well as error")
ax.legend(fontsize=8)
ax.grid(alpha=0.25, axis="y")

fig.suptitle("SIMULATED DATA — multiple comparisons, not a Cookie Cats result "
             "(plan §7)", fontsize=11)
fig.tight_layout()
out_fig = FIGURES / "sim_multiple_comparisons.png"
fig.savefig(out_fig, dpi=140)
plt.close(fig)

results = {
    "note": "SIMULATED DATA. Not a finding about Cookie Cats.",
    "n_sims": N_SIMS, "k_metrics": K, "n_per_arm": N_PER_ARM, "alpha": ALPHA,
    "theoretical_fwer": float(1 - (1 - ALPHA) ** K),
    "observed_fwer_uncorrected": float(any_raw.mean()),
    "observed_fwer_bonferroni": float(bonf.mean()),
    "observed_fwer_bh": float(bh.mean()),
    "power_uncorrected": float(rej_raw[:, true_idx].mean()),
    "power_bonferroni": float(rej_bonf[:, true_idx].mean()),
    "power_bh": float(rej_bh[:, true_idx].mean()),
}
say.save()
out = TABLES / "sim_multiple_comparisons.json"
out.write_text(json.dumps(results, indent=2), encoding="utf-8")
print(f"[written] {out.relative_to(ROOT)}")
print(f"[written] {out_fig.relative_to(ROOT)}")
