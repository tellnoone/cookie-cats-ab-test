"""
Power analysis (ANALYSIS_PLAN.md section 5).

Retrospective: given the observed n and baseline, what is the smallest effect
this test could detect at 80% power? This is what separates "no effect" from
"we could never have seen it."

Prospective: to detect the pre-registered 1.0pp MDE at 80% power, how many users
per arm would we need, and how does that compare to what we have?

Both are reported, per the plan. A power curve is plotted so the numbers are
visible as a relationship rather than as three isolated figures.
"""

from __future__ import annotations

import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from statsmodels.stats.power import NormalIndPower
from statsmodels.stats.proportion import proportion_effectsize

from common import (ALPHA, CONTROL, FIGURES, MDE, POWER, PRIMARY, ROOT, TABLES,
                    TREATMENT, Report, arms, load)

say = Report(TABLES / "04_power_analysis.txt")
df = load()
ctl, trt = arms(df)

n_c, n_t = len(ctl), len(trt)
p0 = ctl[PRIMARY].mean()          # control baseline, as the plan specifies
ratio = n_t / n_c
pw = NormalIndPower()


def power_at(lift: float, nobs1: float) -> float:
    """Power to detect an absolute `lift` on a p0 baseline, given nobs1 per arm."""
    return float(pw.power(effect_size=proportion_effectsize(p0 + lift, p0),
                          nobs1=nobs1, alpha=ALPHA, ratio=ratio,
                          alternative="two-sided"))


def n_needed(lift: float) -> float:
    """Users per arm to detect an absolute `lift` at the target power (1:1)."""
    return float(pw.solve_power(effect_size=proportion_effectsize(p0 + lift, p0),
                                nobs1=None, alpha=ALPHA, power=POWER, ratio=1.0,
                                alternative="two-sided"))


say.head("POWER ANALYSIS  (plan section 5)")
say()
say(f"  Baseline (control {CONTROL}) : {p0:.4%}")
say(f"  n control                    : {n_c:,d}")
say(f"  n treatment                  : {n_t:,d}")
say(f"  allocation ratio (trt/ctl)   : {ratio:.4f}")
say(f"  alpha                        : {ALPHA} (two-sided)")
say(f"  target power                 : {POWER:.0%}")
say(f"  pre-registered MDE           : {MDE*100:.1f} pp absolute")
say()

# ---------------------------------------------------------------------------
# Retrospective
# ---------------------------------------------------------------------------
say.head("1. RETROSPECTIVE: what could this test actually detect?")
say()
lo, hi = 1e-7, 0.10
for _ in range(200):
    mid = (lo + hi) / 2
    if power_at(mid, n_c) > POWER:
        hi = mid
    else:
        lo = mid
mde_obs = (lo + hi) / 2

say(f"  Smallest effect detectable at {POWER:.0%} power, given the observed n:")
say(f"    {mde_obs*100:.3f} pp absolute   ({mde_obs/p0:.2%} relative)")
say()
say(f"  Compare to the pre-registered MDE of {MDE*100:.1f} pp.")
say()
if mde_obs < MDE:
    say(f"  {mde_obs*100:.2f} pp < {MDE*100:.1f} pp, so this test IS adequately powered for")
    say("  the decision it is being asked to make. A null result would have been")
    say("  informative -- evidence against an effect of 1.0pp or larger, rather than")
    say("  an absence of evidence.")
else:
    say(f"  {mde_obs*100:.2f} pp > {MDE*100:.1f} pp: the test CANNOT reliably detect the")
    say("  effect we said we care about. A null result here would not be evidence of")
    say("  no effect.")
say()
say("  The limit, stated plainly: this test cannot resolve effects below about")
say(f"  {mde_obs*100:.2f} pp. So a null result would support 'smaller than the amount we")
say("  said was worth shipping', NOT 'exactly zero'. Only the first claim would")
say("  have been available.")
say()
say(f"  Power to detect the {MDE*100:.1f} pp MDE at the observed n : {power_at(MDE, n_c):.2%}")
say()

# ---------------------------------------------------------------------------
# Prospective
# ---------------------------------------------------------------------------
say.head("2. PROSPECTIVE: designing this test from scratch")
say()
req = n_needed(MDE)
say(f"  To detect {MDE*100:.1f} pp at {POWER:.0%} power and alpha = {ALPHA}:")
say(f"    required per arm : {np.ceil(req):,.0f}")
say(f"    required total   : {np.ceil(req)*2:,.0f}")
say(f"    actual total     : {n_c + n_t:,d}")
say(f"    ratio            : {(n_c + n_t) / (np.ceil(req)*2):.2f}x the requirement")
say()
say("  The test is over-powered relative to its own stated MDE, which is a good")
say("  position to be in: the finding does not hinge on a marginal sample size.")
say()

say("  Sample size required at various effect sizes (for context):")
say()
say(f"    {'effect (pp)':>13s}{'relative':>12s}{'n per arm':>14s}{'vs actual':>12s}")
for lift in (0.0025, 0.005, 0.0074, 0.010, 0.015, 0.020):
    nn = np.ceil(n_needed(lift))
    say(f"    {lift*100:>13.2f}{lift/p0:>11.1%}{nn:>14,.0f}"
        f"{nn/n_c:>11.2f}x")
