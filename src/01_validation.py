"""
Validation checks (ANALYSIS_PLAN.md section 4).

These run BEFORE any outcome analysis. If a check fails, the plan says the
outcome analysis does not proceed until the failure is understood -- so this
script writes a machine-readable gate file that 02_primary_analysis.py reads and
refuses to run past silently.

Checks:
  1. Sample Ratio Mismatch  (chi-square vs intended 50/50)
  2. Duplicate user IDs
  3. Cross-contamination     (a user in both arms)
  4. Covariate balance
  5. Missingness

Note on ordering: this script touches outcome columns only for missingness counts
and, under the SRM contingency, for the zero-round mass that distinguishes a
post-assignment filtering artefact from broken randomisation. It does not compute
a treatment effect.
"""

from __future__ import annotations

import json

import numpy as np
from scipy import stats

from common import (ALPHA, CONTROL, GUARDRAIL, PRIMARY, ROOT, SECONDARY,
                    SRM_ALPHA, TABLES, TREATMENT, Report, load)

say = Report(TABLES / "01_validation.txt")
df = load()
results: dict[str, object] = {}

say.head("VALIDATION CHECKS  (plan section 4) -- run before outcome analysis")
say()
say(f"Rows loaded: {len(df):,d}")
say(f"Columns:     {', '.join(df.columns)}")
say()

# ---------------------------------------------------------------------------
# 1. Sample Ratio Mismatch
# ---------------------------------------------------------------------------
say.head("1. SAMPLE RATIO MISMATCH")
say()
n_c = int((df["version"] == CONTROL).sum())
n_t = int((df["version"] == TREATMENT).sum())
n = n_c + n_t
expected = n / 2

chi2, p_srm = stats.chisquare([n_c, n_t], [expected, expected])
say(f"  Intended allocation : 50 / 50")
say(f"  {CONTROL:>10s} (control)   : {n_c:>7,d}  ({n_c/n:.4%})")
say(f"  {TREATMENT:>10s} (treatment) : {n_t:>7,d}  ({n_t/n:.4%})")
say(f"  expected per arm    : {expected:>9,.1f}")
say(f"  difference          : {n_t - n_c:>+7,d}  ({(n_t-n_c)/n*100:+.3f}pp of total)")
say()
say(f"  chi-square (1 df)   : {chi2:.4f}")
say(f"  p-value             : {p_srm:.6f}")
say(f"  trigger threshold   : p < {SRM_ALPHA}")
say()

srm_failed = bool(p_srm < SRM_ALPHA)
if srm_failed:
    say("  >>> SRM CHECK FAILS. p is below the pre-registered 0.01 trigger.")
    say("  >>> The plan's section 4 contingency applies. Investigating below;")
    say("  >>> the outcome analysis is NOT permitted to report a ship decision.")
else:
    say("  SRM check passes.")
results["srm"] = {"n_control": n_c, "n_treatment": n_t, "chi2": float(chi2),
                  "p": float(p_srm), "failed": srm_failed}
say()

