# Analysis Plan — Cookie Cats Gate Placement A/B Test

**Status:** Pre-registered. Committed before any outcome data was analysed.
**Author:** Aman Bhardwaj
**Date committed:** 2026-09-10

> This document is written *before* the analysis. Nothing below is edited after
> outcome data has been inspected. If something has to change (a metric turns out
> to be unavailable, a test is inappropriate), the change goes in a new section at
> the bottom — **Deviations from Plan** — with the reason, rather than being edited
> silently into the text above. The commit history is the audit trail.

---

## 1. Background and Hypothesis

**Context.** Cookie Cats is a mobile puzzle game with progression gates that pause
play and prompt the player either to wait or to make a purchase. The first gate
sits at level 30. A variant moves it to level 40.

**Hypothesis.** Moving the first gate from level 30 to level 40 will increase
player retention, because players encounter less forced friction early in the
experience and are more likely to reach the point where the game becomes habitual.

**Competing hypothesis worth stating.** The gate may itself create anticipation and
structure, so delaying it could *reduce* retention. This is a two-sided question,
not a one-sided one, and the test is specified accordingly.

**Business decision this informs.** Whether to change default gate placement for
all new players.

---

## 2. Metrics

### Primary metric (one only)

| | |
|---|---|
| **Metric** | 7-day retention (proportion of players who returned 7 days after install) |
| **Why this one** | Closer to long-term player value than 1-day retention. A 1-day metric can move on novelty or curiosity alone; a 7-day metric requires the player to have found a reason to come back. |
| **Direction** | Two-sided. We want to detect harm as well as benefit. |

Only one metric is designated primary. Every additional metric tested at
&alpha; = 0.05 inflates the family-wise error rate, so secondary metrics are
explicitly labelled as such and treated as supporting evidence, not as
independent grounds to ship.

### Secondary metrics

- **1-day retention.** Supporting evidence. If 1-day moves but 7-day does not, that
  is a signal of a novelty effect rather than a durable improvement.

### Guardrail metric

- **Total game rounds played.** This must not degrade materially even if retention
  improves. A change that keeps players nominally "retained" while collapsing
  engagement is not a win.

### Metrics explicitly *not* being analysed

The dataset contains no revenue, session-length, session-count, or timestamp
fields, so the following are **not available** and will not be analysed:

- **Revenue / in-app purchase conversion.** This is the metric the gate most
  directly targets, and its absence is a real limitation of this analysis rather
  than a choice. A gate that reduces retention slightly while increasing purchases
  could still be commercially correct, and this dataset cannot see that.
- **Session length and session count.** Not present.
- **Time-to-churn / survival.** No timestamps, so no time-to-event modelling.

Available but deliberately **excluded** from the decision:

- **Level-30 and level-40 reaching rates.** Not in the data as such, and any proxy
  built from `sum_gamerounds` is post-treatment: the gate placement itself changes
  what progress a given number of rounds represents, so conditioning on rounds
  conditions on a variable the treatment affects. That invites collider bias, so no
  proxy is constructed.
- **Any transformation of `sum_gamerounds` used as a retention substitute.** The
  guardrail is a guardrail; it does not get promoted to primary if 7-day retention
  disappoints.

---

## 3. Minimum Detectable Effect and Decision Rule

**Baseline 7-day retention (from the control arm, or from prior knowledge):**
**19.02%** (control arm `gate_30`, n = 44,700). Verified before finalising the MDE
via `src/00_baseline_peek.py`, which blinds the treatment arm's outcome columns
before aggregating, so the MDE could not be chosen with knowledge of the result it
would be applied to. Output: `outputs/tables/00_baseline_peek.txt`.

**Minimum detectable effect (MDE):** **1.0** percentage points absolute
(19.02% → 20.02%, a 5.3% relative lift).

**Justification for this MDE.** Gate placement is core progression logic. Moving
it for all new players is not a config flip: it shifts the difficulty curve, the
economy tuning around the gate, and the point at which a player first meets a
paywall prompt. That carries real regression risk and needs QA across the
progression system. A lift small enough to be invisible in a cohort's behaviour
does not repay that cost, and the same cycle could fund a test with more upside.

1.0pp absolute (5.3% relative) is the threshold because at a 19% baseline it is
about the smallest improvement that would still be visible above the ordinary
seasonal and acquisition-mix variation in a retention cohort — and therefore about
the smallest one we could expect to survive launch rather than dissolve on contact
with a different traffic mix.

Two consequences, stated plainly:

- It sits inside this test's sensitivity. The observed sample detects 0.74pp at 80%
  power (Section 5), so a null result here is informative about effects of 1.0pp and
  larger. It is not a shrug.
