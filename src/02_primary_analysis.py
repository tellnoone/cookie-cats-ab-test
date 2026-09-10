"""
Primary metric: 7-day retention (ANALYSIS_PLAN.md sections 3 and 6).

Two-proportion z-test, absolute difference with a 95% CI, relative lift against
a stated baseline, and a 10,000-iteration bootstrap.

The plan's decision rule keys off the CONFIDENCE INTERVAL'S LOWER BOUND against
the 1.0pp MDE, not off the p-value. That is implemented literally below.

This script reads outputs/tables/01_validation_gate.json. If validation failed,
it still computes the estimate -- the magnitude is informative -- but it reports
NO SHIP DECISION, per the section 4 contingency.
"""

from __future__ import annotations

import json

import numpy as np
from scipy import stats
from statsmodels.stats.proportion import proportions_ztest

from common import (ALPHA, CONTROL, MDE, N_BOOT, PRIMARY, ROOT, SEED, TABLES,
                    TREATMENT, Report, arms, load)

say = Report(TABLES / "02_primary_analysis.txt")
rng = np.random.default_rng(SEED)

# ---------------------------------------------------------------------------
# Validation gate
# ---------------------------------------------------------------------------
gate_path = TABLES / "01_validation_gate.json"
if not gate_path.exists():
    raise SystemExit("Run 01_validation.py first. The plan requires validation "
                     "to run before outcome analysis.")
gate = json.loads(gate_path.read_text(encoding="utf-8"))
conditional = gate["gate"]["conditional_analysis_required"]

say.head("PRIMARY METRIC: 7-DAY RETENTION")
say()

if conditional:
    say("!" * 74)
    say("!!  READ THIS BEFORE THE RESULT")
    say("!" * 74)
    say()
    say(f"  Validation FAILED {gate['gate']['n_failed']} of 5 checks. Sample Ratio")
    say(f"  Mismatch: p = {gate['srm']['p']:.6f}, below the pre-registered 0.01 trigger.")
    say()
    say("  Per ANALYSIS_PLAN.md section 4, this analysis is CONDITIONAL. The arms are")
    say("  not demonstrably exchangeable, so no ship/no-ship decision is drawn from")
    say("  the primary metric below. The estimate is reported because its magnitude")
    say("  is informative, but it is evidence from a compromised experiment.")
    say()
    say("!" * 74)
    say()

df = load()
ctl, trt = arms(df)

# ---------------------------------------------------------------------------
# Point estimates
# ---------------------------------------------------------------------------
x_c, n_c = int(ctl[PRIMARY].sum()), len(ctl)
x_t, n_t = int(trt[PRIMARY].sum()), len(trt)
p_c, p_t = x_c / n_c, x_t / n_t
diff = p_t - p_c
rel = diff / p_c

say.head("Observed retention")
say()
say(f"  {'arm':<12s}{'n':>10s}{'retained':>11s}{'rate':>10s}")
say(f"  {CONTROL + ' (ctl)':<12s}{n_c:>10,d}{x_c:>11,d}{p_c:>9.4%}")
say(f"  {TREATMENT + ' (trt)':<12s}{n_t:>10,d}{x_t:>11,d}{p_t:>9.4%}")
say()
say(f"  Absolute difference (trt - ctl) : {diff*100:+.4f} pp")
say(f"  Relative lift                   : {rel:+.3%}  (on a {p_c:.2%} baseline)")
say()
say("  The relative figure is shown with the baseline attached because a")
say("  '4% change in retention' means nothing without knowing 4% of what.")
say()

# ---------------------------------------------------------------------------
# Two-proportion z-test + CI
# ---------------------------------------------------------------------------
say.head("Two-proportion z-test (plan section 6)")
say()
z, p_val = proportions_ztest([x_t, x_c], [n_t, n_c], alternative="two-sided")

# Unpooled SE for the CI on the difference (the pooled SE belongs to the test).
se_diff = np.sqrt(p_t * (1 - p_t) / n_t + p_c * (1 - p_c) / n_c)
z_crit = stats.norm.ppf(1 - ALPHA / 2)
ci_lo, ci_hi = diff - z_crit * se_diff, diff + z_crit * se_diff

say(f"  z statistic          : {z:+.4f}")
say(f"  p-value (two-sided)  : {p_val:.4f}")
say(f"  alpha                : {ALPHA}")
say()
say(f"  Difference           : {diff*100:+.4f} pp")
say(f"  95% CI (normal)      : [{ci_lo*100:+.4f}, {ci_hi*100:+.4f}] pp")
say(f"  SE of difference     : {se_diff*100:.4f} pp")
say()
chi2, p_chi = stats.chi2_contingency(
    np.array([[x_t, n_t - x_t], [x_c, n_c - x_c]]), correction=False)[:2]
