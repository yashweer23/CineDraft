'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const C = require('../engine.js');

test('540 complete legacy drafts preserve budget, roles, uniqueness, and reproducibility', () => {
  let completed = 0;
  for (const genre of C.genres) for (const budget of [90, 140, 200]) {
    for (let seed = 1; seed <= 10; seed++) for (const strategy of ['cheap', 'expensive', 'fit']) {
      const state = C.start(genre, budget, 'Verification film', seed);
      while (state.picks.length < 8) {
        let hand = C.deal(state);
        assert.equal(new Set(hand.map(p => p.id)).size, 3);
        if (state.picks.length < 3) {
          state.rerolls++;
          hand = C.deal(state, hand.map(p => p.id));
        }
        const legal = hand.filter(p => C.affordable(state, p));
        assert.ok(legal.length, `Dead end: ${genre}/${budget}/${seed}/${strategy}`);
        legal.sort((a, b) => strategy === 'cheap' ? a.cost - b.cost
          : strategy === 'expensive' ? b.cost - a.cost : C.fit(b, genre) - C.fit(a, genre));
        const pick = legal[0];
        assert.equal(pick.role, C.slots[state.picks.length][0]);
        assert.ok(!state.picks.some(p => p.id === pick.id));
        state.picks.push(pick);
        assert.ok(C.spent(state) <= budget);
      }
      const result = C.release(state);
      assert.deepEqual(C.release(JSON.parse(JSON.stringify(state))), result);
      assert.equal(result.weeks.reduce((a, b) => a + b, 0), result.gross);
      for (const metric of ['critics', 'audience', 'score']) {
        assert.ok(result[metric] >= 0 && result[metric] <= 100);
      }
      completed++;
    }
  }
  assert.equal(completed, 540);
});

test('legacy offers repeat for the same seed and state', () => {
  const a = C.start('Crime', 90, 'A', 42);
  const b = C.start('Crime', 90, 'A', 42);
  assert.deepEqual(C.deal(a), C.deal(b));
});

test('legacy brief validation and incomplete release rejection', () => {
  assert.throws(() => C.start('Mystery', 90, 'A', 42));
  assert.throws(() => C.start('Crime', 10, 'A', 42));
  assert.throws(() => C.release(C.start('Crime', 90, 'A', 42)));
});
