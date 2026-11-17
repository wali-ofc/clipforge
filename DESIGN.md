---
name: ClipForge
description: Local-first video clipping — a warm paper workshop for making short vertical clips
colors:
  paper-ground: "#f2efe7"
  paper-sheet: "#fbfaf6"
  paper-sunk: "#eae5d9"
  ink: "#16150f"
  ink-soft: "#555045"
  ink-muted: "#6b6556"
  rule: "#d9d2c4"
  rule-strong: "#bcb3a0"
  signal: "#b8412a"
  signal-deep: "#9c3522"
  signal-wash: "#fbefea"
  ok: "#3e6b46"
  warn: "#8a6417"
  bad: "#9a3024"
typography:
  display:
    fontFamily: "Archivo, ui-sans-serif, system-ui, sans-serif"
    fontSize: "clamp(2.25rem, 4.4vw, 3.5rem)"
    fontWeight: 800
    lineHeight: 0.98
    letterSpacing: "-0.05em"
  title:
    fontFamily: "Archivo, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.0625rem"
    fontWeight: 700
    lineHeight: 1.3
    letterSpacing: "-0.025em"
  body:
    fontFamily: "Archivo, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 400
    lineHeight: 1.6
  label:
    fontFamily: "Roboto Mono, ui-monospace, monospace"
    fontSize: "0.6875rem"
    fontWeight: 500
    lineHeight: 1.4
    letterSpacing: "0.14em"
rounded:
  sm: "2px"
  md: "3px"
spacing:
  tight: "0.5rem"
  base: "1rem"
  section: "2.5rem"
components:
  button-primary:
    backgroundColor: "{colors.signal}"
    textColor: "#fffaf6"
    rounded: "{rounded.sm}"
    padding: "0.6rem 1.05rem"
  button-ghost:
    backgroundColor: "{colors.paper-sheet}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    padding: "0.6rem 1.05rem"
  field:
    backgroundColor: "{colors.paper-sheet}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    padding: "0.7rem 0.8rem"
  badge:
    backgroundColor: "{colors.paper-sunk}"
    textColor: "{colors.ink-soft}"
    rounded: "{rounded.sm}"
    padding: "0.2rem 0.45rem"
  sheet:
    backgroundColor: "{colors.paper-sheet}"
    rounded: "{rounded.md}"
    padding: "1.25rem"
---

# Design System: ClipForge

## Overview

**Creative North Star: "The Workshop Sheet."**

ClipForge looks like a well-run bench, not a software dashboard. The ground is warm gray paper, type is near-black and dense, hairline rules divide work into legible bands, and a single vermilion signal marks the actions and the live state. The reference world is the print shop and the editing room: registration marks, timecode, spec strips, ruled ledgers, and measured rulers. Nothing glows, nothing floats in a colored halo, and no section announces itself with a small uppercase label above a heading.

The system is deliberately quiet in its expression and loud in its information. Clip scores, tracking fallbacks, timecodes, and job stages are printed plainly, because the product's promise is honesty about what the local machine actually did. Motion is limited to one authored moment: the tally pulse on a live state, plus the measured movement of the progress ruler as data changes. Everything else is a fast state transition from an already-visible default.

**Key Characteristics:**
- Paper ground, sheet surfaces, hairline rules, near-square corners
- One signal color doing real jobs: action, active tool, tally, progress, fallback warning
- Self-hosted Archivo for words, Roboto Mono for measurements
- Ruler, registration marks, and spec rows as the recurring structural vocabulary
- Desktop sidebar / mobile top nav; one coherent system across all four screens

## Colors

One accent on neutral paper; state colors are earthy and only ever carry meaning.