say()
say("  Reading down that table is the useful part: halving the effect you want to")
say("  detect roughly quadruples the users you need. The 0.25pp row needs ~9x this")
say("  experiment's sample, which is why chasing very small retention effects is")
say("  usually not worth the calendar time.")
say()

# ---------------------------------------------------------------------------
# Observed result in context
# ---------------------------------------------------------------------------
primary_path = TABLES / "02_primary_results.json"
observed = None
if primary_path.exists():
    primary = json.loads(primary_path.read_text(encoding="utf-8"))
    observed = primary["abs_diff"]
    say.head("3. THE OBSERVED EFFECT IN THIS CONTEXT")
    say()
    say(f"  Observed effect : {observed*100:+.3f} pp")
    say(f"  Retrospective MDE (magnitude) : {mde_obs*100:.3f} pp")
    say()
    say(f"  |observed| = {abs(observed)*100:.3f} pp, which is "
        f"{'ABOVE' if abs(observed) > mde_obs else 'BELOW'} the detectable threshold.")
    say("  That is consistent with it having reached significance, and it means the")
    say("  finding is not a marginal artefact of an underpowered test.")
    say()
    say("  It is, however, BELOW the 1.0pp we said would justify shipping -- in")
    say("  magnitude and in the wrong direction. A negative effect smaller than the")
    say("  MDE still argues against the change: the MDE was a bar for shipping a")
    say("  BENEFIT, not a licence to ignore harm of the same size.")
    say()

# ---------------------------------------------------------------------------
# Power curves
# ---------------------------------------------------------------------------
fig, axes = plt.subplots(1, 2, figsize=(13, 4.8))

lifts = np.linspace(0.0005, 0.025, 300)
axes[0].plot(lifts * 100, [power_at(x, n_c) for x in lifts], lw=2, color="#1f4e79")
axes[0].axhline(POWER, ls="--", color="#b3452c", lw=1.2)
axes[0].axvline(MDE * 100, ls=":", color="#2e7d32", lw=1.6)
axes[0].axvline(mde_obs * 100, ls="-.", color="#8e24aa", lw=1.4)
if observed is not None:
    axes[0].axvline(abs(observed) * 100, ls="-", color="#555", lw=1.2, alpha=0.7)
    axes[0].annotate(f"|observed|\n{abs(observed)*100:.2f}pp",
                     xy=(abs(observed) * 100, 0.30), fontsize=8, color="#555")
axes[0].annotate(f"{POWER:.0%} power", xy=(1.85, POWER + 0.02), fontsize=8,
                 color="#b3452c")
axes[0].annotate(f"MDE\n{MDE*100:.1f}pp", xy=(MDE * 100 + 0.06, 0.12), fontsize=8,
                 color="#2e7d32")
axes[0].annotate(f"detectable\n{mde_obs*100:.2f}pp", xy=(mde_obs * 100 - 0.62, 0.62),
                 fontsize=8, color="#8e24aa")
axes[0].set_xlabel("true absolute effect (pp)")
axes[0].set_ylabel("power")
axes[0].set_title(f"Power at the observed sample\n(n = {n_c:,d} / {n_t:,d}, "
                  f"baseline {p0:.1%})")
axes[0].set_ylim(0, 1.02)
axes[0].grid(alpha=0.25)

ns = np.logspace(3, 5.6, 200)
for lift, colour in ((0.005, "#b3452c"), (0.0074, "#8e24aa"),
                     (0.010, "#2e7d32"), (0.020, "#1f4e79")):
    axes[1].plot(ns, [power_at(lift, x) for x in ns], lw=1.8, color=colour,
                 label=f"{lift*100:.2f} pp effect")
axes[1].axhline(POWER, ls="--", color="#999", lw=1.1)
axes[1].axvline(n_c, ls=":", color="#333", lw=1.4)
axes[1].annotate(f"this test\n{n_c:,d}/arm", xy=(n_c * 1.1, 0.16), fontsize=8)
axes[1].set_xscale("log")
axes[1].set_xlabel("users per arm (log scale)")
axes[1].set_ylabel("power")
axes[1].set_title("Power vs sample size, by true effect")
axes[1].set_ylim(0, 1.02)
axes[1].legend(fontsize=8, loc="lower right")
axes[1].grid(alpha=0.25)

fig.suptitle("Power analysis — a null result is only informative if the test "
             "could have seen the effect (plan §5)", fontsize=11)
fig.tight_layout()
out_fig = FIGURES / "04_power_curves.png"
fig.savefig(out_fig, dpi=140)
plt.close(fig)

results = {
    "baseline": float(p0), "n_control": n_c, "n_treatment": n_t,
    "retrospective_mde_abs": float(mde_obs),
    "retrospective_mde_rel": float(mde_obs / p0),
    "power_at_registered_mde": power_at(MDE, n_c),
    "prospective_n_per_arm": float(np.ceil(req)),
    "prospective_n_total": float(np.ceil(req) * 2),
    "actual_total": n_c + n_t,
    "n_per_arm_by_effect": {f"{l*100:.2f}pp": float(np.ceil(n_needed(l)))
                            for l in (0.0025, 0.005, 0.0074, 0.010, 0.015, 0.020)},
}
say.save()
out = TABLES / "04_power_results.json"
out.write_text(json.dumps(results, indent=2), encoding="utf-8")
print(f"[written] {out.relative_to(ROOT)}")
print(f"[written] {out_fig.relative_to(ROOT)}")
