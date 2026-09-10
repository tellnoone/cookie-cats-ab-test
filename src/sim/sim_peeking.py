"""
SIMULATED DATA ONLY (ANALYSIS_PLAN.md section 7).

Nothing in this file is a finding about Cookie Cats. The real dataset is a
finished snapshot with no timestamps, so it cannot support a sequential
analysis. Peeking is therefore demonstrated on data generated here.

What is demonstrated:
  1. A/A simulation with NO true effect, tested repeatedly as data accumulates.
     The false-positive rate rises well above the nominal 5%.
  2. The same simulation with an alpha-spending correction (O'Brien-Fleming-style
     via a Pocock/OBF boundary), restoring the intended error rate.
  3. For contrast, a single fixed-horizon test at the end, which is what the
     plan's "no peeking" rule enforces by construction.
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

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import ALPHA, FIGURES, ROOT, SEED, TABLES, Report  # noqa: E402

say = Report(TABLES / "sim_peeking.txt")
rng = np.random.default_rng(SEED)

N_SIMS = 2_000
N_FINAL = 20_000          # users per arm at the end of the "experiment"
N_LOOKS = 10              # equally spaced interim analyses
BASELINE = 0.19           # roughly Cookie Cats-like, for realism only

say.head("SIMULATION: THE COST OF PEEKING  (simulated data -- NOT Cookie Cats)")
say()
say("  " + "*" * 70)
say("  *  Every number below comes from data generated in this script.        *")
say("  *  None of it is a result about Cookie Cats. The real dataset has no   *")
say("  *  time dimension, so a sequential analysis is impossible on it.       *")
say("  " + "*" * 70)
say()
say(f"  Simulations        : {N_SIMS:,d}")
say(f"  Users per arm      : {N_FINAL:,d}")
say(f"  Interim looks      : {N_LOOKS} (equally spaced)")
say(f"  True effect        : ZERO (this is an A/A test)")
say(f"  Baseline rate      : {BASELINE:.0%}")
say(f"  Nominal alpha      : {ALPHA}")
say()

look_points = np.linspace(N_FINAL // N_LOOKS, N_FINAL, N_LOOKS).astype(int)


def run_aa(n_sims: int) -> np.ndarray:
    """Return an (n_sims, N_LOOKS) array of z-statistics from A/A experiments."""
    z = np.empty((n_sims, N_LOOKS))
    for i in range(n_sims):
        # Both arms drawn from the SAME distribution: no effect exists.
        a = rng.random(N_FINAL) < BASELINE
        b = rng.random(N_FINAL) < BASELINE
        ca, cb = np.cumsum(a), np.cumsum(b)
        for j, k in enumerate(look_points):
            pa, pb = ca[k - 1] / k, cb[k - 1] / k
            pool = (ca[k - 1] + cb[k - 1]) / (2 * k)
            se = np.sqrt(2 * pool * (1 - pool) / k)
            z[i, j] = (pb - pa) / se if se > 0 else 0.0
    return z


z = run_aa(N_SIMS)
z_crit = stats.norm.ppf(1 - ALPHA / 2)

# ---------------------------------------------------------------------------
# 1. Uncorrected peeking
# ---------------------------------------------------------------------------
say.head("1. UNCORRECTED: stop as soon as p < 0.05")
say()
crossed = np.abs(z) > z_crit
ever = crossed.any(axis=1)
fixed_only = crossed[:, -1]

say(f"  {'look':>6s}{'n/arm':>9s}{'false pos at this look':>26s}"
    f"{'cumulative':>13s}")
for j, k in enumerate(look_points):
    cum = crossed[:, :j + 1].any(axis=1).mean()
    say(f"  {j+1:>6d}{k:>9,d}{crossed[:, j].mean():>25.2%}{cum:>13.2%}")
say()
say(f"  False-positive rate, ONE test at the end : {fixed_only.mean():.2%}"
    f"   (nominal {ALPHA:.0%})")
say(f"  False-positive rate, peeking {N_LOOKS} times   : {ever.mean():.2%}")
say(f"  Inflation factor                         : {ever.mean()/ALPHA:.2f}x")
say()
say("  There is no effect in this data. Any 'significant' result is a false")
say(f"  positive by construction. Testing once behaves as advertised ({fixed_only.mean():.1%}).")
say(f"  Testing ten times as the data arrives finds a spurious winner "
    f"{ever.mean():.0%} of")
say("  the time -- and the analyst who stops at the first significant look has")
say("  no way of telling that is what happened.")
say()

# ---------------------------------------------------------------------------
# 2. Corrected with an alpha-spending boundary
# ---------------------------------------------------------------------------
say.head("2. CORRECTED: O'Brien-Fleming alpha-spending boundary")
say()
say("  The fix is to spend the error budget across the looks rather than")
say("  charging the full 5% at each one. O'Brien-Fleming spends very little")
say("  early -- an early stop must clear a high bar -- and approaches the")
say("  nominal alpha at the final look.")
say()

frac = look_points / N_FINAL


def obf_boundary(t: np.ndarray, alpha: float) -> np.ndarray:
    """O'Brien-Fleming z-boundary: z_crit(alpha/2) / sqrt(t), calibrated."""
    return stats.norm.ppf(1 - alpha / 2) / np.sqrt(t)


