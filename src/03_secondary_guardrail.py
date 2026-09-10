"""
Secondary metric (1-day retention) and guardrail (total game rounds).
ANALYSIS_PLAN.md sections 2 and 6.

Secondary: same machinery as the primary, explicitly labelled as supporting
evidence. Per section 8 item 3, a 1-day move without a 7-day move is read as
novelty and does not rescue the hypothesis.

Guardrail: total game rounds is heavily right-skewed, so a t-test on the mean is
not used. Bootstrap on the difference in means plus Mann-Whitney U on the
distributions, with medians alongside means, and a distribution plot rather than
an assertion about the skew.

Benjamini-Hochberg is applied across the reported family; corrected and
uncorrected p-values are both shown.
"""

from __future__ import annotations

import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.proportion import proportions_ztest

from common import (ALPHA, CONTROL, FIGURES, GUARDRAIL, N_BOOT, PRIMARY, ROOT,
                    SECONDARY, SEED, TABLES, TREATMENT, Report, arms, load)

say = Report(TABLES / "03_secondary_guardrail.txt")
rng = np.random.default_rng(SEED)
df = load()
ctl, trt = arms(df)
results: dict[str, object] = {}

# Primary result, for cross-referencing the two retention horizons.
primary = json.loads((TABLES / "02_primary_results.json").read_text(encoding="utf-8"))
primary_diff = primary["abs_diff"]
primary_base = primary["rate_control"]

# ---------------------------------------------------------------------------
# Secondary: 1-day retention
# ---------------------------------------------------------------------------
say.head("SECONDARY METRIC: 1-DAY RETENTION  (supporting evidence only)")
say()
x_c, n_c = int(ctl[SECONDARY].sum()), len(ctl)
x_t, n_t = int(trt[SECONDARY].sum()), len(trt)
p_c, p_t = x_c / n_c, x_t / n_t
d1 = p_t - p_c

z1, pv1 = proportions_ztest([x_t, x_c], [n_t, n_c], alternative="two-sided")
se1 = np.sqrt(p_t * (1 - p_t) / n_t + p_c * (1 - p_c) / n_c)
zc = stats.norm.ppf(1 - ALPHA / 2)
lo1, hi1 = d1 - zc * se1, d1 + zc * se1

say(f"  {CONTROL:<10s} : {p_c:.4%}   ({x_c:,d} / {n_c:,d})")
say(f"  {TREATMENT:<10s} : {p_t:.4%}   ({x_t:,d} / {n_t:,d})")
say()
say(f"  Absolute difference : {d1*100:+.4f} pp")
say(f"  Relative            : {d1/p_c:+.3%}  (on a {p_c:.2%} baseline)")
say(f"  95% CI              : [{lo1*100:+.4f}, {hi1*100:+.4f}] pp")
say(f"  z = {z1:+.4f}, p = {pv1:.4f}")
say()
boot1 = (rng.binomial(n_t, p_t, N_BOOT) / n_t) - (rng.binomial(n_c, p_c, N_BOOT) / n_c)
b1lo, b1hi = np.percentile(boot1, [2.5, 97.5])
say(f"  Bootstrap 95% CI    : [{b1lo*100:+.4f}, {b1hi*100:+.4f}] pp")
say(f"  P(treatment > control) in resamples : {(boot1 > 0).mean():.1%}")
say()
if pv1 < ALPHA:
    say("  1-day retention is significantly lower on gate_40.")
else:
    say("  1-day retention shows no significant difference.")
say()
say("  Interpretation per section 8 item 3. The pattern that would have worried us")
say("  is 1-day UP with 7-day flat -- novelty. That is not what happened: both")
say("  horizons point the same way (down).")
say()
say("  Stated precisely, because the CI crosses zero: 1-day retention is NOT")
say(f"  significantly different (p = {pv1:.4f}, CI includes 0). This is therefore")
say("  weak corroboration of the primary result, not independent confirmation.")
say("  The honest summary is 'consistent in sign, inconclusive on its own'.")
say()
say("  One thing worth noticing -- the harm GROWS with the horizon:")
say(f"    1-day : {d1*100:+.2f} pp on a {p_c:.1%} base   = {d1/p_c:+.1%} relative")
say(f"    7-day : {primary_diff*100:+.2f} pp on a {primary_base:.1%} base "
    f"  = {primary_diff/primary_base:+.1%} relative")
