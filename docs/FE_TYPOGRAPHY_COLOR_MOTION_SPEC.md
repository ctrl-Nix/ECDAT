# ECDAT Frontend Typography / Color / Motion Pass
## Implementation Specification (SIH 2026 PS 26164 · Spec Version 1.0)

---

## 1. Header

**Feature:** `FE` — Frontend Typography / Color / Motion Pass  
**Owner:** Frontend Lane (Karan / Satyam)  
**Spec Version:** 1.0 · Authored: 2026-09-20  

| Status | Detail |
|---|---|
| **Spec Status** | Complete; awaiting design-system review |
| **Implementation Status** | Ready for implementation (Wave 3, post-DFS/ENR/AUD) |
| **Merge Order** | Wave 3 (after CONF, DFS, ENR, AUD complete in Wave 2) |
| **Reviewer Sign-Off** | Pending |

### Changelog

| Version | Date | Change | Rationale |
|---|---|---|---|
| 1.0 | 2026-09-20 | Initial specification | No prior Step 1 proposal provided; written from contract + codebase audit |

### Deviation Notes from Contract

- **C-24 (Theme Toggle Scope):** Dark theme and toggle implementation scope is **unresolved** per §7 of SYSTEM_INTERFACE_CONTRACT.md. This spec documents light theme as confirmed in-scope; dark theme is flagged as pre-answered ambiguity (§11). Implementation must await human resolution.
- **C-07 (Design Tokens Location):** Contract specifies design tokens belong **only** in `dashboard/src/index.css`, `tailwind.config.js`, and `dashboard/public/fonts/`. This spec enforces that constraint.
- **C-17 (GSAP Usage Restriction):** GSAP + ScrollTrigger are exclusive to `dashboard/src/pages/LandingPage/index.jsx` per contract. All other motion work uses framer-motion (already in `package.json`).

---

## 2. Goal & Context

The ECDAT dashboard ("Quiet Precision" design system) currently serves findings via a light-theme, pink-and-forest-green color palette with Tailwind CSS variables and minimal motion (Google CDN fonts, basic transitions). This feature consolidates the design system by: **(a)** migrating to self-hosted fonts to eliminate external CDN dependencies and support air-gapped deployment; **(b)** documenting and extending the color-token vocabulary to support consistent semantic risk tiers, UI states, and (conditionally) a dark theme; and **(c)** establishing framer-motion animation patterns for dashboard entry, state changes, and data-load feedback that reinforce "quiet precision" over theatricality. 

This work directly addresses **PS 26164 Requirement 5** (Recommendation & Reporting): judges expect a professionally polished, cohesive visual identity and rapid, non-distracting feedback when analysts interact with findings. The contract's Wave 3 placement ensures this lands after the core analytical features (DFS, CONF, ENR) are proven, preventing visual-system churn mid-sprint.

---

## 3. Scope

### In-Scope

- **Self-hosted fonts:** Migrate from `@import url('https://fonts.googleapis.com/...')` to local `dashboard/public/fonts/` directory with `@font-face` declarations in `dashboard/src/index.css`.
- **Comprehensive CSS color-variable system:** Define complete light-theme palette in `:root` covering status states, tiers, semantic warnings, interaction feedback, and text hierarchy. Document variable naming convention and usage per Tailwind theme extension in `tailwind.config.js`.
- **Framer-motion animation library:** Standardize motion patterns (fade-in on viewport entry, bounce on status change, shimmer on load, slide on navigation) across `dashboard/src/` components using consistent `variants`, `transition`, and `duration` vocabulary.
- **Typography scale:** Document font sizing, weight hierarchy, letter-spacing, and line-height standards for headings, body, captions, and data tables in `dashboard/src/index.css`.
- **Design token documentation:** Create `DESIGN_TOKENS.md` living in `dashboard/` with exhaustive variable reference, color-to-semantic-meaning mapping, motion curve documentation, and component application examples.
- **Motion governance:** Define "no GSAP outside LandingPage" enforcement, framer-motion-only patterns, and performance guidelines (e.g., no `will-change` spam, GPU-backed transforms only).

### Out-of-Scope

- **Dark theme implementation:** Deferred pending **C-24 resolution** (see §11 "Pre-Answered Ambiguities"). This spec provides CSS variable architecture *compatible* with dark-theme addition (`:root[data-theme="dark"]` pattern sketched in §11), but does not commit to rendering dark-mode components.
- **Component-specific styling overrides:** Tailwind utility classes and BEM-style `.component` selectors remain the responsibility of individual feature owners (DFS, TRI, CMP, etc.). This feature owns only the **foundational tokens** and **animation patterns**.
- **SVG / image optimization:** Icon strategy (Lucide React) is stable; this feature does not audit or replace icons.
- **Accessibility (a11y) audit:** WCAG compliance is enforced by existing CI linters; this feature documents motion-induced accessibility considerations (e.g., `prefers-reduced-motion`) but does not perform full a11y remediation.
- **Performance profiling:** This feature defines motion guidelines; performance measurement lives in QA.

---

## 4. Required Context Files

Implementer **must** read these files in order before opening a PR:

1. **`SYSTEM_INTERFACE_CONTRACT.md`** (§1.4, §6 Wave 3, §7 C-07, C-17, C-24, §5 Shared Resources)  
   Establishes file ownership, merge order, and flagged conflicts.

2. **`AGENT_RULES.md`**  
   Governs code review workflow and pre-implementation reading requirements.

3. **`dashboard/tailwind.config.js`**  
   Current theme extension pattern; must preserve existing `fontFamily.sans`, `fontFamily.mono`, and color-variable mapping to CSS custom properties.

4. **`dashboard/src/index.css`**  
   Current `:root` variable definitions (void, surface, cyan, purple, green, critical/high/medium/low tiers, text hierarchy t1–t4). Implementer extends, never replaces.

5. **`dashboard/package.json`**  
   Confirms `framer-motion@^11.18.2` and `gsap@^3.15.0` are already pinned. No version changes without explicit contract amendment.

6. **`dashboard/src/pages/LandingPage/index.jsx`**  
   Demonstrates GSAP + ScrollTrigger usage pattern; **establishes this as the ONLY permitted GSAP consumer**. All other components must use framer-motion.

7. **`dashboard/src/components/ProjectDemoWalkthrough.jsx`**  
   Demonstrates framer-motion patterns in use (`motion.div`, `AnimatePresence`, variants, transitions). Establishes vocabulary for this feature.

8. **`dashboard/index.html`** and **`dashboard/vite.config.js`**  
   Entry point and build configuration; verify no hardcoded CDN font references outside `dashboard/src/index.css`.

9. **`docs/DASHBOARD_IMPROVEMENT_REVIEW.md`**  
   Design audit context; provides rationale for "Quiet Precision" aesthetic and current light-theme choices.

---

## 5. File Ownership

### Files This Feature Creates or Modifies (SOLE Tier)

Per SYSTEM_INTERFACE_CONTRACT.md §1.4:

| Path | Ownership Tier | Action | Notes |
|---|---|---|---|
| `dashboard/src/index.css` | **SOLE** | Modify | Extend `:root` CSS variables; add `@font-face` declarations; preserve all existing class definitions (.card, .badge, .btn-primary, etc.) |
| `dashboard/tailwind.config.js` | **SOLE** | Modify | Extend theme.extend.colors and theme.extend.fontFamily; no structural changes to config file format |
| `dashboard/public/fonts/` | **SOLE** | Create | New directory; contains self-hosted font files (woff2, fallback formats). Create `fonts/README.md` documenting font inventory and licensing. |
| `dashboard/DESIGN_TOKENS.md` | **SOLE** | Create | New documentation; exhaustive token reference, usage patterns, component examples |
| `dashboard/src/motion.constants.js` | **SOLE** | Create | New module; centralized framer-motion animation curve definitions, preset variants, transition timing constants |