say(f"  Chi-square cross-check : chi2 = {chi2:.4f}, p = {p_chi:.4f}")
say("  (Equivalent to the z-test, as the plan notes. Agreement is a sanity check.)")
say()

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------
say.head(f"Bootstrap ({N_BOOT:,d} iterations, percentile CI)")
say()
say("  Resampling with replacement WITHIN each arm, so arm sizes are preserved")
say("  and only sampling variation in the outcome is simulated.")
say()

# Binomial draws are exact for a resampled mean of a 0/1 vector and avoid
# materialising 10,000 x 90,189 booleans.
boot_c = rng.binomial(n_c, p_c, N_BOOT) / n_c
boot_t = rng.binomial(n_t, p_t, N_BOOT) / n_t
boot_diff = boot_t - boot_c

b_lo, b_hi = np.percentile(boot_diff, [100 * ALPHA / 2, 100 * (1 - ALPHA / 2)])
p_trt_wins = float((boot_diff > 0).mean())

say(f"  Bootstrap mean difference : {boot_diff.mean()*100:+.4f} pp")
say(f"  Bootstrap SE              : {boot_diff.std(ddof=1)*100:.4f} pp")
say(f"  95% percentile CI         : [{b_lo*100:+.4f}, {b_hi*100:+.4f}] pp")
say()
say("  Agreement with the normal-approximation CI above is expected here: n is")
say("  large and p is near 0.19, so the approximation is comfortable. The")
say("  bootstrap is reported because it does not RELY on that being true.")
say()
say.rule()
say("  For a non-technical stakeholder:")
say()
say(f"    In {p_trt_wins:.1%} of {N_BOOT:,d} simulated re-runs of this experiment,")
say(f"    the gate-40 arm had higher 7-day retention than gate-30.")
say(f"    In {1-p_trt_wins:.1%} of them, gate-30 was higher.")
say()
say("    A coin-flip result would be 50%. This is not that.")
say.rule()
say()

# ---------------------------------------------------------------------------
# Decision rule
# ---------------------------------------------------------------------------
say.head("DECISION RULE (plan section 3, applied literally)")
say()
say(f"  MDE threshold        : {MDE*100:.1f} pp absolute")
say(f"  Observed difference  : {diff*100:+.4f} pp")
say(f"  95% CI               : [{ci_lo*100:+.4f}, {ci_hi*100:+.4f}] pp")
say()

significant = p_val < ALPHA
ci_spans_zero = ci_lo < 0 < ci_hi
ci_above_mde = ci_lo > MDE
ci_below_mde = ci_hi < MDE

say(f"  statistically significant at {ALPHA}   : {significant}")
say(f"  CI spans zero                     : {ci_spans_zero}")
say(f"  CI lower bound exceeds MDE        : {ci_above_mde}")
say(f"  CI entirely below the MDE         : {ci_below_mde}")
say()

if ci_spans_zero:
    row = "Confidence interval spans zero"
    verdict = "DO NOT SHIP -- report as null"
elif diff < 0 and significant:
    row = "Effect is negative and significant"
    verdict = ("DO NOT SHIP -- investigate whether the gate serves a function we "
               "did not anticipate")
elif ci_above_mde:
    row = "Positive, significant, CI lower bound exceeds MDE"
    verdict = "SHIP"
else:
    row = "Positive and significant but CI includes effects below the MDE"
    verdict = "DO NOT SHIP on this evidence -- underpowered for a decision"

say(f"  Matched rule : {row}")
say(f"  Pre-registered verdict : {verdict}")
say()

if ci_below_mde:
    say("  Additionally, the whole interval lies below +1.0pp. Per section 8 item 1,")
    say("  this abandons the hypothesis for decision purposes: even the optimistic")
    say("  end of what the data supports is not worth shipping.")
    say()

if conditional:
    say.rule("!")
    say("  BUT: validation failed. Per section 4, the above verdict is NOT issued as")
    say("  the recommendation. The recommendation is to re-run the test with")
    say("  assignment fixed. See section 9 of the plan for the deviation log.")
    say.rule("!")
say()

results = {
    "n_control": n_c, "n_treatment": n_t,
    "rate_control": p_c, "rate_treatment": p_t,
    "abs_diff": diff, "rel_lift": rel,
    "z": float(z), "p_value": float(p_val),
    "ci_lower": float(ci_lo), "ci_upper": float(ci_hi), "se": float(se_diff),
    "boot_ci_lower": float(b_lo), "boot_ci_upper": float(b_hi),
    "boot_p_treatment_wins": p_trt_wins,
    "significant": bool(significant), "ci_spans_zero": bool(ci_spans_zero),
    "ci_below_mde": bool(ci_below_mde),
    "matched_rule": row, "verdict": verdict,
    "conditional_on_failed_validation": bool(conditional),
}
say.save()
out = TABLES / "02_primary_results.json"
out.write_text(json.dumps(results, indent=2), encoding="utf-8")
print(f"[written] {out.relative_to(ROOT)}")
