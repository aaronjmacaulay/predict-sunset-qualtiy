todo i wnat ot make a risk list to decide which poc to make first
i think there is an uncertiaintiy whether all users will rate sunset in a consitent way
if that is not true  should seperate features of a sunset to how desiarable to a particular users
if true need to change need to change forcast sunset to predict the feature rather then desiarabity

how do you usuggest we structure that in the poc to do first

---

## Proposal

### Why this is the risk to resolve first

The scoring model already built (`score = gate × canvas × clarity × aerosol` in
[sunset_score.py](src/sunset_score.py)) implicitly assumes a single, universal
"good sunset" ground truth — one number, same meaning for everyone. Every
downstream POC tier in [research.md](research.md) (pinpoint scoring, terrain,
live satellite confirmation) inherits that assumption. If it's wrong, we don't
get to patch it later — the target variable itself changes shape. That makes
this an architecture-gating risk, not a feature-level one, and it's cheap and
fast to check. Resolve it before writing more forecasting code.

### Risk list (ordered by how much they'd force a rebuild)

| # | Risk | If wrong, what breaks | Cost to test |
|---|---|---|---|
| 1 | **Rating consistency** — do people agree on what makes a sunset good? | The entire single-score architecture; would need to predict decomposed features + per-user preference instead | Low — no weather data or code needed, just human ratings |
| 2 | Physical model correctness — are the four terms/weights in `sunset_score.py` actually predictive of *anyone's* rating? | Calibration constants (μ, σ, exponents), not the architecture | Medium — needs #1 resolved first, since "predictive of what" depends on the answer |
| 3 | Hyperlocal/terrain effect size — does upwind sampling + terrain geometry meaningfully change scores vs. naive overhead sampling? | Justifies (or not) Tier 2 engineering effort | Medium — already partially reasoned through in research.md §4, §6 |
| 4 | Live satellite/webcam value — does the final-hour ground-truth layer change outcomes enough to justify the effort? | Justifies (or not) Tier 3 | High — the hardest, rightly deferred |

Row 1 is the one your todo is pointing at, and it should come first: it's the
cheapest to test and the only one that changes what we're even trying to predict.

### POC 1 — Rating Consistency Study

**Goal:** find out whether "sunset quality" behaves like a shared objective
property (everyone ranks the same sunsets similarly) or like a matter of taste
(people cluster into different preference types, or disagree with no pattern).

**Method**
1. Assemble ~30–40 sunset photos spanning the range the scoring model
   distinguishes: post-frontal cirrus, clear/bluebird, smoke-haze, marine
   layer, overcast, dust-enhanced, etc. (The "Scenario results" table in
   research.md §8 is a ready-made list of conditions to source photos for.)
2. Recruit ~20–30 raters, deliberately varied (not just one friend group).
3. Each rates each photo 1–10, no context given beyond the image. A simple
   form (Google Form / Typeform) is enough — no app needed.
4. Analyze agreement:
   - Pairwise inter-rater correlation (or Krippendorff's alpha) across all raters.
   - Cluster raters (e.g. k-means on their rating vectors) to check for
     distinct taste groups vs. one dominant consensus vs. noise.

**Decision rule**
- **High agreement** (e.g. mean pairwise correlation ≳ 0.6, no strong
  clusters) → the single-score architecture is validated. Next POC: calibrate
  `sunset_score.py`'s constants against these human ratings (Tier 1 from
  research.md, now with real ground truth instead of physically-reasoned
  guesses).
- **Low agreement / clear taste clusters** → forecast decomposed *features*
  instead of one score (e.g. color saturation, cloud drama/texture, warm vs.
  pastel palette, sky coverage) and either (a) expose those features raw and
  let users read them, or (b) let a user pick/weight the archetypes they like
  and rank forecasts against that profile. This changes the model output
  shape before any more scoring work is built on the current assumption.

**Why this first:** it's days of effort, needs no weather API or infra, and
its answer determines whether everything else in research.md is calibrating
the right kind of model or the wrong one.
