# FE — Docker/3.11 verification queue

## What I could not verify, and why

- Browser font-loading, color rendering, reduced-motion behavior, and the >=60 FPS target require Chrome/Firefox DevTools, unavailable during this CLI session.
- Docker/air-gapped packaging behavior requires the Docker teammate. This is a frontend-only feature; no Postgres behavior is affected.
- `npm run test` is not configured in `dashboard/package.json` (there is no `test` script).

## Exact commands to run, in order

1. From `dashboard/`: `npm ci` then `npm run build`.
2. From repository root: `Get-ChildItem dashboard/dist/fonts -File | Select-Object Name,Length`.
3. Start `npm run dev` in `dashboard/`, open `http://localhost:5173`, and in DevTools Network filter `Font`; verify each `/fonts/Inter-*.woff2` and `/fonts/JetBrainsMono-*.woff2` request returns 200 and no `fonts.googleapis.com` request occurs. Simulate a missing font by temporarily renaming `dashboard/public/fonts/Inter-Bold.woff2`, reload, verify readable fallback, then restore the file.
4. In browser console run `getComputedStyle(document.documentElement).getPropertyValue('--void').trim()`; inspect risk badges, text tiers and typography classes as described in §12.
5. Exercise §12 animation tests in the browser: dashboard entry, badge scale, delayed loading skeleton, 5+ item stagger, LandingPage GSAP scroll, reduced motion, and Rendering > Frame Rate Meter while interacting.
6. From repository root: `rg -n "import.*gsap|from.*gsap" dashboard/src -g '!pages/LandingPage/**'`.
7. Inspect reduced-motion and contrast manually with browser DevTools/axe or a contrast checker; verify body text combinations meet 4.5:1.

## Expected output for each

1. `npm run build` exits 0 with no CSS/JS errors; built CSS contains no Google Fonts CDN import.
2. Ten files are listed: seven WOFF2 files, both OFL licenses, and README. The build copies fonts into `dashboard/dist/fonts/`.
3. Local font requests return HTTP 200; no Google Fonts CDN request. Text stays legible in fallback when a face is missing.
4. Console returns `#FFF6F7`; current theme is light, existing risk-tier tokens resolve to `#E53935`, `#E65100`, `#D97706`, and `#1E532B` respectively.
5. Verify the §12 behavior manually. Reduced motion should minimize movement; FPS target is >=60 during representative interaction. Performance is not asserted from build output.
6. No matches (rg exit code 1). Any match outside LandingPage is a C-17 issue.
7. Confirm actual foreground/background pairs meet AA. Do not infer contrast from the token names alone.

## What to do if it fails

- Build or CDN import: inspect `dashboard/src/index.css` and `dashboard/public/fonts/` first.
- Missing font in `dist`: check Vite's default public directory and the font URLs at the top of `dashboard/src/index.css`.
- Unmapped Tailwind utility: check `dashboard/tailwind.config.js` and `:root` in `dashboard/src/index.css`.
- Motion preset issue: inspect the corresponding export in `dashboard/src/motion.constants.js`.
- GSAP match: inspect the reported source and keep GSAP/ScrollTrigger exclusive to `dashboard/src/pages/LandingPage/index.jsx`.
- Contrast or reduced-motion issue: inspect token pairing and the framer-motion consumer; this feature does not modify component owners.

## Files I touched that Postgres behaviour depends on

None. This feature changes frontend assets, CSS and documentation only.
