"""
SIMULATED DATA ONLY (ANALYSIS_PLAN.md section 7).

Nothing here is a finding about Cookie Cats.

CUPED (Controlled-experiment Using Pre-Experiment Data): use a pre-period
covariate correlated with the outcome to strip predictable variance out of the
estimate, tightening the confidence interval without changing what is being
estimated.

Why it must be simulated: CUPED needs a PRE-EXPERIMENT measurement per user.
The Cookie Cats snapshot has no pre-period -- `sum_gamerounds` is measured
during the experiment and is affected by the gate, so using it as the covariate
would bias the estimate rather than de-noise it. That is not a technicality; it
is the difference between CUPED and a broken analysis.

Reported: the variance reduction achieved, and the corresponding reduction in
required sample size.
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
from common import ALPHA, FIGURES, POWER, ROOT, SEED, TABLES, Report  # noqa: E402

say = Report(TABLES / "sim_cuped.txt")
rng = np.random.default_rng(SEED)

N_SIMS = 2_000
N_PER_ARM = 10_000
TRUE_EFFECT = 0.010      # +1.0pp, the MDE the real plan pre-registered
BASE_LOGIT = -2.30       # calibrated to ~19% baseline, close to Cookie Cats
U_COEF_X = 1.10          # latent -> pre-period covariate
U_COEF_Y = 2.00          # latent -> outcome
X_SCALE = 2.20

say.head("SIMULATION: CUPED VARIANCE REDUCTION  (simulated -- NOT Cookie Cats)")
say()
say("  " + "*" * 70)
say("  *  Every number below is generated in this script.                     *")
say("  *  The Cookie Cats snapshot has NO pre-experiment period, so CUPED     *")
say("  *  cannot be applied to it. Using sum_gamerounds as the covariate      *")
say("  *  would be invalid: it is measured during the experiment and is       *")
say("  *  affected by the treatment.                                          *")
say("  " + "*" * 70)
say()
say(f"  Simulations    : {N_SIMS:,d}")
say(f"  Users per arm  : {N_PER_ARM:,d}")
say(f"  True effect    : {TRUE_EFFECT*100:+.1f} pp")
say()

# ---------------------------------------------------------------------------
# Data generating process
# ---------------------------------------------------------------------------
say.head("1. THE SETUP")
say()
say("  Each simulated user has a latent engagement level u ~ N(0, 1).")
say()
say(f"    pre-period covariate  X = Poisson(exp({X_SCALE} + {U_COEF_X}u))")
say("        -- e.g. rounds played in the week BEFORE the experiment started")
say(f"    outcome               Y = Bernoulli(sigmoid({BASE_LOGIT} + {U_COEF_Y}u) "
    f"+ effect)")
say()
say("  u drives both, so X predicts Y without being caused by the treatment.")
say("  That is exactly the property CUPED needs, and exactly the property")
say("  sum_gamerounds lacks in the real dataset.")
say()


def gen_arm(n: int, effect: float) -> tuple[np.ndarray, np.ndarray]:
    """Return (X pre-period covariate, Y binary outcome) for one arm."""
    u = rng.standard_normal(n)
    x = rng.poisson(np.exp(X_SCALE + U_COEF_X * u))
    # Effect applied on the probability scale so it is a clean +1.0pp.
    p = 1 / (1 + np.exp(-(BASE_LOGIT + U_COEF_Y * u)))
    y = (rng.random(n) < np.clip(p + effect, 0, 1)).astype(float)
    return x, y


# ---------------------------------------------------------------------------
# One large draw, to characterise the covariate
# ---------------------------------------------------------------------------
x0, y0 = gen_arm(200_000, 0.0)
rho = float(np.corrcoef(x0, y0)[0, 1])
say(f"  Correlation between X and Y : rho = {rho:.4f}")
say(f"  Theoretical variance reduction = rho^2 = {rho**2:.4f}  "
    f"({rho**2:.1%})")
say(f"  Baseline outcome rate       : {y0.mean():.2%}")
say()
say("  CUPED's variance reduction is rho^2 and nothing else. That single fact is")
say("  the most useful thing to know about it -- the payoff is quadratic, so a")
say("  mediocre covariate is nearly worthless and a strong one is transformative.")
say()
say("  Covariate strength sweep (theoretical, from rho^2):")
say()
say(f"    {'rho':>6s}{'var reduction':>16s}{'n needed':>12s}{'verdict':>26s}")
for r_, verdict in ((0.1, "not worth the pipeline"), (0.2, "marginal"),
                    (0.3, "modest"), (0.5, "worthwhile"),
                    (0.7, "large"), (0.9, "transformative")):
    say(f"    {r_:>6.1f}{r_**2:>15.1%}{1-r_**2:>11.0%}{verdict:>26s}")
say()
say(f"  This simulation's covariate sits at rho = {rho:.2f}, so it is in the")
say("  'worthwhile' band -- a realistic figure for a pre-period engagement")
say("  metric predicting retention.")
say()

# ---------------------------------------------------------------------------
# 2. Run the experiments
# ---------------------------------------------------------------------------
say.head("2. PLAIN vs CUPED, over many simulated experiments")
say()

est_plain = np.empty(N_SIMS)
est_cuped = np.empty(N_SIMS)
se_plain = np.empty(N_SIMS)
se_cuped = np.empty(N_SIMS)

for i in range(N_SIMS):
    xc, yc = gen_arm(N_PER_ARM, 0.0)
    xt, yt = gen_arm(N_PER_ARM, TRUE_EFFECT)

    # --- Plain difference in means ---
    est_plain[i] = yt.mean() - yc.mean()
    se_plain[i] = np.sqrt(yt.var(ddof=1) / len(yt) + yc.var(ddof=1) / len(yc))

    # --- CUPED ---
    # theta from the POOLED data. X is pre-treatment, so pooling does not leak
    # the treatment effect into the adjustment.
    x_all = np.concatenate([xc, xt])
    y_all = np.concatenate([yc, yt])
    theta = np.cov(y_all, x_all, ddof=1)[0, 1] / x_all.var(ddof=1)
    xbar = x_all.mean()

    yc_adj = yc - theta * (xc - xbar)
    yt_adj = yt - theta * (xt - xbar)
    est_cuped[i] = yt_adj.mean() - yc_adj.mean()
    se_cuped[i] = np.sqrt(yt_adj.var(ddof=1) / len(yt_adj)
                          + yc_adj.var(ddof=1) / len(yc_adj))

var_red = 1 - est_cuped.var(ddof=1) / est_plain.var(ddof=1)

say(f"  {'':<26s}{'plain':>14s}{'CUPED':>14s}")
say(f"  {'mean estimate (pp)':<26s}{est_plain.mean()*100:>14.4f}"
    f"{est_cuped.mean()*100:>14.4f}")
say(f"  {'true effect (pp)':<26s}{TRUE_EFFECT*100:>14.4f}"
    f"{TRUE_EFFECT*100:>14.4f}")
say(f"  {'bias (pp)':<26s}{(est_plain.mean()-TRUE_EFFECT)*100:>14.4f}"
    f"{(est_cuped.mean()-TRUE_EFFECT)*100:>14.4f}")
say(f"  {'SD of estimates (pp)':<26s}{est_plain.std(ddof=1)*100:>14.4f}"
    f"{est_cuped.std(ddof=1)*100:>14.4f}")
say(f"  {'mean analytic SE (pp)':<26s}{se_plain.mean()*100:>14.4f}"
    f"{se_cuped.mean()*100:>14.4f}")
say()
say("  Both are unbiased -- CUPED reduces variance WITHOUT moving the estimate.")
say("  That is the property that makes it legitimate rather than a thumb on the")
say("  scale. It removes variance that the covariate could have predicted anyway.")
say()
say(f"  Observed variance reduction : {var_red:.2%}")
say(f"  Predicted (rho^2)           : {rho**2:.2%}")
say(f"  SE reduction                : "
    f"{1 - se_cuped.mean()/se_plain.mean():.2%}")
say()

# ---------------------------------------------------------------------------
# 3. What that buys in sample size
# ---------------------------------------------------------------------------
say.head("3. WHAT THE VARIANCE REDUCTION BUYS")
say()
say("  Required n scales with the variance of the estimator, so cutting")
say(f"  variance by {var_red:.1%} cuts the required sample by the same factor.")
say()
z_a = stats.norm.ppf(1 - ALPHA / 2)
z_b = stats.norm.ppf(POWER)
p0 = float(y0.mean())
n_plain = ((z_a + z_b) ** 2 * 2 * p0 * (1 - p0)) / TRUE_EFFECT ** 2
n_cuped = n_plain * (1 - var_red)

say(f"  To detect {TRUE_EFFECT*100:.1f}pp at {POWER:.0%} power, alpha = {ALPHA}:")
say(f"    plain  : {np.ceil(n_plain):>9,.0f} users per arm")
say(f"    CUPED  : {np.ceil(n_cuped):>9,.0f} users per arm")
say(f"    saving : {np.ceil(n_plain-n_cuped):>9,.0f} users per arm "
    f"({1-n_cuped/n_plain:.1%})")
say()
say("  Equivalently, at a fixed sample size the experiment finishes sooner, or")
say("  detects a smaller effect for the same duration.")
say()

# Power at fixed n
crit = z_a
pow_plain = float((np.abs(est_plain / se_plain) > crit).mean())
pow_cuped = float((np.abs(est_cuped / se_cuped) > crit).mean())
say(f"  Power at the simulated n = {N_PER_ARM:,d} per arm:")
say(f"    plain : {pow_plain:.2%}")
say(f"    CUPED : {pow_cuped:.2%}")
say()

# Type I error preserved?
say("  Sanity check -- type I error under a TRUE NULL (effect = 0):")
null_p, null_c = [], []
for _ in range(600):
    xc, yc = gen_arm(N_PER_ARM, 0.0)
    xt, yt = gen_arm(N_PER_ARM, 0.0)
    sp = np.sqrt(yt.var(ddof=1) / len(yt) + yc.var(ddof=1) / len(yc))
    null_p.append(abs(yt.mean() - yc.mean()) / sp > crit)
    x_all = np.concatenate([xc, xt]); y_all = np.concatenate([yc, yt])
    th = np.cov(y_all, x_all, ddof=1)[0, 1] / x_all.var(ddof=1)
    xb = x_all.mean()
    ya, yb_ = yc - th * (xc - xb), yt - th * (xt - xb)
    sc = np.sqrt(yb_.var(ddof=1) / len(yb_) + ya.var(ddof=1) / len(ya))
    null_c.append(abs(yb_.mean() - ya.mean()) / sc > crit)
say(f"    plain : {np.mean(null_p):.2%}   (target {ALPHA:.0%})")
say(f"    CUPED : {np.mean(null_c):.2%}   (target {ALPHA:.0%})")
say()
say("  CUPED buys power without inflating the false-positive rate. It is a")
say("  variance-reduction technique, not a significance-manufacturing one.")
say()

say.head("4. WHY THIS IS NOT APPLIED TO THE REAL DATA")
say()
say("  The temptation with the Cookie Cats snapshot is to use sum_gamerounds as")
say("  the covariate, since it is strongly correlated with retention. That would")
say("  be wrong. CUPED requires the covariate to be measured BEFORE treatment")
say("  assignment. sum_gamerounds is measured during the experiment, and the")
say("  gate directly changes it -- section 5B of the segment analysis shows the")
say("  treatment shifting users between rounds buckets (chi2 p = 0.0001).")
say()
say("  Adjusting for a treatment-affected covariate does not de-noise the")
say("  estimate; it removes part of the causal effect being measured. The")
say("  honest position is that this dataset does not support CUPED, which is")
say("  why section 7 of the plan put it here with simulated data.")

# ---------------------------------------------------------------------------
# Plot
# ---------------------------------------------------------------------------
fig, axes = plt.subplots(1, 3, figsize=(15.5, 4.7))

ax = axes[0]
bins = np.linspace(min(est_plain.min(), est_cuped.min()) * 100,
                   max(est_plain.max(), est_cuped.max()) * 100, 55)
ax.hist(est_plain * 100, bins=bins, alpha=0.6, label="plain", color="#b3452c",
        density=True)
ax.hist(est_cuped * 100, bins=bins, alpha=0.6, label="CUPED", color="#1f4e79",
        density=True)
ax.axvline(TRUE_EFFECT * 100, ls="--", color="#333", lw=1.4,
           label=f"true {TRUE_EFFECT*100:.1f}pp")
ax.set_xlabel("estimated effect (pp)")
ax.set_ylabel("density")
ax.set_title(f"Same centre, narrower spread\nvariance reduced {var_red:.0%}")
ax.legend(fontsize=8)
ax.grid(alpha=0.25)

ax = axes[1]
rhos = np.linspace(0, 0.95, 200)
ax.plot(rhos, (1 - rhos ** 2) * 100, lw=2, color="#1f4e79")
ax.axvline(abs(rho), ls=":", color="#b3452c", lw=1.5)
ax.axhline((1 - rho ** 2) * 100, ls=":", color="#b3452c", lw=1.5)
ax.annotate(f"this covariate\nrho = {rho:.2f}\nn needed {(1-rho**2)*100:.0f}%",
            xy=(abs(rho) + 0.03, (1 - rho ** 2) * 100 + 4), fontsize=8,
            color="#b3452c")
ax.set_xlabel("correlation between covariate and outcome")
ax.set_ylabel("required sample size, % of plain")
ax.set_title("CUPED payoff is rho²\nweak covariates buy almost nothing")
ax.grid(alpha=0.25)

ax = axes[2]
labels = ["plain", "CUPED"]
vals = [np.ceil(n_plain), np.ceil(n_cuped)]  # match the reported figures
bars = ax.bar(labels, vals, color=["#b3452c", "#1f4e79"], alpha=0.88)
for b, v in zip(bars, vals):
    ax.text(b.get_x() + b.get_width() / 2, v * 1.01, f"{v:,.0f}", ha="center",
            fontsize=9)
ax.set_ylabel("users per arm required")
ax.set_title(f"n to detect {TRUE_EFFECT*100:.1f}pp at {POWER:.0%} power\n"
             f"{1-n_cuped/n_plain:.0%} fewer users")
ax.grid(alpha=0.25, axis="y")

fig.suptitle("SIMULATED DATA — CUPED needs a pre-period the real snapshot does "
             "not have (plan §7)", fontsize=11)
fig.tight_layout()
out_fig = FIGURES / "sim_cuped.png"
fig.savefig(out_fig, dpi=140)
plt.close(fig)

results = {
    "note": "SIMULATED DATA. Not a finding about Cookie Cats.",
    "n_sims": N_SIMS, "n_per_arm": N_PER_ARM, "true_effect": TRUE_EFFECT,
    "correlation_x_y": rho, "theoretical_var_reduction": float(rho ** 2),
    "observed_var_reduction": float(var_red),
    "se_reduction": float(1 - se_cuped.mean() / se_plain.mean()),
    "bias_plain_pp": float((est_plain.mean() - TRUE_EFFECT) * 100),
    "bias_cuped_pp": float((est_cuped.mean() - TRUE_EFFECT) * 100),
    "n_required_plain": float(np.ceil(n_plain)),
    "n_required_cuped": float(np.ceil(n_cuped)),
    "sample_saving": float(1 - n_cuped / n_plain),
    "power_plain": pow_plain, "power_cuped": pow_cuped,
    "type1_plain": float(np.mean(null_p)), "type1_cuped": float(np.mean(null_c)),
}
say.save()
out = TABLES / "sim_cuped.json"
out.write_text(json.dumps(results, indent=2), encoding="utf-8")
print(f"[written] {out.relative_to(ROOT)}")
print(f"[written] {out_fig.relative_to(ROOT)}")
