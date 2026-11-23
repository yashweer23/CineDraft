# TMDB ingestion and review

The importer makes explicit read-only requests to TMDB, stores validated checkpoints, then creates an immutable local dataset in one transaction. Catalog requests read PostgreSQL and never fetch TMDB. No import runs at API startup.

## Commands and limits

Run `python -m scripts.import_tmdb --help` from `backend/`, or prefix it with `docker compose run --rm api` from the project root.

| Command | Purpose | Needs TMDB token |
|---|---|---|
| `smoke` | Validate one live image configuration response; no DB writes | Yes |
| `start --dataset LABEL` | Create a run and collect a bounded batch | Yes |
| `resume --run UUID` | Retry failed/missing checkpoints | Yes |
| `status --run UUID` | Inspect plan, resource states and saved report | No |
| `review --run UUID` | Compute/save coverage and exclusion report | No |
| `publish --run UUID` | Atomically create and seal the dataset | No |

Defaults are one discovery page and at most 20 movies. `--pages` accepts 1–50; `--max-movies` accepts 1–2000. Pages contain only source IDs in the checkpoint; movie details are fetched separately. `--ids` accepts actual positive TMDB movie IDs separated by spaces and bypasses discovery. Set `--max-movies` high enough to contain all explicit IDs. No numeric IDs in test fixtures should be used as real movie selections.

The default cutoff is the current UTC date, frozen in the run plan. `--cutoff YYYY-MM-DD` can select an earlier date. It filters release eligibility, **not historical metadata**: ratings and credits reflect the responses fetched during this import, not their values on the cutoff date. The discovery ranking is a bounded popularity sample, not a complete film universe or complete careers.

Dataset labels use 1–71 lowercase letters, digits, hyphens or underscores. `first-import-v1` becomes `tmdb:first-import-v1`. Record the printed run UUID separately from the dataset label. Start labels are unique; resume takes a UUID, not a dataset ID.

## What is stored

`import_runs` stores the frozen plan, status and review report. `import_resources` stores each validated configuration, discovery page or movie payload, SHA-256 hash, fetch timestamp and safe failure code. Only the modeled fields survive validation; these are normalized checkpoints, not byte-for-byte original HTTP bodies. Movie checkpoints include cast, crew and keywords.

Successful checkpoints cannot be edited, and published runs cannot change. Failed resources can become successful on resume. An advisory lock serializes CLI imports without holding one transaction open during HTTP requests. A disconnected process may leave a run staging; the next resume reconstructs selection from its checkpoints.

Publication revalidates all required hashes and data, deduplicates identities/credits, computes eligibility, inserts versioned snapshots and seals the dataset in one database transaction. Failure rolls back that publication. Resource hashes, image configuration, policy version, plan, manual reviews and coverage report form the dataset manifest. `content_hash` hashes that manifest; it is not described as a direct hash of every relational row. Repeated publication of a completed run is a no-op.

A fresh source observation requires a new run and label. Resuming does not refresh successful checkpoints. A permanently missing movie cannot be silently skipped inside a frozen run; start a corrected selection instead. Checkpoints are retained for provenance; retention cleanup is not part of Phase 4.

## Scope and review rules

A movie must have original language `en`, status `Released`, release date on/before the cutoff, runtime at least 60 minutes, no adult flag, and evidence of a narrative cast. Documentary and TV-movie flags exclude a title. Unknown runtime or date, missing adult flag, video flag, or ambiguous format keywords hold a title for review. The 60-minute threshold is this game's explicit policy.

Stand-up, concert, filmed-theater and archive/compilation keywords flag review because a keyword can describe a fictional plot. Confirmed non-narrative titles should be excluded manually. Unresolved review titles never enter the eligible pool. The keyword set is conservative and finite; the importer cannot prove every narrative/exclusion decision automatically. Inspect the first batch before using its data for subsequent game features.

Role mapping is exact and versioned:

