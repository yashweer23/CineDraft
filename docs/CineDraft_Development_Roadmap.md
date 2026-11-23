# CineDraft — Personal Project and Resume Roadmap

Prepared for Sai Yashweer Potelu · 20 October 2026

## The project to build

**CineDraft: a data-driven movie drafting game with explainable simulations and decision analytics.**

Players choose a movie brief, draft a director, cast, and crew under constraints, then simulate a fictional release. The portfolio value comes from the data pipeline, constrained drafting engine, collaboration graph, reproducible simulations, and evidence-based explanations.

The existing prototype is the starting point. This roadmap is a plan; it does not mean the proposed features already exist.

## Current baseline — Phase 0

The current static prototype provides six genres, three budgets, eight roster slots, three recasts, budget feasibility checks, a seeded simulation, browser autosave, film history, and copyable result cards.

It currently uses curated fictional attributes, synthetic costs, genre-based chemistry, and a fixed weekly box-office curve. It has no live movie-data ingestion, backend database, user accounts, real collaboration graph, or multiplayer. The recorded 1,440 simulated-draft checks cover engine invariants, not visual, full-stack, or real-world accuracy verification.

Retain the prototype as a reference and migrate useful behavior incrementally.

## Scope and technology decisions

| Layer | Proposed choice | Purpose |
| --- | --- | --- |
| Frontend | React, TypeScript, Vite, Tailwind CSS | Maintainable draft-room interface and typed game state |
| Backend | Python, FastAPI, Pydantic | API validation, game rules, simulations, and analysis |
| Persistence | PostgreSQL, SQLAlchemy, Alembic | Credits, snapshots, users, drafts, results, and migrations |
| Data processing | Python, Pandas, an HTTP client | Repeatable ingestion and feature generation |
| Collaboration analysis | PostgreSQL joins; NetworkX if useful | Explainable shared-credit relationships |
| Charts | Recharts | Film reports, comparisons, and product analytics |
| Verification | pytest, Playwright, Locust | Engine properties, browser flows, and measured API load |
| Delivery | Docker Compose, GitHub Actions | Reproducible startup and automated checks |

Start with one backend and one database. Run ingestion as a resumable command or scheduled job. Add a queue or Redis only if measured workloads require it. Do not make Kubernetes, microservices, or a separate graph database prerequisites.

**Data:** TMDB is the proposed source for movie and person metadata, credits, and images. Its official API has movie-credit and person-filmography endpoints. Its FAQ currently allows non-commercial API use with attribution and specifies the required logo and notice. Follow the current conditions before integrating or redistributing data. Do not describe TMDB as providing actor salaries, critic reviews, awards, or individual talent ratings.

**Simulation:** scores, costs, chemistry bonuses, awards, and returns remain game constructs. TMDB user votes are not professional critic reviews. A shared credit is evidence of collaboration, not evidence of friendship or real creative compatibility.

## Core release — 14 phases

### Phase 1 — Specify the game and its rules

**Goal:** turn the concept into an implementable product specification.

- [ ] Define eight slots: director, lead, co-lead, two supporting actors, screenwriter, cinematographer, and composer.
- [ ] Define one primary mode: budget-constrained solo drafting with three offers per round.
- [ ] Choose genre options, budget tiers, recast allowance, scoring goals, and minimum pool coverage.
- [ ] Define a person-level duplicate rule: a multi-skilled filmmaker can fill one slot per film.
- [ ] Specify how debut, decade, and cross-era eligibility would work; keep complex historical mode outside the first release.
- [ ] Describe the Eraball-inspired later mode: spin a movie, then select an eligible member of its cast or crew for an open slot.
- [ ] Decide when an impossible offer is replaced and whether a limited backtrack is allowed.

**Complete when:** the rules include at least five worked drafts and edge cases for exhausted pools, missing roles, and an unaffordable final pick.

**Resume evidence:** a short product requirements document and documented trade-offs.

### Phase 2 — Establish the full-stack foundation

**Goal:** make development reproducible.

- [ ] Create frontend, backend, data/scripts, tests, and docs directories in a Git repository.
- [ ] Set up React + TypeScript and FastAPI; pin compatible versions during implementation.
- [ ] Add environment examples, configuration validation, a database connection, and a health endpoint.
- [ ] Add Docker Compose for local development.
- [ ] Create CI for core checks and a minimal frontend/backend integration test.
- [ ] Preserve the original prototype and its useful engine behavior as reference fixtures.

**Complete when:** a fresh checkout starts successfully from documented commands and the frontend reaches the backend.

**Resume evidence:** clean repository structure, reproducible setup, and a passing CI run.

### Phase 3 — Design the database and API contracts

**Goal:** represent film credits and game history without losing provenance.

