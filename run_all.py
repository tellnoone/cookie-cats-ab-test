"""Run the full analysis in the order the plan requires.

Validation runs before outcome analysis, and the outcome scripts read the gate
file validation writes. Running out of order is possible but the scripts will
tell you about it.
"""

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STEPS = [
    ("src/00_baseline_peek.py", "control-arm baseline (pre-registration input)"),
    ("src/01_validation.py", "validation checks -- plan section 4"),
    ("src/02_primary_analysis.py", "primary metric: 7-day retention"),
    ("src/03_secondary_guardrail.py", "secondary + guardrail metrics"),
    ("src/04_power_analysis.py", "power analysis -- plan section 5"),
    ("src/05_segments.py", "exploratory segments"),
    ("src/sim/sim_peeking.py", "SIMULATED: peeking"),
    ("src/sim/sim_multiple_comparisons.py", "SIMULATED: multiple comparisons"),
    ("src/sim/sim_cuped.py", "SIMULATED: CUPED"),
]

failures = []
for script, label in STEPS:
    print(f"\n{'='*74}\n>>> {script}\n    {label}\n{'='*74}")
    t0 = time.time()
    r = subprocess.run([sys.executable, str(ROOT / script)],
                       cwd=ROOT / Path(script).parent)
    elapsed = time.time() - t0
    if r.returncode != 0:
        failures.append(script)
        print(f"\n*** FAILED: {script} (exit {r.returncode})")
    else:
        print(f"\n[ok] {script}  ({elapsed:.1f}s)")

print(f"\n{'='*74}")
if failures:
    print(f"{len(failures)} step(s) failed: {', '.join(failures)}")
    sys.exit(1)
print(f"All {len(STEPS)} steps completed.")
print("Outputs in outputs/tables/ and outputs/figures/")