### Files This Feature Must NOT Touch (Do-Not-Modify List)

- ✋ **`dashboard/src/components/ConfidenceStamp.jsx`** — CONF feature's SOLE file
- ✋ **`dashboard/src/components/AgentStatusTable.jsx`**, **`AgentStatusCard.jsx`**, `dashboard/src/pages/AgentStatusPage/`, **`dashboard/src/hooks/useAgents.js`** — ASP feature's SOLE files
- ✋ **`dashboard/src/components/ComplianceReport.jsx`** — CMP feature's SOLE file
- ✋ **`dashboard/src/components/RiskTrendChart.jsx`**, **`RiskTierBreakdown.jsx`**, `dashboard/src/pages/TrendsPage/` — TRD feature's SOLE files
- ✋ **`dashboard/src/context/AuthContext.jsx`**, **`dashboard/src/pages/LoginPage/`** — RBAC feature's SOLE files
- ✋ **`dashboard/src/pages/LandingPage/index.jsx`** — Frontend lane's SOLE file for GSAP use; FE may not modify motion here
- ✋ **`dashboard/package.json`** — Dependencies are contract-pinned; no changes without cross-feature approval
- ✋ **`dashboard/src/App.jsx`** — Route registration belongs to frontend lane's shared responsibility; FE does not own routing
- ✋ **`dashboard/src/lib/api.js`** — COORDINATED ownership (frontend lane); FE does not modify

### COORDINATED Files (FE Assists But Does Not Own)

Per contract §1.4:

| Path | Tier | Primary Owner | FE's Role |
|---|---|---|---|
| `dashboard/src/components/FindingsTable.jsx` | COORDINATED | Frontend lane (Karan/Satyam) | May apply new color tokens to risk-tier badges or row-hover states; must not restructure table schema |
| `dashboard/src/pages/DashboardPage/index.jsx` | COORDINATED | Frontend lane | May apply new motion patterns to metric-card reveals; must not change data flow |
| `dashboard/src/lib/constants.js`, `mockData.js` | COORDINATED | Frontend lane | Read-only; does not modify |

---

## 6. Tech Stack & Pinned Versions

All versions pinned per contract ground-truth corrections (§0.1, §3.2 of SYSTEM_INTERFACE_CONTRACT.md):

| Dependency | Version | Source | Purpose |
|---|---|---|---|
| **React** | `^18.3.1` | `dashboard/package.json` | Component framework (no changes) |
| **Vite** | `^5.4.1` | `dashboard/package.json` | Build tool (no changes) |
| **Tailwind CSS** | `^3.4.19` | `dashboard/package.json` | Utility-first styling; used via Tailwind config theme extension |
| **framer-motion** | `^11.18.2` | `dashboard/package.json` | Animation library for all FE motion except LandingPage; already pinned |
| **gsap** | `^3.15.0` | `dashboard/package.json` | Animation library exclusive to LandingPage; already pinned; **FE must NOT import this elsewhere** |
| **Inter** (font) | v3+ (self-hosted) | New in `dashboard/public/fonts/` | Sans-serif; UI text, headings; migrated from CDN |
| **JetBrains Mono** (font) | v2.242+ (self-hosted) | New in `dashboard/public/fonts/` | Monospace; code blocks, terminal output; migrated from CDN |
| **PostCSS** | `^8.5.26` | `dashboard/package.json` | CSS transformation pipeline (no changes) |
| **Autoprefixer** | `^10.5.4` | `dashboard/package.json` | CSS vendor prefixing (no changes) |

### Rationale for No New Dependencies

- **No additional motion libraries:** framer-motion provides sufficient declarative animation API for dashboard UX.
- **No icon libraries:** Lucide React (`lucide-react@^0.428.0`) is stable; no typography or color work needed there.
- **No CSS-in-JS:** Tailwind + CSS variables provide dynamic theming without runtime overhead.
- **Fonts:** Migrated from Google Fonts CDN to self-hosted WOFF2 files to support air-gapped deployments (PRODUCT_DESCRIPTION.md §3).

---

## 7. Concrete Interface Definitions

### 7.1 CSS Variables (`:root` in `dashboard/src/index.css`)

#### Light Theme (Confirmed In-Scope)

```css
:root {
  color-scheme: light;

  /* ── Chromatic void token scale (Backgrounds & Surfaces) ────── */
  --void:         #FFF6F7;      /* Main light void background (Light pink) */
  --surface:      #FFFFFF;      /* Pure white for cards & elevated UI */
  --surface-r:    #F8D8DD;      /* Raised surface (hover state) */
  --surface-h:    #FBE8EA;      /* Hover state (lighter pink) */
  --border:       #F8D8DD;      /* Border & divider (light pink) */
  --border-s:     #FF788D;      /* Selected / active border (watermelon) */

  /* ── Brand Accent (Watermelon Pink) ──────────────────────── */
  --cyan:         #FF788D;      /* Primary CTA, interactive, live status */
  --cyan-10:      rgba(255, 120, 141, 0.12);  /* Tinted background overlay */
  --cyan-20:      rgba(255, 120, 141, 0.25);  /* Stronger tint for badges */

  /* ── Quantum-Risk Primary (Deep Forest Green) ─────────────── */
  --purple:       #1E532B;      /* Quantum-vulnerable emphasis, secondary accent */
  --purple-10:    rgba(30, 83, 43, 0.12);  /* Tinted background */

  /* ── Safe / Compliant (Dark Green, same as purple for legacy) */
  --green:        #1E532B;      /* Passing findings, secure algorithms */
  --green-10:     rgba(30, 83, 43, 0.12);  /* Tinted background */

  /* ── Risk Tier Semantics (Professional semantic palette) ──── */
  --critical:     #E53935;      /* Critical risk (red, classically broken) */
  --high:         #E65100;      /* High risk (orange, quantum-vulnerable) */
  --medium:       #D97706;      /* Medium risk (amber, requires attention) */
  --low:          #1E532B;      /* Low risk (green, compliant) */

  /* ── Text Hierarchy (Ultra-dark high-contrast on light bg) ── */
  --t1: #0F172A;  /* Slate-900 — Primary headings, main copy, high emphasis */
  --t2: #334155;  /* Slate-700 — Body text, secondary content */
  --t3: #475569;  /* Slate-600 — Subtext, captions, labels, muted */
  --t4: #64748B;  /* Slate-500 — Disabled text, tertiary metadata */
}
```

#### Dark Theme Skeleton (Out-of-Scope, Blocked by C-24)

Implementer **must not** render dark theme until C-24 is resolved. If dark theme is approved in future, use this pattern in `dashboard/src/index.css`:

```css
/* Dark theme — NOT IMPLEMENTED; awaits C-24 sign-off */
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    /* Dark palette TBD per C-24; reserved structure below */
    --void:         var(--dark-void, #0A1015);
    --surface:      var(--dark-surface, #151B23);
    /* ... additional dark mappings ... */
  }
}

:root[data-theme="dark"] {
  /* Explicit dark-mode toggle; same mappings as @media */
}
```

**Note:** C-24 resolution must include contrast validation (WCAG AAA for body text) before implementation.

---

### 7.2 Tailwind Theme Extension (`dashboard/tailwind.config.js`)

