# Phase 1 — Completion summary

Prepared for Sai Yashweer Potelu, 20 October 2026. Delivery: local VS Code source pack and completed design specifications. Phase 1 is complete as documentation; no claim is made that the proposed rules, backend or data pipeline have been implemented.

## Inspection and preservation

Recovered the prior static prototype's readable `index.html`, `styles.css`, `app.js` and `engine.js` from the existing deployment archive. All four are retained byte-for-byte. No original React/FastAPI source repository was present in this archive. Its source is plain HTML/CSS/JavaScript, so it is already directly editable and runnable. Deployment-specific metadata was excluded from the ZIP.

The prototype has six genres, 90 curated roster records, eight picks, three offer rerolls labeled “recasts,” seeded results, browser autosave, a 30-film history and copyable cards. It does not have top-five filmographies, a completed-roster recast, verified collaboration evidence, API access, a database or server-side draft validation. See [inspection details](../prototype-audit.md).

## Decisions locked for implementation

- Ten genres; eight fixed-order slots; one person can fill only one slot even if multi-skilled.
- Indie $10M, Studio $50M, Blockbuster $200M, stored as integer USD.
- Reserve 35% for non-talent production; hire from the remaining 65% ($6.5M/$32.5M/$130M).
- Marketing is separate, provisionally 20% of actual production commitment at simulation time; unused hiring authorization remains unspent.
- Three distinct candidate offers, two offer rerolls, one optional confirmed final recast.
- Exact minimum-cost assignment respects multi-role identities and protects completion.
- Fictional role-specific fees remain fixed across tiers and within a draft; price changes require versioning.
- Every candidate shows up to five verified, role-specific notable films directly on the card.
- Notability uses smoothed audience reception, vote support, secondary popularity and a small completeness signal, independent of the selected genre.
- Score weights: genre 30%, talent 30%, shared-credit chemistry 25%, budget efficiency 15%.
- Preserve seeds, action history, all model versions and frozen input data; do not rely on seed alone.
- Default competitive comparisons are separated by tier, mode, challenge and version.

## Completed artifacts

| Requirement | Document |
|---|---|
| Rules, budgets, eight roles, rerolls, recast, win conditions, five draft examples | [game-rulebook.md](game-rulebook.md) |
| Attributes, fee formula, capped chemistry, normalized scores, financial assumptions | [scoring-design.md](scoring-design.md) |
| Data fields, role eligibility, top-five ranking, missing information, provenance | [talent-data-spec.md](talent-data-spec.md) |
| Eight screens, film cards, responsive layouts, access and error behavior | [ui-ux-blueprint.md](ui-ux-blueprint.md) |
| State machine, transitions, transaction semantics, edge cases, budget fixtures | [game-state-and-edge-cases.md](game-state-and-edge-cases.md) |
| Decisions, checklist, assumptions and handoff | This document |

## Assumptions and unresolved tuning

Essential behavior is defined so implementation can begin. These issues require evidence later, not a decision to unblock Phase 2:

1. **Pricing and Indie feasibility:** fee curve and price bands are initial defaults. Actual imported role coverage and minimum-cost rosters will determine whether to adjust them.
2. **Catalog scope:** English narrative features are the initial plan. Full worldwide filmographies would require scope changes and different coverage labels.
3. **Genre mapping:** Science Fiction maps to the provider's corresponding genre; no “Sci-fi”/“Science Fiction” duplication in normalized IDs. Validate imported mappings in Phase 4.
4. **Role mappings:** story-only writing, music performance and archival acting are excluded; atypical jobs require review and versioned changes.
5. **Balance:** the 25% chemistry component and budget-efficiency formula may overreward repeat collaborators or bargain rosters. Evaluate strategies before declaring the game balanced.
6. **Financial realism:** the revenue, retention, marketing and studio-share formulas are stylized game rules. They need playtesting, not claims of prediction accuracy.
7. **Assets and data:** source images and metadata are not bundled in this pack; integration needs the proper attribution and source requirements.
8. **Platform scope:** guest local play now; persistent accounts, ownership and competition arrive later. No online deployment is necessary for this phase.

## Completion checklist

- [x] Existing prototype inspected and preserved.
- [x] Complete planned gameplay loop and eight professional slots specified.
- [x] Three integer-USD budget tiers and reserves documented.
- [x] Fictional hiring fee policy and initial formula defined.
- [x] Top-five role-specific works and visible card layout specified.
- [x] Three-candidate offers and exact affordability rules defined.
- [x] Two rerolls and one completed-roster recast specified.
- [x] Rating, chemistry, scoring and commercial definitions documented.
- [x] Eight screens and responsive/accessibility expectations documented.
- [x] Valid state transitions and edge cases specified.
- [x] Future data contracts, provenance and reproducibility specified.
- [x] Five worked fee fixtures and additional edge cases provided.
- [x] README, local run commands and next-phase handoff included.

## Phase 2 entry and exit

Use [the Phase 2 handoff](../phase-02-handoff.md). Its goal is the full-stack foundation: React/TypeScript frontend, FastAPI backend, configuration, database connection, health endpoint, documented local setup and basic checks. Preserve the Phase 0 demo as a working reference.

Phase 2 must not imply completion of the database/domain model, importer, ratings, collaboration graph, authoritative draft engine or new simulator. Those have later phases. A fresh checkout should start the new frontend and backend and visibly demonstrate a successful health request. Pin dependencies when implemented and record exact commands. Stop after the requested phase.
