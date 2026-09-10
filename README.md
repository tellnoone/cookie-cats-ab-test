# Cookie Cats — Gate Placement A/B Test

A pre-registered analysis of whether moving a mobile game's first progression
gate from level 30 to level 40 improves player retention.

**It does not. It makes retention worse.** And the experiment has a sample ratio
mismatch, so the pre-registered rule says the number is not the thing to act on.

---

## Headline result

| | |
|---|---|
| **Primary metric** | 7-day retention |
| **Control** (`gate_30`) | **19.02%** (8,502 / 44,700) |
| **Treatment** (`gate_40`) | **18.20%** (8,279 / 45,489) |
| **Absolute difference** | **−0.82pp** |
| **95% CI** | **[−1.33, −0.31]pp** |
| **Relative** | −4.3% on a 19.02% baseline |
| **p-value** | 0.0016 (two-sided) |
| **Bootstrap CI** (10,000 iters) | [−1.32, −0.32]pp |
| **P(gate_40 > gate_30) in resamples** | **0.1%** |

Moving the gate later reduced 7-day retention. The hypothesis under test was
that it would *increase* retention; the plan also wrote down the competing
hypothesis — that the gate provides structure, so removing it early costs
something — and that is the one the data supports.

**But the recommendation is not "don't ship".** It is **re-run the test.**
The sample ratio mismatch (below) means the arms are not demonstrably
comparable, and the plan fixed in advance what to do about that.

---

## The two findings that mattered more than the headline

### 1. The randomisation is broken (or at least, unexplained)

| | |
|---|---|
| Control | 44,700 (49.56%) |
| Treatment | 45,489 (50.44%) |
| Expected at 50/50 | 45,094.5 |
| Excess | **+789** |
| χ² (1 df) | 6.90 |
| **p** | **0.0086** — below the pre-registered 0.01 trigger |

The plan said a failed SRM triggers investigation, "not a shrug". So:

The obvious benign explanation is that installs which never opened the game were
filtered out *after* assignment. Testing it:

- Only **15%** of the +789 excess is attributable to zero-round users
- The zero-round *rate* does not differ between arms (p = 0.169)
- **+669 of the excess persists** among users who played at least one round

So the explanation does not hold. And there was a trap here worth naming: re-run
the SRM on active users only and you get **p = 0.0227**, which is back above the
0.01 trigger. It would have been easy — and wrong — to write that up as
"resolved on the clean subset". Dropping ~4,000 users lowers power and raises p
by itself; 0.0227 is still significant at 0.05; and the imbalance barely moved.
The conclusion rests on the decomposition of the excess, not on which side of a
threshold a smaller sample's p-value fell.

**Consequence:** no ship/no-ship decision is issued from the primary metric.
The estimate is reported for its magnitude; the recommendation is to fix
assignment and re-run.

### 2. One bot was the entire guardrail result

The guardrail metric is total game rounds played. `userid` **6390605**, in the
control arm, logged **49,854 rounds in 14 days** — 17× the next-highest player,
about 148 rounds an hour sustained around the clock for two weeks. Not a human.

| | With the outlier | Without |
|---|---|---|
| Difference in means | **−1.16 rounds** | **−0.04 rounds** |
| Control SD | 256.7 | 103.3 |
| Control skew | 163.7 | 6.0 |

**Removing one row out of 90,189 takes the entire guardrail effect to zero.**
Any conclusion drawn from the mean would have been a conclusion about one bot.
This is why the plan specified Mann-Whitney and a bootstrap rather than a t-test
on the mean — a decision made before anyone knew this row existed.

Mann-Whitney is immune to it: common-language effect size **0.4962** against
0.5000 for no difference. Verdict: no *material* engagement degradation.

---

## Full results

### Primary and secondary

| Metric | Control | Treatment | Diff | 95% CI | p (raw) | p (BH) |
|---|---|---|---|---|---|---|
| **7-day retention** (primary) | 19.02% | 18.20% | **−0.82pp** | [−1.33, −0.31] | **0.0016** | 0.0047 |
| 1-day retention (secondary) | 44.82% | 44.23% | −0.59pp | [−1.24, +0.06] | 0.0744 | 0.0744 |
| Game rounds (guardrail, MWU) | median 17 | median 16 | — | — | 0.0502 | 0.0744 |

1-day retention points the same way but its interval crosses zero, so it is
**weak corroboration, not confirmation**. The useful detail is that the relative
harm *grows* with the horizon:

- Day 1: −0.59pp on a 44.8% base = **−1.3%** relative
- Day 7: −0.82pp on a 19.0% base = **−4.3%** relative

A novelty effect would predict the opposite shape. A gate that was doing
structural work predicts this one.