- [ ] Model people, movies, genres, credits, and role/job mappings.
- [ ] Model users or guest sessions, drafts, offers, picks, simulation runs, and results.
- [ ] Add dataset snapshots, feature versions, rules versions, and simulation seeds.
- [ ] Use stable external IDs and preserve multiple legitimate crew jobs without double-counting film/person pairs.
- [ ] Define API request/response schemas and a draft state machine.
- [ ] Add migrations, foreign keys, uniqueness constraints, and query indexes.

**Complete when:** migrations work against a clean database and representative credits and completed drafts can be stored and retrieved.

**Resume evidence:** ER diagram and API examples.

### Phase 4 — Build the TMDB ingestion pipeline

**Goal:** obtain a reliable, inspectable dataset rather than calling an external API on every draft click.

- [ ] Import an initial target of roughly 500–1,000 films and 250–500 eligible people; adjust based on role and genre coverage.
- [ ] Retrieve movie details, cast/crew credits, people, and image references through supported endpoints.
- [ ] Normalize IDs, dates, genres, and job names; choose explicit mappings for Director, screenplay/writing jobs, Director of Photography, and Original Music Composer.
- [ ] Make English-language feature films the initial scope; document treatment of documentaries, shorts, concerts, TV credits, and archival appearances.
- [ ] Add conservative request pacing, retries with backoff, 429 handling, resumability, and idempotent upserts.
- [ ] Track source timestamps, failed items, missing values, and coverage counts.
- [ ] Provide fixtures so development and automated tests do not depend on the live API.
- [ ] Add the required TMDB attribution in the application.

**Complete when:** running the import twice does not duplicate records, interrupted work resumes, and a data-quality report identifies gaps.

**Resume evidence:** an ETL diagram, measured imported counts, and a repeatable ingestion command.

### Phase 5 — Derive talent profiles and game ratings

**Goal:** replace arbitrary attributes with transparent, versioned game features.

- [ ] Build role-specific genre affinity from eligible credited filmographies.
- [ ] Derive experience, genre diversity, and a normalized audience-reception proxy.
- [ ] Use vote-count-aware shrinkage so one lightly rated film does not produce an extreme score.
- [ ] Separate popularity from reception; normalize relative to a recorded snapshot.
- [ ] Create synthetic draft prices and tiers from the features, then tune for game balance.
- [ ] Mark sparse-data profiles with confidence or coverage indicators and neutral fallbacks.
- [ ] Define how historical modes would avoid using future credits. Clearly label present-day ratings if used in a historical setting.

**Complete when:** every displayed attribute can show its calculation version, contributing films, and missing-data handling.

**Resume evidence:** a reproducible feature pipeline and a talent-profile explanation screen.

### Phase 6 — Build the collaboration graph

**Goal:** make team chemistry inspectable.

- [ ] Represent people as nodes and shared eligible film credits as edges.
- [ ] Distinguish director–actor, actor–actor, director–cinematographer, and director–composer relationships.
- [ ] Store the movies that support each relationship.
- [ ] Cap bonuses and account for large ensemble casts and prolific careers.
- [ ] Let users open a chemistry edge to inspect shared films and credit roles.
- [ ] Treat unseen combinations neutrally or with an explicitly fictional novelty mechanic.

**Complete when:** every relationship displayed has source-credit evidence and chemistry bonuses cannot grow without limit.

**Resume evidence:** an interactive collaboration view and an explanation of the graph design.

### Phase 7 — Implement an authoritative drafting engine

**Goal:** keep every legal draft completable and every accepted move valid.

- [ ] Move official draft state, offer generation, prices, and recast counts to the backend.
- [ ] Validate eligibility, available slots, person-level uniqueness, and remaining budget.
- [ ] Use feasibility checks that respect both the remaining budget and the role coverage of multi-role candidates.
- [ ] Generate seeded offers with at least one legal continuation.
- [ ] Record each offer and accepted action, with a state version or equivalent concurrency control.
- [ ] Make duplicate requests and page refreshes safe; prevent repeated submissions from consuming picks twice.

**Complete when:** users cannot overspend, draft the same person twice, change the current offers, or strand the roster using a legal action.

**Resume evidence:** documented game-state transitions and property tests for the important invariants.

### Phase 8 — Implement a reproducible release simulation

**Goal:** produce varied outcomes that can be explained and replayed.

- [ ] Combine genre fit, cast appeal, role-weighted features, collaboration bonuses, and production choices.
- [ ] Separate a fictional critic-style score from audience reception and commercial performance.
- [ ] Replace the fixed weekly gross curve with a bounded model that responds to audience retention and campaign choices.
- [ ] Record the data snapshot, rules version, seed, and assumptions with every result.
- [ ] Generate a readable contribution breakdown.
- [ ] Evaluate multiple seeds to show distributions, such as a median and an 80% simulated interval.
- [ ] Keep costs and revenue shares explicit and fictional. Do not advertise real box-office forecasting accuracy.

