# ClaimBitz Hero — Lovable Parity Plan

> **Status:** Audit complete · awaiting approval before implementation
> **Branch:** none yet — create `feature/claimbitz-final-lovable-parity` from `main` at `e1d8df9` before starting
> **Application code modified:** none
> **Lovable source modified:** none

---

## 1. Objective

Make the ClaimBitz landing-page Hero section visually and interactionally identical to the actual Lovable reference (`claimbitz-lovable/src/routes/index.tsx` + `components/claimbitz/WorkspacePreview.tsx`) while preserving every piece of existing ClaimBitz functionality, Indian/INR demo data, real routing (`/dashboard`), accessibility improvements (reduced-motion, focus-visible), and the authoritative `useClaimAgent` data layer.

The Hero is purely marketing/demo — it does not consume real backend data. All changes are presentation-only within landing-scoped files.

---

## 2. Current State

### Files that define the Hero

| File | Role |
|------|------|
| `frontend/src/pages/LandingPage.jsx` lines 432–580 | Hero section wrapper, copy, CTAs, metrics, WorkspacePreview mount |
| `frontend/src/components/landing/WorkspacePreview.jsx` | Looping demo card (document, timeline, activity strip) |
| `frontend/src/components/landing/landingDemo.js` | Nine marketing-only agents (`DEMO_AGENTS`) + `DEMO_CLAIM` fixture |
| `frontend/src/components/claimbitz/AgentTimeline.jsx` | Shared timeline (used by both Hero and dashboard) |
| `frontend/src/components/claimbitz/RiskRing.jsx` | `RiskRing` + `AnimatedPercent` (shared) |
| `frontend/src/index.css` | Tokens, `eyebrow`/`panel`/`story-link` utilities, focus, scrollbar, reduced-motion |

### What exists and matches Lovable

- Header: 64px, max-1240px, 20px horizontal padding, 28px "C" brand mark, four desktop nav links, copper "Launch console" CTA → `/dashboard`
- Hero grid: `0.8fr 1.2fr` at `lg`, gap 40px, pt 40/56px (lg 56px), preview offset `-mr-4`
- Typography: eyebrow "Read. Validate. Decide." in accent-foreground; H1 clamp 36.8–54.4px; body 16px relaxed; CTAs 14.5px/44px; metrics 24px count-up
- WorkspacePreview: elevated card, 850ms steps, 1400ms hold, 1.6s scan, 0.5s progress bar, six document rows, seven-agent timeline, four-item activity footer, 64px risk ring on completion
- Entrance: Hero copy 0.45s fade/rise; preview 0.6s/0.15s delay; metrics 900ms cubic count-up on viewport entry
- All spacing, borders, radii, shadows, and color tokens match class-for-class

### What differs from Lovable

1. **AgentTimeline missing "checks remaining"** — Lovable shows `N checks remaining` under the active agent's activity text; current omits it because `progress` prop is not passed and `checks` metadata is absent from `DEMO_AGENTS`
2. **`story-link` animated underline** — current CSS adds a 1px underline that scales on hover via `::after`; Lovable's `styles.css` defines no such rule, so Lovable nav links only change text color on hover
3. **Favicon** — current `public/favicon.svg` is an old indigo `#4F46E5` shield; the UI brand mark is copper `#C76A2B`
4. **Active ping reduced-motion** — current uses `motion-safe:animate-ping`; Lovable uses unconditional `animate-ping`
5. **Demo data content** — Indian names/INR vs US names/USD (intentional product decision — keep Indian)
6. **Font fallback stacks** — current: `Apple/Segoe/Roboto`; Lovable: `ui-sans-serif/system-ui`. Minimal visual impact unless fonts fail to load
7. **Smooth scroll** — current `html { scroll-behavior: smooth }` makes anchor clicks smooth; Lovable has no such rule (jumps immediately)

---

## 3. Lovable Reference State