The guardrail's Mann-Whitney p is **0.0502** — sitting exactly on the line.
Calling that "not significant" would be as arbitrary as calling 0.0498
significant, so the verdict argues from the effect size and the medians instead.

### Power

| | |
|---|---|
| **Retrospective MDE** (80% power) | **0.74pp** |
| Pre-registered MDE | 1.0pp |
| Power to detect 1.0pp at observed n | **96.6%** |
| Prospective n/arm for 1.0pp | 24,658 (have 44,700) |
| n/arm needed for 0.5pp | 97,679 — **2.2× what we have** |

The test was adequately powered for its own decision. That matters: it means a
null result would have been *informative* rather than an absence of evidence.
The limit, stated plainly — this test cannot resolve effects below ~0.74pp, so
it could never have supported the claim "the true effect is exactly zero".

The observed |effect| of 0.82pp is above the 0.74pp detection threshold, so the
finding is not a marginal artefact of a thin sample.

---

## What the MDE was for

The plan set the MDE at **1.0pp absolute** and required the **confidence
interval's lower bound**, not the p-value, to clear it.

This matters more than it looks. With ~45,000 per arm, a 0.4pp difference can
reach p < 0.05 while being commercially irrelevant. The pre-registered rule
would have said **do not ship** to a statistically significant result that small
— and `02_primary_analysis.py` implements that literally rather than
aspirationally.

In the event, the effect was negative, so a different branch of the rule fired.
But note the asymmetry the plan built in: the MDE was a bar for shipping a
*benefit*, not a licence to ignore *harm* of the same size. A −0.82pp effect is
below the 1.0pp threshold in magnitude and still argues against the change.

---

## Exploratory segments — including one cut done wrong on purpose

Segments are **hypothesis-generating only**. Nothing here changed the
recommendation, and the plan forbade it in advance.

**A valid cut** (`userid` decile — treatment-independent, so it cannot be
contaminated): 8 of 10 deciles negative, **1 of 10** significant at raw α,
**0 of 10** after Benjamini-Hochberg. Each decile holds ~4,500/arm, about a
third of what a 0.8pp effect needs. The consistent *sign* is the signal; no
individual decile's p-value is.

**An invalid cut, shown deliberately** (`sum_gamerounds` buckets): conditioning
on a post-treatment variable inflates the effect to **−3.25pp** in the 41–80
bucket (p = 0.0001), roughly **4× the true aggregate**.

The proof that this cut is invalid is not the inflated estimate — it is that
**bucket membership itself differs by arm** (χ² = 27.6, **p = 0.0001**). The
treatment moves people between buckets, so comparing arms *within* a bucket
compares different populations. A control player who reached 80+ rounds pushed
through a gate; a treatment player who reached 80+ rounds did not. Same bucket,
different kind of player.

This is a worked example, not a finding. Left in because "don't condition on
post-treatment variables" is more convincing with the numbers attached.

---

## Simulations (§7) — clearly separated

The real dataset is a finished snapshot with **no timestamps and no
pre-period**, so three standard demonstrations are impossible on it honestly.
They run on generated data, and every output file opens with a banner saying so.
**None of the numbers below are findings about Cookie Cats.**

### Peeking

An A/A test — **no true effect exists** — checked 10 times as data accumulates:

| | False-positive rate |
|---|---|
| One test at the end | 4.75% (nominal 5%) |
| **Peeking 10 times** | **19.65%** — a **3.9× inflation** |
| With O'Brien-Fleming boundary | 5.05% |

Every "significant" result there is false by construction. The correction's
price is visible: to stop at the first look you need **p < 9.4e-11**, relaxing
to p < 0.0406 by the last one.

### Multiple comparisons

Five null metrics at α = 0.05 → **22.6%** chance of at least one "winner". Each
individual test is perfectly calibrated; the broken part is the decision rule
"ship if *any* metric wins".

And what correction costs, which usually goes unmentioned — power on metrics
that genuinely moved:

| | Power (real effects) | False positives (nulls) |
|---|---|---|
| Uncorrected | 71.7% | 5.1% |
| Bonferroni | 47.6% | 1.0% |
| Benjamini-Hochberg | 54.2% | 2.3% |

Correction is damage control. Naming one primary metric in advance is
prevention.

### CUPED

A pre-period covariate at ρ = 0.48 against a 19.2% baseline:

| | |
|---|---|
| Variance reduction | **24.9%** (theory: ρ² = 23.5%) |
| Sample saving | **6,060 users/arm** (24,352 → 18,292) |
| Bias | −0.0001pp — unbiased |
| Type-I error | 4.0% CUPED / 3.8% plain (target 5%, 600 sims) |

The payoff is **ρ²**, which is the one thing worth remembering: a covariate
correlated 0.2 buys 4%; one correlated 0.9 buys 81%.

