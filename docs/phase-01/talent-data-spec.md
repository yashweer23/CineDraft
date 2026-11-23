# Phase 1 — Talent data and notable works

Status: a future data contract. This pack includes no harvested TMDB dataset, source ratings, portraits, poster files or invented film credits. The old prototype's curated values remain labeled fictional. IDs in future synthetic fixtures must use an explicit `fixture:` namespace, never fabricated TMDB numeric IDs.

## Initial catalog scope

Import English-original-language, released, narrative feature films. Feature eligibility initially requires runtime at least 60 minutes when known; unknown runtime is queued for review rather than guessed. Exclude TV-only credits, documentaries, concerts, stand-up specials, archival compilations and unreleased titles from the game catalog. Some exclusions require review; a movie's genre alone cannot reliably identify every special or archival appearance. Record exclusion reason and manual overrides. People may have worldwide careers, but attributes in this initial game describe **the eligible imported catalog**, not necessarily their entire careers.

Aim initially for 500–1,000 movies and 250–500 eligible people, then adjust using coverage diagnostics. These are planning targets, not current imported counts. A usable catalog needs at least four distinct actors plus all other roles simultaneously, affordable continuation for every enabled tier, and enough variety for three-candidate offers. Prefer at least six eligible people per non-actor role and twelve actors; exact assignment feasibility remains the authority.

## Entities and provenance

| Entity | Required fields | Nullable/source-dependent fields |
|---|---|---|
| Person | internal ID, source=`tmdb`, unique source person ID, name, import timestamp, dataset version | profile path, popularity, biography, source update timestamp |
| Movie | internal ID, unique source movie ID, title, import timestamp, eligibility status/reason, dataset version | original title/language, release date, runtime, genre IDs, audience average/count, popularity, poster path |
| Credit | source credit ID if supplied; person ID, movie ID, cast/crew kind, original job/department, provenance | character, cast order, source credit ID when absent |
| Person-role profile | person ID, eligible normalized role, role mapping version, eligible movie IDs, feature version, pricing version, game fee in integer USD | attributes with coverage, explanatory input records |
| Notable work | person ID, role, movie ID, rank, credited job(s), ranking version, dataset version | title/year/poster/rating as supported by source |
| Dataset snapshot | immutable version, import start/end, scope/filter version, validation report, prior parameters | source change watermark |

Store original strings alongside normalized roles. A single source credit can be observed through several endpoints; deduplicate it by source credit ID. If absent, use a documented composite `(person, movie, kind, job, character)` and retain provenance records, avoiding collapse of distinct valid jobs. In film ranking and collaboration, deduplicate by movie ID regardless of credit-row count.

Use null for unknown values. A zero vote count means unrated, not a zero-quality film. Missing release date has a null year; display “Year unavailable.” Missing images get local placeholders or initials, never a different person's image. No guessed poster URLs. Cache source image paths with provider configuration; obtain image URLs through the documented image configuration during implementation.

Suggested serialized person-role response, shown as a shape rather than fake source data:

```text
person_id: stable internal identity
source_person_id: actual verified source identifier
eligible_role: director | actor | writer | cinematographer | composer
hiring_fee_usd: integer >= 0
fee_is_fictional: true
rating: value + version + contributing movie IDs + coverage
genre_fit: value + selected genre + evidence
notable_works: 0..5 records, each with verified movie identity and matching credits
collaborations: shared movie identities + both people's matching jobs
dataset_version / rules_version / ranking_version / pricing_version
```

## Role eligibility

| Game role | Accept initial source credit | Do not treat as equivalent |
|---|---|---|
| Actor | A valid narrative acting cast credit, including credited voice roles | Self-only appearance, archive footage, stunt-only or unverified cameo claim |
| Director | Crew job exactly `Director` | Assistant Director, producer, actor in a film they did not direct |
| Screenwriter | Crew job `Screenplay` or `Writer` | Novel, Book, Characters, Story-only, Script Supervisor |
| Cinematographer | Crew job `Director of Photography` | Camera Operator, still photographer, editor |
| Composer | Crew job `Original Music Composer` | Music Supervisor, song performer, soundtrack artist without an original-score credit |

These are initial game mapping decisions. Retain source job spelling; compare against an explicit versioned allowlist, and audit unexpected variants rather than broad substring matching. Writing exclusions deliberately favor screenwriting contribution; adding story credits later requires a rule revision. “Known for” lists or department alone cannot prove eligibility. Ambiguous acting character labels go to review and stay out of the game until resolved. Do not infer missing credits from similar names.

One person gets one identity across every profession. The prototype's combined “Trent Reznor & Atticus Ross” entry must be split into actual individual source records during migration; it cannot become a single invented person ID. Each individual then needs their own verified composing credits and fee. No Phase 1 source edit is made to the old entry.

