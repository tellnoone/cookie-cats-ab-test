"""
Pre-registration input: control-arm baseline only.

Section 3 of ANALYSIS_PLAN.md requires a baseline retention rate in order to
finalise the MDE, and permits verifying it from the data. This script therefore
reads the CONTROL arm's outcomes and nothing else.

It is deliberately written so that the treatment arm's outcome columns are
dropped before any aggregation happens. Enforcing that in code rather than by
good intentions is the whole point: the MDE must not be chosen with knowledge
of the result it will be applied to.

Run BEFORE committing the pre-registration. Everything downstream runs after.
"""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "cookie_cats.csv"
OUT = ROOT / "outputs" / "tables" / "00_baseline_peek.txt"

CONTROL = "gate_30"
TREATMENT = "gate_40"
OUTCOMES = ["retention_1", "retention_7", "sum_gamerounds"]

lines: list[str] = []


def say(msg: str = "") -> None:
    print(msg)
    lines.append(msg)


df = pd.read_csv(RAW)

# --- Assignment-level facts. Not outcomes: safe to look at for both arms. ---
sizes = df["version"].value_counts()
say("=" * 68)
say("CONTROL-ARM BASELINE  (pre-registration input)")
say("=" * 68)
say()
say("Group sizes (assignment data, not outcome data):")
for arm in (CONTROL, TREATMENT):
    say(f"  {arm:10s} {sizes[arm]:>7,d}")
say(f"  {'total':10s} {len(df):>7,d}")
say()

# --- Blind the treatment arm before aggregating anything. ---
blinded = df.copy()
blinded[OUTCOMES] = blinded[OUTCOMES].astype("object")
treat_mask = blinded["version"] == TREATMENT
blinded.loc[treat_mask, OUTCOMES] = pd.NA
assert blinded.loc[treat_mask, OUTCOMES].isna().all().all(), "treatment arm not blinded"

control = blinded.loc[blinded["version"] == CONTROL]

say(f"Control arm ({CONTROL}), n = {len(control):,d}")
say("-" * 68)
r7 = control["retention_7"].astype(bool).mean()
r1 = control["retention_1"].astype(bool).mean()
say(f"  7-day retention (PRIMARY baseline) : {r7:.4%}")
say(f"  1-day retention (secondary)        : {r1:.4%}")
say(f"  mean game rounds  (guardrail)      : {control['sum_gamerounds'].astype(float).mean():.2f}")
say(f"  median game rounds                 : {control['sum_gamerounds'].astype(float).median():.1f}")
say()
say("Treatment arm outcomes: BLINDED, not computed.")
say()
say(f"=> Use baseline 7-day retention = {r7:.2%} to finalise the Section 3 MDE.")
say("=" * 68)

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
