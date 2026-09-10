"""
Segment analysis (ANALYSIS_PLAN.md section 6, final subsection).

EXPLORATORY AND HYPOTHESIS-GENERATING ONLY. Per the plan, nothing here changes
the ship decision, and per section 8 a favourable segment does not rescue the
primary result.

This script does two different things, and the difference between them is the
point:

  A. A LEGITIMATE segment cut, on `userid` decile. userid is treatment-
     independent, so slicing by it cannot be contaminated by the treatment.
     Benjamini-Hochberg is applied across the deciles.

  B. A cut that looks natural and is WRONG: segmenting by `sum_gamerounds`.
     Section 2 excluded this from the decision because rounds played is
     measured after the gate takes effect. It is demonstrated here precisely
     to show what the bias looks like, because "don't condition on
     post-treatment variables" is more convincing with the numbers attached.
"""

from __future__ import annotations

import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.proportion import proportions_ztest

from common import (ALPHA, CONTROL, FIGURES, GUARDRAIL, PRIMARY, ROOT, TABLES,
                    TREATMENT, Report, load)

say = Report(TABLES / "05_segments.txt")
df = load()
results: dict[str, object] = {}

overall = json.loads((TABLES / "02_primary_results.json").read_text(encoding="utf-8"))
overall_diff = overall["abs_diff"]

say.head("SEGMENT ANALYSIS -- EXPLORATORY ONLY")
say()
say("  Per plan section 6: hypothesis-generating, not decision-making. Nothing")
say("  below changes the recommendation. Any interesting slice becomes the")
say("  subject of its own pre-registered test, not a reason to revisit this one.")
say()


def compare(sub: pd.DataFrame) -> tuple[float, float, float, int, int]:
    """Return (rate_ctl, rate_trt, p_value, n_ctl, n_trt) for a subset."""
    c = sub[sub["version"] == CONTROL][PRIMARY]
    t = sub[sub["version"] == TREATMENT][PRIMARY]
    if len(c) < 30 or len(t) < 30:
        return (np.nan, np.nan, np.nan, len(c), len(t))
    _, p = proportions_ztest([int(t.sum()), int(c.sum())], [len(t), len(c)],
                             alternative="two-sided")
    return (c.mean(), t.mean(), float(p), len(c), len(t))


# ---------------------------------------------------------------------------
# A. Legitimate: userid decile
# ---------------------------------------------------------------------------
say.head("A. LEGITIMATE CUT: userid decile (treatment-independent)")
say()
say("  If userids are issued in install order, deciles approximate install")
say("  cohorts. Crucially, a user's id cannot be affected by which gate they got,")
say("  so this cut does not condition on anything the treatment touched.")
say()

df["id_decile"] = pd.qcut(df["userid"], 10, labels=False) + 1
rows = []
for dec, sub in df.groupby("id_decile"):
    rc, rt, p, nc, nt = compare(sub)
    rows.append({"decile": int(dec), "n_ctl": nc, "n_trt": nt,
                 "rate_ctl": rc, "rate_trt": rt, "diff": rt - rc, "p_raw": p})
seg_a = pd.DataFrame(rows)
rej, padj, _, _ = multipletests(seg_a["p_raw"], alpha=ALPHA, method="fdr_bh")
seg_a["p_bh"] = padj
seg_a["signif_bh"] = rej

say(f"  {'decile':>7s}{'n ctl':>9s}{'n trt':>9s}{'ctl':>9s}{'trt':>9s}"
    f"{'diff pp':>10s}{'p raw':>9s}{'p BH':>9s}")
for _, r in seg_a.iterrows():
    say(f"  {r['decile']:>7.0f}{r['n_ctl']:>9,.0f}{r['n_trt']:>9,.0f}"
        f"{r['rate_ctl']:>8.2%}{r['rate_trt']:>9.2%}{r['diff']*100:>10.3f}"
        f"{r['p_raw']:>9.4f}{r['p_bh']:>9.4f}")
say()
n_sig_raw = int((seg_a["p_raw"] < ALPHA).sum())
n_sig_bh = int(seg_a["signif_bh"].sum())
say(f"  Segments significant at raw alpha = {ALPHA} : {n_sig_raw} of 10")
say(f"  Segments significant after Benjamini-Hochberg : {n_sig_bh} of 10")
say()
say(f"  All 10 diffs negative? {bool((seg_a['diff'] < 0).all())}")
say(f"  Direction split: {int((seg_a['diff'] < 0).sum())} negative, "
    f"{int((seg_a['diff'] > 0).sum())} positive")