## Selecting up to five notable works

Rank by **the role currently being drafted**, independent of the chosen genre. A director's acting cameo cannot become one of their directing works. For a multi-role person, a writing card and directing card may show different lists. Use eligible released films across the imported career scope, not only recent releases or the current game genre. Label the section “Notable films · from our catalog” until broad coverage is established.

1. Join the person to verified eligible movie credits for the requested role.
2. Deduplicate movie IDs. Combine matching credited jobs into one compact label.
3. Filter by the snapshot's scope and released cutoff. Do not use future data in any later historical challenge.
4. Compute reception shrinkage `B=(v*R+500*C)/(v+500)`; `C` is the frozen catalog prior. When R or valid v is absent use `B=C` **internally only**, flag unavailable reception, and set v=0 for ranking signals.
5. Let `P` be the percentile rank of `log(1+movie_popularity)` in the eligible catalog (0–1), ties averaged; use 0 if absent. Let `V=min(log(1+v)/log(100001),1)`. Let `D` be the fraction of four present source fields: release date, poster path, valid reception pair, original language.
6. Compute `notability = 0.75*(B/10) + 0.15*V + 0.08*P + 0.02*D`.
7. Sort descending by notability, then descending vote count, then ascending movie source ID. The stable ID resolves exact ties. Take the first five.

Credit validity is a hard gate, not a small scoring factor. Completeness has only 2% weight so an absent poster does not eclipse a meaningful work. Confidence smoothing and capped vote influence reduce low-vote outliers while preserving discovery. This ranking is an explainable editorial/game choice, not a definitive ranking of artistic quality.

For illustration with prior 6.5: a 9.9-rated film with two votes has B≈6.514, whereas an 8.0-rated film with 5,000 votes has B≈7.864. The two-vote outlier cannot dominate merely because its raw rating is higher. These are synthetic numeric examples, not real movie records.

If only three verified works exist, show those three with “3 verified films available.” With none, show “Filmography unavailable” and no fake titles. A missing eligible credit makes the person ineligible for that role even if a generic known-for list exists. A missing rating or poster alone does not remove an otherwise verified film.

Keep full role-filtered filmography accessible in a details drawer. It is distinct from the card's stable top five; filtering the drawer by genre must not silently change the card's career list. Each ranked item should explain that it was selected from verified matching credits using reception, vote support and secondary visibility signals.

## Card display contract

Always show name, current game role, fictional hiring fee, game talent strength, selected-genre fit, specialties, career coverage, and all available notable titles up to five. Each work has title, source-supported year, credited role, small poster when available, and source audience rating when available. Label that rating “TMDB audience,” not critics. Use an accessible “No rating” label for missing data.

No hover or extra screen should be required to read the five titles. On narrow screens, stack cards and allow ordinary page scrolling. Keep the full-filmography control as an enhancement. Shared-credit messages link to evidence and must not claim friendship. All game-derived fields must be visually distinguishable from source metadata.

## Reproducibility and import behavior

The later importer will fetch details and credits, validate, and commit an immutable dataset snapshot. Requests need bounded retries with backoff, source error handling, resumable checkpoints and idempotent upserts. Do not call TMDB on every pick. Keep the old valid snapshot available while an import fails. Record exclusions and missing-data counts per role and genre. Source attribution and privacy-sensitive credentials belong in their appropriate layers.

Each completed game stores genre, tier, reserve rule, offers and action sequence, person/slot assignments, locked individual fees, exact attributes and evidence references, all version IDs, seed and PRNG version, frozen configuration, rounding convention and full simulation output. A seed alone cannot reproduce changed data or a different reroll sequence. A durable normalized snapshot of the inputs is required; mutable live catalog joins alone are insufficient.

## Official integration references

Reviewed 20 October 2026:

- [Movie credits](https://developer.themoviedb.org/reference/movie-credits) documents `GET /3/movie/{movie_id}/credits`.
- [Person movie credits](https://developer.themoviedb.org/reference/person-movie-credits) documents `GET /3/person/{person_id}/movie_credits`.
- [FAQ and attribution](https://developer.themoviedb.org/docs/faq) describes non-commercial access and attribution requirements.

When integrating TMDB, include an approved, subordinate logo and the notice: “This product uses the TMDB API but is not endorsed or certified by TMDB.” Put attribution in the application's About/Credits section and verify applicable terms before distribution. The bundled offline prototype currently makes no TMDB calls. The formulas, scope decisions and job allowlist above are CineDraft design choices, not claims that TMDB supplies talent quality, salaries or chemistry.