# Calibrate the overall alpha so the family-wise rate lands on 0.05.
def fwer_for(scale: float) -> float:
    bound = obf_boundary(frac, ALPHA) * scale
    return float((np.abs(z) > bound).any(axis=1).mean())


lo, hi = 0.5, 2.0
for _ in range(60):
    mid = (lo + hi) / 2
    if fwer_for(mid) > ALPHA:
        lo = mid
    else:
        hi = mid
scale = (lo + hi) / 2
bound = obf_boundary(frac, ALPHA) * scale

say(f"  {'look':>6s}{'n/arm':>9s}{'info frac':>12s}{'z boundary':>13s}"
    f"{'~nominal p':>14s}")
for j, k in enumerate(look_points):
    p_equiv = 2 * stats.norm.sf(bound[j])
    say(f"  {j+1:>6d}{k:>9,d}{frac[j]:>12.2f}{bound[j]:>13.3f}{p_equiv:>14.2e}")
say()
corrected = (np.abs(z) > bound).any(axis=1).mean()
say(f"  False-positive rate with the boundary : {corrected:.2%}"
    f"   (target {ALPHA:.0%})")
say(f"  Compare uncorrected                   : {ever.mean():.2%}")
say()
say("  Read the boundary column. To stop at the FIRST look you would need")
say(f"  p < {2*stats.norm.sf(bound[0]):.1e} -- not p < 0.05. That is the price of holding")
say("  the option to stop early, and it is a steep one at 10% of the data.")
say(f"  By the final look the bar has relaxed to p < {2*stats.norm.sf(bound[-1]):.4f}, just")
say("  inside the nominal 0.05, which is the characteristic OBF shape.")
say()
say("  This is why the plan fixes a single analysis: it buys the full 0.05 at")
say("  the one moment that matters, rather than rationing it across looks nobody")
say("  committed to in advance.")
say()

# ---------------------------------------------------------------------------
# 3. What the plan does
# ---------------------------------------------------------------------------
say.head("3. WHY THE PLAN SAYS 'NO PEEKING'")
say()
say("  Section 3 fixes one analysis on the full dataset after validation passes.")
say("  For this dataset that is enforced by construction -- it arrives as a")
say("  completed snapshot -- but the rule is stated because it is the rule that")
say("  would apply to a live test.")
say()
say("  The alternative is not 'never look'. It is: decide the looks in advance")
say("  and spend alpha across them, as in part 2. What is not available is")
say("  looking whenever you like and applying 0.05 each time, which is the")
say(f"  {ever.mean()/ALPHA:.1f}x inflation in part 1.")
say()

