# CINEDRAFT — PHASE 1: GAME DESIGN, RULES & EXPERIENCE SPECIFICATION

## PROJECT OVERVIEW

CineDraft is a movie-themed strategic drafting and film studio simulation game inspired by fantasy drafting games such as EraBall.

Players act as film studio executives, assembling a cast and crew using real-world movie personalities, managing production budgets, and eventually simulating the critical, audience, and commercial performance of their fictional film.

The objective is to create a polished, strategically interesting, data-driven game that will also serve as a technically impressive full-stack portfolio project.

**This task covers Phase 1 only: Game Design, Rules, and Experience Specification.**

Do not implement the entire game, backend, database, data pipeline, or simulation engine yet.

First inspect the existing repository, understand the current prototype, and preserve its useful gameplay and design elements.

Your responsibility is to establish a comprehensive, technically implementable foundation for subsequent development.

---

## 1. CORE GAMEPLAY

The player assumes the role of a movie studio executive.

The gameplay flow is:

1. Select a movie genre.
2. Select a production budget category.
3. Enter the drafting room.
4. Draft eight cast and crew members.
5. Manage the available budget and talent salaries.
6. Review the complete production team.
7. Make permitted casting changes.
8. Release the fictional movie.
9. Receive simulated critical, audience, and financial results.
10. Explore why the film succeeded or failed.

The game should balance accessibility, strategic decision-making, realism, and replayability.

The experience should feel like running a movie studio rather than selecting random celebrities.

## 2. MOVIE GENRES

Players select a genre before drafting.

Initial supported genres:

- Action
- Adventure
- Comedy
- Crime
- Drama
- Horror
- Mystery
- Romance
- Science Fiction
- Thriller

Genre selection should eventually influence talent suitability, collaboration value, audience expectations, and simulated film performance.

Do not assume that the most famous individual is necessarily the best choice for a particular genre.

Design the game so that less-famous genre specialists can outperform more expensive mainstream celebrities in appropriate circumstances.

## 3. REALISTIC PRODUCTION BUDGET SYSTEM

IMPORTANT CHANGE: Completely replace the previous fictional credit system with a movie production budget expressed in US dollars.

Use three selectable production categories:

| Category | Total Budget | Description |
|---|---|---|
| Indie Production | $10,000,000 | Smaller independent film with significant budget constraints |
| Studio Picture | $50,000,000 | Mid-budget studio film with established talent |
| Big-Budget Blockbuster | $200,000,000 | Major studio production with access to premium talent |

Display budgets using familiar movie-industry formatting:

- $10M
- $50M
- $200M
- $750K
- $125K

Internally, store all monetary values as integer US dollars rather than floating-point millions.

### Budget allocation

The selected budget is the total production budget, not just the money available for hiring talent.

For the initial design, reserve 35% for non-talent production expenses.

The remaining 65% becomes the cast and crew hiring budget.

Examples:

**Indie Production — $10M**
- Total production budget: $10M
- Non-talent production reserve: $3.5M
- Available talent budget: $6.5M

**Studio Picture — $50M**
- Total production budget: $50M
- Non-talent production reserve: $17.5M
- Available talent budget: $32.5M

**Blockbuster — $200M**
- Total production budget: $200M
- Non-talent production reserve: $70M
- Available talent budget: $130M

These percentages are initial gameplay design choices and should remain configurable.

Marketing and distribution costs should not be silently included in this production budget. Document how they will be handled during the later financial simulation.

### Talent compensation

Each draft candidate has a hiring fee.

IMPORTANT:

Talent prices must be clearly described as **fictional, game-generated hiring fees**, not verified real-world salaries.

Eventually, prices should take account of:

- Career experience
- Filmography
- Popularity
- Role
- Genre specialization
- Historical audience reception
- Market demand as approximated by the game
- Selected production tier, if relevant to the pricing model

Ensure all eight positions remain realistically fillable in each budget category.

Avoid a pricing model where expensive stars always dominate or inexpensive candidates are automatically weak.

## 4. THE EIGHT DRAFTING POSITIONS

Each player must recruit exactly eight people.

| Position | Slots |
|---|---|
| Director | 1 |
| Lead Actor | 1 |
| Co-Lead Actor | 1 |
| Supporting Actor | 2 |
| Screenwriter | 1 |
| Cinematographer | 1 |
| Composer | 1 |

Rules:

- Each position must be filled.
- A person cannot occupy multiple positions within the same draft.
- A person may be eligible for multiple professional positions based on actual movie credits.
- Director eligibility must use directing credits.
- Actor eligibility must use acting credits.
- Screenwriter eligibility must use appropriate writing credits.
- Cinematographer eligibility must use cinematography credits.
- Composer eligibility must use relevant original-score composing credits.
- Lead and supporting actor designation is a game assignment, not necessarily their historical billing.

