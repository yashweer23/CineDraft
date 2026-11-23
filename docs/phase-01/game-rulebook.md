# Phase 1 — Game rulebook

Status: approved implementation baseline for later phases; not yet the behavior of the bundled Phase 0 prototype. Rules version: `design-1.0`. All monetary amounts are fictional game economics in USD.

## Objective and loop

Act as a studio executive. Choose a genre and production tier; draft eight distinct people; optionally replace one person after filling the roster; finalize; receive fictional reviews, commercial results, and a studio score with explanations. Every completed film is a valid finish, including a financial loss. The replay objective is to improve the studio score within the same tier. A score of 80 or more earns a “Studio standout” badge; non-negative simulated profit separately earns “Cost recovered.” These are independent achievements, not requirements to finish.

Use Classic Draft as the only initial playable mode. No historical eligibility, multiplayer, live auction, negotiation, or unlimited undo is part of the core design. Real people from different eras may be mixed using the same present-day dataset snapshot; the UI must not imply they are currently available for hire.

## Genre and roles

Initial genres: Action, Adventure, Comedy, Crime, Drama, Horror, Mystery, Romance, Science Fiction, Thriller. Freeze the genre before the first offer. A new genre requires a new draft.

The fixed order is:

| Round | Slot ID | Display label | Required eligibility |
|---|---|---|---|
| 1 | director | Director | Director |
| 2 | lead | Lead actor | Acting credit |
| 3 | co_lead | Co-lead actor | Acting credit |
| 4 | supporting_1 | Supporting actor 1 | Acting credit |
| 5 | supporting_2 | Supporting actor 2 | Acting credit |
| 6 | writer | Screenwriter | Screenplay or Writer |
| 7 | cinematographer | Cinematographer | Director of Photography |
| 8 | composer | Composer | Original Music Composer |

Credit mappings are exact, versioned game policy; see the data spec for exclusions. Lead/supporting labels are game assignments, never claims about a person's prior billing or gender. A person with several eligible roles still occupies just one slot. Use person identity, not names or role-specific IDs, to enforce this.

## Production budget

| Category | Total authorization | Non-talent reserve (35%) | Talent envelope (65%) |
|---|---:|---:|---:|
| Indie Production | $10,000,000 | $3,500,000 | $6,500,000 |
| Studio Picture | $50,000,000 | $17,500,000 | $32,500,000 |
| Big-Budget Blockbuster | $200,000,000 | $70,000,000 | $130,000,000 |

Store money as non-negative integer USD, never floats in millions. Implement reserve as `total_budget_usd * 35 // 100`; talent allocation is the exact remainder. Display $10M, $3.5M, $750K, $125K; provide exact dollars in details. Rounding the display never changes affordability. If a future configurable percentage does not divide evenly, the whole-dollar remainder stays in the talent envelope.

`talent_spend = sum(locked_role_fees)`; `talent_remaining = talent_envelope - talent_spend`; `production_committed = reserve + talent_spend`. The reserve cannot be spent on talent. Unspent talent money remains unspent; it is not silently added to marketing. The selected tier is spending authorization, not automatically the final production cost.

Marketing will be a separate, disclosed expense at release, with a provisional assumption of 20% of actual production commitment (integer USD). It does not reduce the hiring envelope. The later simulator must show production cost, marketing, gross receipts, studio share and profit separately. Distribution is represented by a provisional 50% studio share of gross; do not also subtract an undisclosed duplicate distribution charge. These are game assumptions, not real contracts.

All hiring fees are fictional and fixed at the start of a draft for that dataset and pricing version. Same person + same professional role has the same fee in all three tiers. All four actor slots share the actor fee. A multi-role person may have different director and writer fees, shown before selection. Prices do not change when a player rerolls or changes genre.

## Offers and selecting people

Generate three distinct eligible candidates for the current slot, excluding drafted person IDs. Cards must show the fee, game attributes, data coverage and up to five verified role-specific works immediately. The draft cannot rely on the player recognizing a name.

At least one offered candidate must leave a complete feasible roster. Disabled cards may show an unaffordable aspirational choice, but explain whether its fee or the remaining roles' minimum cost prevents selection. Prefer three legal choices when the pool supports them. If only one or two eligible people exist, show those people plus a clear shortage message; never duplicate a card to fill a column.

Candidate order is deterministic for a persisted seed, rules version, dataset snapshot and action history. Before generating any offer, sort eligible IDs stably. Sample without replacement using a versioned PRNG. If none of the sampled offers is legal, replace its last card with a seeded selection from the feasible candidates. A generated offer has its own ID and state version.