# ---------------------------------------------------------------------------
# Plot
# ---------------------------------------------------------------------------
fig, axes = plt.subplots(1, 3, figsize=(16, 4.7))

ax = axes[0]
cum_unc = [crossed[:, :j + 1].any(axis=1).mean() for j in range(N_LOOKS)]
cum_cor = [(np.abs(z[:, :j + 1]) > bound[:j + 1]).any(axis=1).mean()
           for j in range(N_LOOKS)]
ax.plot(range(1, N_LOOKS + 1), np.array(cum_unc) * 100, "o-", lw=2,
        color="#b3452c", label="peeking, uncorrected")
ax.plot(range(1, N_LOOKS + 1), np.array(cum_cor) * 100, "s-", lw=2,
        color="#1f4e79", label="O'Brien-Fleming boundary")
ax.axhline(ALPHA * 100, ls="--", color="#333", lw=1.3, label="nominal 5%")
ax.set_xlabel("number of looks taken")
ax.set_ylabel("cumulative false-positive rate (%)")
ax.set_title("A/A test: no effect exists\nyet peeking keeps finding one")
ax.legend(fontsize=8)
ax.grid(alpha=0.25)
ax.set_xticks(range(1, N_LOOKS + 1))

ax = axes[1]
ax.plot(frac, bound, "s-", lw=2, color="#1f4e79", label="OBF boundary")
ax.axhline(z_crit, ls="--", color="#b3452c", lw=1.3,
           label=f"fixed 0.05 ({z_crit:.2f})")
ax.set_xlabel("information fraction (n so far / n final)")
ax.set_ylabel("|z| required to stop")
ax.set_title("Alpha spending\nearly stops must clear a higher bar")
ax.legend(fontsize=8)
ax.grid(alpha=0.25)

ax = axes[2]
n_show = 60
for i in range(n_show):
    colour = "#b3452c" if ever[i] else "#bbbbbb"
    ax.plot(look_points, z[i], lw=0.8, alpha=0.65, color=colour)
ax.axhline(z_crit, ls="--", color="#333", lw=1.1)
ax.axhline(-z_crit, ls="--", color="#333", lw=1.1)
ax.plot(look_points, bound, lw=1.8, color="#1f4e79")
ax.plot(look_points, -bound, lw=1.8, color="#1f4e79")
ax.set_xlabel("users per arm")
ax.set_ylabel("z statistic")
ax.set_title(f"{n_show} A/A trajectories\nred = crossed 0.05 at some look")
ax.grid(alpha=0.25)

fig.suptitle("SIMULATED DATA — demonstrates peeking, not a Cookie Cats result "
             "(plan §7)", fontsize=11)
fig.tight_layout()
out_fig = FIGURES / "sim_peeking.png"
fig.savefig(out_fig, dpi=140)
plt.close(fig)

results = {
    "note": "SIMULATED DATA. Not a finding about Cookie Cats.",
    "n_sims": N_SIMS, "n_final_per_arm": N_FINAL, "n_looks": N_LOOKS,
    "true_effect": 0.0, "nominal_alpha": ALPHA,
    "fpr_single_test": float(fixed_only.mean()),
    "fpr_peeking": float(ever.mean()),
    "inflation_factor": float(ever.mean() / ALPHA),
    "fpr_obf_corrected": float(corrected),
    "obf_first_look_nominal_p": float(2 * stats.norm.sf(bound[0])),
    "obf_final_look_nominal_p": float(2 * stats.norm.sf(bound[-1])),
    "cumulative_fpr_by_look": [float(x) for x in cum_unc],
}
say.save()
out = TABLES / "sim_peeking.json"
out.write_text(json.dumps(results, indent=2), encoding="utf-8")
print(f"[written] {out.relative_to(ROOT)}")
print(f"[written] {out_fig.relative_to(ROOT)}")
