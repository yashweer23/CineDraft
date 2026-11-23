# Demonstrate CineDraft in two to three minutes

Open with a question the viewer can answer by the end: **“If we hire a cheaper director, do we actually make a more profitable fictional film?”** The [2:10 captioned walkthrough](worked-film.mp4) and [run data](worked-film.json) follow one reproducible offline film. The video explains actual engine outputs; it is not footage of a live PostgreSQL session. [Caption transcript](worked-film.srt).

| Time | What to show | What to explain |
|---|---|---|
| 0:00–0:19 | Thriller brief, $200M blockbuster | $70M is reserved for production; $130M is available for hires. The catalog is fictional. |
| 0:19–0:47 | Director card, its five works, then eight picks | The selected card must leave a complete, affordable roster. This fixed example spends $62M. |
| 0:47–1:07 | Actor 12 / Director 06, *Synthetic Thriller Study 19* | Each has a named credit on this film. Their six shared films reach the 12-point edge cap. |
| 1:07–1:26 | Four component contributions | Genre fit, talent, chemistry and efficiency reconcile to 53/100 after rounding. |
| 1:26–1:46 | Release ledger | $399,067,581 gross is not profit. Receipts of $199,533,791 less $132M production and $26.4M marketing leave $41,133,791. |
| 1:46–2:10 | Swap Director 06 for Director 02 | The fee drops $7,975,000. Across 64 paired scenarios the median fictional profit difference is **−$6,018,638.50**. The original result replays exactly. |

For your own **live studio recording**, prepare the catalog locally, start a Blockbuster practice draft, save its recovery token privately, and hide it before recording. Capture the brief, one card, a dossier and shared credits. Finish the other seven picks off camera or use a cut with a label. Show the review screen, finalize, release, expand **Why this score?**, then open **What-if lab**. Run the original-person control and one affordable substitution. Read the actual numbers on your screen; a newly created live draft gets its own seed and need not match the worked film. Record a rehearsal first and make sure no token, password or open `.env` file appears.

## Three resume bullets to adapt after running the project yourself

- Built a React/TypeScript and FastAPI movie drafting game with PostgreSQL persistence, eight distinct hiring slots, fictional USD budgets, and server-validated offers that preserve roster feasibility.
- Implemented role-specific talent profiles and a movie-credit graph that explains casting chemistry; compared one-person substitutions across 64 paired release scenarios while preserving the original result.
- Optimized the exact roster-assignment solver from **12.26 ms to 4.48 ms median per solve** on a 100-person, eight-slot synthetic workload; verified the same minimum cost and selected identities against the previous implementation.

Use the third bullet only with its [benchmark method and raw evidence](../phase-13/evidence/assignment.json). The last comparison is a pure Python solver measurement. The broader 1,800-draft study covers generated strategy runs on a different synthetic corpus. Neither constitutes API latency, observed user growth, real-world revenue, or a TMDB ingestion count.

## Interview questions worth rehearsing

**Why isn't choosing the cheapest person per role enough?** One candidate may qualify for two roles and a film can hire that identity only once. The solver finds a distinct assignment for the remaining slots and returns a witness with the minimum cost.

**Why store the source credits?** A chemistry number alone cannot explain itself. The evidence connects two role-specific people to distinct shared movies and the credited jobs on each, so the viewer can inspect a concrete example.

**What stops a double-click from hiring someone twice?** The server checks ownership and revision and ties a request ID to its exact body and saved response. Retrying that request returns its receipt; changing the body under the same ID is rejected.

**What makes a what-if comparison fair?** For each of 64 scenarios, both teams see the same random draws. The comparison summarizes paired differences instead of treating two independent lucky runs as the effect of a substitution. These are scenario ranges, not confidence intervals or causal claims about real people.

**What evidence is missing?** Live PostgreSQL integration and restore, live HTTP benchmarks, independent clean-machine setup, and observed human sessions still need results on your stack. Show the evidence ledger rather than asserting a green hosted pipeline or a production deployment.
