# ECDAT dashboard design tokens

The source of truth for design tokens is `src/index.css` and `tailwind.config.js` (C-07). Use existing variables and utilities instead of component-local hardcoded colors. This feature preserves existing component styles and applies shared motion presets to DashboardPage metric-card reveals and risk badges through the coordinated presentation surface.

## Color Tokens

| Token | Value | Meaning |
| --- | --- | --- |
| `--void` | `#FFF6F7` | Main light background |
| `--surface` | `#FFFFFF` | Cards and elevated surfaces |
| `--surface-r` | `#F8D8DD` | Raised surface |
| `--surface-h` | `#FBE8EA` | Hover surface |
| `--border` | `#F8D8DD` | Dividers |
| `--border-s` | `#FF788D` | Selected border |
| `--cyan` | `#FF788D` | Brand accent and actions |
| `--cyan-10` | `rgba(255,120,141,.12)` | Light accent tint |
| `--cyan-20` | `rgba(255,120,141,.25)` | Strong accent tint |
| `--purple` | `#1E532B` | Quantum risk emphasis (legacy name) |
| `--purple-10` | `rgba(30,83,43,.12)` | Quantum tint |
| `--green` | `#1E532B` | Safe/compliant |
| `--green-10` | `rgba(30,83,43,.12)` | Safe tint |
| `--critical` | `#E53935` | Critical risk |
| `--high` | `#E65100` | High risk |
| `--medium` | `#D97706` | Medium risk |
| `--low` | `#1E532B` | Low risk |
| `--t1` | `#0F172A` | Primary text |
| `--t2` | `#334155` | Body text |
| `--t3` | `#475569` | Captions and labels |
| `--t4` | `#64748B` | Tertiary metadata |

Tailwind maps these variables to `bg-*`, `text-*`, and `border-*` utilities. Risk badges use `.badge-critical`, `.badge-high`, `.badge-medium`, and `.badge-low`. The spec refers to 24 tokens in §12, but §7.1/§9 enumerate 21 and existing `:root` contains those same 21; no new variables were named or authorized.

## Typography Scale

Use `.heading-h1` through `.heading-h4` for 36/30/24/20px headings; `.text-body-lg`, `.text-body`, and `.text-body-sm` for 16/14/13px body copy; `.text-caption` and `.text-overline` for uppercase labels; `.text-mono` and `.text-mono-sm` for technical values. `.text-numeric` enables tabular figures. Body copy uses Inter and the technical scale uses JetBrains Mono with system fallbacks.

## Framer-Motion Patterns

Import reusable presets from `src/motion.constants.js` and use framer-motion for dashboard motion. For a viewport reveal: `<motion.div variants={fadeSlideUp} initial="hidden" whileInView="visible" viewport={viewportConfig}>…</motion.div>`. For a list, use `staggerContainer` on its parent and `staggerItem` on children. GSAP and ScrollTrigger remain exclusive to `src/pages/LandingPage/index.jsx`.

Keep animation to opacity and transforms, avoid layout properties and persistent `will-change`, and limit simultaneous motion. Framer Motion's reduced-motion configuration should be exercised in browser verification; do not assume a user's setting has been checked without testing.

## Component Styling

Use existing `.card`, `.card-raised`, `.badge-*`, and `.btn-primary` styles. Keep component layout and colors with their owning feature; request new shared colors through the FE token owner.

## Accessibility

Keep text contrast at least WCAG AA (4.5:1 for normal text). Color is not the only risk indicator; retain text labels. Preserve visible `:focus-visible` rings. Verify reduced-motion behavior in a browser with the OS/browser preference enabled. Contrast values are palette-dependent and must be measured for each foreground/background pairing before claiming compliance.

## Dark Theme Roadmap (C-24 Pending)

C-24 remains unresolved. This release renders only the light theme and adds no dark selectors or toggle. A future approved design may define overrides using `:root[data-theme="dark"]` in `src/index.css`, then validate contrast before exposing the theme. No dark theme is implemented by this feature.

## Motion governance

Do not import GSAP outside LandingPage. Prefer GPU-friendly opacity and transforms, use stagger for lists, avoid layout animation and `will-change` spam. A browser FPS check is required for visual acceptance; build success alone does not establish performance.