- It means a *statistically significant* result below 1.0pp is still a **do not
  ship**. With ~45,000 per arm, a 0.4pp difference can clear p < 0.05 while being
  commercially irrelevant. The decision rule below enforces that by making the
  confidence interval's lower bound — not the p-value — the thing that has to clear
  the bar.

**Significance level:** &alpha; = 0.05, two-sided.
**Target power:** 80%.

### Decision rule (fixed in advance)

| Outcome | Decision |
|---|---|
| Effect is positive, statistically significant, and the confidence interval's lower bound exceeds the MDE | **Ship** |
| Effect is positive and significant but the confidence interval includes effects below the MDE | **Do not ship on this evidence.** Report as directionally positive but underpowered for a decision; recommend a longer or larger follow-up |
| Confidence interval spans zero | **Do not ship.** Report as null |
| Effect is negative and significant | **Do not ship.** Investigate whether the gate serves a function we did not anticipate |
| Guardrail metric degrades materially | **Do not ship regardless of the primary metric result** |

**No peeking.** The analysis is run once, on the full dataset, after validation
checks pass. Because this dataset arrives as a completed snapshot, this is
enforced by construction — but the rule is stated because it is the rule that
would apply if this were live.

---

## 4. Validation Checks (run and pass before any outcome analysis)

These run first. If any fails, the outcome analysis does not proceed until the
failure is understood.

- [ ] **Sample Ratio Mismatch.** Chi-square test of observed group sizes against the
      intended allocation ratio. A significant SRM means assignment or logging is
      broken and the comparison is untrustworthy regardless of what the outcome
      data says.
      *Threshold:* p < 0.01 on the SRM test triggers investigation, not a shrug.
- [ ] **Duplicate user IDs.** Each user appears exactly once.
- [ ] **Cross-contamination.** No user appears in both arms.
- [ ] **Covariate balance.** Groups are comparable on any pre-treatment or
      treatment-independent characteristics available.
- [ ] **Missingness.** Extent and pattern of missing outcome data, and whether it
      differs by arm. Differential missingness is itself a finding.

**If SRM fails:** the outcome analysis does not become the headline. In order:

1. **Do not report a ship/no-ship decision from the primary metric.** A broken
   randomisation means the arms are not exchangeable, and no amount of correct
   downstream statistics repairs that.
2. **Investigate direction and mechanism.** Which arm is over-represented, and by
   how much? Check whether the discrepancy is concentrated in users with degenerate
   outcomes (e.g. `sum_gamerounds == 0`), which is the signature of filtering
   applied *after* assignment — installs that never opened the game, bot/fraud
   exclusion, or a logging drop on one arm's client build.
3. **Test the post-assignment-filtering hypothesis specifically** by comparing the
   arms' zero-round mass and re-running the SRM on users who showed any activity. If
   the imbalance is confined to never-played installs, the bias is plausibly benign
   for a retention comparison — but it is still reported, not waved through.
4. **Report the analysis as conditional and clearly labelled**, with the SRM failure
   stated before any result rather than in a footnote. The estimate may still be
   worth computing as evidence about the *magnitude* of any effect, but it is
   evidence from a compromised experiment.
5. **Recommend re-running with fixed assignment**, rather than shipping on this data.

*Disclosure on ordering.* The arm sizes (44,700 / 45,489) were visible in the
assignment counts printed by the baseline check, since validation precedes outcome
analysis by design. This contingency was therefore written knowing the arm sizes but
**not** knowing either arm's treatment outcome. It is written to constrain the
conclusion, not to excuse it. Section 9 records what the SRM test actually returned
and what was done about it.

---

## 5. Power Analysis

Two calculations, both reported:

**Retrospective.** Given the observed sample size per arm and the observed baseline
retention rate, what is the smallest effect this test could detect at 80% power?
This tells us whether a null result means "no effect" or "we could never have
seen it."

**Prospective.** If designing this test from scratch to detect the MDE stated in
Section 3 at 80% power and &alpha; = 0.05, how many users per arm would be
required? Report the number and compare it to what we actually have.

**Computed** (`src/04_power_analysis.py`; baseline 19.02%, n = 44,700 / 45,489,
&alpha; = 0.05 two-sided, power 80%):

| | Result |
|---|---|
| **Retrospective MDE** | **0.74pp** absolute (3.9% relative) |
| **Prospective n/arm to detect 1.0pp** | **24,658** per arm (49,316 total) |
| **Actual n** | 90,189 total — **1.83&times;** what the stated MDE requires |
| **Power at observed n for a true 1.0pp effect** | **96.6%** |