say()
say("  This is the useful reading. The primary effect is small, so individual")
say("  deciles at ~4,500 per arm are badly underpowered -- each has roughly a")
say("  third of the sample needed to see a 0.8pp effect. Most deciles will look")
say("  'not significant' whatever the truth is, and one or two may look large by")
say("  chance. The consistency of the SIGN across deciles is more informative")
say("  than any single decile's p-value.")
say()
results["userid_deciles"] = seg_a.to_dict(orient="records")

# ---------------------------------------------------------------------------
# B. The wrong cut, demonstrated
# ---------------------------------------------------------------------------
say.head("B. THE WRONG CUT: segmenting by sum_gamerounds (post-treatment)")
say()
say("  Section 2 excluded this from the decision. Here is why, with numbers.")
say()
say("  `sum_gamerounds` is measured AFTER the gate takes effect. The gate is")
say("  literally a device that stops people playing, so the treatment changes")
say("  this variable. Splitting on it compares groups that are not like-for-like:")
say("  a given bucket means something different in each arm.")
say()

bins = [-1, 0, 5, 20, 40, 80, 160, np.inf]
labels = ["0", "1-5", "6-20", "21-40", "41-80", "81-160", "160+"]
df["rounds_bucket"] = pd.cut(df[GUARDRAIL], bins=bins, labels=labels)

rows_b = []
for b, sub in df.groupby("rounds_bucket", observed=True):
    rc, rt, p, nc, nt = compare(sub)
    rows_b.append({"bucket": str(b), "n_ctl": nc, "n_trt": nt,
                   "rate_ctl": rc, "rate_trt": rt, "diff": rt - rc, "p_raw": p})
seg_b = pd.DataFrame(rows_b)

say(f"  {'rounds':>9s}{'n ctl':>9s}{'n trt':>9s}{'ctl':>9s}{'trt':>9s}"
    f"{'diff pp':>10s}{'p raw':>9s}")
for _, r in seg_b.iterrows():
    say(f"  {r['bucket']:>9s}{r['n_ctl']:>9,.0f}{r['n_trt']:>9,.0f}"
        f"{r['rate_ctl']:>8.2%}{r['rate_trt']:>9.2%}{r['diff']*100:>10.3f}"
        f"{r['p_raw']:>9.4f}")
say()

pos = seg_b[seg_b["diff"] > 0]
say("  What is actually wrong here needs stating carefully, because the obvious")
say("  reading is not the right one.")
say()
say(f"  {len(pos)} of {len(seg_b)} buckets show a positive difference, but they are")
say("  the two smallest effects in the table:")
for _, r in pos.iterrows():
    say(f"    {r['bucket']:>7s} : {r['diff']*100:+.3f} pp  (p = {r['p_raw']:.4f})")
say("  Those are noise, not a sign reversal. This is NOT Simpson's paradox, and")
say("  calling it that would be overclaiming -- the aggregate sign does not")
say("  genuinely flip inside any well-populated bucket.")
say()
say("  The real distortion is one of MAGNITUDE:")
say(f"    aggregate effect           : {overall_diff*100:+.2f} pp")
worst = seg_b.loc[seg_b["diff"].idxmin()]
say(f"    worst bucket ({worst['bucket']:>6s})      : {worst['diff']*100:+.2f} pp"
    f"  (p = {worst['p_raw']:.4f})")
say(f"    ratio                      : {worst['diff']/overall_diff:.1f}x the aggregate")
say()
say("  Conditioning on a post-treatment variable manufactures effects several")
say("  times larger than the real one. A reader shown only that row would")
say("  conclude the gate change costs mid-engagement players 3.2pp of retention,")
say("  which is roughly four times the actual aggregate harm.")
say()

# The smoking gun: does bucket MEMBERSHIP differ by arm?
say("  The smoking gun -- bucket membership itself differs by arm:")
say()
tab = pd.crosstab(df["rounds_bucket"], df["version"])
shares = tab / tab.sum()
say(f"    {'bucket':>9s}{CONTROL:>11s}{TREATMENT:>11s}{'shift':>9s}")
for b in tab.index:
    sc, st = shares.loc[b, CONTROL], shares.loc[b, TREATMENT]
    say(f"    {str(b):>9s}{sc:>10.2%}{st:>11.2%}{(st-sc)*100:>+8.2f}pp")