```javascript
export default {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'Segoe UI', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'Consolas', 'monospace'],
      },
      colors: {
        // All colors map to CSS variables; no hardcoded hex values in utilities
        void: 'var(--void)',
        surface: 'var(--surface)',
        'surface-r': 'var(--surface-r)',
        'surface-h': 'var(--surface-h)',
        border: 'var(--border)',
        'border-s': 'var(--border-s)',
        
        cyan: 'var(--cyan)',
        'cyan-10': 'var(--cyan-10)',
        'cyan-20': 'var(--cyan-20)',
        
        purple: 'var(--purple)',
        'purple-10': 'var(--purple-10)',
        
        green: 'var(--green)',
        'green-10': 'var(--green-10)',
        
        critical: 'var(--critical)',
        high: 'var(--high)',
        medium: 'var(--medium)',
        low: 'var(--low)',
        
        t1: 'var(--t1)',
        t2: 'var(--t2)',
        t3: 'var(--t3)',
        t4: 'var(--t4)',
      },
      // Optional: Add custom spacing, shadow, or animation scales here if needed
      // Do NOT add motion keyframes; see §7.4 for framer-motion variants instead
    },
  },
  plugins: [],
};
```

---

### 7.3 Font Face Declarations (`dashboard/src/index.css`)

```css
/* ── Self-Hosted Font Faces ────────────────────────────────────── */

/* Inter: Geometric sans-serif for UI text, headings, body copy */
@font-face {
  font-family: 'Inter';
  src: 
    url('/fonts/Inter-Regular.woff2') format('woff2'),
    url('/fonts/Inter-Regular.woff') format('woff');
  font-weight: 400;
  font-style: normal;
  font-display: swap;  /* Prevent invisible text during load */
}

@font-face {
  font-family: 'Inter';
  src: 
    url('/fonts/Inter-Medium.woff2') format('woff2'),
    url('/fonts/Inter-Medium.woff') format('woff');
  font-weight: 500;
  font-style: normal;
  font-display: swap;
}

@font-face {
  font-family: 'Inter';
  src: 
    url('/fonts/Inter-SemiBold.woff2') format('woff2'),
    url('/fonts/Inter-SemiBold.woff') format('woff');
  font-weight: 600;
  font-style: normal;
  font-display: swap;
}

@font-face {
  font-family: 'Inter';
  src: 
    url('/fonts/Inter-Bold.woff2') format('woff2'),
    url('/fonts/Inter-Bold.woff') format('woff');
  font-weight: 700;
  font-style: normal;
  font-display: swap;
}

/* JetBrains Mono: Monospace for code, terminal, technical copy */
@font-face {
  font-family: 'JetBrains Mono';
  src: 
    url('/fonts/JetBrainsMono-Regular.woff2') format('woff2'),
    url('/fonts/JetBrainsMono-Regular.woff') format('woff');
  font-weight: 400;
  font-style: normal;
  font-display: swap;
}

@font-face {
  font-family: 'JetBrains Mono';
  src: 
    url('/fonts/JetBrainsMono-Medium.woff2') format('woff2'),
    url('/fonts/JetBrainsMono-Medium.woff') format('woff');
  font-weight: 500;
  font-style: normal;
  font-display: swap;
}

@font-face {
  font-family: 'JetBrains Mono';
  src: 
    url('/fonts/JetBrainsMono-SemiBold.woff2') format('woff2'),
    url('/fonts/JetBrainsMono-SemiBold.woff') format('woff');
  font-weight: 600;
  font-style: normal;
  font-display: swap;
}
```

**File Location:** `dashboard/public/fonts/` directory.  
**Font Files to Acquire:**
- `Inter-Regular.woff2`, `Inter-Medium.woff2`, `Inter-SemiBold.woff2`, `Inter-Bold.woff2`
- `JetBrainsMono-Regular.woff2`, `JetBrainsMono-Medium.woff2`, `JetBrainsMono-SemiBold.woff2`

**Licensing:** Both Inter (Raskin/Colizzi) and JetBrains Mono are SIL Open Font License (OFL); unrestricted self-hosting permitted. Include `OFL.txt` license in `dashboard/public/fonts/`.

---

### 7.4 Framer-Motion Animation Patterns (`dashboard/src/motion.constants.js`)

**New file; centralized animation vocabulary.**

```javascript
/**
 * dashboard/src/motion.constants.js
 * Centralized framer-motion animation patterns for the ECDAT dashboard.
 * All motion work (except LandingPage GSAP) uses these preset variants and transitions.
 * 
 * RULE: Do not use GSAP outside LandingPage (enforced by §5 do-not-touch list).
 */

/* ── Easing Curves ─────────────────────────────────────────────── */
export const easing = {
  easeInOut: [0.4, 0, 0.2, 1],      // Snappy, professional
  easeOut: [0, 0, 0.2, 1],          // Entry/reveal
  easeIn: [0.4, 0, 1, 1],           // Exit/dismiss
  bounce: 'circOut',                // Spring-like (framer built-in)
};

/* ── Transition Presets ────────────────────────────────────────── */
export const transitions = {
  snappy: { duration: 0.2, ease: easing.easeInOut },
  standard: { duration: 0.3, ease: easing.easeInOut },
  deliberate: { duration: 0.5, ease: easing.easeInOut },
  slow: { duration: 0.8, ease: easing.easeInOut },
  bounce: { type: 'spring', stiffness: 300, damping: 20, mass: 1 },
};

/* ── Variant Collections ───────────────────────────────────────── */

/**
 * Fade + Slide from Top (typical entry reveal)
 * Usage: <motion.div initial="hidden" whileInView="visible" variants={fadeSlideDown} />
 */
export const fadeSlideDown = {
  hidden: { opacity: 0, y: -16 },
  visible: { opacity: 1, y: 0, transition: transitions.standard },
};

/**
 * Fade + Slide from Bottom (viewport-triggered reveal, e.g., stat cards)
 */
export const fadeSlideUp = {
  hidden: { opacity: 0, y: 24 },
  visible: { opacity: 1, y: 0, transition: transitions.standard },
};

/**
 * Fade-Only (minimal motion for data table rows, list items)
 */
export const fadeOnly = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: transitions.snappy },
};

/**
 * Scale + Fade (badge entrance, badge state change)
 */
export const scaleUp = {
  hidden: { opacity: 0, scale: 0.92 },
  visible: { opacity: 1, scale: 1, transition: transitions.bounce },
};

/**
 * Shimmer skeleton (async loading state)
 * Rendered via CSS @keyframes; motion.div drives container visibility
 */
export const skeletonFade = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: transitions.snappy },
};

/**
 * Pulse / Glow (alert state, "live" indicator)
 * Use sparingly; only for critical status indicators
 */
export const pulse = {
  hidden: { opacity: 0.4 },
  visible: {
    opacity: [0.4, 1, 0.4],
    transition: { duration: 2, repeat: Infinity, ease: 'easeInOut' },
  },
};

/**
 * StaggerChildren (for list animations)
 * Usage: <motion.div variants={staggerContainer} initial="hidden" animate="visible">
 *          <motion.div variants={staggerItem} />
 *          <motion.div variants={staggerItem} />
 *        </motion.div>
 */
export const staggerContainer = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.05, delayChildren: 0 },
  },
};

export const staggerItem = {
  hidden: { opacity: 0, y: 8 },
  visible: { opacity: 1, y: 0, transition: transitions.snappy },
};

/* ── Animation Durations (ms, for reference in components) ────── */
export const durations = {
  instant: 0.15,
  quick: 0.25,
  normal: 0.3,
  slow: 0.5,
  deliberate: 0.8,
  long: 1.2,
};

/* ── Common Transition Objects ─────────────────────────────────── */
export const viewportConfig = {
  once: true,           // Animate only on first viewport entry
  amount: 0.2,          // Trigger when 20% of element is visible
  margin: '50px',       // Add 50px margin to viewport for early trigger
};
```

**Usage Example:**

```jsx
import { fadeSlideUp, staggerContainer, staggerItem, viewportConfig } from '@/motion.constants';
import { motion } from 'framer-motion';

export function FindingsList({ items }) {
  return (
    <motion.div
      variants={staggerContainer}
      initial="hidden"
      whileInView="visible"
      viewport={viewportConfig}
    >
      {items.map((item) => (
        <motion.div key={item.id} variants={staggerItem}>
          {/* Finding card */}
        </motion.div>
      ))}
    </motion.div>
  );
}
```