**Reading of these numbers.** The retrospective MDE (0.74pp) is *smaller* than the
effect we said we care about (1.0pp), so this test is adequately powered for the
decision it is being asked to make. That is the favourable case: a null result can
be reported as evidence against an effect of 1.0pp or larger, rather than as an
absence of evidence.

The honest limit: the test cannot resolve effects below ~0.74pp. Detecting 0.5pp at
80% power would need 97,679 per arm — 2.2&times; the users available. So a null
result here is **not** evidence that the true effect is zero; it is evidence that
the effect is smaller than the amount we declared worth shipping. Those are
different claims, and only the second is supported.

---

## 6. Statistical Methods

### Primary and secondary metrics (binary outcomes)

- **Test:** Two-proportion z-test (equivalently, chi-square test of independence).
- **Estimate reported:** Absolute difference in retention rates, with a 95%
  confidence interval. The point estimate and interval are the headline result;
  the p-value is reported alongside, not instead.
- **Also reported:** Relative lift, with the absolute baseline stated so the
  relative figure cannot mislead.

### Bootstrap (primary metric)

- Resample with replacement within each arm, 10,000 iterations.
- Report the percentile confidence interval on the difference in retention.
- Report the proportion of bootstrap samples in which the treatment arm exceeds
  control — a directly interpretable statement for a non-technical stakeholder.
- **Rationale:** distribution-free, and produces an interval that does not depend
  on the normal approximation holding at the tails.

### Guardrail metric (skewed count data)

- Total game rounds is expected to be heavily right-skewed with a large mass near
  zero. A t-test on the mean is **not** appropriate without justification.
- **Test:** Bootstrap on the difference in means, and Mann-Whitney U on the
  distributions. Report both, and report medians alongside means.
- The skew and the reason for this choice will be shown in the README with a
  distribution plot, not just asserted.

### Multiple comparisons

Only the primary metric drives the decision, so no correction is applied to it.
Where several metrics are reported together, Benjamini-Hochberg is applied to the
family and both corrected and uncorrected values are shown.

### Segment analysis

Any segment-level analysis is **exploratory and hypothesis-generating only**. A
segment finding does not change the ship decision in Section 3. It becomes the
subject of its own pre-registered test.

---

## 7. Simulation Component (clearly separated from the real analysis)

The following are demonstrated on **simulated data**, because the real dataset is a
finished snapshot without the pre-period or time-series structure required. This
separation is stated in the README so no reader can mistake simulated results for
findings about Cookie Cats.

- **Peeking.** A/A simulation (no true effect) checked repeatedly as data
  accumulates, showing false-positive inflation above the nominal 5%, then
  corrected with an alpha-spending or always-valid sequential approach.
- **Multiple comparisons.** Five metrics tested at &alpha; = 0.05, with and without
  correction.
- **CUPED.** A pre-experiment covariate correlated with the outcome, used to reduce
  variance; report the variance reduction achieved and the corresponding reduction
  in required sample size.

---

## 8. What Would Change My Mind

The hypothesis is that moving the gate to level 40 **increases** 7-day retention.
Any one of the following abandons it:

1. **A 95% CI on the difference in 7-day retention whose upper bound falls below
   +1.0pp.** This is the main one. It does not require the effect to be negative or
   significant: an interval lying entirely below the MDE means even the optimistic
   end of what the data supports is not worth shipping, so the hypothesis is dead
   for decision purposes regardless of sign.
2. **A negative point estimate**, whether or not it reaches significance. That is
   direct evidence for the competing hypothesis in Section 1 — that the gate
   supplies structure or anticipation — and would move me from "ship it" to "the
   gate is doing something we did not model."
3. **1-day retention moves but 7-day does not.** I would read that as novelty rather
   than durable improvement and would not ship on it. Recorded here so I cannot
   later present a 1-day win as the finding.
4. **The guardrail degrades materially** (total game rounds down beyond bootstrap-CI
   noise) **even if 7-day retention improves.** Retained-but-not-playing is not a
   win, and I would treat retention bought with an engagement loss as a reason to
   stop rather than a trade to make on this evidence.
5. **The SRM test fails.** Then I abandon the *test*, not merely the hypothesis, and
   report per the Section 4 contingency.

What would *not* change my mind: a favourable segment. Section 6 commits segment
findings to being hypothesis-generating, and I am not going to rescue a null primary
result by locating a subgroup where it worked.

---

## 9. Deviations from Plan

*Nothing below this line is written before the analysis. Every deviation is logged
here with its reason and the date, rather than edited into the sections above.*

