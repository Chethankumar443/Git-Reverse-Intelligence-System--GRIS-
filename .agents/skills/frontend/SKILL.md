---
name: frontend-guidelines
description: Custom guidelines for building the KSP Crime Intelligence Copilot frontend using Astro.js, React, Tailwind CSS v4, and Vercel AI SDK.
---

# Frontend Guidelines - KSP Crime Copilot

This skill enforces best practices and constraints when working on the KSP Crime Intelligence Copilot frontend.

## Tech Stack Rules
1. **Framework:** Astro.js for static/SSR routing. React for interactive components (Islands).
2. **Hydration:** Always load interactive React components in Astro using `client:load` or `client:only="react"` directives.
3. **Styling:** Tailwind CSS v4. No `tailwind.config.js` exists. Theme customizations, spacing, and utilities must be defined directly in `src/styles/globals.css` using the `@theme` directive.
4. **AI UI Components:** Use Vercel AI SDK (`ai` and `@ai-sdk/react`) to connect to `/api/assistant/query` using Server-Sent Events (SSE) streaming.
5. **Icon Library:** Lucide React (`lucide-react`).

## Design Language Defaults (from docs/DESIGN.md)
1. **Canvas:** Stark white canvas background (`#ffffff`).
2. **Cobalt Blue (#0064e0):** Reserved exclusively for in-product purchase, checkout, and primary actions inside details/commerce flows (e.g., "Add to Cart", "Configure", "Pre-order", "Download PDF", "Query Assistant").
3. **Ink Button (#000000):** Used for marketing/nav primary buttons.
4. **Pill Shapes:** Every button, tab, badge, and search input must use `rounded-full` (`100px` radius).
5. **Corner Softening:** Cards containing product or key showcase elements must use `rounded-xxxl` (`32px` radius). Tighter thumbnails or selectors use `rounded-lg` (`8px`) or `rounded-xl` (`16px`).
6. **Typography:** Outfit/Montserrat fallbacks for Optimistic VF. Enable OpenType features `ss01` and `ss02` for all display titles and h1-h6 headings (`font-feature-settings: "ss01" on, "ss02" on`).
7. **Elevation:** Keep elevation flat. Use borders (`1px solid var(--color-hairline-soft)`) rather than shadows for static cards. Only use sticky-rail-shadows (`rgba(20,22,26,0.3) 0px 1px 4px 0px`) for sticky elements like the bottom bar or right summary rails.