---

### 7.5 Typography Scale (`dashboard/src/index.css`)

```css
/* ── Typography Scale Definition ──────────────────────────────── */

/* Base sizing: 14px (0.875rem) = 1 unit; scales upward for headings, downward for captions */

/* Headings (h1–h6, .heading-* utility classes) */
.heading-h1 {
  font-size: 2.25rem;  /* 36px */
  font-weight: 800;
  line-height: 1.2;
  letter-spacing: -0.02em;
  color: var(--t1);
}

.heading-h2 {
  font-size: 1.875rem; /* 30px */
  font-weight: 700;
  line-height: 1.25;
  letter-spacing: -0.01em;
  color: var(--t1);
}

.heading-h3 {
  font-size: 1.5rem;   /* 24px */
  font-weight: 700;
  line-height: 1.3;
  letter-spacing: 0;
  color: var(--t1);
}

.heading-h4 {
  font-size: 1.25rem;  /* 20px */
  font-weight: 600;
  line-height: 1.4;
  letter-spacing: 0;
  color: var(--t1);
}

/* Body text */
.text-body-lg {
  font-size: 1rem;     /* 16px */
  font-weight: 400;
  line-height: 1.6;
  color: var(--t2);
}

.text-body {
  font-size: 0.875rem; /* 14px */
  font-weight: 400;
  line-height: 1.5;
  color: var(--t2);
}

.text-body-sm {
  font-size: 0.8125rem; /* 13px */
  font-weight: 400;
  line-height: 1.5;
  color: var(--t2);
}

/* Captions & labels */
.text-caption {
  font-size: 0.75rem;  /* 12px */
  font-weight: 500;
  line-height: 1.4;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--t3);
}

.text-overline {
  font-size: 0.625rem; /* 10px */
  font-weight: 700;
  line-height: 1.4;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--t3);
}

/* Monospace (code, terminal) */
.text-mono {
  font-family: 'JetBrains Mono', 'Fira Code', Consolas, monospace;
  font-size: 0.8125rem; /* 13px */
  line-height: 1.6;
  font-weight: 400;
  color: var(--t2);
}

.text-mono-sm {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem;  /* 12px */
  line-height: 1.5;
  font-weight: 500;
}

/* Numeric alignment (tabular numbers for tables, metrics) */
.text-numeric {
  font-variant-numeric: tabular-nums;
  font-feature-settings: "tnum" on, "lnum" on;
}
```

**Rationale:** Typography scale is logarithmic, not linear. Headings use aggressive weight and tight line-height; body uses generous line-height for reading comfort. Monospace is ever-present for code blocks and technical context.

---

### 7.6 Component Styling Classes (Preserved Existing, Documented Here)

**Do NOT add new .component classes; these are locked to current dashboard.**

```css
/* ── Cards ──────────────────────────────────────────────────────── */
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
}
.card-raised {
  background: var(--surface-r);
  border: 1px solid var(--border-s);
  border-radius: 14px;
}

/* ── Risk Badges ────────────────────────────────────────────────── */
.badge { 
  display: inline-flex; 
  align-items: center; 
  border-radius: 9999px;
  padding: 2px 10px; 
  font-size: 11px; 
  font-weight: 600; 
  border: 1px solid; 
}
.badge-critical { color: var(--critical); border-color: rgba(255,61,61,0.25); background: rgba(255,61,61,0.06); }
.badge-high     { color: var(--high);     border-color: rgba(255,122,26,0.25); background: rgba(255,122,26,0.06); }
.badge-medium   { color: var(--medium);   border-color: rgba(251,191,36,0.25); background: rgba(251,191,36,0.06); }
.badge-low      { color: var(--low);      border-color: rgba(0,229,160,0.25);  background: rgba(0,229,160,0.06); }

/* ── Buttons ────────────────────────────────────────────────────── */
.btn-primary {
  background: var(--cyan);
  color: var(--void);
  font-weight: 600;
  border-radius: 8px;
  padding: 8px 16px;
  font-size: 13px;
  cursor: pointer;
  transition: opacity 0.1s ease;
}
.btn-primary:hover { opacity: 0.88; }

/* ── Live Ping Animation (ONLY valid decorative animation in CSS) */
@keyframes live-ping {
  0%    { transform: scale(1); opacity: 0.8; }
  70%   { transform: scale(2.2); opacity: 0; }
  100%  { transform: scale(2.2); opacity: 0; }
}
.live-ping::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 50%;
  background: inherit;
  animation: live-ping 1.6s cubic-bezier(0,0,0.2,1) infinite;
}

/* ── Shimmer (async load skeleton) ────────────────────────────── */
.shimmer {
  background: linear-gradient(90deg, var(--surface) 0%, var(--surface-h) 50%, var(--surface) 100%);
  background-size: 300% 100%;
  animation: shimmer 1.8s linear infinite;
  border-radius: 6px;
}
@keyframes shimmer {
  0%   { background-position: 100% 0; }
  100% { background-position: -100% 0; }
}
```

---

## 8. Step-by-Step Implementation Plan

**Merge prerequisite:** All Wave 1 and Wave 2 features stable (RBAC, CONF, DFS, ENR, AUD). Frontend lane ensures no merge conflicts on `dashboard/src/App.jsx`, `dashboard/src/lib/constants.js`, or `mockData.js`.