**Source:** `claimbitz-lovable/src/routes/index.tsx` lines 489–571 (Hero) + `WorkspacePreview.tsx` + `AgentTimeline.tsx` + `RiskPanel.tsx` (RiskRing/AnimatedPercent only) + `data.ts` (AGENTS/CLAIM fixtures) + `styles.css`

### Lovable Hero behavior

- Identical grid, typography, CTA, and metric structure to current
- WorkspacePreview uses `AGENTS` from `data.ts` (nine agents with `checks` field: 3,4,5,4,3,4,2,2,1) and passes `progress={0.4}` to `AgentTimeline`
- AgentTimeline renders `remaining = max(1, ceil(agent.checks × (1 - progress)))` as `"N checks remaining"` at 11px (compact) or 11.5px (normal) below the activity text, adding ~20px of vertical content to the active row
- Nav links use the `story-link` class but Lovable's `styles.css` defines no pseudo-element for it — only Tailwind color transitions apply
- Active ping is unconditional `animate-ping` (no reduced-motion gate)
- Fixture data is US/USD (Hartley, Meridian, $412.00)

### What is mock/demo only (must NOT be ported to dashboard)

- `data.ts` AGENTS array, CLAIM object, checks counts, seconds, OUTCOMES, RISK_SIGNALS, OUTPUT_CONTENT, LOGS
- The `progress={0.4}` constant is presentation tuning for the marketing loop, not real pipeline state
- All hardcoded patient names, insurer names, and amounts
- The nine-agent model (real ClaimBitz has eight)

---

## 4. Recording / Prototype Findings

**No recordings, videos, GIFs, screenshots, or external design-file links were found** in the workspace. The only external reference is the Lovable editor URL in `claimbitz-lovable/README.md`:
`https://lovable.dev/projects/5bcf829c-c939-4ed8-b281-708b4dbea1ec`

All timing, easing, and state information in this plan is derived exclusively from source inspection. The following behaviors **cannot be confirmed** without a recording or live capture:

| Behavior | Why recording is needed |
|----------|------------------------|
| First visible demo step after BootSplash fade | BootSplash blocks for ~1.35s; preview reaches step 1 at 0.85s — which step is actually first-visible depends on hydration/render timing |
| AnimatePresence default swap timing | framer-motion 12 vs motion 13 may have different unspecified defaults for result-card crossfade |
| Exact card height with checks line | The extra ~20px changes layout; text wrapping near breakpoints needs visual verification |
| Font fallback rasterization | The different fallback stacks may produce different metrics if Inter fails to load |
| Smooth-scroll feel | Whether the current smooth anchor behavior is perceived as better or worse UX than Lovable's instant jump |

These are marked "needs verification" in the animation table below.

---

## 5. Parity Matrix