### Primary
- **Signal Vermilion** (#b8412a): The only accent. Primary actions, active tool marker, tally square, progress fill, and the source badge. Its scarcity is the point.

### Neutral
- **Paper Ground** (#f2efe7): The application field; flat, warm, slightly gray rather than yellow cream.
- **Paper Sheet** (#fbfaf6): Panels, inputs, and raised surfaces.
- **Paper Sunk** (#eae5d9): Ruler track, code/specimen strips, de-emphasized chips.
- **Ink** (#16150f): Headlines and primary text.
- **Ink Soft** (#555045): Body copy and control labels.
- **Ink Muted** (#6b6556): Metadata and mono labels; preserves contrast on paper.
- **Rule / Rule Strong** (#d9d2c4 / #bcb3a0): Hairline dividers and control strokes.

### State
- **Field Green** (#3e6b46): Completed states and successful tracking.
- **Ochre** (#8a6417): Degraded or fallback states.
- **Deep Red** (#9a3024): Failure states, distinct from the signal accent by darkness and icon.

**The One Signal Rule.** Vermilion never decorates. It appears on an action, an active state, a measurement, or a warning — and nowhere else.

## Typography

**Display Font:** Archivo (self-hosted variable, with system sans fallback)
**Body Font:** Archivo
**Label/Mono Font:** Roboto Mono (self-hosted variable)

**Character:** Archivo's industrial grotesque carries weight without editorial preciousness; its expanded width gives headlines a printed-sign presence. Roboto Mono is reserved for data, labels, timecodes, and identifiers — never used as a "technical" costume.

### Hierarchy
- **Display** (800, clamp(2.25rem, 4.4vw, 3.5rem), 0.98, -0.05em): Two-line landing statements only.
- **Display Small** (800, clamp(1.9rem, 3.4vw, 2.6rem), 1.02, -0.045em): Secondary page statements.
- **Title** (700, 1.0625rem, 1.3, -0.025em): Section and card headings.
- **Body** (400, 0.9375rem, 1.6): Lede and paragraph text; measure capped near 66ch.
- **Label** (500, 0.6875rem, 0.14em, uppercase): Metadata, controls, timecodes.

**The Heading Carries It Rule.** No eyebrow or kicker above a heading. If a heading needs a label to make sense, rewrite the heading.

## Layout

A 246px left rail on desktop becomes a compact two-tab top nav below 1024px. Content uses a centered 1180px measure with 20–32px gutters. The primary surfaces use a two-column field: editorial text on the left, the working sheet on the right, collapsing to a single stack on mobile. Sections are separated by full-width hairlines rather than whitespace alone; data is arranged in 150px-label / value spec rows. Density is high but rhythmic: tight groups, generous separation between sections, and more space above a heading than below it.

## Elevation & Depth

Flat by default, with one ambient stack on primary sheets: `0 1px 2px rgba(22,21,15,0.05), 0 18px 36px -28px rgba(22,21,15,0.4)`. Depth comes mainly from paper tone, hairlines, and the single inset of a sheet against the ground. Dividers carry structure; shadows never carry a colored halo.

**The Flat-By-Default Rule.** A sheet is flat until it is a primary working surface; cards inside a sheet use borders only.

## Shapes

Corners are almost square: 2px for controls, chips, and cards; 3px for sheets. Borders are 1px hairlines. The recurring silhouettes are the ruled band, the near-square sheet, the crop-mark bracket, and the ruler track. No pill-shaped buttons, no glass, no offset block shadows.

## Components

### Buttons
- **Shape:** Near-square (2px), 42px minimum height, bold 0.8125rem label.
- **Primary:** Signal vermilion with off-white text; hover deepens to #9c3522; active translates 1px; disabled becomes paper-300 with muted ink.
- **Ghost / Quiet:** Paper sheet with a rule-strong stroke, or borderless text; used for secondary and navigation actions.
- **Danger:** Paper ground, deep-red stroke and text, red wash on hover.

### Badges
- Monospace, uppercase, 0.625rem, hairline stroke, 2px radius. Tones: neutral, ok, warn, bad, accent. Used for state, score, and tracking status.

### Sheets
- Paper-sheet ground, 1px rule border, 3px radius, 1.25rem body padding, ruled head. The container for every primary work area.

### Fields and dropzones
- Fields: paper-sheet ground, rule-strong stroke, 2px radius; focus shifts the stroke to signal and adds a 3px signal-wash ring.
- Dropzones: dashed rule-strong stroke, paper-50 ground, four registration crop marks; dragging switches to a solid signal stroke and signal-wash ground.

### Ruler (signature)
- An 8px track of paper-sunk with 10% tick marks; a vermilion fill and a 2px ink playhead at the current value. Used for upload progress and job progress, and as a tick band under clip timecodes.

### Navigation
- Desktop: left rail, wordmark and tally footer, active tool marked by a 3px vermilion bar. Mobile: top bar with logo and a two-tab ruled strip, active tab on a signal wash.

## Do's and Don'ts

### Do:
- **Do** use the ruler for anything measured — progress, timecode, duration.
- **Do** use Roboto Mono only for data, labels, and identifiers, with tabular numerals.
- **Do** call out every tracking fallback in plain language on the clip card.
- **Do** theme browser surfaces: selection, caret, focus ring, and scrollbars all come from the palette.

### Don't:
- **Don't** use a decorative fixed-cell grid background; structure comes from rules and rulers.
- **Don't** stack icon-plus-heading-plus-text cards as a page structure.
- **Don't** put an eyebrow label above a heading or number sections that carry no sequence.
- **Don't** use gradient text, glass, neon glow, or hard offset block shadows.
- **Don't** imply cloud processing, accounts, or virality scoring anywhere in the interface.