### Step 1: Create Font Directory & Acquire Font Files
- **File:** `dashboard/public/fonts/`
- **Action:** 
  - Create directory `dashboard/public/fonts/`
  - Download Inter WOFF2 files (weights 400, 500, 600, 700) from [fonts.google.com](https://fonts.google.com) or fonttools conversion
  - Download JetBrains Mono WOFF2 files (weights 400, 500, 600) from [fonts.jetbrains.com](https://fonts.jetbrains.com)
  - Create `dashboard/public/fonts/OFL.txt` with Inter + JetBrains Mono OFL licenses
  - Create `dashboard/public/fonts/README.md` documenting inventory and sourcing

### Step 2: Update `dashboard/src/index.css` — Add Font Face Declarations
- **File:** `dashboard/src/index.css` (top of file, before `:root`)
- **Action:** Remove `@import url('https://fonts.googleapis.com/...')` line
- **Action:** Add `@font-face` declarations from §7.3 (8 font declarations: 4× Inter, 4× JetBrains Mono)
- **Verify:** No external CDN font requests in final CSS

### Step 3: Extend `:root` CSS Variables in `dashboard/src/index.css`
- **File:** `dashboard/src/index.css` `:root` block (lines 14–49)
- **Action:** Append C-24-compliant dark-theme skeleton variables (see §7.1) as comments/reserved structure
- **Action:** Document all existing variables with inline comments tying each to semantics (background, accent, tier, text hierarchy)
- **Example:**
  ```css
  /* Quantum-Risk Primary (Deep Forest Green) — semantic meaning: quantum-vulnerable findings */
  --purple: #1E532B;
  ```
- **Verify:** All 24 CSS variables documented and accessible to Tailwind config

### Step 4: Update `dashboard/tailwind.config.js` — Ensure Color Mapping
- **File:** `dashboard/tailwind.config.js`
- **Action:** Verify all color mappings in `theme.extend.colors` point to CSS variables
- **Action:** No hardcoded hex values; all via `var(--*)` references
- **Verify:** `tailwind build` completes without errors; utilities can reference `bg-cyan`, `text-t1`, `border-critical`, etc.

### Step 5: Create `dashboard/src/motion.constants.js` — Centralized Motion Vocabulary
- **File:** `dashboard/src/motion.constants.js` (new)
- **Action:** Copy full module from §7.4
- **Action:** Document all preset variants, transitions, and easing curves
- **Action:** Add JSDoc comments for each variant explaining use case
- **Verify:** Import in one non-LandingPage component and confirm framer-motion animations work

### Step 6: Extend `dashboard/src/index.css` — Add Typography Scale Classes
- **File:** `dashboard/src/index.css` (append after component classes)
- **Action:** Add all `.heading-*`, `.text-*`, `.text-mono*`, `.text-numeric` classes from §7.5
- **Action:** Remove any redundant or conflicting class definitions from existing CSS
- **Verify:** Dashboard renders headings and body text using new typography utilities without visual regression

### Step 7: Create `dashboard/DESIGN_TOKENS.md` — Comprehensive Documentation
- **File:** `dashboard/DESIGN_TOKENS.md` (new)
- **Content:**
  - Complete CSS variable reference table (name, value, semantic meaning, usage)
  - Color-to-tier mapping (which variables control Critical/High/Medium/Low badge styles)
  - Typography scale guide with examples
  - Framer-motion animation patterns with code snippets
  - Dark-theme roadmap (awaiting C-24 resolution)
  - Component styling guide (when to use .card, .badge-critical, .btn-primary, etc.)
  - Accessibility notes (contrast ratios, reduced-motion considerations)
  - Troubleshooting (e.g., "My custom color isn't working" → check Tailwind config extends)

### Step 8: Audit & Test Component Rendering
- **Files affected:** All components in `dashboard/src/`
- **Action:** Run `npm run build` and verify no CSS errors
- **Action:** Open dashboard in browser (dev server or built preview)
- **Action:** Verify:
  - Fonts load correctly (check Network tab; no Google Fonts CDN requests)
  - Color tokens render as expected (risk badges, buttons, backgrounds)
  - Framer-motion animations don't stutter (Chrome DevTools Performance tab)
  - No contrast issues (axe DevTools or manual WCAG check)
- **Document:** Screenshot or video evidence of motion/color/typography working

### Step 9: Validate GSAP Confinement (C-17 Enforcement)
- **Action:** Grep codebase for `gsap` imports outside `LandingPage`:
  ```bash
  grep -r "import.*gsap\|from.*gsap" dashboard/src --exclude-dir=pages/LandingPage
  ```
- **Expected:** Zero matches (GSAP only in LandingPage)
- **Action:** If matches found, refactor to framer-motion or mark for human review
- **Verify:** No GSAP ScrollTrigger instances outside LandingPage

### Step 10: Document Dark Theme C-24 Blocker
- **File:** `dashboard/DESIGN_TOKENS.md` and/or `dashboard/README-frontend.md`
- **Action:** Add section titled "Dark Theme (C-24 Pending)"
- **Content:**
  - CSS variable skeleton provided (see §7.1)
  - Component override pattern documented (`:root[data-theme="dark"]`)
  - Waiting for contract C-24 sign-off before implementation
  - Link to contract text: `SYSTEM_INTERFACE_CONTRACT.md §7`

---

## 9. Naming & Symbol Registry

### New CSS Variables

No new variables introduced. All work extends or documents existing `:root` set:

```
--void, --surface, --surface-r, --surface-h
--border, --border-s
--cyan, --cyan-10, --cyan-20
--purple, --purple-10
--green, --green-10
--critical, --high, --medium, --low
--t1, --t2, --t3, --t4
```

### New JavaScript Exports (`dashboard/src/motion.constants.js`)

```javascript
// Easing curves
easing.easeInOut, easing.easeOut, easing.easeIn, easing.bounce

// Transition presets
transitions.snappy, transitions.standard, transitions.deliberate, 
transitions.slow, transitions.bounce

// Variants
fadeSlideDown, fadeSlideUp, fadeOnly, scaleUp, skeletonFade, 
pulse, staggerContainer, staggerItem

// Durations
durations.instant, durations.quick, durations.normal, 
durations.slow, durations.deliberate, durations.long

// Config
viewportConfig
```

### New Tailwind Utility Classes

No new utilities. All existing Tailwind utilities map to CSS variables:

```
bg-void, bg-surface, bg-cyan, bg-critical, ...
text-t1, text-t2, text-t3, text-t4
border-border, border-cyan, border-critical, ...
```

### New CSS Classes (Typography + Components)

```
.heading-h1, .heading-h2, .heading-h3, .heading-h4
.text-body-lg, .text-body, .text-body-sm
.text-caption, .text-overline, .text-mono, .text-mono-sm, .text-numeric
```

### Collision Check

✅ **No symbol collisions.** No other feature (DEP, CNT, CONF, DFS, etc.) defines or claims ownership of CSS variables or framer-motion patterns. CONF owns `ConfidenceStamp.jsx` component (not this feature's variables). ASP/TRD/CMP own specific page components (not the motion library).

---

## 10. Known Cross-Feature Risks

### C-07: Design Tokens Ownership

**From Contract:** `dashboard/src/index.css`, `tailwind.config.js`, and `dashboard/public/fonts/` are **SOLE** to this feature. No other feature may define color tokens or font-family aliases.

**Risk:** CONF, DFS, TRI, CMP, TRD features might attempt to add custom Tailwind colors or CSS overrides for their own components.

**Resolution (Already Decided in Contract):**
- All custom colors must be expressed via the shared `:root` variable set.
- If a feature needs a new color (e.g., DFS adds a "filter-active" badge tint), it requests FE to add the variable via amendment or post-merge PR.
- No feature may create `theme.extend.colors` entries outside the FE-owned `tailwind.config.js`.

**Enforcement:** Code review must reject any Tailwind `colors: { ... }` in non-FE files.

---

### C-17: GSAP Confinement

**From Contract:** GSAP + ScrollTrigger are **exclusive to `dashboard/src/pages/LandingPage/index.jsx`**. All other motion must use framer-motion.

**Risk:** LandingPage feature owner (frontend lane) or TRD might accidentally import GSAP in another component.

**Resolution (Already Decided in Contract):**
- FE writes the motion.constants.js library with framer-motion patterns only.
- Code review must flag any `import gsap` outside LandingPage as a blocker.

**Enforcement:** Linting rule (if available) or manual grep check per §8 Step 9.

---

### C-24: Theme Toggle Scope

**From Contract:** "Light or dark dashboard theme; is a toggle in scope?" — **Status: UNRESOLVED, blocks FE.**

**Risk:** FE implements dark theme in this sprint, but C-24 sign-off disallows it → wasted work.

**Resolution (Deferred to §11):** FE provides CSS variable skeleton and dark-mode-ready component pattern in DESIGN_TOKENS.md but does NOT render dark-theme variants until C-24 is resolved.

---

### Interaction with COORDINATED Files

**`FindingsTable.jsx` (COORDINATED ownership):**
- DFS owns filtering/sorting logic and table schema.
- FE may update badge colors (e.g., risk tiers) to use new CSS variables, but must not restructure columns.
- Risk: DFS and FE might conflict on row-hover background or column header styling.
- **Resolution:** FE defines the color palette; DFS applies it via existing `.badge-*` classes. No merge conflicts expected.

---

## 11. Pre-Answered Ambiguities

### Ambiguity 1: Dark Theme Implementation Scope

**Situation:** Implementer is tempted to render dark-mode components using CSS `@media (prefers-color-scheme: dark)` or add dark-theme toggle UI.

**Answer (Per C-24):** **Do not implement dark theme colors or toggle.** Provide CSS variable skeleton in `dashboard/src/index.css` (see §7.1) as a placeholder. Document the pattern in `DESIGN_TOKENS.md` under "Dark Theme Roadmap (C-24 Pending)." Wait for human sign-off on C-24 before rendering any dark-variant components.

**Reference:** SYSTEM_INTERFACE_CONTRACT.md §7, item C-24: "Light or dark dashboard theme; is a toggle in scope? | FE TRD CMP | **Low**"

---

### Ambiguity 2: Where Do Custom Component Colors Go?

**Situation:** DFS feature owner wants to add a `.filter-active-pill` style with a custom background tint that isn't in the current palette.

**Answer:** DFS **must not** create custom colors in their component CSS. Instead, they request FE to add a new CSS variable (e.g., `--filter-active-bg`) to `:root` in `dashboard/src/index.css`. FE adds it, Tailwind config maps it to `bg-filter-active`, and DFS uses `className="bg-filter-active"`. This keeps all color definitions in one place (SOLE FE ownership, §5).

**Enforcement:** Code review should reject any `.component { color: #xyz; }` hardcoding in non-FE files.

---

### Ambiguity 3: Framer-Motion Variants in Components vs. motion.constants.js

**Situation:** Implementer writing a new component wants to define a custom variant for a fade-in-left animation.

**Answer:** Check `dashboard/src/motion.constants.js` first. If a variant already exists (e.g., `fadeSlideUp`), reuse it. If genuinely unique to the component, define it **inline in the component file** with JSDoc explaining its purpose. Do NOT add it to motion.constants.js unless the animation is reusable across 2+ components. This keeps motion.constants.js as the library of **common patterns**, not a kitchen sink.

**Example:**
```jsx
// ✅ Good: Reuse from library
<motion.div variants={fadeSlideUp} initial="hidden" whileInView="visible" />

// ✅ Good: Inline variant specific to this component
const uniqueFlipVariant = {
  hidden: { rotateY: 90, opacity: 0 },
  visible: { rotateY: 0, opacity: 1 },
};
<motion.div variants={uniqueFlipVariant} />

// ❌ Bad: Adding a one-off animation to motion.constants.js
// (motion.constants.js should not grow unboundedly)
```

---

### Ambiguity 4: Performance Impact of Framer-Motion Animations

**Situation:** Implementer adds framer-motion animations to every stat card and finding row, and the dashboard feels janky.

**Answer:** Framer-motion uses GPU-backed transforms (`transform`, `opacity`) which are performant. However, avoid:
- **Animating layout properties** (`width`, `height`, `margin`) — causes reflow. Use `layoutId` sparingly.
- **Too many simultaneous animations** — stagger with `staggerChildren` (see `motion.constants.js`).
- **Animating color with `color` property** — use opacity instead, or pre-define multiple colors and animate `backgroundColor` on a fixed container size.
- **Disabling GPU acceleration** — always use `will-change: transform` sparingly, let framer-motion optimize.

If dashboard feels slow after animation additions:
1. Open Chrome DevTools → Performance tab.
2. Record a scroll interaction; look for long "Rendering" or "Compositing" frames.
3. Refactor offending animations to use only `opacity` and `transform`.
4. Test on low-end devices (simulator or actual hardware).

---

### Ambiguity 5: Fallback Fonts if Self-Hosted Fonts Fail to Load

**Situation:** In an air-gapped deployment, network request to `/fonts/Inter-Bold.woff2` hangs or 404s.

**Answer:** All font declarations use `font-display: swap` (§7.3), which tells the browser:
1. Load the custom font asynchronously.
2. **Immediately display text in the fallback font** (Segoe UI, system-ui, sans-serif for Inter; Fira Code, Consolas for Mono).
3. Once the custom font loads, swap it in (without reflow).

This ensures the dashboard is **always readable**, even if fonts are missing. Font loading should be nearly instant in production (local file serve), so fallbacks are rarely seen.

**Test:** Simulate slow network via Chrome DevTools Network tab → "Slow 3G" → reload. Verify text is readable the entire time.

---

### Ambiguity 6: Checking CSS Variable Contrast for Accessibility

**Situation:** Implementer adds a new `:root` variable (e.g., `--info-bg: #E0F2FE;`) and isn't sure if text on it meets WCAG standards.

**Answer:** Use [webaim.org/resources/contrastchecker](https://webaim.org/resources/contrastchecker) or automated tool (axe DevTools, WAVE). For light backgrounds on light theme:
- **WCAG AA (normal text):** Minimum 4.5:1 contrast ratio
- **WCAG AAA (normal text):** Minimum 7:1 contrast ratio
- **Large text (18pt+):** AA is 3:1, AAA is 4.5:1

Current palette (dark text on light backgrounds):
- `--t1` (#0F172A) on `--void` (#FFF6F7): ~14:1 ✅ (exceeds AAA)
- `--critical` (#E53935) on white: ~3.5:1 ✅ (AA for large text)

If adding new colors, validate using same tool. Document results in `DESIGN_TOKENS.md`.

---

### Ambiguity 7: Responsive Tailwind Utilities and CSS Variables

**Situation:** Implementer uses Tailwind responsive prefixes (e.g., `md:bg-cyan`) and wonders if it works with `var(--cyan)`.

**Answer:** Yes. Tailwind's responsive system works seamlessly with CSS variables. Example:
```jsx
<div className="bg-void md:bg-surface lg:text-t1 md:text-t2">
  {/* Void on mobile, surface on md+, cyan on lg+ */}
</div>
```

All color mappings in `tailwind.config.js` use `var(--*)`, so Tailwind's JIT engine correctly applies responsive variants.

---

### Ambiguity 8: Prefers-Reduced-Motion & framer-motion

**Situation:** A user has `prefers-reduced-motion: reduce` set in OS accessibility settings. Should animations still play?

**Answer:** framer-motion respects `prefers-reduced-motion` **automatically** (as of v10+). If a user has it enabled, animations will:
- Disable or reduce to instant transitions.
- Preserve layout and functionality (no jank, just less flourish).

No additional code needed. Test via Chrome DevTools:
1. Render → Emulate CSS Media Feature Prefers Reduced Motion → select "prefers-reduce-motion"
2. Interact with dashboard; animations should be minimal or instant.

---

### Ambiguity 9: Using CSS Variables in Pseudoclasses (::before, ::after, :hover, etc.)

**Situation:** Implementer wants to use `var(--cyan)` inside a `:hover` state or `::before` content.

**Answer:**
- ✅ **For `::before`/`::after` backgrounds, borders, colors:** Works fine.
  ```css
  .button::before {
    background: var(--cyan);  /* ✅ Works */
  }
  ```

- ❌ **For CSS `content` property:** Does NOT work. CSS variables do not expand inside string content.
  ```css
  .label::after {
    content: var(--label-text);  /* ❌ Fails; use static text or JS instead */
  }
  ```

- ✅ **For `:hover`, `:focus`, `:active` states:** Works if you redefine the variable.
  ```css
  .button {
    background: var(--surface);
    transition: background 0.1s;
  }
  .button:hover {
    background: var(--surface-h);  /* ✅ Works */
  }
  ```

All current uses in `dashboard/src/index.css` (`.nav-item:hover`, `.btn-primary:hover`, etc.) follow the ✅ pattern.

---

### Ambiguity 10: Animation Performance on Mobile vs. Desktop

**Situation:** Animations are smooth on desktop but janky on mobile/low-end devices.

**Answer:** 
1. **Reduce animation scope:** Animate only critical UI (entry, state change). Avoid animating every finding row.
2. **Use `will-change` sparingly:**
   ```jsx
   <motion.div style={{ willChange: 'transform' }}>
     {/* Only for continuously animated elements */}
   </motion.div>
   ```
3. **Simplify variants on mobile:** Use `AnimatePresence` with conditional rendering instead of complex multi-step sequences.
4. **Test on low-end device:** Use Chrome DevTools Device Emulation or actual older phone.

Performance checklist:
- FPS counter (Chrome DevTools → Rendering → Frame Rate Meter) should stay **≥ 60 FPS**.
- No "jank" frames (drops below 50 FPS).
- Scrolling is smooth (60 FPS throughout).

If still slow, refactor to use CSS animations (`@keyframes`) instead of JavaScript-driven motion (last resort).

---

### C-24 Resolution Placeholder

**Open Question:** "Light or dark dashboard theme; is a toggle in scope?"

**Current Assumption (for this spec):** Light theme only. Dark theme is documented as "reserved structure" in `dashboard/src/index.css` but not rendered.

**Resolution When C-24 is Answered:**
- If **approved:** FE implements dark-theme `:root` variables, `@media (prefers-color-scheme: dark)` block, and theme-toggle UI in a follow-up PR.
- If **deferred:** Close out as "future work" in `DESIGN_TOKENS.md`.
- If **rejected:** Remove dark-theme skeleton from CSS and mark C-24 as "out-of-scope."

**Blocker:** This feature **cannot merge** if C-24 remains unresolved and a dependent feature (CMP, TRD) insists on dark-mode support. Escalate to product lead.

---

## 12. Test Plan / Definition of Done

### Pre-Merge Checklist

- [ ] All 13 sections of spec reviewed by frontend lane (Karan/Satyam)
- [ ] No file conflicts with COORDINATED or do-not-touch files
- [ ] GSAP confinement verified (no imports outside LandingPage)

### Build & Rendering Tests

**Command:** `npm run build` (from `dashboard/` directory)

**Expected:**
- ✅ Zero CSS errors
- ✅ Zero JavaScript build warnings related to motion or fonts
- ✅ Final bundle includes self-hosted fonts in `/dist/fonts/`
- ✅ No external font CDN requests in built CSS

---

### Font Loading Test

**Command:** `npm run dev` and open [http://localhost:5173](http://localhost:5173) in browser

**Steps:**
1. Open Chrome DevTools → Network tab.
2. Filter by "Font" type.
3. Verify:
   - ✅ Requests to `/fonts/Inter-*.woff2` succeed (HTTP 200)
   - ✅ Requests to `fonts.googleapis.com` **do not appear** (no CDN fallback)
   - ✅ Font file sizes are reasonable (Inter-Regular ~30KB, JetBrains Mono ~35KB)
   - ✅ Load time < 100ms (typical with local serve)

**Fallback Test:**
1. Simulate missing font file: Rename `dashboard/public/fonts/Inter-Bold.woff2` → `Inter-Bold.woff2.backup`
2. Reload dashboard.
3. Text should render in fallback font (Segoe UI) **immediately**, then swap to Inter when font is restored.
4. Restore font file.

---

### Color Token Test

**Command:** Open dashboard in browser (dev or prod build)

**Steps for Each Color Token:**

For `--void` (light pink background):
- [ ] Hero section uses `--void` as background → appears as light pink
- [ ] No white background where `--void` is expected

For `--cyan` (watermelon accent):
- [ ] Primary buttons use `--cyan` → appear pink
- [ ] Active nav items have `--cyan` text and border
- [ ] Focus ring on inputs is `--cyan`

For `--critical`, `--high`, `--medium`, `--low` (risk tiers):
- [ ] Dashboard mock findings table displays badges in correct colors:
  - Critical finding badge → red
  - High finding badge → orange
  - Medium finding badge → amber
  - Low finding badge → dark green
- [ ] Inspect element → computed styles should show `--critical`, etc., resolving to correct hex

For text hierarchy (`--t1`, `--t2`, `--t3`, `--t4`):
- [ ] Main headings (h1, h2) render in `--t1` (darkest)
- [ ] Body text renders in `--t2` (lighter)
- [ ] Captions render in `--t3` (lighter still)
- [ ] Disabled/placeholder text renders in `--t4` (lightest)

**Command to verify token values:**
```bash
# In browser console:
getComputedStyle(document.documentElement).getPropertyValue('--void').trim()
# Should output: #FFF6F7
```

---

### Framer-Motion Animation Tests

**All tests performed in browser (Chrome/Firefox) with DevTools open.**

#### Test 1: Fade-Slide Entry Animation
- [ ] Navigate to dashboard page
- [ ] Stat cards (top-right) fade in + slide from bottom when page loads
- [ ] Animation duration ~300ms, smooth easing

#### Test 2: Risk Badge Scale Animation
- [ ] Open a findings card
- [ ] Risk tier badge (CRITICAL, HIGH, etc.) scales up on reveal
- [ ] Animation uses spring-like easing (bouncy, not jarring)

#### Test 3: Shimmer Skeleton Loading
- [ ] If a data fetch is delayed, loading skeleton appears
- [ ] Shimmer gradient sweeps left-to-right infinitely
- [ ] When data loads, skeleton fades out and content fades in

#### Test 4: Stagger List Animation
- [ ] If a list of 5+ findings is rendered:
  - First finding fades in immediately
  - Subsequent findings fade in with 50ms stagger
  - Entire sequence completes in ~300ms total

#### Test 5: GSAP Confinement
- [ ] Open LandingPage (`/` route)
- [ ] Scroll animations with GSAP ScrollTrigger work (elements move on scroll)
- [ ] Open DashboardPage
- [ ] No scroll-triggered GSAP animations; framer-motion viewport-entry used instead

#### Test 6: Motion Respects Prefers-Reduced-Motion
- [ ] Open DevTools → Rendering → Emulate CSS Media Feature → Prefers Reduced Motion
- [ ] Dashboard loads with minimal/instant animations
- [ ] Functionality (buttons, navigation) unaffected

#### Test 7: Performance (FPS Check)
- [ ] Open DevTools → Rendering → Frame Rate Meter
- [ ] Interact (scroll, hover, click) on dashboard
- [ ] FPS counter stays ≥ 60 FPS (green zone)
- [ ] No red "jank" frames

---

### Typography Scale Test

**Command:** Open dashboard in browser

**Steps for Each Typography Class:**

- [ ] `.heading-h1` appears in a main page title → size ~36px, weight 800, dark color
- [ ] `.heading-h2` appears in section titles → size ~30px, weight 700
- [ ] `.text-body` appears in card descriptions → size ~14px, weight 400, readable
- [ ] `.text-caption` appears in table headers → size ~12px, weight 500, uppercase, light gray
- [ ] `.text-mono` appears in code blocks / terminal → monospace font, line-height 1.6
- [ ] `.text-numeric` appears in metric values (e.g., "42 findings") → tabular numbers (aligned in columns)

**Contrast Check:** Verify text is readable:
- [ ] Dark text on light backgrounds contrast ≥ 4.5:1 (WCAG AA)
- [ ] Use axe DevTools or [webaim.org/resources/contrastchecker](https://webaim.org/resources/contrastchecker)

---

### CSS Variable Documentation Test

**File:** `dashboard/DESIGN_TOKENS.md`

**Steps:**
- [ ] Document exists and is readable (valid Markdown)
- [ ] Contains sections:
  - [ ] "Color Tokens" — table of all 24 `:root` variables with hex values and semantics
  - [ ] "Typography Scale" — sizing, weight, line-height, use cases
  - [ ] "Framer-Motion Patterns" — code examples for `fadeSlideUp`, `staggerContainer`, etc.
  - [ ] "Component Styling" — when to use `.card`, `.badge-critical`, `.btn-primary`
  - [ ] "Accessibility" — contrast ratios, reduced-motion, keyboard focus
  - [ ] "Dark Theme Roadmap (C-24 Pending)" — CSS variable skeleton, awaiting sign-off
- [ ] All code examples are copy-paste-ready (no typos, valid JSX/CSS)

---

### Regression Test (Existing Components)

**Command:** Run existing test suite (if any) for dashboard components

```bash
npm run test  # (if configured)
```

**Manual Checks:**
- [ ] FindingsTable renders without layout shift (color token changes should not reflow)
- [ ] Navigation sidebar nav items highlight correctly (`.nav-item.active` uses `--cyan`)
- [ ] Buttons are clickable and responsive (no motion interference)
- [ ] Modals/dialogs open/close smoothly (no flash or FOUC)
- [ ] Charts (Recharts) render and animate correctly

---

### Merge Criteria (Definition of Done)

**All of the following must be true:**

1. ✅ **File ownership respected:** No modifications to SOLE/FROZEN files outside `dashboard/src/index.css`, `tailwind.config.js`, `dashboard/public/fonts/`, and new FE-owned files.
2. ✅ **Self-hosted fonts:** `dashboard/public/fonts/` exists with Inter + JetBrains Mono WOFF2 files, zero external CDN requests.
3. ✅ **CSS variables complete:** All 24 `:root` variables defined and documented, no hardcoded colors in component CSS.
4. ✅ **Tailwind config:** `tailwind.config.js` extends colors and fonts, all mappings use `var(--*)`.
5. ✅ **Framer-motion library:** `dashboard/src/motion.constants.js` created with preset variants, transitions, easing.
6. ✅ **GSAP confinement:** Zero GSAP imports outside LandingPage (verified via grep).
7. ✅ **Typography scale:** All heading and text classes (.heading-h1, .text-body, .text-mono, etc.) render correctly.
8. ✅ **Design documentation:** `DESIGN_TOKENS.md` complete with tables, code examples, C-24 blocker noted.
9. ✅ **No visual regressions:** Dashboard renders identically to pre-FE state (colors, layout, fonts match).
10. ✅ **Animation performance:** All framer-motion animations run at ≥60 FPS; prefers-reduced-motion respected.
11. ✅ **Build succeeds:** `npm run build` completes with zero CSS/JS errors.
12. ✅ **Code review:** Frontend lane (Karan/Satyam) + spec author sign-off.

---

## 13. Rollback Plan

### If This Feature Breaks the Build

**Symptom:** `npm run build` fails with CSS or JavaScript errors.

**Rollback Steps:**
1. **Revert the entire `dashboard/` change:**
   ```bash
   git checkout main -- dashboard/
   npm ci  # reinstall original package-lock.json
   npm run build  # verify build succeeds
   ```
2. **Identify the broken commit:**
   ```bash
   git log --oneline dashboard/src/index.css dashboard/tailwind.config.js | head -5
   git revert <commit-hash>  # revert only the problematic commit
   ```
3. **Investigate the error:**
   - CSS syntax error (missing semicolon, invalid variable reference)?
   - JavaScript import error (motion.constants.js exports missing)?
   - Font file 404 (public/fonts/ files missing)?
4. **Fix and re-test before re-landing.**

---

### If Font Files Fail to Load in Production

**Symptom:** Dashboard renders with fallback fonts (Segoe UI instead of Inter); performance regression or accessibility issues reported.

**Diagnosis:**
1. **Check `/dashboard/public/fonts/` directory:**
   ```bash
   ls -la dashboard/public/fonts/
   ```
   If directory is empty or missing, fonts were not bundled during build.

2. **Check Vite config (`dashboard/vite.config.js`):**
   Ensure `publicDir` is set to `public` (default). If fonts are in a different directory, update config:
   ```javascript
   export default defineConfig({
     publicDir: 'public',  // or your custom path
   });
   ```

3. **Check `index.css` font-face URLs:**
   If `@font-face src:` points to wrong path (e.g., `/fonts/` when served from `/dashboard/fonts/`), fix the path.

**Rollback:**
- Revert to Google Fonts CDN (temporary):
  ```css
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');
  ```
- Deploy; verify dashboard works.
- Investigate font bundling issue separately (CI/CD configuration, Docker build, etc.).

---

### If Color Tokens Break Existing Components

**Symptom:** Dashboard colors appear wrong; buttons are invisible, text is unreadable.

**Cause:** Likely a CSS variable was renamed or deleted, breaking Tailwind config mappings.

**Rollback:**
1. **Revert `dashboard/src/index.css` and `dashboard/tailwind.config.js`:**
   ```bash
   git checkout main -- dashboard/src/index.css dashboard/tailwind.config.js
   ```
2. **Verify existing colors render:**
   ```bash
   npm run build && npm run preview
   ```
3. **Compare the reverted CSS with the broken version:**
   ```bash
   git diff main -- dashboard/src/index.css
   ```
   Look for missing `:root` variables or broken Tailwind mappings.

4. **If a variable was accidentally deleted:**
   ```bash
   git log --reverse dashboard/src/index.css | grep "deleted var"
   git show <commit>  # show what was removed
   ```
   Add the variable back to `:root`.

---

### If Framer-Motion Animations Cause Performance Issues

**Symptom:** Dashboard feels slow or janky; FPS < 60.

**Rollback:**
1. **Temporarily disable animations:**
   ```jsx
   // In motion.constants.js, set all durations to 0:
   const transitions = {
     snappy: { duration: 0, ease: easing.easeInOut },
     // ... all durations set to 0
   };
   ```
2. **Test dashboard performance:**
   ```bash
   npm run dev
   # Open DevTools → Rendering → Frame Rate Meter
   # Interact and check FPS
   ```
3. **If FPS is now ≥ 60:**
   - A specific animation is the culprit.
   - Identify which `<motion.div>` or variant is slow (use React DevTools Profiler).
   - Simplify that animation (use only `opacity` and `transform`; avoid layout property changes).
   - Re-test.

4. **If FPS is still < 60:**
   - Problem is not animations; likely a rendering issue in component logic.
   - Investigate other changes in this feature PR (font loading, CSS, etc.).

**Full Revert (if needed):**
```bash
git revert <PR-merge-commit>  # revert entire FE feature
npm ci && npm run build && npm run preview
# Verify dashboard is responsive again
```

---

### If C-24 (Theme Toggle) Blocks Merge

**Symptom:** PR is ready, but C-24 is unresolved; product lead or another team says dark theme is out-of-scope and PR should merge as-is.

**Resolution:**
1. **Confirm C-24 status with product lead.**
   - If **approved (dark theme is in-scope):** Implement dark-theme CSS variables and toggle UI; re-merge.
   - If **deferred (dark theme is future work):** Keep `DESIGN_TOKENS.md` "C-24 Pending" section; merge with light-theme only.
   - If **rejected (light theme only):** Remove dark-theme CSS variable skeleton; merge.

2. **If unsure, DO NOT block on C-24.** Ship light theme (confirmed in-scope) and document the roadmap in `DESIGN_TOKENS.md`.

---

## Summary

This specification provides a complete, contract-aligned implementation plan for the **Frontend Typography / Color / Motion Pass** feature. It covers:

1. **Self-hosted fonts** (Inter, JetBrains Mono) to eliminate CDN dependencies.
2. **Comprehensive CSS color-variable system** with 24 semantic tokens for backgrounds, accents, risk tiers, and text hierarchy.
3. **Framer-motion animation library** with reusable variants and transitions, excluding GSAP (confined to LandingPage per C-17).
4. **Typography scale** with heading, body, caption, and monospace classes.
5. **Design documentation** in `DESIGN_TOKENS.md` for implementers and future maintainers.
6. **Detailed implementation steps** (10 phases) tied to specific files and actions.
7. **Risk mitigation** for known conflicts (C-07, C-17, C-24) and cross-feature interactions.
8. **Comprehensive test plan** with pass/fail criteria for fonts, colors, motion, and performance.
9. **Rollback procedures** for build failures, font issues, color regressions, and performance problems.

**Blocker:** C-24 (dark theme scope) is unresolved. This spec documents light theme as confirmed in-scope and defers dark-theme implementation until C-24 is resolved.

**Ready for implementation in Wave 3** (post-RBAC, CONF, DFS, ENR, AUD).

---

**Specification prepared by:** Senior Design Systems Engineer  
**Date:** September 20, 2026  
**Baseline:** SYSTEM_INTERFACE_CONTRACT.md v2, ARCHITECTURE.md, AGENT_RULES.md, ECDAT codebase audit