**Why this is not applied to the real data.** The tempting move is to use
`sum_gamerounds` as the covariate, since it correlates strongly with retention.
That would be wrong — it is measured *during* the experiment and the gate
changes it (χ² p = 0.0001, above). Adjusting for a treatment-affected covariate
does not remove noise; it removes part of the causal effect being measured.

---

## Repository layout

```
ANALYSIS_PLAN.md          Pre-registration. Committed before outcome analysis.
                          Section 9 logs every deviation.
data/
  raw/cookie_cats.csv     90,189 rows
  PROVENANCE.md           Source URL, SHA-256, three-mirror verification
src/
  common.py               Shared constants (alpha, MDE, seed) and loaders
  00_baseline_peek.py     Control-arm baseline; BLINDS the treatment arm
  01_validation.py        SRM, duplicates, contamination, balance, missingness
  02_primary_analysis.py  7-day retention; reads the validation gate
  03_secondary_guardrail.py  1-day retention, game rounds, BH correction
  04_power_analysis.py    Retrospective + prospective power
  05_segments.py          Exploratory; one valid cut and one invalid one
  sim/
    sim_peeking.py              SIMULATED
    sim_multiple_comparisons.py SIMULATED
    sim_cuped.py                SIMULATED
outputs/
  tables/                 Text reports + JSON for programmatic use
  figures/                PNGs
run_all.py                Runs everything in plan order
```

### Reproducing

```bash
pip install -r requirements.txt
python run_all.py
```

Seeded (`SEED = 20260910` in `src/common.py`), so bootstrap and simulation
figures reproduce exactly. Runtime is a couple of minutes, dominated by the
guardrail bootstrap.

---

## How the pre-registration was actually enforced

The document is only worth something if it constrained the analysis. Three
places where it did, mechanically rather than on trust:

**1. The MDE could not be reverse-engineered from the result.** Section 3 needed
a baseline, which had to come from the data. `00_baseline_peek.py` casts the
treatment arm's outcome columns to null and asserts they are null *before*
aggregating anything. The 19.02% baseline was available; the answer was not.

**2. The validation gate is a file, not an intention.** `01_validation.py`
writes `01_validation_gate.json`. `02_primary_analysis.py` reads it and refuses
to print a recommendation when it says validation failed — which is why the
primary output leads with the SRM failure instead of burying it.

**3. The commit history is the audit trail.** The pre-registration is commit 1,
and **no outcome analysis code existed in the tree at that point**. Every
subsequent commit is additive. `git log` shows the order things were decided in.

```
c978a58  Add section 7 simulations: peeking, multiple comparisons, CUPED
09f6add  Add exploratory segment analysis, contrasting a valid and an invalid cut
bef2bf2  Add secondary/guardrail analysis and power analysis
5fec294  Primary analysis: 7-day retention is LOWER on gate_40
79cc782  Add section 4 validation checks; SRM fails at the pre-registered trigger
9d40a16  Pre-register analysis plan for Cookie Cats gate placement test
```

---

## Limitations

Stated because they bound what this analysis can support:

- **No revenue data.** The gate's most direct purpose is monetisation. A gate
  that costs a little retention while increasing purchases could still be the
  right commercial call, and this dataset cannot see that. This is the largest
  gap in the analysis.
- **The SRM is unexplained.** Not "explained away" — unexplained. Without access
  to the assignment service or logs, the mechanism cannot be identified.
- **No pre-period, no timestamps.** No CUPED, no sequential testing, no
  survival analysis, no novelty-decay curve on the real data.
- **No covariate balance in the usual sense.** No country, device, install date
  or channel. `userid` is the only treatment-independent field, and passing a
  balance check on it is weak reassurance rather than evidence of comparability.
- **One dataset, one time window.** Retention responds to season, acquisition
  mix and competing releases. A single snapshot cannot separate those.

---

## Recommendation

1. **Do not ship the level-40 gate.** The evidence points the wrong way, and no
   branch of the decision rule supports shipping.
2. **Do not treat −0.82pp as the effect size.** Re-run with assignment fixed and
   an SRM check that gates the analysis before anyone sees an outcome.
3. **Instrument revenue before re-running.** The current metric set cannot answer
   the commercial question, only the retention one.
4. **The interesting question is now the opposite one.** If a gate at 30 retains
   better than a gate at 40, the competing hypothesis deserves a real test —
   what does the gate *do*? A gate at level 20 would be one arm of it. That is a
   new pre-registered experiment, not a reanalysis of this one.

---

*Data: the canonical Cookie Cats A/B dataset (90,189 players), verified
byte-identical across three independent mirrors — see `data/PROVENANCE.md`.*