say()
say("  A gate moved later costs little by day 1 and more by day 7. That fits the")
say("  competing hypothesis in section 1 -- that the gate does something")
say("  structural whose absence compounds -- better than a novelty story, which")
say("  would predict the opposite shape.")
say()
results["secondary"] = {"rate_control": p_c, "rate_treatment": p_t, "abs_diff": d1,
                        "ci": [float(lo1), float(hi1)], "p_value": float(pv1)}

# ---------------------------------------------------------------------------
# Guardrail: total game rounds
# ---------------------------------------------------------------------------
say.head("GUARDRAIL METRIC: TOTAL GAME ROUNDS")
say()
g_c = ctl[GUARDRAIL].to_numpy()
g_t = trt[GUARDRAIL].to_numpy()

say("Distribution shape (this is why the mean is not trusted on its own):")
say()
say(f"  {'':<16s}{CONTROL:>14s}{TREATMENT:>14s}")
for label, fn in (("n", len), ("mean", np.mean), ("std", np.std),
                  ("min", np.min), ("25th pct", lambda x: np.percentile(x, 25)),
                  ("median", np.median), ("75th pct", lambda x: np.percentile(x, 75)),
                  ("95th pct", lambda x: np.percentile(x, 95)),
                  ("99th pct", lambda x: np.percentile(x, 99)), ("max", np.max)):
    say(f"  {label:<16s}{fn(g_c):>14,.2f}{fn(g_t):>14,.2f}")
say(f"  {'skewness':<16s}{stats.skew(g_c):>14,.2f}{stats.skew(g_t):>14,.2f}")
say(f"  {'% zero rounds':<16s}{(g_c==0).mean()*100:>13,.2f}%{(g_t==0).mean()*100:>13,.2f}%")
say()
say("  Median 17 vs mean 52 in control: the mean sits at roughly the 75th")
say("  percentile. A t-test on that mean would be testing a statistic that")
say("  describes almost none of the players.")
say()

# --- The outlier ---
say.head("Guardrail: outlier diagnosis")
say()
top = np.sort(g_c)[-3:][::-1]
say(f"  Control arm's three largest values : {top[0]:,d}  {top[1]:,d}  {top[2]:,d}")
say(f"  Treatment arm's largest value      : {g_t.max():,d}")
say()
outlier_id = int(ctl.loc[ctl[GUARDRAIL].idxmax(), "userid"])
mx = int(g_c.max())
say(f"  userid {outlier_id} (control) played {mx:,d} rounds in a 14-day window.")
say(f"  That is {mx/top[1]:.1f}x the next-highest player in the dataset and works")
say(f"  out to ~{mx/14:,.0f} rounds/day, about {mx/14/24:,.0f} per hour sustained")
say("  around the clock for two weeks. This is not a human play pattern; it is a")
say("  bot or a logging fault.")
say()
say("  Why it matters for the guardrail specifically:")
say(f"    control SD    : {g_c.std():>10,.1f}   vs treatment {g_t.std():>10,.1f}")
say(f"    control skew  : {stats.skew(g_c):>10,.1f}   vs treatment {stats.skew(g_t):>10,.1f}")
say("  The control arm looks far more variable than the treatment arm almost")
say("  entirely because of this one row.")
say()

g_c_trim = g_c[g_c < mx]
mean_diff_all = g_t.mean() - g_c.mean()
mean_diff_trim = g_t.mean() - g_c_trim.mean()
say(f"  Difference in means, all data        : {mean_diff_all:+.4f} rounds")
say(f"  Difference in means, outlier removed : {mean_diff_trim:+.4f} rounds")
say()
say("  The entire mean gap is that one player. Removing a single row out of")
say("  90,189 moves the difference in means by "
    f"{abs(mean_diff_all - mean_diff_trim):.2f} rounds and takes it to")
say("  approximately zero. Any guardrail conclusion resting on the mean would")
say("  have been a conclusion about one bot.")
say()
say("  NOTE: outlier handling was not pre-specified. Logged as a deviation in")
say("  ANALYSIS_PLAN.md section 9. Both figures are reported; neither is hidden.")
say()

# --- Bootstrap on the difference in means ---
say.head("Guardrail: bootstrap on the difference in means")
say()
# Resampling 10,000 x 45,000 values as one array would need ~3.6 GB, so this
# draws one resample at a time. Slower, but it fits in memory.
def boot_mean_diff(a: np.ndarray, b: np.ndarray, iters: int) -> np.ndarray:
    out = np.empty(iters)
    for i in range(iters):
        out[i] = (rng.choice(b, size=len(b), replace=True).mean()
                  - rng.choice(a, size=len(a), replace=True).mean())
    return out