For Phase 1, use a fixed role order.

Design the rules so configurable role ordering could be added later.

## 5. THREE-CANDIDATE DRAFTING SYSTEM

Retain the existing three-candidate drafting concept.

During each round:

1. The player sees the position they are currently filling.
2. Three eligible candidates appear.
3. Every candidate displays their hiring fee and professional information.
4. The player compares the candidates.
5. The player selects one person.
6. The selected person is added to the roster.
7. Their fee is deducted from the remaining talent budget.
8. The player advances to the next position.

Design for two free candidate-offer rerolls per complete draft.

A reroll replaces the current offer where possible and must not erase previously selected people or change the player's budget.

The backend, when implemented, must be responsible for validating every pick.

### Budget protection

Never allow a selection that leaves the player unable to afford the remaining required positions.

Define an affordability system that considers:

- Remaining budget
- Unfilled positions
- Minimum feasible cost of remaining roles
- Candidate eligibility
- Duplicate restrictions
- Available candidate pools

The draft engine must not generate a situation where the user is forced to abandon an otherwise valid game because all future offers are unaffordable.

Specify how the engine handles candidate shortages and impossible combinations.

## 6. CRITICAL FEATURE — TOP 5 WORKS FOR EVERY CANDIDATE

This is a mandatory gameplay and UI requirement.

**Every draft candidate should display their top five notable film works directly on their candidate card.**

Players should not have to recognize every celebrity by name.

The purpose is to help players make informed decisions and discover talented, lesser-known individuals.

For example, a player who does not recognize a screenwriter or cinematographer should still be able to evaluate that person based on their filmography.

### Information to display

Each candidate card should show:

**Primary information**
- Name
- Portrait
- Professional role
- Fictional hiring fee
- Overall talent rating
- Genre specialization

**Filmography section**
- Up to five notable films
- Film title
- Release year
- Movie poster thumbnail where available
- The candidate's credited role in that movie
- TMDB audience rating where available

**Additional information**
- Genre compatibility
- Career experience
- Previous collaborations with already drafted talent, where applicable

### Example layout

DIRECTOR — DAVID FINCHER

Hiring Fee: $XXM (fictional example)

Genre Strength: Crime / Thriller

Notable Films:
1. Se7en (1995)
2. Fight Club (1999)
3. Zodiac (2007)
4. The Social Network (2010)
5. Gone Girl (2014)

[VIEW FULL FILMOGRAPHY]

[SELECT DIRECTOR]

This example is illustrative. Actual lists must eventually be generated from verified film credits rather than permanently hardcoded.

### Top five selection logic

Do not simply select the five most popular movies without considering the person's contribution.

Design an explainable ranking methodology using:

- Film audience rating
- Number of audience votes
- Popularity as a secondary signal
- Whether the person has the appropriate professional credit
- Credibility and completeness of source data

Avoid allowing films with extremely few votes to dominate rankings.

Do not invent film credits, ratings, years, or posters.

For actors, show films in which they have acting credits.

For directors, show films they actually directed.

For screenwriters, show films with appropriate writing credits.

For cinematographers, show films with cinematography credits.

For composers, show films with relevant scoring credits.

Handle multiple credits and professional roles correctly.

If only three verified films exist for an individual, display those three films rather than inventing five.

The five notable works should represent the person's overall career, while genre-specific suitability should be displayed separately.

### UX requirement

The five notable works must be visible on every candidate card, without requiring the player to open another screen.

On desktop, use a compact but readable filmography section.

On mobile, maintain access to all five titles through responsive layout without burying the information.

Clicking a film or using "View Full Filmography" should eventually open a more detailed panel.

This feature should make selecting lesser-known candidates genuinely enjoyable and strategically useful.

## 7. GENRE FIT AND TALENT RATINGS

Define a transparent initial talent-rating framework.

Attributes should eventually be calculated from real movie data.

Suggested dimensions:

- Role-specific strength
- Genre experience
- Career experience
- Versatility
- Historical film reception
- Popularity
- Collaboration familiarity

Distinguish popularity from quality and experience from performance.

Do not penalize less-famous people simply because they have smaller filmographies.

Document mechanisms for handling low sample counts and missing data.

Ratings should be explainable through supporting films and credits.

Do not implement complex machine-learning models during Phase 1.

## 8. COLLABORATION AND CHEMISTRY

Design the rules for a collaboration system based on previous film credits.

Examples:

- Director and actor who have worked together
- Director and composer with shared credits
- Director and cinematographer with shared credits
- Two actors who appeared in the same film
- Writer and director who worked on the same movie

Previous collaborations should generate possible in-game bonuses.

The system must eventually show the specific movies supporting each relationship.

