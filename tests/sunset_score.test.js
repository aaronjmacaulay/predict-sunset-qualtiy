// sunset_score.test.js — regression lock for sunset_score.js.
//
// sunset_score.js is the actively maintained scoring implementation. This
// test freezes its current, known-correct scores (verified against
// sunset_score.py's original worked examples) so that any future change -
// intentional calibration or accidental breakage - shows up here instead
// of silently changing scores. A failure here after a deliberate tuning
// change is expected: update the expected value AND note why in the same
// commit, don't just silence the test.
//
// Run: node --test tests/sunset_score.test.js
// (run it from the repo root: `npm test`.)

const test = require("node:test");
const assert = require("node:assert/strict");
const { score, SCENARIOS } = require("../src/sunset/sunset_score");

const EXPECTED_SCORES = {
  "Post-frontal classic": 90,
  "Marine layer (coastal summer)": 4,
  "Wildfire smoke, moderate": 30,
  "Wildfire smoke, heavy": 3,
  "Pair A: clear to the west": 72,
  "Pair B: same sky, deck 120km west": 26,
  "Bluebird clear sky": 25,
  "Solid overcast": 0,
  "Ideal sky, but ridge to the west": 24,
};

test("all documented scenarios still score as expected", () => {
  for (const [name, expected] of Object.entries(EXPECTED_SCORES)) {
    const observation = SCENARIOS[name];
    assert.ok(observation, `Scenario "${name}" is missing from SCENARIOS`);
    assert.equal(
      score(observation),
      expected,
      `"${name}" expected ${expected}, got ${score(observation)}`
    );
  }
});

test("every scenario in SCENARIOS has a corresponding expected value", () => {
  for (const name of Object.keys(SCENARIOS)) {
    assert.ok(
      name in EXPECTED_SCORES,
      `Scenario "${name}" has no expected value in this test - add one`
    );
  }
});