| Area | Current ClaimBitz | Lovable Reference | Gap | Action | Priority |
|------|-------------------|-------------------|-----|--------|----------|
| Hero grid/spacing | `0.8fr/1.2fr`, gap 40, pt 40/56 | Same | None | — | — |
| Hero typography | clamp, weights, tracking match | Same | None | — | — |
| Eyebrow "Read. Validate. Decide." | `eyebrow !text-accent-foreground` | Same | None | — | — |
| H1 headline | Same clamp/weight/leading | Same | None | — | — |
| Body copy | Same 16px relaxed | Same | None | — | — |
| Primary CTA | h-11, copper, → `/dashboard` | Same, → `/console` | Route | **INTENTIONAL** — keep `/dashboard` | — |
| Secondary CTA | Same bordered, → `#how-it-works` | Same | None | — | — |
| Metric count-up | 900ms cubic rAF | Same | None | — | — |
| Preview entrance | 0.6s / 0.15s delay | Same | None | — | — |
| Preview card chrome | elevated shadow, border, radius | Same | None | — | — |
| Demo loop timing | 850ms / 1400ms | Same | None | — | — |
| Scan line | 1.6s infinite easeInOut, steps 0-2 | Same | None | — | — |
| Region highlights | 300ms color transition | Same | None | — | — |
| Progress bar | scaleX, 0.5s easeOut, snap on reset | Same | None | — | — |
| Risk ring (completion) | 64px, 24%, 1.2s easeOut | Same | None | — | — |
| Result swap | AnimatePresence mode="wait" | Same | **Needs verification** — default timing may differ between framer-motion 12 and motion 13 | Verify visually after implementation | P3 |
| Timeline node/connector | 21/17px, 0.45s connector, 1.8s pulse, spring check | Same | None | — | — |
| **Timeline checks remaining** | **Missing** — `progress` prop ignored, no `checks` data | Lovable renders "N checks remaining" at 11px | **PARTIAL** | Add `checks` to `DEMO_AGENTS`; pass `progress={0.4}`; render conditionally in AgentTimeline | **P1** |
| **Nav link underline** | Current CSS adds `::after` underline animation | Lovable has no underline rule | **EXTRA** | Remove the `story-link` pseudo-element rules from `index.css` | **P2** |
| **Favicon** | Indigo `#4F46E5` shield | Copper brand mark / `.ico` | **STALE** | Replace with copper "C" mark | **P2** |
| Active ping | `motion-safe:animate-ping` | `animate-ping` | **INTENTIONAL** — keep reduced-motion handling | — | — |
| Demo data content | Indian names, ₹ | US names, $ | **INTENTIONAL** — keep Indian | — | — |
| Smooth scroll | `html { scroll-behavior: smooth }` | Not present | **INTENTIONAL** — keep as UX enhancement | — | — |
| Font fallback stacks | Apple/Segoe/Roboto | ui-sans-serif/system-ui | **PARTIAL** | Optional alignment; low visual impact | P3 |

---

## 6. Missing Elements

Only one genuinely missing visual element was identified:

1. **"N checks remaining" text under the active agent in WorkspacePreview's AgentTimeline** — Lovable renders this at 11px (compact mode) in `text-accent-foreground` with `tabular-nums`. Current omits it because `DEMO_AGENTS` lacks `checks` values and `WorkspacePreview` does not pass `progress`.

Everything else either matches or is intentionally different.

---

## 7. Visual Differences

### Typography
- **Checks remaining line:** Missing 11px `tabular-nums text-accent-foreground` line. Adds ~20px to the active agent row height.
- All other Hero typography matches class-for-class.

### Spacing
- The missing checks line causes the active timeline row to be ~20px shorter than Lovable, potentially making the entire preview card shorter during processing steps.

### Layout
- No structural difference. Grid proportions, breakpoints, and wrapping behavior are identical.

### Colors
- `text-white` vs `text-primary-foreground` in CTA — both resolve to `#FFFFFF`. Source-only semantic difference, no visual delta.
- RiskRing stroke uses `var(--color-success)` vs Lovable's `var(--success)` — same resolved value via different token architecture.

### Borders / Radius / Shadows
- No difference. All Hero borders, radii, and shadows match.

### Icons
- Same Lucide icons at same sizes throughout.

### Alignment
- No difference.

### States
- Processing/completion/reset cycle behavior is identical.
- Active-agent highlighting and region highlighting are identical except for the missing checks line.

---

## 8. Animation & Motion Specification

