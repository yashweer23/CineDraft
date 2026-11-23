# Phase 1 — Scoring design

This document specifies a transparent first model for later implementation. It does not change the bundled prototype simulator, assert that movie credits measure individual skill, or claim that any formula predicts real commercial outcomes. All weights and thresholds below are versioned balance hypotheses.

## Data-derived attributes

Calculate features separately for each eligible person-role pair using all eligible credited feature films in the frozen catalog. Never derive the person's role from their best-known department alone. Exclude unreleased films from reception and experience calculations.

For each film with valid audience rating `R` (0–10) and vote count `v > 0`, use `B = (v*R + m*C)/(v+m)`, with prior weight `m=500` and `C` the catalog-wide mean valid rating for that snapshot (fallback 6.0). These are game defaults. Missing rating or votes contributes no observed reception evidence; do not display a prior as a source rating.

| Attribute | Initial calculation and range | Interpretation |
|---|---|---|
| Reception `R_p` | `10 * (sum(B) + 3*C)/(n_rated+3)`; clamp 0–100 | Smoothed reception of credited films; attribution to the individual remains imperfect |
| Experience `E` | `100 * min(log(1+n)/log(31), 1)` | Diminishing returns after 30 distinct eligible films |
| Versatility `V` | `100 * min(distinct eligible genres/6, 1)` | Descriptive breadth; not automatically superior quality |
| Popularity `P` | Percentile of `log(1+popularity)` among observed people in the same role | Visibility, separately labeled; missing value uses 50 for appeal and 0 for pricing |
| Talent strength `T` | `0.8*R_p + 0.2*E` | Game proxy, with popularity excluded |
| Genre fit `G` | `100*(n_g + 5*q_g)/(n+5)`, clamped 0–100 | Smoothed role-specific genre exposure |

Here `n` is the count of distinct eligible movies, `n_g` the count tagged with the selected genre, and `q_g` the fraction of eligible role credits in that genre in the catalog. A movie with multiple matching jobs counts once. With no role-specific evidence the person is not eligible for that role. If a genre has no catalog evidence, use `q_g=0.5` and report a catalog gap before competitive release. Popularity ties receive the average percentile; a single observed value maps to 50.

Display low coverage for 1–2 eligible films, moderate for 3–7, and broader for 8+. Missing data should increase uncertainty and display a coverage flag, not turn into a fake zero rating. Sparse profiles shrink toward a prior. Test specialists with few films against famous generalists during balancing; these formulas do not prove fairness by themselves.

Role-specific strength and genre fit on a card use these features. Show their inputs and calculation version in the details panel. Career duration is descriptive: `latest release year - earliest release year + 1` where dates exist; do not confuse it with age or active years.

## Fictional fees

Pricing is a separate versioned model, fixed across budget tiers. Define `z = (0.45*T + 0.35*P_price + 0.20*E)/100`, where `P_price` uses 0 if popularity is absent. Set `raw_fee = floor + (ceiling-floor)*z^2`; round to the nearest $25,000 using half-up rounding, then clamp to the role's limits. Integer cents/dollars or Decimal arithmetic avoids platform-dependent ties. Fees are locked as integer USD at draft creation.

| Role | Minimum | Maximum |
|---|---:|---:|
| Director | $150K | $20M |
| Actor, any of four slots | $100K | $30M |
| Screenwriter | $125K | $5M |
| Cinematographer | $100K | $4M |
| Composer | $75K | $6M |

Bounds are calibration knobs, not claims about real pay. The floor sum is $850K for eight slots; actual catalog minima will be higher and must be measured. A catalog is enabled for a budget tier only after the exact assignment validator proves completion and acceptable choice coverage. If Indie coverage fails, revise this versioned pricing curve or catalog before shipping; do not quietly discount specific offers. Lower popularity can reduce price without reducing talent strength, allowing specialist value.

## Collaboration evidence and caps

Use shared eligible movie IDs for the pair's drafted professional roles. Deduplicate a shared film even if either person has multiple matching credits. Define edge bonus `b_ij = min(12, 4 * shared_film_count)` for the designated relationships below.

Evaluate twelve edges: director–each of four actors (4), director–writer (1), director–cinematographer (1), director–composer (1), writer–lead (1), writer–co-lead (1), and actor–actor among lead/co-lead and each with its adjacent supporting slot (3: lead/co-lead, lead/supporting_1, co-lead/supporting_2). Every edge has equal weight in this baseline. More than three shared films cannot increase its bonus.

