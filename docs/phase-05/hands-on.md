# Phase 5 hands-on lab

## 1. Read the calculation before building

Open `backend/app/talent/calculation.py` and [formulas.md](formulas.md). Identify the separate source rating, shrunk film reception, person reception and game talent strength. Explain why popularity does not enter strength but does enter fictional pricing.

Run the synthetic example. Find the two actors with the same strength and different fees. Read the price's raw Decimal string and reproduce its $25,000 half-up rounding.

## 2. Preview a real local dataset

Finish the local PostgreSQL checks and Phase 4 publication. Copy its exact sealed dataset ID from Swagger. Run `scripts.build_talent` with `--dry-run`. Inspect role counts, low-coverage profiles, missing role/genre evidence, role fee ranges and the optimistic roster lower bound. A 20-movie import may have substantial gaps.

Checkpoint: explain why a low lower-bound cost cannot certify a draft if one person would need to fill two roles.

## 3. Publish and compare

Remove `--dry-run` and build with a fresh label. Save its dataset/feature/pricing IDs and hashes. Run it again; the existing successful build should return `created: false`. Open Talent Lab, load the catalog and choose the version. Record one profile's fee, strength and coverage.

## 4. Change genre, then role

Change the genre in the Talent Lab. Genre exposure fit can change; the same person's fee and top-five works must not change. Then select a different professional role. A multi-role person may have a different strength, fee and film list, or be absent when there is no matching credit.

Open calculation evidence. Trace one work from `movie_id` through `credited_jobs` and the ranked components to the visible title. The Phase 4 raw filmography route still shows the chronological list.

## 5. Inspect sparse evidence

Find a low-coverage profile. Inspect rated movie count and reception-prior flags. A missing source rating must display “No audience rating,” even when the game calculation has a prior-based value. A role/genre catalog gap displays a warning; do not interpret its fallback score as observed genre expertise.

If your real dataset has no missing fields, use the synthetic fixture exercise from the README. Never modify source metadata just to manufacture a demonstration.

## 6. Freeze history

Create a second dataset through a new Phase 4 import, or build the same dataset under a second label to practice version handling. Confirm both versions remain selectable. The first should keep its fee/rank values. Old draft snapshots are unchanged by new publications.

Read the PostgreSQL tests for immutable rows and a forced pricing-insert failure. That test ensures feature rows roll back too. Do not imitate direct SQL mutation attempts on your real data; the test suite uses isolated schemas.

## 7. Explain it in an interview

Use your own results to answer:

- What happens to a 9.9 rating supported by only two votes?
- How does one person's actor profile differ from their director profile?
- Why is a hiring fee fictional and independent of the production tier?
- How do you preserve an older game's source inputs when TMDB changes?
- What do coverage reports reveal that a single talent score hides?

Record your commands, actual results and one limitation in `docs/development-log.md`. Phase 6 adds shared-film evidence for collaboration.