| Animation | Trigger | Initial State | Final State | Duration | Easing | Loop | Priority |
|-----------|---------|---------------|-------------|----------|--------|------|----------|
| BootSplash bar | Mount | scaleX 0 | scaleX 1 | 0.9s | cubic `[0.4,0,0.2,1]` | Once | Exists/match |
| BootSplash fade | 1000ms timeout | opacity 1 | opacity 0 | 0.35s | easeOut | Once | Exists/match |
| Hero copy entrance | Mount | opacity 0, y 8 | opacity 1, y 0 | 0.45s | Library default | Once | Exists/match |
| Preview entrance | Mount | opacity 0, y 14 | opacity 1, y 0 | 0.6s (0.15s delay) | easeOut | Once | Exists/match |
| Metric count-up | Viewport entry (once) | 0 | Target value | 900ms | Cubic-out `1-(1-p)³` | Once | Exists/match |
| Demo step advance | Previous step timeout | step N | step N+1 | 850ms interval | Instant state change | Yes (7.35s cycle) | Exists/match |
| Completion hold | Step 7 reached | Complete state | Reset to step 0 | 1400ms hold | Instant reset | Yes | Exists/match |
| Progress bar scale | Step change | Previous fraction | `(step+0.5)/9` or 1 | 0.5s (0 on reset) | easeOut | Per step | Exists/match |
| Scan line sweep | Steps 0-2 | top 0% | top 100% | 1.6s | easeInOut | Infinite while mounted | Exists/match |
| Region highlight | Step change | border-transparent | border-primary bg-primary-subtle | 300ms | CSS transition | Per step | Exists/match |
| Result card swap | Step 6→7 / 7→0 | Opacity/y swap | Crossfade | **Needs verification** | Library default | Per cycle | **P3** |
| Risk ring fill | Completion mount | 0% | 24% | 1.2s | easeOut | Per cycle | Exists/match |
| Percent count-up | Completion mount | 0 | 24 | 1.2s | easeOut | Per cycle | Exists/match |
| Timeline connector fill | Agent completes | scaleY 0 | scaleY 1 | 0.45s | easeOut | Per agent | Exists/match |
| Active agent pulse | Agent active | scale 1, opacity 0.5 | scale 1.45, opacity 0 | 1.8s | easeInOut | Infinite while active | Exists/match |
| Check spring | Agent completes | scale 0.3, opacity 0 | scale 1, opacity 1 | Spring 500/26 | Spring | Once per agent | Exists/match |
| Activity expand | Agent becomes active | height 0 | height auto | 0.25s | easeOut | Per agent | Exists/match |
| **Checks remaining** | Agent active + checks data present | **Not rendered** | 11px "N checks remaining" | Part of activity expand | — | Per agent | **P1 — MISSING** |
| Footer item entrance | New items keyed | opacity 0 | opacity 1 | Library default | — | Per step | Exists/match |
| Active ping | Agent active in footer | ping animation | — | 1s cubic | Infinite | Exists (motion-safe gated) |
| Nav hover | Mouse enter | text-muted-foreground | text-foreground | 150ms | CSS transition | — | Exists/match |
| **Nav underline** | Mouse enter | **scaleX 0** | **scaleX 1** | **0.25s ease** | CSS transition | — | **P2 — EXTRA (remove)** |
| CTA hover | Mouse enter | bg-primary | bg-primary-hover | 150ms | CSS transition | — | Exists/match |
| CTA active | Mouse down | scale 1 | scale 0.98 | Instant | — | — | Exists/match |

---

## 9. Interaction Specification

### CTA behavior
- Primary "Launch console": `<Link to="/dashboard">` with ArrowRight icon that translates 3px right on group hover. **Must remain `/dashboard`.**
- Secondary "How it works": `<a href="#how-it-works">` with smooth scroll (current) or instant jump (Lovable). **Keep smooth.**

### Hover
- Nav links: text color change. Current additionally shows animated underline (gap vs Lovable).
- CTAs: background color change + `active:scale-[0.98]`.
- No hover interactions on the preview card or its contents.

### Focus
- Current provides global `focus-visible` ring via `index.css`. Lovable only defines rings on selected controls. **Keep current behavior.**

### Demo interaction
- The preview is non-interactive: no click, hover, or keyboard actions. It is a self-advancing timer-driven loop.
- Activity footer uses `aria-live="polite"` — announces changes to screen readers (shared concern: rapid 850ms announcements).