These bonuses must be capped.

Do not automatically assume that sharing a film means two people have excellent real-world personal chemistry.

Treat collaboration as an evidence-backed game mechanic.

## 9. GAME SCORING SYSTEM

Define an initial transparent scoring model.

Use these starting weights:

| Component | Weight |
|---|---|
| Genre Compatibility | 30% |
| Talent Strength | 30% |
| Collaboration Chemistry | 25% |
| Budget Efficiency | 15% |

These weights are initial hypotheses, not final validated values.

All components should be normalized and their calculations documented.

Describe how these components eventually influence:

- Critics' score
- Audience score
- Fictional worldwide box office
- Production profitability
- Final studio score

The game should reward intelligent casting, appropriate genre selection, collaboration, and efficient spending.

Spending $200M must not automatically result in a better final score than spending $10M.

For competitive play, define separate budget-tier leaderboards or a normalized scoring method.

Commercial outcomes must be clearly described as fictional simulations, not real-world financial predictions.

The actual simulation engine will be implemented in a later phase.

## 10. RECASTING AND DRAFT COMPLETION

Allow one recast after all eight positions have initially been filled.

Recasting rules:

- The player selects one existing position.
- The original person is temporarily considered for replacement.
- Alternative eligible candidates are displayed.
- The player must be able to afford the replacement.
- The removed person's salary becomes available when calculating affordability.
- The replacement must not conflict with another selected person.
- Canceling the recast restores the original roster without any budget changes.
- The recast is consumed only after a replacement is confirmed.

Prevent negative balances and invalid rosters.

After confirmation, the player can move to the movie premiere and results simulation.

## 11. FUTURE MOVIE ROULETTE MODE

Design, but do not implement, an optional alternative drafting mode.

In Movie Roulette:

1. The game reveals a random real movie.
2. The player sees the movie title, year, and poster.
3. The player selects an eligible individual from the movie's credited cast or crew.
4. The selected person's professional credit must match the required draft slot.
5. Their hiring fee is deducted from the budget.
6. The next round begins.

If the revealed movie has no valid candidates for the current position, the game automatically draws another eligible movie.

Prevent duplicate talent selections.

Document how rerolls and affordability work in this mode.

Movie Roulette should share the same underlying drafting and scoring systems as Classic Draft.

## 12. UI / UX DESIGN SPECIFICATION

Design CineDraft as a premium, cinematic web application.

Visual direction:

- Dark cinematic interface
- Refined typography
- Movie posters and portraits
- Subtle gold or warm accent colors
- Clean information hierarchy
- Elegant transitions
- Responsive layouts
- High-quality visual presentation

Avoid a generic administrative dashboard appearance.

### Required screens to design

**Screen 1 — Main Menu**
- CineDraft branding
- Start New Production
- How to Play
- Future game-mode selection

**Screen 2 — Genre Selection**
- Available genres
- Genre descriptions
- Genre-based visual identity

**Screen 3 — Production Budget**
- Indie Production — $10M
- Studio Picture — $50M
- Big-Budget Blockbuster — $200M
- Brief explanation of budget constraints
- Available hiring budget

**Screen 4 — Draft Room**
- Current drafting position
- Three candidate cards
- Candidate portraits
- Hiring fees
- Top five notable films
- Genre compatibility
- Talent ratings
- Remaining hiring budget
- Drafted roster
- Reroll control
- Selection confirmation

**Screen 5 — Candidate Details**
- Full filmography
- Career attributes
- Role-specific credits
- Genre strengths
- Collaboration evidence

**Screen 6 — Production Review**
- Complete eight-person roster
- Individual salaries
- Total talent spending
- Remaining production allocation
- Team chemistry indicators
- Recasting option
- Finalize Production button

**Screen 7 — Movie Premiere**
- Fictional movie identity
- Cast and crew presentation
- Simulation introduction
- Results reveal

**Screen 8 — Results**
- Critics' score
- Audience score
- Worldwide box office
- Profitability
- Final studio score
- Breakdown of contributing factors
- Potential improvements
- Replay option

Do not build the actual results simulator yet.

### UX considerations

Prioritize clarity and ease of use.

Players should immediately understand:

- Why a candidate is eligible
- What movies the candidate worked on
- Why the candidate costs a certain amount in the game
- How selecting them affects the remaining budget
- How well they match the selected genre
- Whether they have worked with previously drafted people

Clearly distinguish real filmography information from fictional ratings, salaries, and simulated outcomes.

## 13. GAME STATES AND EDGE CASES

Define the formal game state machine.

Include states such as:

- Main Menu
- Genre Selected
- Budget Selected
- Draft Started
- Draft In Progress
- Awaiting Pick
- Draft Completed
- Recast Available
- Production Finalized
- Simulation Running
- Results Available

