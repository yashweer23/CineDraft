# Versioned talent, ranking and fee calculations

The implementation follows the Phase 1 scoring/data specifications. These are explainable game proxies calculated from the eligible imported catalog. A film's reception does not isolate an individual's contribution, and incomplete careers affect coverage. Source audience ratings remain separate from every game-derived number.

Versions: `talent-1.0`, `notability-1.0`, `fictional-fees-1.0`. Frozen parameters and input/output checksums are saved with each publication. The pure implementation is `backend/app/talent/calculation.py`.

## Evidence and priors

Use a sealed dataset's eligibility and exact mapped roles. The builder does not silently reinterpret ingestion policy. A person-role needs at least one eligible movie with a matching mapped credit. Deduplicate by person, role and movie, combining jobs such as Writer and Screenplay. One person keeps one identity across roles.

The catalog reception prior `C` is the unweighted mean rating of all distinct eligible movies with a non-null rating and positive votes. Fall back to 6.0 if no such movies exist and report this explicitly. Vote count 0 or missing means unavailable reception, even if a source average is present. Valid zero audience ratings with positive votes remain valid.

For observed film reception:

```text
B = (v × R + 500 × C) / (v + 500)
```

Unknown reception uses `B=C` internally for ranking only. It contributes no observed evidence to the person's reception average. The API never substitutes C into the source `audience_rating` field.

## Role-specific attributes

| Attribute | Calculation |
|---|---|
| Reception | `10 × (sum(B over rated role films) + 3C) / (rated role film count + 3)` |
| Experience | `100 × min(ln(1+n) / ln(31), 1)` |
| Versatility | `100 × min(distinct game genres / 6, 1)` |
| Talent strength | `0.8 × reception + 0.2 × experience` |
| Genre fit | `100 × (n_g + 5q_g) / (n+5)` |

Here `n` is the number of distinct eligible films for the person-role and `n_g` is the number in the selected genre. Every attribute is bounded by its inputs to 0–100. Genre fit measures exposure, not proof of skill in that genre. Experience caps at 30 films. Popularity never enters talent strength.

`q_g` is the fraction of distinct person/movie pairs for that role in the catalog tagged with the genre. Multiple jobs never increase the denominator. When no such genre evidence exists, use the Phase 1 fallback `q_g=0.5` and flag a catalog gap. A smoothed score in a gap must be read alongside the displayed warning and zero evidence count.

Popularity uses the average zero-based rank among observed people eligible for the same role, divided by `N−1`, multiplied by 100. Ties average their rank; one observation maps to 50. Ranking raw nonnegative popularity is mathematically equivalent to ranking `ln(1+popularity)`, since the transformation is strictly increasing. Missing popularity stays null in the source-like percentile field, uses 50 for the later appeal input and 0 for pricing. Zero popularity is an observed value, not missing.

Coverage: 1–2 films = low; 3–7 = moderate; 8+ = broader. These labels refer to this catalog, not complete careers. Career span is the difference between latest and earliest known release years plus one, not age or active working years. Specialties show up to three observed genres ordered by movie count descending, genre fit descending, then genre ID. Fallback-only genres are never specialties.

## Ranked notable works

A list uses eligible movies for the selected professional role and is independent of the selected game genre. Let:

- `B`: shrunk reception above, using C internally when unavailable.
- `V = min(ln(1+v) / ln(100001), 1)` with effective v=0 for unavailable reception.
- `P`: movie popularity percentile across observed eligible catalog movies, in 0–1; missing uses 0.
- `D`: fraction present among release date, poster path, valid reception pair and original language.

```text
notability = 0.75 × B/10 + 0.15 × V + 0.08 × P + 0.02 × D
```

Sort by unrounded notability descending, effective votes descending, then ascending source and source ID. TMDB IDs sort numerically; synthetic keys sort lexically. UUID is the last tie-breaker. Take at most five unique movies, preserving the combined matching credited jobs. Full raw filmography remains in the Phase 4 endpoint.

Each item stores its rank and weighted score components. Title, year, poster and audience rating are read from the pinned immutable dataset. Null source fields remain null. The UI shows every available title up to five and uses placeholders for unavailable images. A list with fewer films has no invented filler.

## Fictional fees

Use the stored six-decimal attributes, with `P_price=0` when popularity is missing:

```text
z = (0.45 × talent_strength + 0.35 × P_price + 0.20 × experience) / 100
raw_fee = floor + (ceiling − floor) × z²
fee = clamp(round_half_up(raw_fee / 25000) × 25000, floor, ceiling)
```

| Role | Floor USD | Ceiling USD |
|---|---:|---:|
| Director | 150,000 | 20,000,000 |
| Actor | 100,000 | 30,000,000 |
| Writer | 125,000 | 5,000,000 |
| Cinematographer | 100,000 | 4,000,000 |
| Composer | 75,000 | 6,000,000 |

Use Decimal arithmetic at 50 significant digits and `ROUND_HALF_UP`. Feature display/storage values have six decimal places. Exact fees are integer USD; no binary floating-point arithmetic determines a monetary rounding boundary. For example, $112,500 rounds to $125,000; $112,499.999 rounds to $100,000 under a $25,000 increment. Price evidence includes the input values, raw Decimal fee string, bounds and rounding rule.

The same person-role fee is used for all genres and tiers. All four acting slots share the actor fee. Prices remain fictional game parameters; they are not salary estimates, current hiring quotes or statements about a person's availability.

## Calibration and feasibility

Report per-role count/min/max and an optimistic roster lower bound: four cheapest distinct actors plus one cheapest profile in each other role. Cross-role identity overlap makes this a lower bound only. Missing roles prevent even this calculation. A lower bound above a tier budget proves the current prices cannot fit; one below it does not prove a valid unique-person roster exists.

Every tier remains disabled and every profile/version is marked `playable: false`. Exact matching, offer coverage and gameplay balance are later work. No secret discounts are applied to make Indie budgets pass. Changing parameters or evidence requires a new version; the initial curve is implemented as specified, not claimed to be empirically balanced.