On selection, the future backend checks the offer ID, slot, version, person identity, eligibility and completion feasibility. Atomically record the pick and locked fee, then generate the next offer. A browser-supplied price is never authoritative. Successful picks cannot be undone before roster completion; the optional final recast provides one change.

## Exact completion protection

For a tentative pick, remove every already-used person and that candidate from the remaining pool. Construct a bipartite graph: unfilled slots on one side, people on the other; allowed edges represent verified eligibility and have that role's integer fee. Find a minimum-cost assignment covering **every** remaining slot, with each person used at most once.

Accept only when an assignment exists and its cost is at most the remaining talent budget after the tentative pick. With no unfilled slots the minimum cost is zero. Equality is allowed. Independent per-role minima are insufficient: the same low-cost multi-role person cannot fill two remaining jobs. Store a witness assignment for diagnostics; it is not a guaranteed future offer or an auto-pick.

Before starting, verify that the selected catalog/tier can complete a draft. If not, return a configuration error before consuming an attempt. Never secretly increase a budget, invent a talent record, or charge a reroll for a system shortage. Freeze the dataset during a draft; if infrastructure fails, retain state and allow retry. Verified legal picks and feasibility-aware offers preserve the invariant at each turn.

## Two candidate rerolls

There are two free offer rerolls across all eight rounds. They replace only the current offer and never erase picks or alter money. Prefer three people not in the current hand. If too few fresh people exist, reuse some old people while maximizing replacements, retaining a feasible choice. Disable reroll with an explanation if no different valid offer set exists; do not consume the allowance. A changed hand consumes exactly one reroll, even if a few cards repeat. Allow previously rejected people to reappear in later offers.

Accept a reroll once per unique request ID. Save the resulting offer so refreshing the browser cannot generate free new candidates. Rerolls are unavailable after the eighth pick.

## One completed-roster recast

Review all eight people before finalizing. One confirmed replacement is permitted. Choose a slot, keep the existing roster intact, and calculate `replacement_capacity = talent_remaining + old_fee`. Offer up to three different, eligible people outside the other seven picks and excluding the original person. Do not allow candidate rerolls in this step.

Opening the recast panel creates and caches an offer for that slot. Cancel leaves the original person, price, remaining money, and recast allowance untouched. Reopening the same slot shows the same alternatives; checking another slot has a separate cached offer. If no alternative is affordable, explain this and allow cancel/finalization. A confirmed replacement is atomic: `new_spend = old_spend - old_fee + new_fee`, validate uniqueness and eight filled slots, then consume the single recast. Repeated submissions do not replace twice. Finalization prevents further changes.

## Five worked draft budgets

These are synthetic fee fixtures to test accounting, not real salaries or claims about actual people. A–H are distinct fictional test identities with the required credits. Actual candidate selection later comes from verified catalog records. Fees are shown in millions for readability; implementation values are integer dollars.

| Fixture | Genre / tier | Director | Lead | Co-lead | Support 1 | Support 2 | Writer | Camera | Score | Total talent | Talent left |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | Crime / Indie | .9 | 1.2 | 1.0 | .5 | .4 | .7 | .8 | .6 | $6.1M | $.4M |
| 2 | Horror / Indie | .75 | 1.5 | 1.0 | .5 | .5 | .75 | .75 | .75 | $6.5M | $0 |
| 3 | Drama / Studio | 4 | 8 | 5 | 2 | 1.5 | 2.5 | 2 | 1.5 | $26.5M | $6M |
| 4 | Science Fiction / Blockbuster | 20 | 30 | 25 | 15 | 12 | 5 | 4 | 6 | $117M | $13M |
| 5 | Comedy / Studio | 3 | 7 | 5 | 2 | 1 | 2 | 1.5 | 1 | $22.5M | $10M |

“Camera” means cinematographer and “Score” means composer. Fixture 2 tests exact affordability. For fixture 1, a recast replacing the $400K supporting actor with a $700K person yields $6.4M spent and $100K remaining; cancel yields the unchanged $6.1M. A replacement costing $900K fails because capacity is $800K.

## Movie Roulette — future mode only

Use the same slots, prices, uniqueness and feasibility validator. Precompute movies with at least one currently feasible person in the required role. Seeded sampling reveals a movie and its verified eligible people (use a scrollable cast list if more than three). Every selectable person must pass the normal continuation check. Ignore movies with no valid continuation without consuming player rerolls; if none exist, pause with a dataset error. This avoids unbounded random retries.

Two rerolls replace the revealed movie if another valid movie exists. Do not consume a reroll when the eligible movie set cannot change. The one final recast uses Classic Draft alternatives and the same replacement budget rule. Save movie IDs and offer IDs as part of the action history. Roulette has separate challenge rankings because its offer constraints differ.
