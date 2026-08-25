# Middle Platform UI Design System

## Visual Language

The official Middle Platform V3 visual language is `Premium Neutral Enterprise SaaS + Muted Accent`.

Use black, white, and gray as the foundation, then layer warm neutral surfaces, graphite structure, muted accent identity, and restrained semantic status. The interface should feel premium, quiet, refined, modern, editorial, professional, and high-end enterprise SaaS.

The approved design baseline is:

- `docs/ui-reference/homepage-approved.html`
- `docs/ui-reference/homepage-approved.png`
- `docs/DESIGN_BASELINE.md`

These assets are the visual source of truth for future Middle Platform UI work.

## Design Tokens

Use shared tokens from `design-system/tokens.css`. Future React migration should move or mirror these tokens into `frontend/src/design-system/tokens.css`.

Implementation tokens must remain neutral foundation, graphite, charcoal, neutral gray, low-saturation accent, and muted status first. High-saturation colors preserved inside the approved HTML are `REFERENCE_ONLY / LEGACY_REFERENCE_COLOR`; they are not future React global design tokens.

Do not introduce a separate blue-dominant theme, dark navy sidebar theme, high-saturation primary color system, or nearly colorless wireframe treatment.

## Motion Tokens

Use shared motion constants from `design-system/motion.ts`. Future React migration should move or mirror them into `frontend/src/design-system/motion.ts`.

Motion must be subtle, non-blocking, and compatible with `prefers-reduced-motion`.

## Component Baseline

Reuse these shared component concepts before introducing new UI:

- PlatformLayout
- Sidebar
- Topbar
- PageHeader
- GlobalFilterBar
- BrandWorkspaceSelector
- BrandBanner
- StatCard
- CategoryCard
- ProjectCard
- FeedbackTable
- QuickNavigation
- Button
- Select
- Dropdown
- Badge
- Card
- Table
- Dialog
- Drawer
- Toast
- EmptyState
- LoadingState
- ErrorState

## Component Governance

Rule: `REUSE FIRST`.

Do not create one-off UI systems or names such as:

- AntaButton
- EccoButton
- NewBlueCardV2
- WorkspaceCardFinal
- SpecialDashboardCard

If a component is genuinely missing, add it to the shared design system first and keep its API brand-neutral.

## Homepage Structure Contract

The approved homepage structure is locked:

Light Sidebar -> Topbar -> Middle Platform global homepage -> date and primary action -> global filters -> Brand Workspace selector -> current brand banner -> KPI -> P1-P4 -> connected projects -> development feedback summary module -> quick navigation -> footer.

Future AI or developer changes must not:

- reorder KPI and P1-P4
- delete the brand banner
- turn the brand selector into a capability selector
- add a second workspace area on the right
- delete the feedback module
- redesign the sidebar
- apply broad color changes

## Brand Selector Contract

The Brand Workspace selector can select only brands, for example:

- ANTA / Anta
- ECCO
- BSH / Bosch-Siemens

It must not contain capabilities or projects such as activity configuration, listing processing, SMS processing, or ECCO configuration.

## P1-P4 Business Semantics

Visual source of truth and business source of truth are separate.

Official business semantics:

- P1 = Data Efficiency
- P2 = Content Efficiency
- P3 = Configuration Efficiency
- P4 = Review

Future implementation must use the Product Contract / Registry for business semantics even when approved HTML includes demo wording.

## Visual Regression Gate

Current status:

- `STRUCTURAL_VISUAL_REGRESSION = READY`
- `VISUAL_REGRESSION = PARTIAL`
- `RUNTIME_VISUAL_BASELINE = PENDING_SCREENSHOT_COMPARISON`
- `docs/ui-reference/homepage-approved.png` is the Product Design Source.
- Playwright runtime screenshot evidence is stored under `tests/visual/runtime/` for global home, Workspace Entry states, and single-brand workspace pages.

Future key UI changes must compare Playwright runtime screenshots from `http://127.0.0.1:8785/` with confirmed runtime baselines before reporting a full visual regression gate as ready. If an unapproved major visual change exists:

- `VISUAL_REGRESSION_GATE = FAIL`
- `MERGE_GATE = BLOCKED`

Intentional major visual changes require Product Owner approval and a baseline version increment.
