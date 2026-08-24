# Middle Platform UI Design System

## Visual Language

The official Middle Platform visual language is `Premium Monochrome Enterprise SaaS`.

Use black, white, and gray first. Use only low-saturation accents for selected states, hover accents, status, small icons, charts, brand accents, and small interactive highlights.

The approved design baseline is:

- `docs/ui-reference/homepage-approved.html`
- `docs/ui-reference/homepage-approved.png`
- `docs/DESIGN_BASELINE.md`

These assets are the visual source of truth for future Middle Platform UI work.

## Design Tokens

Use shared tokens from `design-system/tokens.css`. Future React migration should move or mirror these tokens into `frontend/src/design-system/tokens.css`.

Implementation tokens must remain black, white, graphite, charcoal, neutral gray, low saturation accent, and muted status first. High-saturation colors preserved inside the approved HTML are `REFERENCE_ONLY / LEGACY_REFERENCE_COLOR`; they are not future React global design tokens.

Do not introduce a separate blue-dominant theme, dark navy sidebar theme, or high-saturation primary color system.

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

Light Sidebar -> Topbar -> Middle Platform global homepage -> date and primary action -> global filters -> Brand Workspace selector -> current brand banner -> KPI -> P1-P4 -> connected projects -> development feedback summary -> quick navigation -> footer.

Future AI or developer changes must not:

- reorder KPI and P1-P4
- delete the brand banner
- turn the brand selector into a capability selector
- add a second workspace area on the right
- delete the feedback table
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

- `VISUAL_REGRESSION = PARTIAL`
- `RUNTIME_VISUAL_BASELINE = PENDING_REACT_MIGRATION`
- `docs/ui-reference/homepage-approved.png` is the Product Design Source.
- `tests/visual/baseline/homepage.png` is `SEEDED REFERENCE ONLY`.

The seeded screenshot is not an operational Playwright regression gate. After React/Vite runtime migration, future key UI changes must compare Playwright runtime screenshots from `http://127.0.0.1:8785/` with confirmed runtime baselines. If an unapproved major visual change exists:

- `VISUAL_REGRESSION_GATE = FAIL`
- `MERGE_GATE = BLOCKED`

Intentional major visual changes require Product Owner approval and a baseline version increment.