**Complete when:** replaying the same run reproduces its outcome, changing its seed gives controlled variation, and the report accounts for every displayed contribution.

**Resume evidence:** a simulation design note, sensitivity analysis, and reproducible run examples.

### Phase 9 — Build the polished draft-room frontend

**Goal:** make the complete game pleasant to play.

- [ ] Port the setup, draft, review, and results flow to React.
- [ ] Show talent portraits where available, filmography evidence, prices, fit, and readable empty/loading states.
- [ ] Explain disabled picks, remaining reserves, and recast consequences.
- [ ] Add responsive layouts, keyboard interaction, reduced-motion behavior, and accessible dialogs.
- [ ] Support resume-after-refresh and interrupted API requests.
- [ ] Show film reports, credits, charts, and a local or server-backed filmography.

**Complete when:** a user completes the full loop on desktop and mobile widths, including refresh and error recovery.

**Resume evidence:** screenshots and a short end-to-end demonstration.

### Phase 10 — Add accounts, daily challenges, and leaderboards

**Goal:** make the project usable beyond one browser.

- [ ] Keep a guest route and add a secure account/session flow.
- [ ] Store owned drafts and film history; enforce ownership on every relevant API.
- [ ] Add a daily challenge using a fixed catalog, rules version, deadline/timezone, and competition policy.
- [ ] Define attempt limits and whether first or best attempts count.
- [ ] Use reproducible offer rules that do not leak or depend unpredictably on other players' actions.
- [ ] Compute official results on the server and reject client-supplied scores.
- [ ] Rank within comparable challenge, budget, and rules-version groups; document tie-breakers.

**Complete when:** two accounts compete under the same challenge rules, cannot access each other's private drafts, and cannot submit an arbitrary score.

**Resume evidence:** persistent user flows, challenge reproducibility, and score-integrity checks.

### Phase 11 — Add the “What if I changed this pick?” lab

**Goal:** create a distinctive, interview-worthy decision feature.

- [ ] Let a player replace one eligible talent in a completed film.
- [ ] Respect uniqueness, role, catalog, and budget constraints.
- [ ] Re-evaluate the original and alternative with the same set of random seeds.
- [ ] Show changes in median reviews, gross, simulated return, and chemistry, plus uncertainty.
- [ ] Link each change to the features and shared credits that explain it.
- [ ] Keep hypothetical runs separate from official leaderboard entries.

**Complete when:** identical alternatives show zero paired difference, and valid replacements produce repeatable, attributable comparisons.

**Resume evidence:** a demonstration that compares two casts under controlled randomness.

### Phase 12 — Add a small business-intelligence layer

**Goal:** demonstrate how you turn usage data into product decisions.

- [ ] Record draft starts, picks, recasts, abandonment, completions, and replays with consistent event IDs.
- [ ] Deduplicate retries and exclude internal test sessions from real usage metrics.
- [ ] Create SQL summaries for the completion funnel, median round time, talent pick rate, genre popularity, and budget allocation.
- [ ] Compare pick rates and simulated success with sample sizes and relevant budget/genre filters.
- [ ] Build an internal dashboard with a clear synthetic/demo-data label where applicable.
- [ ] Use initial playtests to propose and evaluate one concrete interface or balance improvement.

**Complete when:** a dashboard metric can be traced back to source events and at least one recommendation is supported by data.

**Resume evidence:** SQL analytics, dashboard screenshots, and a short decision memo. Never present simulated sessions as actual users.

### Phase 13 — Validate correctness, balance, and performance

**Goal:** replace broad claims with measured evidence.

- [ ] Add regression and property tests throughout development; use this phase for integrated validation.
- [ ] Run generated drafts across genres, budgets, depleted pools, and multi-role cases.
- [ ] Verify deterministic replays, paired comparisons, versioned snapshots, and accounting totals.
- [ ] Use Playwright to cover complete drafts, resuming, recasts, authentication, and results on mobile widths.
- [ ] Compare random, genre-greedy, and star-heavy draft strategies over multiple seeds. Examine whether expensive or popular picks always dominate.
- [ ] Load-test representative endpoints with a documented machine, database size, concurrency, and request mix.
- [ ] Record p50/p95 latency, throughput, error rates, and before/after evidence for one optimization.
- [ ] Run a few human playtests and fix observed friction.

**Complete when:** critical game invariants and user journeys pass, results are reproducible, and benchmark and playtest reports state their limitations.

**Resume evidence:** honest measured counts, benchmark plots, and a specific optimization story.

### Phase 14 — Ship and package the project for interviews

**Goal:** make the project easy to run, review, and explain.