# --- SRM contingency, step 2-3: is this a post-assignment filtering artefact? ---
if srm_failed:
    say.head("1b. SRM INVESTIGATION  (plan section 4 contingency, steps 2-3)")
    say()
    say("Hypothesis under test: the imbalance is not broken randomisation but")
    say("filtering applied AFTER assignment -- installs that never opened the game.")
    say("Signature would be an arm-dependent mass of zero-round users.")
    say()

    zero = df[GUARDRAIL] == 0
    z_c = int(zero[df["version"] == CONTROL].sum())
    z_t = int(zero[df["version"] == TREATMENT].sum())
    say(f"  zero-round users, {CONTROL:>8s} : {z_c:>6,d}  ({z_c/n_c:.4%} of arm)")
    say(f"  zero-round users, {TREATMENT:>8s} : {z_t:>6,d}  ({z_t/n_t:.4%} of arm)")

    # Do the arms differ in their zero-round *rate*?
    zc_tab = np.array([[z_c, n_c - z_c], [z_t, n_t - z_t]])
    chi2_z, p_z = stats.chi2_contingency(zc_tab, correction=False)[:2]
    say(f"  difference in rate         : {(z_t/n_t - z_c/n_c)*100:+.4f}pp"
        f"   (chi2 p = {p_z:.4f})")
    say()

    # Re-run the SRM on users who showed any activity at all.
    act = df[df[GUARDRAIL] > 0]
    a_c = int((act["version"] == CONTROL).sum())
    a_t = int((act["version"] == TREATMENT).sum())
    chi2_a, p_a = stats.chisquare([a_c, a_t], [(a_c + a_t) / 2] * 2)
    say("  SRM re-run on active users only (sum_gamerounds > 0):")
    say(f"    {CONTROL:>10s} : {a_c:>7,d}")
    say(f"    {TREATMENT:>10s} : {a_t:>7,d}")
    say(f"    chi-square      : {chi2_a:.4f}   p = {p_a:.6f}")
    say()

    # The decisive question is not whether p clears a threshold on the smaller
    # subset -- dropping users lowers power and will raise p on its own. It is how
    # much of the arm-size excess actually disappears when the zero-round users
    # are removed. Decompose it.
    exc_tot, exc_act = n_t - n_c, a_t - a_c
    say("  Decomposition of the arm-size excess:")
    say(f"    excess overall            : {exc_tot:>+6,d}")
    say(f"    excess among active users : {exc_act:>+6,d}"
        f"   ({exc_act/exc_tot:.1%} of it)")
    say(f"    attributable to 0-round   : {exc_tot - exc_act:>+6,d}"
        f"   ({(exc_tot-exc_act)/exc_tot:.1%} of it)")
    say()

    share_persisting = exc_act / exc_tot
    if share_persisting > 0.5 or p_a < ALPHA:
        say("  Conclusion: the imbalance PERSISTS among active users. Only "
            f"{(exc_tot-exc_act)/exc_tot:.0%} of the")
        say("  excess is attributable to never-played installs, and the zero-round rate")
        say(f"  itself does not differ significantly between arms (p = {p_z:.3f}). The")
        say("  post-assignment-filtering explanation is therefore NOT supported.")
        say()
        say("  Note on the p-values: p rises from 0.0086 to 0.0227 when zero-round users")
        say("  are dropped, but that is mostly the loss of ~4,000 users, not the")
        say("  imbalance resolving. p = 0.0227 is still significant at 0.05. Reading the")
        say("  move across the 0.01 trigger as 'now passes' would be exactly the shrug")
        say("  the plan forbids.")
        verdict = "persists_among_active"
    else:
        say("  Conclusion: the excess is largely confined to zero-round users, which is")
        say("  consistent with post-assignment filtering of never-played installs rather")
        say("  than broken randomisation. Still reported, not waved through.")
        verdict = "confined_to_zero_round"
    results["srm_investigation"] = {
        "zero_control": z_c, "zero_treatment": z_t, "p_zero_rate": float(p_z),
        "active_control": a_c, "active_treatment": a_t, "p_srm_active": float(p_a),
        "excess_overall": int(exc_tot), "excess_active": int(exc_act),
        "share_persisting": float(share_persisting), "verdict": verdict}
    say()

# ---------------------------------------------------------------------------
# 2. Duplicate user IDs
# ---------------------------------------------------------------------------
say.head("2. DUPLICATE USER IDs")
say()
n_ids = int(df["userid"].nunique())
n_dupe = len(df) - n_ids
say(f"  rows            : {len(df):,d}")
say(f"  unique userids  : {n_ids:,d}")
say(f"  duplicate rows  : {n_dupe:,d}")
say()
say("  PASS -- each user appears exactly once." if n_dupe == 0
    else f"  FAIL -- {n_dupe:,d} duplicated userid(s).")
results["duplicates"] = {"rows": len(df), "unique": n_ids, "duplicate_rows": n_dupe,
                         "failed": n_dupe != 0}
say()

# ---------------------------------------------------------------------------
# 3. Cross-contamination
# ---------------------------------------------------------------------------
say.head("3. CROSS-CONTAMINATION")
say()
per_user_arms = df.groupby("userid")["version"].nunique()
both = int((per_user_arms > 1).sum())
say(f"  users appearing in both arms : {both:,d}")
say()
say("  PASS -- no user is in both arms." if both == 0
    else f"  FAIL -- {both:,d} user(s) in both arms.")
results["contamination"] = {"users_in_both_arms": both, "failed": both != 0}
say()

