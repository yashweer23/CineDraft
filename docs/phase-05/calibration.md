# Synthetic calibration walkthrough

All people, movies and source observations in this example are invented fixtures. They illustrate the formulas; they are not real film credits, TMDB ratings or salaries. Run from backend with its dependencies installed:

```powershell
python -m scripts.talent_example
```

This command needs no database, token or network. Its exact output is bundled in `data/phase5-calibration.json`. It does not publish data or add these records to your real catalog. The separate `seed_demo` command is the earlier one-film PostgreSQL exercise.

The example has seven synthetic films, three people and four role profiles. Two actors have identical film evidence and different visibility observations. A third person has both directing and writing credits. Writer and Screenplay jobs on one film count only once.

| Synthetic profile | Role | Talent strength | Fictional fee USD |
|---|---|---:|---:|
| Synthetic Visible Actor | Actor | 70.731227 | 18,725,000 |
| Synthetic Less-Visible Actor | Actor | 70.731227 | 5,875,000 |
| Synthetic Director-Writer | Director | 68.707550 | 3,175,000 |
| Synthetic Director-Writer | Writer | 64.843042 | 675,000 |

The actors' strength is identical because popularity is excluded from that formula. Their fees differ because pricing explicitly includes the role popularity percentile. The director-writer keeps one person identity and different role evidence/fees.

The unweighted observed catalog prior is approximately 7.483333. The two-vote 9.9 film shrinks strongly toward that prior. The 8.0 film with 5,000 votes ranks first for the actors; the raw two-vote outlier does not displace better-supported works. The actors' top five are Synthetic Supported Drama, Synthetic Crime Film, Synthetic Adventure Film, Synthetic Older Comedy and Synthetic Romance Film. The director has only three matching works and the writer only one; lists remain shorter than five.

The example's unrated film retains unavailable audience reception. Internal prior use does not make a source rating appear. No poster paths are invented. A synthetic source tag appears on every UI profile built from fixture records.

These prices also expose a balance issue worth studying: even the less-visible actor costs $5.875M, nearly the entire $6.5M Indie talent envelope. The example has only two actors and lacks composers/cinematographers, so it is not a playable pool. The delivered curve follows the Phase 1 design; inspect real catalog distributions before calibrating a later version. No secret per-tier discount is introduced.

Try changing a fixture's votes, popularity or role in a copy of `scripts/talent_example.py`, rerun it, and explain the affected outputs. Changes to this isolated example do not edit a published database version. Changing production formulas requires a new formula version and build label.