- [ ] Put the maintained code in a GitHub repository with a clear README and architecture/ER diagrams.
- [ ] Include environment examples, migration/import commands, fixtures, tests, and a documented demo mode.
- [ ] Keep CI green; tag a versioned release and document changes.
- [ ] Deploy the frontend and backend only when the target environment is chosen, or provide a fully reproducible local Docker demo.
- [ ] Explain that GitHub stores the code; a running Python API and PostgreSQL need a suitable runtime.
- [ ] Add basic error logging, health checks, and a migration/backup procedure appropriate to the deployment.
- [ ] Record a two-to-three-minute demo showing a draft, collaboration evidence, result explanation, and one what-if comparison.
- [ ] Write resume bullets using only completed features and actual measurements.

**Complete when:** another developer can run the project from the README and an interviewer can understand its main engineering decisions from the demo.

**Resume evidence:** repository, release, demonstration, design notes, and measured results.

## Optional extensions — choose only after the core release

### Phase 15 — Real-time multiplayer draft rooms

Build small rooms with alternating picks, reconnect handling, timeouts, and server-side turn ownership. Add WebSockets only for the behaviors that need live updates. Define whether talent pools are exclusive and how disconnects affect fairness.

**Exit criterion:** two browsers finish a match despite a reconnect, and out-of-turn or duplicate actions are rejected.

### Phase 16 — AI studio commentary

Generate a film synopsis, producer-style explanation, or fictional review from the already-computed results and cited credit evidence. Keep the scoring engine deterministic and independent from the language model. Provide a non-AI fallback, output constraints, and cost limits.

**Exit criterion:** generated text cannot change official scores and does not invent factual collaborations or real reviews.

### Phase 17 — Optional ML experiment

Only pursue this if it serves a defined research question. Predict an observed historical-film outcome using features available at the prediction cutoff. Compare a simple baseline with the proposed model using temporal splits, leakage checks, and held-out metrics. Keep post-release votes/revenue out of pre-release feature sets.

**Exit criterion:** a documented experiment with honest evaluation and limitations. Historical predictive performance does not validate predictions for imaginary casts.

## Suggested sequence and effort

The numbers below are a planning estimate for one student developer, not a delivery promise.

| Period | Focus |
| --- | --- |
| Weeks 1–2 | Phases 1–3: rules, project setup, database/API design |
| Weeks 3–4 | Phases 4–6: ingestion, talent features, collaboration graph |
| Weeks 5–6 | Phases 7–8: constrained drafting and release simulation |
| Weeks 7–8 | Phases 9–10: polished frontend, accounts, challenges |
| Weeks 9–10 | Phases 11–12: what-if comparisons and analytics |
| Weeks 11–14 | Phases 13–14: integrated checks, playtests, delivery, documentation |

Allow roughly **10–14 weeks at 12–15 focused hours per week** for the core, with overlap between implementation and testing. Reassess after the first ingestion and end-to-end vertical slice. Unknown hosting, unfamiliar tooling, or poor source-data coverage can increase the effort.

A working solo MVP arrives after Phase 9. The distinctive portfolio version is complete after Phase 14. Multiplayer, AI commentary, and ML are optional projects of their own; they are not needed to make the core resume-worthy.

## What to demonstrate on a resume

Prioritize these four claims, once implemented:

1. Built a full-stack, data-driven movie drafting game with persistent, server-validated drafts.
2. Developed a repeatable movie-credit ingestion pipeline and explainable collaboration graph.
3. Implemented reproducible simulations and paired what-if comparisons that explain roster trade-offs.
4. Added product analytics and verified behavior through automated and performance tests.

For quantified bullets, collect the number of eligible records actually imported, tested drafts, measured API latencies, completed playtests, or a demonstrated performance improvement. Do not invent scale, users, accuracy, or revenue.

## A practical prompt for each implementation phase

> Implement Phase N from CineDraft_Development_Roadmap.md in the existing CineDraft repository. First inspect the current source and instructions. Preserve working behavior and completed phases. Explain any incompatible assumption before replacing it. Implement this phase's tasks, run checks that cover its real risks, update documentation, and report the exit criteria achieved and any blockers. Keep future phases out of scope.

## Official data-source references

Reviewed 20 October 2026:

- [TMDB API FAQ and attribution](https://developer.themoviedb.org/docs/faq)
- [Movie credits endpoint](https://developer.themoviedb.org/reference/movie-credits)
- [Person movie credits endpoint](https://developer.themoviedb.org/reference/person-movie-credits)
- [Rate limiting and 429 guidance](https://developer.themoviedb.org/docs/rate-limiting)

These sources support the API/data-access statements. The game design, schedule, ratings methodology, and engineering roadmap are proposed decisions for this project.

