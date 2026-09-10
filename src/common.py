"""Shared constants and loaders.

Kept deliberately small. Anything that encodes an analysis *decision* belongs in
ANALYSIS_PLAN.md and in the script that acts on it, not hidden in a helper.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "cookie_cats.csv"
TABLES = ROOT / "outputs" / "tables"
FIGURES = ROOT / "outputs" / "figures"

CONTROL = "gate_30"
TREATMENT = "gate_40"

# From ANALYSIS_PLAN.md, fixed before outcome analysis.
ALPHA = 0.05
POWER = 0.80
MDE = 0.010            # 1.0pp absolute, primary decision threshold
SRM_ALPHA = 0.01       # SRM investigation trigger
N_BOOT = 10_000
SEED = 20260910

PRIMARY = "retention_7"
SECONDARY = "retention_1"
GUARDRAIL = "sum_gamerounds"


def load() -> pd.DataFrame:
    """Load the raw snapshot with outcome columns as clean dtypes."""
    df = pd.read_csv(RAW)
    for col in (PRIMARY, SECONDARY):
        df[col] = df[col].astype(bool)
    return df


def arms(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (control, treatment) frames."""
    return df[df["version"] == CONTROL], df[df["version"] == TREATMENT]


class Report:
    """Accumulates console output and writes it to a file verbatim."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.lines: list[str] = []

    def __call__(self, msg: str = "") -> None:
        print(msg)
        self.lines.append(msg)

    def rule(self, char: str = "-", width: int = 74) -> None:
        self(char * width)

    def head(self, title: str) -> None:
        self.rule("=")
        self(title)
        self.rule("=")

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text("\n".join(self.lines) + "\n", encoding="utf-8")
        print(f"\n[written] {self.path.relative_to(ROOT)}")