### Scroll behavior
- Current smooth-scrolls anchor navigation. Lovable jumps. **Keep smooth.**
- Sections below Hero use `scroll-mt-16` for sticky-header offset. **Exists and matches.**

### Responsive interaction
- Below `md` (768px): desktop nav links hidden, no mobile menu replacement. CTA remains visible.
- Below `lg` (1024px): Hero becomes single-column, preview stacks below copy.
- Below `sm` (640px): preview card stacks document above timeline.
- Footer activity wraps; long descriptions hidden below `lg`.

---

## 10. Data / Functionality Mapping

| Element | Data Source | Current Functionality | Lovable Mock? | Implementation Rule |
|---------|-------------|-----------------------|---------------|---------------------|
| Eyebrow text | Hardcoded | Static copy | Same static copy | Keep as-is |
| H1 headline | Hardcoded | Static copy | Same | Keep |
| Body text | Hardcoded | Static copy | Same | Keep |
| CTA target | `/dashboard` | Real route | `/console` (Lovable route) | **Keep `/dashboard`** |
| Metrics (27.4s, 38, 9) | Hardcoded marketing | Count-up animation | Same values | Keep |
| Preview claim rows | `landingDemo.js` DEMO_AGENTS regions + DEMO_CLAIM | Marketing fixture | `data.ts` AGENTS/CLAIM | **Keep Indian data** |
| Preview timeline | `DEMO_AGENTS.slice(0,7)` via AgentTimeline | Marketing loop | `AGENTS.slice(0,7)` | Keep; add `checks` field for visual parity |
| Progress prop | Not passed | — | `progress={0.4}` | **Add to WorkspacePreview** |
| Risk ring value | `DEMO_CLAIM.risk` (24) | Animated gauge | `CLAIM.risk` (24) | Keep (same value) |
| Risk label | `DEMO_CLAIM.riskLabel` | Static text | Same | Keep |
| Activity footer agents | `DEMO_AGENTS[step-2..step+1]` | Timer-driven | Same | Keep |
| Completion text | "9 / 9 agents · 27.4s" | Static | Same | Keep |

**No Hero element uses real backend data, `useClaimAgent`, or `POST /process`.** All Hero data is marketing-only.

---

## 11. Responsive Plan

| Breakpoint | Behavior | Status |
|------------|----------|--------|
| ≥ 1024px (`lg`) | Two-column `0.8fr 1.2fr`, preview offset right, full nav | **Match** |
| 768–1023px (`md`) | Single-column, desktop nav visible | **Match** |
| 640–767px (`sm`) | Preview splits doc/timeline horizontally | **Match** |
| < 640px | Preview stacks vertically, activity wraps, descriptions hidden | **Match** |
| < 768px (`md`) | Nav links hidden, no mobile menu | **Match** (shared limitation) |

No responsive changes needed for Hero parity. The checks-remaining line may slightly increase card height at narrow widths — verify visually after implementation.

---

## 12. Accessibility Plan

### Keep (current improvements over Lovable)
- Global `focus-visible` ring via `index.css`
- `motion-safe:animate-ping` (Lovable uses unconditional ping)
- Reduced-motion media query for CSS animations/transitions
- Smooth scroll for anchor navigation

### Shared concerns (not regressions, but worth noting)
- `aria-live="polite"` on the activity footer receives changes every 850ms — consider debouncing or announcing only on completion
- BootSplash does not inert/aria-hide the page behind it
- Metrics `dd` before `dt` is non-standard `dl` order
- Several small-text elements (footnote at 11px, subtle-foreground on `#F5F5F3`) may not meet WCAG AA normal-text contrast

### Do not introduce
- Do not remove `motion-safe:` gating
- Do not remove the global focus-visible ring
- Do not remove reduced-motion handling

---

## 13. Performance Plan

No Hero-specific performance changes are indicated. The existing implementation:

- Cleans up timers on unmount
- Uses `requestAnimationFrame` for count-up
- Uses CSS transitions for color/layout changes where possible
- Limits scan-line mount to steps 0–2

### Shared concern (not a regression)
- The preview loop rerenders every 850ms indefinitely and does not pause when the tab is hidden or the Hero scrolls offscreen. This is identical to Lovable and is not a parity fix, but could be a future optimization.

---

## 14. Implementation Phases

### Phase 1 — Restore checks-remaining detail (P1)

**Objective:** Make the active agent row in the Hero's timeline match Lovable by showing "N checks remaining."

**Files likely affected:**
- `frontend/src/components/landing/landingDemo.js` — add `checks` field to each of the nine `DEMO_AGENTS`
- `frontend/src/components/landing/WorkspacePreview.jsx` — pass `progress={0.4}` to `AgentTimeline`
- `frontend/src/components/claimbitz/AgentTimeline.jsx` — conditionally render checks remaining when `agent.checks` is a number (guard so dashboard agents without `checks` are unaffected)

**Exact changes:**
1. In `landingDemo.js`, add `checks: N` to each agent (values: 3, 4, 5, 4, 3, 4, 2, 2, 1 — matching Lovable `data.ts`)
2. In `WorkspacePreview.jsx`, change `<AgentTimeline agents={...} activeIndex={...} compact />` to include `progress={0.4}`
3. In `AgentTimeline.jsx`, inside the processing expansion block, add the checks-remaining paragraph only when `typeof agent.checks === 'number'` and `progress` is truthy

**Verification:**
- Landing Hero preview shows "N checks remaining" under each active agent
- Dashboard AgentTimeline is unaffected (no `checks` on real agents)
- Build passes
- Tests pass
- No mock data leaks into dashboard

**Expected result:** Active agent row is ~20px taller, matching Lovable's preview card height during processing.

**Commit message:** `style(landing): restore checks-remaining detail in Hero timeline`

---

### Phase 2 — Remove extra nav underline + update favicon (P2)

**Objective:** Remove the `story-link` underline that Lovable does not render; replace the stale indigo favicon.

**Files likely affected:**
- `frontend/src/index.css` — remove the `.story-link > span::after` block (lines ~170–188)
- `frontend/public/favicon.svg` — replace indigo shield with copper "C" brand mark

**Exact changes:**
1. Delete the `story-link > span::after` and `story-link:hover > span::after` CSS rules
2. Replace the favicon SVG fill from `#4F46E5` to `#C76A2B` (the shield can remain; alternatively replace with the brand "C" square)

**Verification:**
- Nav links on hover only change text color, no underline
- Browser tab shows copper favicon
- No visual regression elsewhere

**Commit message:** `style(landing): remove extra nav underline and update favicon to copper`

---

### Phase 3 — Optional font-fallback alignment (P3)

**Objective:** Align font fallback stacks for pixel-identical rendering if primary fonts fail.

**Files likely affected:**
- `frontend/src/index.css` — update `--font-sans` and `--font-mono` fallback lists
- `frontend/index.html` — optionally adjust loaded font weights to match Lovable (400–700 instead of 300–900)

**This phase is optional** and should only proceed if visual testing reveals fallback-font differences. Mark as deferred unless evidence appears.

**Commit message:** `style(global): align font fallback stacks with Lovable reference`

---

## 15. Explicitly DO NOT IMPLEMENT

The following Lovable-only behaviors must NOT enter the ClaimBitz application:

- ❌ `data.ts` as any data source (AGENTS, CLAIM, OUTCOMES, RISK_SIGNALS, OUTPUT_CONTENT, LOGS)
- ❌ Lovable's nine-agent model replacing the real eight-agent model on the dashboard
- ❌ Fake processing timers, elapsed time, or scenario switching
- ❌ Fake risk scores, claim data, or OCR results on the dashboard
- ❌ US names/amounts replacing Indian demo data
- ❌ `/console` route replacing `/dashboard`
- ❌ TanStack Start/Router/Nitro/React 19 migration
- ❌ Lovable SSR shell, route metadata, or error boundaries replacing Vite SPA behavior
- ❌ Unconditional `animate-ping` replacing `motion-safe:animate-ping`
- ❌ Removal of the global `focus-visible` ring
- ❌ Removal of the reduced-motion media query
- ❌ Any inert/non-functional control (Download, Assign Reviewer) that has no real backend behavior

---

## 16. Regression Protection

The following must remain untouched and verified after every phase:

- `frontend/src/hooks/useClaimAgent.js` — not modified
- `frontend/src/pages/Dashboard.jsx` — not modified
- `frontend/src/pages/SubmissionPage.jsx` — not modified
- `frontend/src/pages/InsurerPortalPage.jsx` — not modified
- All four routes (`/`, `/dashboard`, `/submission`, `/portal/:insurerId`) remain functional
- Real `POST /process` behavior unchanged
- `VITE_API_BASE_URL` behavior unchanged
- Demo mode toggle and demo payload unchanged
- `localStorage` keys `binaryblitz.latestClaim` and `binaryblitz.lastApplicationNumber` unchanged
- Upload, drag/drop, reset, copy, Submit, and portal auto-fill behavior unchanged
- Dashboard AgentTimeline must not render checks-remaining (guard on `agent.checks`)

---

## 17. Verification Checklist

After each phase:

- [ ] Desktop (1440px): Hero layout correct, preview card correct height, checks visible
- [ ] Laptop (1280px): same
- [ ] Tablet (768px): single-column Hero, preview stacks, no overflow
- [ ] Mobile (390px): preview stacks document/timeline, no horizontal overflow
- [ ] Hover: nav links change color only (no underline after Phase 2); CTAs change background
- [ ] Focus: visible copper ring on keyboard navigation
- [ ] Keyboard: tab through header → CTAs; no focus trap in preview
- [ ] Reduced motion: CSS animations/transitions disabled; preview timer still runs (shared limitation)
- [ ] Animation timing: scan, highlights, risk ring, count-up all function
- [ ] No horizontal overflow at any width
- [ ] No console errors
- [ ] `npm run build` passes
- [ ] `npx vitest run` passes (10/10)
- [ ] `/` loads correctly
- [ ] `/dashboard` loads and functions (empty/demo/upload/process/complete/error/reset)
- [ ] `/submission` loads
- [ ] `/portal/aetna` loads
- [ ] No Lovable mock data imports in dashboard (`grep` for `landingDemo`, `DEMO_AGENTS`, `DEMO_CLAIM`, `data.ts`)
- [ ] Favicon shows copper mark in browser tab
- [ ] Backend API behavior unchanged

---

## 18. Definition of Done

Hero parity is complete when:

1. The WorkspacePreview's active agent row shows "N checks remaining" matching Lovable's exact 11px styling
2. The navigation links hover without an animated underline (matching Lovable's text-only hover)
3. The favicon is copper-branded (not indigo)
4. All items in the verification checklist above pass
5. No Lovable mock/fixture data appears outside `components/landing/`
6. Dashboard functionality is unaffected
7. Build and tests pass
8. Changes are committed on `feature/claimbitz-final-lovable-parity`, not on `main`

---

### Recommended Next Implementation Step

**Phase 1 only:** Restore the checks-remaining detail in the Hero timeline.

This is the single visual gap with the most impact (changes active-row height and preview card density). It affects only three files (`landingDemo.js`, `WorkspacePreview.jsx`, `AgentTimeline.jsx`), requires no new dependencies, and is fully guarded from the dashboard by the conditional `typeof agent.checks === 'number'` check.

Do not implement Phases 2 or 3 in the same commit. Each phase should be a separate, independently verifiable change.
