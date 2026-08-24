# Middle Platform Design Baseline V1.0

## 1. Baseline Version

`MIDDLE_PLATFORM_DESIGN_BASELINE=1.0`

This baseline freezes the Product Owner approved Middle Platform homepage design for future implementation and review work. It is a design baseline, not a product redesign.

## 2. Approved Assets

- Approved HTML: `docs/ui-reference/homepage-approved.html`
- Approved screenshot: `docs/ui-reference/homepage-approved.png`
- Baseline version file: `docs/ui-reference/BASELINE_VERSION`

## 3. Visual Source of Truth

`APPROVED HTML + APPROVED SCREENSHOT = MIDDLE PLATFORM VISUAL SOURCE OF TRUTH`

The HTML is the source of truth for page structure, layout hierarchy, spacing, component order, and baseline dimensions. The screenshot is the source of truth for final visual density, tone, contrast, and texture.

## 4. Layout Rules

The approved homepage structure is locked:

1. Light Sidebar
2. Topbar
3. Middle Platform global homepage header
4. Date and primary action area
5. Global filter bar
6. Brand Workspace selector
7. Current brand banner
8. KPI cards
9. P1-P4 classified entry cards
10. Connected projects
11. Development feedback summary
12. Quick navigation
13. Footer

Do not swap the KPI and P1-P4 order, remove the brand banner, turn the brand selector into a capability selector, add a second workspace area, remove the feedback table, redesign the sidebar, or introduce broad color changes without Product Owner approval.

## 5. Color Rules

The formal visual language is `Premium Monochrome Enterprise SaaS`.

The interface is black, white, gray, low saturation, calm, clean, airy, structured, minimal, and professional. The approved page uses a light background, white surfaces, graphite text, neutral gray borders, and restrained accents.

Implementation color roles are mapped in `design-system/tokens.css`. Shared implementation tokens must be black, white, graphite, charcoal, neutral gray, low saturation accent, and muted status first. Accent colors may be used only for selected states, hover accents, status, small icons, charts, brand accents, and small interactive highlights. Accent colors must not become large backgrounds, global primary surfaces, or large banner fills.

High-saturation colors that exist inside `docs/ui-reference/homepage-approved.html` are `REFERENCE_ONLY / LEGACY_REFERENCE_COLOR` from the Product Owner approved source asset. They must not be promoted into future React global design tokens.

Forbidden directions:

- large saturated blue surfaces
- large green surfaces
- high saturation purple
- rainbow gradients
- heavy shadows
- glow effects
- traditional OA styling
- heavy borders
- dark navy sidebar

## 6. Typography

Use system UI fonts consistent with the approved HTML:

`-apple-system`, `BlinkMacSystemFont`, `Segoe UI`, `PingFang SC`, `Hiragino Sans GB`, `Microsoft YaHei`, `sans-serif`.

Baseline text scale:

- Body: 14px
- Topbar and controls: 13px
- Captions: 11-12px
- Page title: 22px / 600
- Section title: 14-16px / 500-600

Avoid all-bold interfaces. Headings may use 600 weight; body and metadata should remain 400-500.

## 7. Spacing

Spacing follows the approved HTML:

- Topbar height: 56px
- Sidebar width: 200px
- Main content padding: 20-24px
- Section gap: 16-20px
- Card padding: 16-20px
- Control padding: 6-14px
- Component gaps: 4px, 6px, 8px, 10px, 12px, 16px

## 8. Radius

Approved radius scale:

- Small controls: 6px
- Brand logo and small media: 8px
- Cards and panels: 8-10px
- Toggle: 10px / pill
- Avatar and badge dots: circular

## 9. Shadow

Shadows must stay subtle:

- Small shadow: `0 1px 3px rgba(0,0,0,.08)`
- Dropdown shadow: `0 8px 24px rgba(0,0,0,.12)`
- Medium card shadow: `0 4px 16px rgba(0,0,0,.08)`

No glow, dramatic elevation, or high-contrast shadow systems.

## 10. Accent Color Rules

Allowed accent directions:

- Dusty Blue
- Slate Blue
- Sage
- Muted Teal
- Warm Sand
- Muted Amber
- Dusty Rose
- Lavender Gray

The current approved HTML includes blue selected states, green success, orange pending, and red risk/status. These are status and small interactive accents, not global theme surfaces.

## 11. Motion Rules

Motion tokens are defined in `design-system/motion.ts`.

Allowed motion:

- subtle fade
- small translate
- card micro lift
- dropdown fade or slide
- number transition
- restrained chart animation

Forbidden motion:

- bounce
- glow
- particles
- large scale
- flash
- complex 3D
- long transition
- blocking animation

All future implementation must support `prefers-reduced-motion`.

## 12. Component Governance

Reuse shared baseline components before creating new components. The governed component set is documented in `docs/UI_DESIGN_SYSTEM.md`.

Forbidden one-off component names include brand- or iteration-specific variants such as `AntaButton`, `EccoButton`, `NewBlueCardV2`, `WorkspaceCardFinal`, and `SpecialDashboardCard`.

## 13. Page Fidelity Rules

Future implementations must preserve:

- sidebar type and placement
- topbar type and placement
- brand selector semantics
- current brand banner
- KPI placement
- P1-P4 placement
- connected projects section
- feedback summary table
- quick navigation section
- footer
- premium monochrome visual language

Business semantics are separate from visual fidelity. P1-P4 official product contract remains:

- P1 = Data Efficiency
- P2 = Content Efficiency
- P3 = Configuration Efficiency
- P4 = Review

Approved HTML may contain demo text, but future product implementation must use the Product Contract / Registry as the business source of truth.

## 14. Visual Regression Rules

Current status:

- `STRUCTURAL_VISUAL_REGRESSION = READY`
- `VISUAL_REGRESSION = PARTIAL`
- `RUNTIME_VISUAL_BASELINE = PENDING_SCREENSHOT_COMPARISON`

Visual reference and runtime regression are separate:

- Product design reference: `docs/ui-reference/homepage-approved.png`
- Runtime screenshot: `tests/visual/runtime/homepage.png`

Current structural visual regression foundation is stored in `tests/visual/`. `tests/visual/runtime/homepage.png` is generated by Playwright from the real runtime at `http://127.0.0.1:8785/` as visual evidence; pixel screenshot comparison remains pending.

Allowed differences:

- real data length
- browser font rendering
- responsive wrapping
- 1-4px reasonable engineering variance

Disallowed differences:

- module order changes
- sidebar type changes
- brand selector semantic changes
- banner position changes
- P1-P4 position changes
- visual language changes
- broad color changes

## 15. Intentional Design Change Procedure

Do not directly overwrite Baseline V1.0.

Required process:

1. Proposed change
2. Screenshot or demo
3. Product Owner approval
4. Baseline version increment, such as V1.0 to V1.1
5. Update approved assets
6. Update design tokens
7. Update visual regression baseline
8. PR and review

Developer preference is not sufficient approval for baseline replacement.
