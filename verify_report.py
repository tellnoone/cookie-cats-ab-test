"""Audit every quantitative figure quoted in README.md against the generated JSON.

The README is written by hand, so every number in it is a transcription that can
be wrong or can go stale when a script changes. This checks each one against the
JSON the analysis actually produced.

Run after run_all.py. A mismatch means the README is wrong, not the analysis.
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent
T = ROOT / "outputs" / "tables"


def load(name):
    return json.loads((T / name).read_text(encoding="utf-8"))


val = load("01_validation_gate.json")
pri = load("02_primary_results.json")
sec = load("03_secondary_guardrail.json")
pwr = load("04_power_results.json")
seg = load("05_segments.json")
pk = load("sim_peeking.json")
mc = load("sim_multiple_comparisons.json")
cu = load("sim_cuped.json")

checks = []


def chk(label, claimed, actual, tol=5e-3):
    ok = abs(claimed - actual) <= tol
    checks.append((ok, label, claimed, actual))


# --- Headline table ---
chk("control 7d retention %", 19.02, pri["rate_control"] * 100, 0.005)
chk("treatment 7d retention %", 18.20, pri["rate_treatment"] * 100, 0.005)
chk("abs diff pp", -0.82, pri["abs_diff"] * 100, 0.005)
chk("CI lower pp", -1.33, pri["ci_lower"] * 100, 0.005)
chk("CI upper pp", -0.31, pri["ci_upper"] * 100, 0.005)
chk("relative %", -4.3, pri["rel_lift"] * 100, 0.05)
chk("p-value", 0.0016, pri["p_value"], 5e-5)
chk("boot CI lower", -1.32, pri["boot_ci_lower"] * 100, 0.02)
chk("boot CI upper", -0.32, pri["boot_ci_upper"] * 100, 0.02)
chk("P(trt>ctl) %", 0.1, pri["boot_p_treatment_wins"] * 100, 0.05)
chk("n control", 44700, val["srm"]["n_control"], 0)
chk("n treatment", 45489, val["srm"]["n_treatment"], 0)

# --- SRM ---
chk("SRM chi2", 6.90, val["srm"]["chi2"], 0.005)
chk("SRM p", 0.0086, val["srm"]["p"], 5e-5)
inv = val["srm_investigation"]
chk("SRM excess", 789, inv["excess_overall"], 0)
chk("SRM excess active", 669, inv["excess_active"], 0)
chk("share persisting %", 84.8, inv["share_persisting"] * 100, 0.1)
chk("15% attributable", 15.2, (1 - inv["share_persisting"]) * 100, 0.1)
chk("zero-rate p", 0.169, inv["p_zero_rate"], 5e-4)
chk("SRM p active", 0.0227, inv["p_srm_active"], 5e-5)

# --- Guardrail ---
g = sec["guardrail"]
chk("outlier userid", 6390605, g["outlier_userid"], 0)
chk("outlier rounds", 49854, g["outlier_rounds"], 0)
chk("mean diff all", -1.16, g["mean_diff_all"], 0.005)
chk("mean diff trimmed", -0.04, g["mean_diff_trimmed"], 0.005)
chk("MWU p", 0.0502, g["mannwhitney_p"], 5e-5)
chk("common lang effect", 0.4962, g["common_language_effect"], 5e-5)
chk("median ctl", 17, g["median_control"], 0)
chk("median trt", 16, g["median_treatment"], 0)
chk("ctl skew", 163.7, g["skew_control"], 0.05)
chk("trt skew", 6.0, g["skew_treatment"], 0.05)

# --- Secondary ---
s = sec["secondary"]
chk("1d ctl %", 44.82, s["rate_control"] * 100, 0.005)
chk("1d trt %", 44.23, s["rate_treatment"] * 100, 0.005)
chk("1d diff pp", -0.59, s["abs_diff"] * 100, 0.005)
chk("1d CI lo", -1.24, s["ci"][0] * 100, 0.005)
chk("1d CI hi", 0.06, s["ci"][1] * 100, 0.005)
chk("1d p", 0.0744, s["p_value"], 5e-5)

# --- BH ---
bh = sec["multiple_comparisons"]
chk("BH primary", 0.0047, bh["p_bh"][0], 5e-5)
chk("BH secondary", 0.0744, bh["p_bh"][1], 5e-5)
chk("BH guardrail", 0.0744, bh["p_bh"][2], 5e-5)

# --- Power ---
chk("retrospective MDE pp", 0.74, pwr["retrospective_mde_abs"] * 100, 0.005)
chk("power at 1pp %", 96.6, pwr["power_at_registered_mde"] * 100, 0.05)
chk("prospective n/arm", 24658, pwr["prospective_n_per_arm"], 0)
chk("n for 0.5pp", 97679, pwr["n_per_arm_by_effect"]["0.50pp"], 0)

# --- Segments ---
chk("bucket membership chi2", 27.6, seg["bucket_membership_chi2"], 0.05)
chk("bucket membership p", 0.0001, seg["bucket_membership_p"], 5e-5)
worst = min(r["diff"] for r in seg["rounds_buckets"])
chk("worst bucket pp", -3.25, worst * 100, 0.005)
dec_neg = sum(1 for r in seg["userid_deciles"] if r["diff"] < 0)
dec_sig_raw = sum(1 for r in seg["userid_deciles"] if r["p_raw"] < 0.05)
dec_sig_bh = sum(1 for r in seg["userid_deciles"] if r["signif_bh"])
chk("deciles negative", 8, dec_neg, 0)
chk("deciles sig raw", 1, dec_sig_raw, 0)
chk("deciles sig BH", 0, dec_sig_bh, 0)

# --- Sims ---
chk("peek single %", 4.75, pk["fpr_single_test"] * 100, 0.05)
chk("peek 10 %", 19.65, pk["fpr_peeking"] * 100, 0.05)
chk("peek inflation", 3.9, pk["inflation_factor"], 0.05)
chk("peek OBF %", 5.05, pk["fpr_obf_corrected"] * 100, 0.05)
chk("OBF first look p", 9.4e-11, pk["obf_first_look_nominal_p"], 1e-11)
chk("OBF final look p", 0.0406, pk["obf_final_look_nominal_p"], 5e-5)

chk("mc theoretical fwer %", 22.6, mc["theoretical_fwer"] * 100, 0.05)
chk("mc power raw %", 71.7, mc["power_uncorrected"] * 100, 0.05)
chk("mc power bonf %", 47.6, mc["power_bonferroni"] * 100, 0.05)
chk("mc power bh %", 54.2, mc["power_bh"] * 100, 0.051)

chk("cuped rho", 0.48, cu["correlation_x_y"], 0.005)
chk("cuped var red %", 24.9, cu["observed_var_reduction"] * 100, 0.05)
chk("cuped theory %", 23.5, cu["theoretical_var_reduction"] * 100, 0.05)
chk("cuped n plain", 24352, cu["n_required_plain"], 1)
chk("cuped n cuped", 18292, cu["n_required_cuped"], 1)
chk("cuped saving", 6060, cu["n_required_plain"] - cu["n_required_cuped"], 1)
chk("cuped type1 %", 4.0, cu["type1_cuped"] * 100, 0.05)
chk("cuped bias pp", -0.0001, cu["bias_cuped_pp"], 5e-4)

import sys

bad = [c for c in checks if not c[0]]
print(f"{len(checks) - len(bad)}/{len(checks)} README claims verified")
if bad:
    print("\nMISMATCHES:")
    for _, label, claimed, actual in bad:
        print(f"  {label:<28s} README={claimed!r:>14}  actual={actual!r}")
    sys.exit(1)
print("All README figures match the generated outputs.")
