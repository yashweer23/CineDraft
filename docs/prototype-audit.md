# Existing prototype inspection

Inspection date: 20 October 2026. Source: `cinedraft-deploy.tar.gz` already present in this workspace. This was a static deployment archive, not a full version-controlled React/FastAPI project. It contained four editable application assets and deployment configuration. Only the application assets were exported into the local project.

## Current implementation

| File | What it contains |
|---|---|
| `index.html` | Header, main render target, modal, footer, local CSS and JS script tags |
| `styles.css` | Responsive dark/green/warm-accent interface, decorative poster, cards, results; optional Google Fonts import |
| `app.js` | DOM templates and handlers, brief state, localStorage save/restore normalization, pick/reroll controls, timed premiere, results and 30-film archive |
| `engine.js` | IIFE exported as `window.Cine` and CommonJS, six genres, eight slots, 90 curated records, seeded PRNG, cost/reserve checks and simplified release model |

All four files were preserved byte-for-byte. The new server, tests and documentation sit alongside them. No deployment URL or hosting configuration is needed to run locally.

## Behavior found in source

- Budgets are `90`, `140`, `200`, displayed as millions; the engine always reserves `25` for combined production and marketing.
- Eight slots are director, four actors, screenwriter, cinematographer and composer.
- Talent rows contain role-specific IDs, name, invented cost, craft, draw and genre affinities. There are no real person IDs, verified film credits, poster records or portrait assets.
- Offers contain three candidates and attempt to include at least one legal continuation. Reserved future costs use greedy cheapest-per-role choices; that works with the current single-role records but is not an exact multi-role assignment solver.
- The interface calls offer rerolls “recasts” and allows three. There is no completed-roster replacement feature.
- Chemistry is a function of shared genre affinity, not an actual collaboration graph.
- Results use seeded randomness and a fixed weekly revenue split of 48%, 28%, 15%, 9%. Studio receipts are simplified to 50% of gross less combined committed costs.
- Browser refresh restores a normalized draft and previous offer when valid. There is no backend identity or mutation authorization.
- Film titles and names are escaped in templates. Persistence failures show a toast; there is no account sync or database.

## Migration gaps and known limitations

1. **Money representation:** converting the model requires integer USD throughout, replacing fixed production/marketing reserve with configurable production-only reserve, and changing every display/validation path together. Merely relabeling $90M as $10M would break feasibility.
2. **Identity:** IDs such as `director-0` are array-position-based and unsuitable for durable multi-role data. One composer record combines two people and must be replaced by separate verified identities later.
3. **Film data:** top-five lists cannot be responsibly filled from names alone. Add role-verified credits and source metadata before showing them as facts.
4. **Genre handling:** the existing compact text row format splits on spaces. It can produce an undefined fit value if a matching genre appears after the third position. The current rows have at most three tags; future data must replace this positional scheme with robust explicit features.
5. **Authority:** engine helpers assume the UI calls them sensibly. `release()` checks roster length but is not a full authoritative validator. Do not expose this engine directly as a trusted server API or use its local scores for competitive rankings.
6. **Determinism:** current results repeat for the same state and seed, but editing global talent rows can change a restored game's inputs. Future immutable snapshots must prevent that drift.
7. **History identity:** current history deduplicates by seed and title; future persistence needs actual draft IDs and database uniqueness.
8. **Assets:** the visual identity currently uses initials and CSS art; the optional font import can fail offline without preventing gameplay.

These are documented migration constraints, not claimed fixed features. Keep this prototype as a reference while the new architecture is introduced phase by phase. The local server added in this pack serves files only; it is not the planned FastAPI game backend.

## Useful elements to preserve

Keep the concise brief → draft → review → premiere loop, visible roster progress, disabled overspend selections with explanations, seeded outcomes, fictional-rating labels, browser recovery and clear result contributions. Reuse the visual tone where helpful while making the required notable works readable. Keep a separate legacy save key when introducing the new data format; do not attempt to reinterpret million-valued saves as integer dollars.