`chemistry H = 60 + 40 * sum(b_ij)/(12*12)`, so H is 60–100. Zero recorded collaborations gives a neutral 60, not a claim of incompatibility. Incomplete filmography means “No shared credits found in this dataset,” not “Never worked together.” Each edge opens the actual supporting movies and roles. No gossip, friendship claims, or subjective personal relationship data are used.

The greatest possible chemistry improvement over an unfamiliar team contributes 10 points to the final score (25% of a 40-point range). This cap should keep established partnerships from dominating genre suitability.

## Aggregate score

Weight role contributions in order `[1.5, 1.3, 1.1, 0.7, 0.7, 1.4, 1.1, 0.9]`; divide by their sum. Let `G_team` and `T_team` be weighted means of the corresponding 0–100 attributes. Actor star power `P_cast` is the mean of the four actor popularity values.

For spend efficiency, define `q = 0.5*G_team + 0.5*T_team`, `u = talent_spend/talent_envelope` and `E_budget = clamp(q*(1-0.30*u), 0, 100)`. This rewards useful talent at a lower share of the available envelope; it does not reward an unfilled roster. Compute only for complete valid rosters. A premium hire must improve quality enough to justify the efficiency trade-off. Calibration may reveal cheap-team dominance; evaluate it rather than assuming these weights fix it.

`studio_score = round_half_up(0.30*G_team + 0.30*T_team + 0.25*H + 0.15*E_budget)`.

All components are 0–100 and weights total 1. The studio score is deterministic, has no direct dollar or gross-revenue bonus, and remains separate from simulated profit. For example, G=80, T=85, H=70, E=75 yields 78.25, displayed as **78**. Show each weighted contribution, retain unrounded values in the result snapshot.

Compare rankings only within budget tier, game mode, challenge ID, catalog version and rules version. The same roster may receive different efficiency across tiers; this is intentional and another reason not to use a shared cross-tier leaderboard. A larger spending authorization does not guarantee a stronger score.

## Proposed release outputs — Phase 8 work

Use independently named random streams for critics, audience and revenue so adding one draw to a formula does not perturb other streams. Seed derivation, PRNG version, iteration count and rounding belong in the result record. Use uniform noise initially, pending balance testing.

| Output | Initial game formula |
|---|---|
| Critics | `clamp(0.50*T_team + 0.35*G_team + 0.15*H + U[-5,5], 0,100)` |
| Audience | `clamp(0.30*T_team + 0.30*G_team + 0.20*H + 0.20*P_cast + U[-5,5], 0,100)` |
| Gross multiplier `k` | `clamp(0.50 + 0.018*audience + 0.010*critics + 0.008*P_cast + U[-0.6,0.6], 0.2,5.0)` |
| Worldwide theatrical gross | `round_half_up(production_committed * k)` |
| Marketing | `round_half_up(0.20 * production_committed)` |
| Studio receipts | `round_half_up(0.50 * worldwide_gross)` |
| Simulated profit | `studio_receipts - production_committed - marketing` |
| Return on total cost | `100*profit/(production_committed + marketing)` |

Calculate reviews to full precision for downstream formulas, then round display values. Apply integer-dollar rounding at each named financial output consistently. No streaming, merchandising, taxes, financing, awards, or contractual back-end compensation is modeled in this baseline. Gross is revenue collected by theaters, not studio profit. The term “production profitability” must not omit marketing from this displayed all-in profit.

For example, actual production commitment $10M, marketing $2M and worldwide gross $30M produce studio receipts $15M and profit $3M (25% return on $12M cost). A $20M gross yields a $2M loss despite matching twice the production cost.

For a four-week display, retention `r = clamp(0.40 + 0.004*audience, 0.40,0.80)` and normalized weights `[1,r,r²,r³]/sum` distribute the simulated total. Round weeks 1–3 down to dollars; assign the residual to week 4 so the total matches exactly. This is still a stylized game run, not a calibrated release model.

## Explanation and balance gates

Results must show component values, weight contributions, top two genre contributors, evidence-backed chemistry links, hiring allocation and the financial reconciliation. Describe associations within the model, not claims that a person would make a real film succeed or fail. When a source rating is displayed, label it TMDB audience rating; it is not the simulated critics score.

Later test random, cheapest, genre specialist, star-heavy and collaboration-heavy strategies using identical seed sets in each tier. Report completion, mean/median score, variation and profit distributions. Check coverage by genre and price band and compare sparse/prolific profiles. Do not tune on one favorite celebrity. Any balance revision increments pricing/rating/rules versions; completed games keep their old inputs. The Phase 11 casting lab will use paired seeds for baseline and replacement, and report mean changes plus intervals over at least 100 paired simulations.