chi2_m, p_m = stats.chi2_contingency(tab.to_numpy())[:2]
say()
say(f"    chi-square on membership : {chi2_m:.2f}, p = {p_m:.4f}")
say()
if p_m < ALPHA:
    say("    Significant. The treatment MOVED people between buckets, which is")
    say("    direct proof that the conditioning variable is treatment-affected.")
else:
    say("    Not significant at the aggregate level, but the mechanism still")
    say("    applies -- absence of a detectable shift is not exchangeability.")
say()
say("  That is the whole objection in one line. When the treatment changes which")
say("  bucket you land in, comparing arms WITHIN a bucket is comparing different")
say("  populations. The gate at level 30 stops control players earlier, so a")
say("  control player who still reached 80+ rounds pushed through a gate while a")
say("  treatment player who reached 80+ rounds did not. Same bucket, different")
say("  kind of player.")
say()
say("  Had this cut not been excluded in advance, it would have supplied a")
say("  tempting and false story with a very convincing p-value attached")
say(f"  (p = {worst['p_raw']:.4f} on the worst bucket). Pre-registration is what")
say("  makes it unavailable.")
say()
results["rounds_buckets"] = seg_b.to_dict(orient="records")
results["rounds_buckets_positive"] = int(len(pos))
results["bucket_membership_chi2"] = float(chi2_m)
results["bucket_membership_p"] = float(p_m)
results["worst_bucket_amplification"] = float(worst["diff"] / overall_diff)

# ---------------------------------------------------------------------------
# Plot
# ---------------------------------------------------------------------------
fig, axes = plt.subplots(1, 2, figsize=(13.5, 4.8))

ax = axes[0]
err = 1.96 * np.sqrt(
    seg_a["rate_trt"] * (1 - seg_a["rate_trt"]) / seg_a["n_trt"]
    + seg_a["rate_ctl"] * (1 - seg_a["rate_ctl"]) / seg_a["n_ctl"]) * 100
ax.errorbar(seg_a["decile"], seg_a["diff"] * 100, yerr=err, fmt="o",
            color="#1f4e79", capsize=3, lw=1.3, ms=5)
ax.axhline(0, color="#333", lw=1)
ax.axhline(overall["abs_diff"] * 100, ls="--", color="#b3452c", lw=1.4,
           label=f"overall {overall['abs_diff']*100:+.2f}pp")
ax.set_xlabel("userid decile (proxy for install cohort)")
ax.set_ylabel("difference in 7-day retention (pp)")
ax.set_title("A. Legitimate cut: treatment-independent\nwide CIs — each decile is "
             "underpowered")
ax.legend(fontsize=8)
ax.grid(alpha=0.25)
ax.set_xticks(range(1, 11))

ax = axes[1]
colours = ["#2e7d32" if d > 0 else "#b3452c" for d in seg_b["diff"]]
ax.bar(seg_b["bucket"], seg_b["diff"] * 100, color=colours, alpha=0.85)
ax.axhline(0, color="#333", lw=1)
ax.axhline(overall["abs_diff"] * 100, ls="--", color="#1f4e79", lw=1.4,
           label=f"overall {overall['abs_diff']*100:+.2f}pp")
ax.set_xlabel("sum_gamerounds bucket (POST-TREATMENT — do not use)")
ax.set_ylabel("difference in 7-day retention (pp)")
ax.set_title("B. The wrong cut: post-treatment conditioning\neffects up to 4x the aggregate")
ax.legend(fontsize=8)
ax.grid(alpha=0.25, axis="y")

fig.suptitle("Segments are exploratory — and one of these cuts is invalid by "
             "construction (plan §6)", fontsize=11)
fig.tight_layout()
out_fig = FIGURES / "05_segments.png"
fig.savefig(out_fig, dpi=140)
plt.close(fig)

say.head("SEGMENT CONCLUSION")
say()
say("  No segment changes the recommendation, and none was permitted to. The")
say("  userid cut shows a consistent sign with intervals too wide to say more.")
say("  The rounds cut shows why the plan excluded it.")
say()
say("  If anything here were to be pursued, it would be pursued as a NEW")
say("  pre-registered experiment with its own primary metric and its own MDE.")

say.save()
out = TABLES / "05_segments.json"
out.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
print(f"[written] {out.relative_to(ROOT)}")
print(f"[written] {out_fig.relative_to(ROOT)}")