# ---------------------------------------------------------------------------
# 4. Covariate balance
# ---------------------------------------------------------------------------
say.head("4. COVARIATE BALANCE")
say()
say("  Stated plainly: this dataset has NO true pre-treatment covariates. There is")
say("  no country, device, install date, or acquisition channel. `sum_gamerounds`")
say("  and both retention flags are measured after the gate takes effect, so none")
say("  of them can be used to establish that the arms started comparable.")
say()
say("  The one treatment-independent field is `userid`. If ids are issued in")
say("  install order -- the usual case -- then its distribution is a weak proxy for")
say("  when a player joined, and an imbalance would suggest the arms were drawn")
say("  from different time windows or id ranges.")
say()
ids_c = df.loc[df["version"] == CONTROL, "userid"]
ids_t = df.loc[df["version"] == TREATMENT, "userid"]
say(f"  {'':22s}{CONTROL:>14s}{TREATMENT:>14s}")
for label, fn in (("min", np.min), ("25th pct", lambda x: np.percentile(x, 25)),
                  ("median", np.median), ("75th pct", lambda x: np.percentile(x, 75)),
                  ("max", np.max), ("mean", np.mean)):
    say(f"  userid {label:<15s}{fn(ids_c):>14,.0f}{fn(ids_t):>14,.0f}")
ks, p_ks = stats.ks_2samp(ids_c, ids_t)
mw_u, p_mw = stats.mannwhitneyu(ids_c, ids_t, alternative="two-sided")
say()
say(f"  KS test on userid distribution : D = {ks:.5f}, p = {p_ks:.4f}")
say(f"  Mann-Whitney U on userid       : p = {p_mw:.4f}")
say()
if min(p_ks, p_mw) < ALPHA:
    say("  >>> Imbalance detected on userid. Worth noting alongside the SRM result.")
else:
    say("  No detectable imbalance on the only treatment-independent field available.")
    say("  This is weak reassurance, not covariate balance in the usual sense.")
results["covariate_balance"] = {"ks_p": float(p_ks), "mw_p": float(p_mw),
                                "failed": bool(min(p_ks, p_mw) < ALPHA)}
say()

# ---------------------------------------------------------------------------
# 5. Missingness
# ---------------------------------------------------------------------------
say.head("5. MISSINGNESS")
say()
miss = df.isna().sum()
say("  Missing values by column:")
for col, k in miss.items():
    say(f"    {col:<18s} {k:>6,d}  ({k/len(df):.4%})")
say()
if miss.sum() == 0:
    say("  No missing values anywhere, so differential missingness by arm cannot")
    say("  arise. Note what this does NOT mean: a player who never returned is")
    say("  recorded as retention = False, not as missing. Absent players are encoded")
    say("  as negative outcomes rather than dropped, which is the right encoding here")
    say("  but means 'no missingness' is a statement about the snapshot's")
    say("  completeness, not about attrition.")
else:
    by_arm = df.groupby("version").apply(lambda g: g.isna().mean(), include_groups=False)
    say("  Missing rate by arm:")
    say(by_arm.to_string())
results["missingness"] = {"total_missing": int(miss.sum()),
                          "failed": bool(miss.sum() > 0)}
say()

# ---------------------------------------------------------------------------
# Gate
# ---------------------------------------------------------------------------
say.head("VALIDATION SUMMARY")
say()
checks = [("Sample Ratio Mismatch", results["srm"]["failed"]),
          ("Duplicate user IDs", results["duplicates"]["failed"]),
          ("Cross-contamination", results["contamination"]["failed"]),
          ("Covariate balance", results["covariate_balance"]["failed"]),
          ("Missingness", results["missingness"]["failed"])]
for label, failed in checks:
    say(f"  [{'FAIL' if failed else 'PASS'}]  {label}")
say()
n_failed = sum(f for _, f in checks)
if n_failed:
    say(f"  {n_failed} of {len(checks)} checks FAILED.")
    say("  Per plan section 4, the outcome analysis proceeds only as a CONDITIONAL")
    say("  analysis, with the failure reported ahead of any result and no ship")
    say("  decision drawn from the primary metric.")
else:
    say("  All checks pass. Outcome analysis may proceed as pre-registered.")

results["gate"] = {"n_failed": int(n_failed),
                   "conditional_analysis_required": bool(n_failed > 0)}
say.save()

gate_path = TABLES / "01_validation_gate.json"
gate_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
print(f"[written] {gate_path.relative_to(ROOT)}")
