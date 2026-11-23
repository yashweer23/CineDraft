# Phase 1 — UI/UX blueprint

Specification only. Keep the original prototype playable while implementing the future React interface incrementally. The design should feel like a studio call sheet and film festival program rather than an administrative dashboard.

## Visual foundation

Use charcoal backgrounds, warm ivory text and restrained gold accents. Suggested tokens: canvas `#141713`, surface `#20251E`, primary text `#F1F0E8`, secondary text `#BCC4B4`, accent `#DDA85C`, danger `#F29283`. These are starting values; verify text/background contrast for actual combinations. Aim for WCAG AA contrast, clear keyboard focus and minimum 44px touch targets. Do not communicate affordability only through red or green.

Use a serif display face for film titles and a readable sans serif for figures and controls, with local/system fallbacks. The current prototype's CSS is a useful reference, not a requirement to reuse every selector. Keep font downloads optional. Respect reduced motion and preserve information when animation is disabled. Avoid autoplay sound.

## Screen specifications

| Screen | Primary content | Main action and behavior |
|---|---|---|
| 1. Main menu | CineDraft name, “Draft your next film,” Continue production if saved, Start new production, How to play, local/account status | Continue restores exact offers; a new draft confirms before discarding an unfinished one. Future modes appear only as clearly unavailable previews, without dead buttons. |
| 2. Genre selection | Ten labeled genre tiles with one-line descriptions; chosen state uses text/icon and color | Continue enabled after choosing one genre; back preserves choice. |
| 3. Production budget | Three cards with $10M/$50M/$200M, 35% reserve and 65% hiring allocation shown as exact subtotals | “Start draft” locks genre and tier. Explain fictional fees and separate later marketing cost. Optional title, up to 60 characters. |
| 4. Draft room | Current slot and round, three candidate cards, remaining hiring money, committed talent spend, production reserve, roster progress, two rerolls | Select opens a confirmation summary naming person, fee, post-pick balance and minimum needed for remaining slots. Commit only once, then advance and focus the new round heading. |
| 5. Candidate details | Full role-filtered filmography, credited jobs, attribute calculations, data coverage, shared-credit evidence | Drawer on desktop, full-screen sheet on mobile; escape/back closes and restores focus. No loss of draft state. |
| 6. Production review | Eight named slots and fees, reserve, talent spend, unused envelope, actual production commitment, genre/chemistry summaries | Choose one slot for optional recast; preview old/new fee and net difference; confirm or cancel. “Finalize production” locks the roster after a clear final confirmation. |
| 7. Movie premiere | Fictional title, genre, complete credits, simulation status | Optional short reveal; “Skip animation” shows the same saved result. A failed simulation offers retry without allowing roster edits. |
| 8. Results | Studio score and contributions; critics, audience, gross, production cost, marketing, studio receipts, profit and return; weekly curve; evidence links | “Draft another film,” open saved films, inspect explanations. Future “What if?” control appears only when implemented. |

Genre descriptions: Action—physical stakes; Adventure—journeys and discovery; Comedy—humor and timing; Crime—criminal worlds; Drama—character and conflict; Horror—fear and dread; Mystery—clues and investigation; Romance—relationships; Science Fiction—speculative science; Thriller—suspense and tension. These explain the game labels, not rigid artistic boundaries.

## Candidate card — mandatory visible hierarchy

1. Portrait or initials; name and drafted professional role.
2. Hiring fee with “Fictional game fee” caption; overall game strength and selected-genre fit, each /100.
3. Up to three genre specialty chips; concise career coverage such as “8 verified films in our catalog.”
4. **Notable films**: up to five visible rows. Each row includes a small poster placeholder/image, wrapping title, year if known, matching credited job and TMDB audience rating if available. Avoid ellipsis as the only way to access a full title.
5. Shared-credit evidence with current roster where found, or a neutral “No shared credits found in this dataset.”
6. “View full filmography” and “Select [role]” controls.

Film titles are visible before choosing; never put all five inside a hover popup, collapsed accordion, carousel-only view or separate page. A long name or title wraps without overlapping price or buttons. A person with fewer than five verified films gets fewer rows plus a coverage note. Missing photos use initials; missing posters use a generic film icon, not unrelated stock artwork. If the future data service fails, preserve the draft and show retry; do not substitute fabricated facts.

The selection button shows an understandable disabled reason, e.g. “Would leave $250K; remaining roles need at least $400K.” Link details to the minimum feasible completion explanation without implying the witness team is reserved for the player. Keyboard users can read this reason via adjacent text, even if the disabled control cannot receive focus.

## Draft-room layout

Wide screens (roughly 1200px+): compact roster sidebar and three equal-width candidate cards. Avoid making the sidebar so wide that five titles become unreadable. The hiring-budget summary stays visible but never covers content. Cards should grow vertically with titles rather than clip them.

Medium screens (768–1199px): roster becomes a summary above the draft; use one or two card columns according to actual available width. Three equal cards are not worth unreadable text. Narrow screens (<768px): single card column, all five film rows shown on each, roster in a clearly labeled expandable panel. Candidate film rows themselves stay expanded. Keep enough bottom padding for any fixed controls and device safe area.

Use appropriate heading hierarchy and landmarks. Announce completed picks, remaining allowance and errors in a polite live region. Preserve focus after reroll, selection and modal close. Do not reorder selected cards unexpectedly while a keyboard user navigates. Prevent repeated submission while the server commits, but show loading and retry text if it takes time.

## Money language

Use “Hiring budget remaining” for the spendable balance and “Non-talent production reserve” for the locked allocation. “Total production authorization” is the selected $10M/$50M/$200M tier. “Production committed” means reserve plus hired fees. Do not label the whole tier as cash available to draft.

On recast, show current person and fee, proposed person and fee, net cost/refund and resulting balance. Previewing never changes the visible committed roster; confirm changes it atomically. If canceled, return focus to that slot and restore the original totals exactly.

Results display a financial bridge in order: worldwide gross → studio receipts → production cost → separate marketing → profit. Use “Simulated” in the section label. A revenue figure and a loss can coexist without contradiction because theaters retain part of gross.

## Interaction acceptance checks

- At 390px width, all five film titles per card are readable with vertical scrolling and no horizontal page overflow.
- At 1280px width, three candidates fit with readable works and costs.
- At 200% zoom, no essential budget, title or control disappears.
- Tab, Enter, Space and Escape cover selection, details, confirmation and cancellation.
- Refresh restores the same roster, balance, reroll count and offer; a draft is never silently restarted.
- Images failing to load preserve layout and useful alternative text.
- Busy controls cannot submit twice; server errors keep the previous legal state visible.
- Source metadata and fictional game attributes are labeled distinctly.
- Reduced-motion preference removes nonessential transitions and premiere animation.

These are future acceptance checks. The included verification report records only checks actually run against the current prototype.
