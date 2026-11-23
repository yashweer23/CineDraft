# Hands-on Phase 4 lab

Work through these after setup, migration and the real PostgreSQL test command. Keep notes in `docs/development-log.md`. This phase teaches API consumption, source validation and reproducible local data.

## 1. Trace a source response

Read `backend/app/tmdb/client.py`, then `payloads.py`. Run `smoke`. Explain why the bearer token belongs in a header and why the application stores a validated subset instead of an arbitrary response. Find the checks for movie ID, image host and maximum response size.

Checkpoint: you can explain what `smoke` proves (credential/endpoint/configuration access) and what it does not prove (movie scope, database persistence, complete coverage).

## 2. Collect and inspect

Start the 20-movie import in the README. Copy its run ID. Run `status` and `review`. Record counts of eligible, excluded and review movies, mapped composers, missing runtime, and duplicate credits. Explain why a discovery sample is not a full filmography.

Open `policy.py`. Trace one inclusion and one exclusion from report reason to code. If all films qualify, inspect a synthetic exclusion case in `backend/tests/test_tmdb_policy.py`; do not invent a real excluded title.

## 3. Resume a staging run

Before publishing, run `resume` once. Every successful resource should be reused. To practice interruption on a new small batch, interrupt `start` with Ctrl+C after recording its run ID, then run `status` and `resume`. Existing successful resources stay ready; incomplete resources are collected. Source requests are reads, so interrupted requests do not modify TMDB.

Never edit a successful checkpoint to force a retry. Explain why frozen selection matters if TMDB popularity ordering changes between days.

## 4. Review and publish

If the batch has review flags, inspect their source evidence. Leave uncertainty as review or use the [manual review format](ingestion.md). Pass the same file to `review` and `publish`. A dataset can contain both eligible and noneligible movies; only eligible ones appear by default. If none qualify, publication correctly stops.

Run `publish` twice. The first successful publication reports `created: true`; the second reports `created: false`. Inspect `/api/catalog/datasets`. Explain why no gameplay action is needed to trigger this import.

## 5. Explore exact roles

In Swagger, list directors, select a returned UUID and list films with `role=director`. Compare with `role=writer`. A person who has no mapped writing credit may correctly get an empty list. A multi-role person keeps one identity. `credited_jobs` contains the actual accepted jobs; popularity does not create a role.

Ask yourself: why is this list not ready to be labeled “top five notable works”? Phase 5 must specify scoring, shrinkage, role filtering, deterministic tie-breaking and coverage treatment first.

## 6. Preserve an older version

Record the first dataset's report. Create a second run under a new label, such as `second-import-v1`, using a small batch. Review and publish it. Confirm that both datasets remain listed and the first still returns its own movie facts. Source observations can change across runs without mutating older snapshots.

Do not use SQL updates to change a sealed dataset. The PostgreSQL integration suite contains direct mutation attempts that should fail; run them in its isolated test schema instead of experimenting on your saved import.

## 7. Read the tests

From backend with development dependencies installed: `python -m pytest -q`. Read the mocked HTTP tests for 401, 429, timeouts and invalid JSON. Read the real PostgreSQL tests for resume, publication atomicity and role-specific catalog results. Without PostgreSQL configuration those 17 tests skip; a skip is not evidence that persistence passed.

Completion checklist: you can import, inspect, resume, publish and query your own local dataset; explain its incomplete coverage; and show a passing PostgreSQL test result from your machine.