| Role | Accepted source credit |
|---|---|
| Director | Crew job `Director` |
| Actor | Cast with a nonempty narrative character label |
| Writer | Crew job `Writer` or `Screenplay` |
| Cinematographer | Crew job `Director of Photography` |
| Composer | Crew job `Original Music Composer` |

Known-for departments do not confer a role. Self/archival, uncredited/cameo and stunt/stand-in labels do not become eligible acting credits; their original text remains available in checkpoints and the credit review report. Voice characters can qualify. No per-credit override is implemented: ambiguous acting credits remain unmapped pending a reviewed policy change/new version. The film-level override cannot silently repair credits.

One source person has one stable identity across roles. Source credit IDs are deduplication keys; when absent, a canonical composite of movie, person, kind, job and character is used. Identical repeats collapse; conflicting repeats stop publication. Writer and Screenplay remain distinct source jobs attached to one role. Names never merge different source identities.

## Manual film reviews

Start with `data/reviews.example.json` (an empty object). Create your private `data/reviews.local.json` and use source movie IDs from the report as JSON string keys. Replace all explanatory placeholders; this example is a format illustration, not importable source data:

```json
{
  "<actual-source-movie-id-from-report>": {
    "decision": "eligible",
    "reason": "Record the evidence and source used to confirm narrative format and runtime.",
    "reviewer": "Your name",
    "confirmed_narrative_feature": true,
    "verified_runtime_minutes": 100
  }
}
```

`reason` needs at least ten characters. Supply an actually verified runtime when resolving missing/zero runtime; do not copy the illustrative value. An eligible decision requires `confirmed_narrative_feature: true`; it can clear format/video flags and a missing runtime, but cannot bypass hard exclusions, missing date/adult flag, or missing narrative cast. An exclusion needs `decision: "excluded"`, `reason`, and `reviewer`; omit the optional confirmation/runtime fields.

**Pass the same review file to both review and publish.** Review saves a report, not implicit future overrides. Publication always recomputes from the supplied file.

```powershell
# Mount the local data folder so a one-off API container can read your review file.
docker compose run --rm -v "${PWD}/data:/reviews:ro" api python -m scripts.import_tmdb review --run $runId --reviews /reviews/reviews.local.json
docker compose run --rm -v "${PWD}/data:/reviews:ro" api python -m scripts.import_tmdb publish --run $runId --reviews /reviews/reviews.local.json
```

Native Python from `backend/` uses `--reviews ../data/reviews.local.json`. Movie IDs outside the run and unknown review fields are rejected. Reviews become part of the sealed manifest; corrections need a new dataset.

## Coverage, images and missing values

Reports contain movie decisions, per-role unique people, per-genre eligible films, missing fields, duplicate counts, unmapped crew jobs and cast review items. Coverage warnings are advisory thresholds, **not a playability proof**. Every Phase 4 dataset is marked `playable: false` until later features, prices and draft feasibility exist.

A person's metadata is chosen from the first credit observation in stable movie-ID order. Their coverage counts only eligible imported movies with mapped credits; it is not a complete career filmography. Null popularity, rating, artwork or runtime is not invented. A rating with zero/missing votes becomes null. Original observations remain in checkpoints.

Image URLs combine validated TMDB image configuration, a supported size and a genuine source path. Missing/unsafe paths produce null. Images are not downloaded into the ZIP. The studio includes a TMDB notice and links to an externally hosted logo; external assets need internet access. Verify the current official logo and attribution guidance before public distribution.

## HTTP behavior

The backend sends the token only in an Authorization header to allowed TMDB read paths. It uses a 20-second HTTP timeout with a 5-second connect timeout, at most four attempts, exponential backoff with jitter, and a local rate of at most four request starts per second. HTTP 429/5xx and transient network errors retry; other unexpected statuses stop. Retry-After above 60 seconds stops with a resumable error. Responses are capped at 16 MiB and validated before storage. These are application limits, not a promised provider quota.

Errors do not print credentials, full URLs with tokens or upstream bodies. There are no write/import endpoints in the API. Local development binds published Docker ports to loopback. Authorization for future game actions remains a later phase.