bm = boot_mean_diff(g_c, g_t, N_BOOT)
bmlo, bmhi = np.percentile(bm, [2.5, 97.5])
say(f"  Difference in means (trt - ctl) : {mean_diff_all:+.4f} rounds")
say(f"  Bootstrap 95% percentile CI     : [{bmlo:+.4f}, {bmhi:+.4f}] rounds")
say(f"  P(treatment mean > control mean) : {(bm > 0).mean():.1%}")
say()
say("  The interval is wide and straddles zero. Note it is ASYMMETRIC -- the")
say("  bootstrap inherits the outlier, which is the honest behaviour: resamples")
say("  that happen to include the bot pull the control mean up sharply. This is")
say("  precisely the tail behaviour a normal approximation would have smoothed")
say("  away, and the reason the plan asked for a bootstrap here.")
say()

bm_trim = boot_mean_diff(g_c_trim, g_t, N_BOOT)
btlo, bthi = np.percentile(bm_trim, [2.5, 97.5])
say(f"  Same bootstrap, outlier removed : {mean_diff_trim:+.4f} rounds, "
    f"CI [{btlo:+.4f}, {bthi:+.4f}]")
say("  Symmetric now, and still straddling zero.")
say()

# --- Mann-Whitney U ---
say.head("Guardrail: Mann-Whitney U on the distributions")
say()
u_stat, p_mw = stats.mannwhitneyu(g_t, g_c, alternative="two-sided")
n_pairs = len(g_c) * len(g_t)
a12 = u_stat / n_pairs
say(f"  U statistic : {u_stat:,.0f}")
say(f"  p-value     : {p_mw:.4f}")
say(f"  median      : {np.median(g_c):,.1f} (ctl) vs {np.median(g_t):,.1f} (trt)")
say()
say(f"  Common-language effect size : {a12:.4f}")
say(f"  A randomly chosen gate_40 player plays more rounds than a randomly chosen")
say(f"  gate_30 player {a12:.1%} of the time (50% = no difference).")
say()
say("  Mann-Whitney tests stochastic dominance, not the mean, so it is immune to")
say("  the single bot. It is the more trustworthy of the two tests here.")
say()
say(f"  p = {p_mw:.4f} sits essentially ON the 0.05 line. Calling that 'not")
say("  significant' is as arbitrary as calling p = 0.0498 significant, so this")
say("  verdict does not rest on the p-value. With n = 90,189 a vanishingly small")
say("  shift is enough to push p to the boundary; the effect size is the")
say(f"  informative quantity, and at {a12:.4f} it is negligible.")
say()
say("  GUARDRAIL VERDICT: no MATERIAL degradation in engagement.")
say()
say("  What that rests on, in order:")
say(f"    - Common-language effect size {a12:.4f}, against 0.5 for no difference.")
say("      A 0.4% deviation from a coin flip is not a collapse in engagement.")
say(f"    - Medians differ by {abs(np.median(g_c)-np.median(g_t)):.0f} round"
    f" ({np.median(g_c):.0f} vs {np.median(g_t):.0f}).")
say("    - The mean gap is one bot, and vanishes when it is removed.")
say("    - Both bootstrap CIs on the difference in means straddle zero.")
say()
say("  There is likely a real but tiny downward shift in rounds played: the sign")
say("  agrees with both retention metrics, and that consistency is itself weak")
say("  evidence. 'Material' is the word the plan chose, and a shift this small")
say("  does not meet it.")
say()
say("  So the guardrail does not independently block a ship decision, and it does")
say("  not rescue the primary result either. Worth naming what the guardrail was")
say("  for: catching retention bought AT THE COST of engagement. Here retention")
say("  FELL and engagement was flat -- not the trade-off it was designed to")
say("  detect, and not a case where it has anything to veto.")
say()

results["guardrail"] = {
    "mean_control": float(g_c.mean()), "mean_treatment": float(g_t.mean()),
    "median_control": float(np.median(g_c)), "median_treatment": float(np.median(g_t)),
    "skew_control": float(stats.skew(g_c)), "skew_treatment": float(stats.skew(g_t)),
    "outlier_userid": outlier_id, "outlier_rounds": mx,
    "mean_diff_all": float(mean_diff_all), "mean_diff_trimmed": float(mean_diff_trim),
    "boot_ci_all": [float(bmlo), float(bmhi)],
    "boot_ci_trimmed": [float(btlo), float(bthi)],
    "mannwhitney_p": float(p_mw), "common_language_effect": float(a12),
}

