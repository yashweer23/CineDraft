# Release 0.14.0 — local portfolio package

This is the fourteenth and final core roadmap phase. It packages the existing game for local review and adds a richer fictional catalog, a reproducible worked film, captioned video, architecture diagrams, operations guide, and interview material. The API schema changes only its application/health version. No endpoint, ruleset, scoring formula, migration or runtime dependency changed.

## Evidence ledger

| Check | Status | Evidence or command |
|---|---|---|
| Python app regression | **574 passed; 106 skipped** | `python -m pytest -q` from `backend/`; the skips require PostgreSQL |
| React checks / build | **55 passed; build passed** | `npm run test:frontend`, `npm run build:frontend` |
| Original game | **4 passed** | `npm test` at root |
| Browser journeys | **8 passed, mocked HTTP** | `npm run test:browser:all`; guest, account/challenge, what-if and analytics at 1280 and 390 px |
| Source packager | **8 checks passed** | Standard-library tests: reproducibility, no overwrite, missing files, traversal, symlink, hash/manifest mismatch |
| Backup wrapper | **3 checks passed with a simulated subprocess** | `npm run test:ops`; binary preservation, no clobber, failed output cleanup; no real dump claim |
| Offline demo catalog | **Calculated** | 36 people, 20 films, 228 credits, 38 person-role profiles, 341 graph edges; [preview](demo-preview.json) |
| Worked film and comparison | **Calculated; original result replay matched** | [JSON output](worked-film.json); fixed alternate director, 64 paired scenarios |
| Local video | **Included** | 130 seconds, 1280×720 H.264 with burned-in captions, plus SRT; illustrates the offline worked film |
| Live PostgreSQL and browser → API → DB | **Not run here** | Run the two Docker checks and live guest journey from the README. The two added integration tests cover demo publication/reuse and rejection of an incomplete existing dataset. |
| HTTP throughput / latency | **Not measured here** | [Phase 13 benchmark](../../README-phase13.md#5-measure-your-live-api) |
| Backup restore, Windows and independent setup | **Not run here** | [Restore drill](operations.md#restore-drill-into-a-new-database); have a second person follow the root README |
| Human playtests / remote CI / publication | **No new observations or hosted runs** | [Playtest worksheet](../phase-13/playtest.md); no GitHub remote, tag push or deployment was performed |

The included CI workflow targets an ephemeral PostgreSQL 17 service for the complete backend suite, runs frontend and original-game checks, and builds/verifies a source ZIP. Local results above do not establish that hosted CI has run or passed. See [the workflow](../../.github/workflows/ci.yml) and GitHub's [PostgreSQL service-container documentation](https://docs.github.com/en/actions/tutorials/use-containerized-services/create-postgresql-service-containers).

## Turn the local package into a reviewed release

1. Unzip into a clean folder. If upgrading, preserve private configuration and take a backup before merging. Verify migration head, readiness, actual owner commands, release/replay and the restore drill.
2. Run the PostgreSQL suite and live guest journey; retain actual counts. Run the public and owner-read benchmarks with hardware, dataset and concurrency details. Have another person run the quickstart and record any problem. Observe actual playtests before reporting usability findings.
3. Build the source ZIP from `release-files.txt` and verify it. Add any intentional new source file to that list. Never put private `.env`, caches, backup dumps, downloaded gameplay exports, or local participant notes in it. Hashes detect accidental changes; they are not a digital signature.
4. If using Git, review `git status` and the staged diff. Commit only the intended source to your chosen repository. Once checks are green at the intended commit, create a local tag with `git tag -a v0.14.0 -m "CineDraft 0.14.0: portfolio release"`. Verify with `git show --no-patch v0.14.0`. Do not move an existing tag to hide later changes. Publish the tag/assets only when you choose a remote and have verified access.
5. Attach the release notes, ZIP checksum, and your own live demo recording to your portfolio. The local Docker workflow remains the supported demo even if you do not deploy a public service.

## After the core roadmap

The highest-value next work is closing the unchecked rows above and recording your own live studio demo. If you want a new feature afterward, the roadmap's **optional Phase 15 is real-time multiplayer draft rooms**: server-controlled turns, exclusive picks, reconnects and idempotent retries. It is not part of this release. Do not change the existing solo results to implement it.