| Date | Section | Change | Reason |
|---|---|---|---|
| 2026-09-10 | 4 | **SRM check failed.** Recorded, not edited away. | χ² = 6.90, p = 0.0086, below the 0.01 trigger. The section 4 contingency was executed as written; see below. |
| 2026-09-10 | 4 | Covariate balance run on `userid` only. | No true pre-treatment covariates exist in the dataset — no country, device, install date or channel. `userid` is the sole treatment-independent field. Logged because the plan asked for balance on "any characteristics available" and the honest answer is "almost none were". |
| 2026-09-10 | 6 | **Outlier handling for the guardrail was not pre-specified.** Results reported both with and without the outlier. | One control-arm user (`userid` 6390605) logged 49,854 rounds in 14 days, 17× the next-highest player. That single row *is* the entire difference in guardrail means (−1.16 rounds with it, −0.04 without). Since no rule existed, both figures are reported and neither is hidden. No outlier rule was applied to the primary metric, which is binary and unaffected. |
| 2026-09-10 | 6 | Added a deliberately **invalid** segment cut (`sum_gamerounds` buckets) as a demonstration. | Section 2 excluded this cut from the decision. It is shown in `05_segments.py` to make the exclusion concrete rather than asserted. It informs nothing; it is a worked example of the bias. |
| 2026-09-10 | 6 | Bootstrap for the binary metrics drawn from the binomial rather than by literal row resampling. | Mathematically identical for the mean of a 0/1 vector, and avoids materialising a 10,000 × 90,189 array. The guardrail bootstrap, where the distribution shape matters, does resample rows. |
| 2026-09-10 | 7 | CUPED and peeking demonstrated on simulated data, as the plan anticipated. | Confirmed on inspection: the snapshot has no timestamps and no pre-period. Not a deviation so much as the plan's own contingency being exercised. |

### What the SRM failure meant in practice

The plan said a failed SRM triggers investigation, "not a shrug". Recording what
happened, since this is the deviation that mattered:

**The test.** 44,700 control vs 45,489 treatment against an intended 50/50.
&chi;<sup>2</sup> = 6.90, p = 0.0086. Below the 0.01 trigger.

**The investigation** (section 4 contingency, steps 2–3). The hypothesis was
post-assignment filtering of never-played installs. It does not hold:

- Only **15%** of the +789 excess is attributable to zero-round users.
- The zero-round *rate* does not differ between arms (p = 0.169).
- **+669 of the excess persists** among users who played at least one round.

One thing worth flagging about how this nearly went wrong. Re-running the SRM on
active users only gives p = 0.0227, which sits back above the 0.01 trigger, and
it would have been easy to write that up as "resolved on the clean subset".
It is not resolved: dropping ~4,000 users lowers power and raises p on its own,
0.0227 is still significant at 0.05, and the imbalance itself barely moved. The
conclusion was therefore drawn from the decomposition of the excess rather than
from which side of a threshold a smaller sample's p-value landed on. That is the
shrug the plan was written to prevent, and it presented itself in exactly the
form the plan anticipated.

**Consequence.** Per step 1 of the contingency, no ship/no-ship decision is
issued from the primary metric. The estimate is reported for its magnitude and
the recommendation is step 5: re-run with assignment fixed.

**Judgement, stated separately from the rule.** The imbalance is small in
practical terms (49.56% / 50.44%), the arms show no detectable difference on the
only treatment-independent covariate available, and the primary result is
directionally stable across every cut examined. So the estimate is probably
close to right. That is a *judgement*, and the pre-registered rule outranks it —
which is the point of having fixed the rule in advance. Both are reported rather
than one being quietly resolved into the other.

### Outcome against section 8

Section 8 named five conditions that would abandon the hypothesis. Three fired:

- **Item 1** (CI upper bound below +1.0pp): the CI is [−1.33, −0.31]pp, entirely
  below +1.0pp. Fired — and would have fired even had the effect been positive.
- **Item 2** (negative point estimate): −0.82pp. Fired.
- **Item 5** (SRM failure): fired.

The two that did not fire: item 3 (1-day up, 7-day flat) — both horizons moved
down together; and item 4 (guardrail degradation) — engagement was flat.

The hypothesis that moving the gate to level 40 increases 7-day retention is
abandoned. The competing hypothesis stated in section 1 — that the gate itself
provides structure whose removal costs retention — is the one consistent with
the data, and the pattern in section 2's secondary metric (harm growing from
−1.3% relative at day 1 to −4.3% at day 7) fits it.

Recording that the competing hypothesis was written down *before* the analysis,
which is the only reason it can be cited now without it being a story invented
to fit the result.