Document valid transitions between states.

Create an edge-case matrix covering:

- Duplicate candidates
- A person with multiple professional roles
- Insufficient remaining budget
- No affordable candidates
- Missing portrait
- Missing or incomplete filmography
- Candidate with fewer than five movies
- Candidate with multiple credits on one film
- Unavailable role-specific credits
- Reroll after an offer is exhausted
- Recasting a candidate
- Canceling a recast
- Browser refresh
- Repeated selection submissions
- An incomplete roster
- Identical random seeds

Define the intended handling for each case.

## 14. DATA AND REPRODUCIBILITY REQUIREMENTS

Plan for future integration with TMDB.

Movie and talent data should eventually include:

- Stable TMDB person ID
- Stable TMDB movie ID
- Name and title
- Movie release date
- Genre information
- Movie ratings and vote counts
- Popularity indicators
- Cast credits
- Crew department and job credits
- Portrait and poster references
- Import timestamps

Design for versioned talent ratings and scoring formulas.

Every completed game should eventually store:

- Genre
- Budget category
- Selected roster
- Individual fictional hiring fees
- Talent attributes used
- Dataset version
- Scoring version
- Random seed
- Simulation output

This ensures that completed games and casting comparisons can be reproduced.

Include the appropriate TMDB attribution and plan to comply with its applicable terms.

## 15. PHASE 1 DELIVERABLES

Create the following Markdown documents within the repository:

**docs/phase-01/game-rulebook.md**
- Complete gameplay flow
- Drafting rules
- Budget tiers
- Role eligibility
- Rerolls
- Recasting
- Winning conditions

**docs/phase-01/scoring-design.md**
- Talent rating concepts
- Genre fit
- Collaboration bonuses
- Budget efficiency
- Proposed scoring weights
- Simulated outcome definitions
- Balancing assumptions

**docs/phase-01/talent-data-spec.md**
- Required person and movie information
- Role-based credit eligibility
- Top-five filmography ranking methodology
- Missing-data handling
- Fictional fee rules
- Data provenance

**docs/phase-01/ui-ux-blueprint.md**
- Screen-by-screen layouts
- Candidate-card requirements
- Top-five film display
- Budget selection screen
- Draft room
- Responsive behavior
- Visual style

**docs/phase-01/game-state-and-edge-cases.md**
- Game state machine
- Valid transitions
- Edge-case matrix
- Budget validation scenarios
- Reroll and recast behavior

**docs/phase-01/phase-01-summary.md**
- Summary of completed design work
- Design decisions made
- Explicit assumptions
- Open design questions
- Known risks
- Requirements for Phase 2

Use Mermaid diagrams where useful.

Update the main README with a brief project overview and links to these documents.

## 16. IMPORTANT DEVELOPMENT INSTRUCTIONS

1. Inspect the existing codebase before proposing changes.
2. Preserve the existing working prototype.
3. Do not remove existing functionality unnecessarily.
4. Focus on design specifications rather than premature implementation.
5. Do not build the complete frontend or backend during Phase 1.
6. Do not introduce unnecessary dependencies.
7. Use realistic movie industry terminology.
8. Store monetary values in integer USD.
9. Make fictional salary assumptions explicit.
10. Never invent actual filmography credits.
11. Keep the three-candidate system as the primary game mode.
12. Make the top-five notable works an essential, visible candidate-card feature.
13. Design all systems to support later FastAPI, React, PostgreSQL, and TMDB integration.
14. Make every proposed rule specific enough to translate into automated tests.
15. Prefer concrete default decisions over leaving essential mechanics undefined.

## 17. COMPLETION CRITERIA

Phase 1 is complete when:

- The complete gameplay loop is documented.
- All eight professional positions are defined.
- All three budget categories have clear rules.
- The fictional hiring fee system is specified.
- The top-five filmography feature is fully designed.
- Three-candidate drafting and affordability rules are defined.
- Reroll and recasting behavior is specified.
- Initial scoring concepts are documented.
- All required screens have detailed blueprints.
- Game state transitions and edge cases are documented.
- Future data requirements are defined.
- Phase 2 implementation requirements are clear.
- Existing prototype behavior has been inspected and preserved.

## FINAL OUTPUT

After completing Phase 1, provide:

1. A summary of the repository inspection.
2. All created or updated files.
3. Important gameplay and architecture decisions.
4. The finalized three-tier budget model.
5. An explanation of how top-five works will be chosen and displayed.
6. Open issues or assumptions.
7. A Phase 1 completion checklist.
8. A concise handoff for Phase 2.

Do not automatically proceed to Phase 2.

**Begin by inspecting the existing CineDraft repository, then create the Phase 1 design documentation.**