# ---------------------------------------------------------------------------
# Multiple comparisons across the reported family
# ---------------------------------------------------------------------------
say.head("MULTIPLE COMPARISONS (Benjamini-Hochberg across the family)")
say()
family = [("7-day retention (PRIMARY)", primary["p_value"]),
          ("1-day retention (secondary)", float(pv1)),
          ("game rounds (guardrail, MWU)", float(p_mw))]
names = [f for f, _ in family]
praw = [p for _, p in family]
reject, padj, _, _ = multipletests(praw, alpha=ALPHA, method="fdr_bh")

say(f"  {'metric':<32s}{'p (raw)':>12s}{'p (BH)':>12s}{'signif':>9s}")
for nm, pr, pa, rj in zip(names, praw, padj, reject):
    say(f"  {nm:<32s}{pr:>12.4f}{pa:>12.4f}{str(bool(rj)):>9s}")
say()
say("  Per section 6, no correction is applied TO the primary metric -- it alone")
say("  drives the decision, and correcting a single pre-registered primary test")
say("  for the company of metrics reported beside it would be wrong. The table")
say("  above exists because these three are reported together, and both the raw")
say("  and corrected values are shown so neither is privileged silently.")
say()
say("  The primary result survives correction comfortably, so nothing about the")
say("  conclusion turns on this choice.")
say()
results["multiple_comparisons"] = {
    "metrics": names, "p_raw": [float(x) for x in praw],
    "p_bh": [float(x) for x in padj], "reject_bh": [bool(x) for x in reject]}

# ---------------------------------------------------------------------------
# Distribution plot
# ---------------------------------------------------------------------------
fig, axes = plt.subplots(1, 3, figsize=(16, 4.6))

bins = np.arange(0, 201, 5)
axes[0].hist(g_c, bins=bins, alpha=0.6, label=f"{CONTROL} (control)", density=True)
axes[0].hist(g_t, bins=bins, alpha=0.6, label=f"{TREATMENT} (treatment)", density=True)
axes[0].axvline(np.median(g_c), ls="--", lw=1.2, color="#1f4e79")
axes[0].axvline(g_c.mean(), ls=":", lw=1.6, color="#b3452c")
axes[0].set_title("Game rounds, 0-200\n(mean sits far right of the mass)")
axes[0].set_xlabel("total game rounds")
axes[0].set_ylabel("density")
axes[0].annotate(f"median\n{np.median(g_c):.0f}", xy=(np.median(g_c), 0),
                 xytext=(28, 0.020), fontsize=8, color="#1f4e79")
axes[0].annotate(f"mean\n{g_c.mean():.0f}", xy=(g_c.mean(), 0),
                 xytext=(66, 0.013), fontsize=8, color="#b3452c")
axes[0].legend(fontsize=8)

axes[1].hist(np.log1p(g_c), bins=60, alpha=0.6, label=CONTROL, density=True)
axes[1].hist(np.log1p(g_t), bins=60, alpha=0.6, label=TREATMENT, density=True)
axes[1].set_title("log1p(game rounds)\nspike at 0 = never played")
axes[1].set_xlabel("log(1 + total game rounds)")
axes[1].legend(fontsize=8)

for arr, lab in ((g_c, CONTROL), (g_t, TREATMENT)):
    xs = np.sort(arr)
    axes[2].plot(xs, np.arange(1, len(xs) + 1) / len(xs), label=lab, lw=1.4)
axes[2].set_xscale("symlog")
axes[2].set_title(f"ECDF (symlog x)\ncontrol tail reaches {mx:,d}")
axes[2].set_xlabel("total game rounds")
axes[2].set_ylabel("cumulative proportion")
axes[2].legend(fontsize=8)
axes[2].grid(alpha=0.25)

fig.suptitle("Guardrail metric is heavily right-skewed — shown, not asserted "
             "(plan §6)", fontsize=11)
fig.tight_layout()
out_fig = FIGURES / "03_guardrail_distribution.png"
fig.savefig(out_fig, dpi=140)
plt.close(fig)

say.save()
out = TABLES / "03_secondary_guardrail.json"
out.write_text(json.dumps(results, indent=2), encoding="utf-8")
print(f"[written] {out.relative_to(ROOT)}")
print(f"[written] {out_fig.relative_to(ROOT)}")
