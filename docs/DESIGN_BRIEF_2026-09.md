# Impulse dashboard redesign brief (2026-09-01)

Source: Isaiah's memo 225 plus the UI review in `UI_REVIEW_2026-09-01.md`. Mock-up: Claude Design canvas "Impulse Dashboard Redesign" (three artboards: Home dark, Home light, Settings). Working files for the canvas live with the session that made it; this brief is the durable version.

## Direction

- Left panel stays fixed, the right panel switches. Sidebar: brand, Home, Snippets, Dictionary, then Settings and a listening indicator at the bottom.
- Hot pink `#FF1493` is the only brand color on dark. On light use `#E0117F` for contrast. One small secondary (green `#34D399`) for the live dot only.
- Dark and light themes, nothing else. Appearance control: System / Dark / Light. Delete the neon_dark and midnight_green themes.
- Home is stats-first: words today, speed (wpm), time saved, streak; a 14-day words-per-day bar graph with hover values; recent dictations as time + two-line text + copy on hover.
- Gone: level, XP, rank, avatar, Welcome header, achievements view, challenges view, in-page minimize/close, the Copy Last toolbar row.
- Settings becomes a page, not a modal: General, Audio, Model, Data, License as tabs. Ollama rows hidden unless an endpoint answers.

## Tokens

Dark: bg `#0A0A0B`, sidebar `#0F0F11`, card `#131316`, line `rgba(255,255,255,0.07)`, text `#EDEDEF`, text-2 `#9A9AA3`, text-3 `#6B6B75`.
Light: bg `#F4F4F5`, sidebar `#FAFAFA`, card `#FFFFFF`, line `rgba(0,0,0,0.08)`, text `#18181B`, text-2 `#5F5F68`, text-3 `#8A8A93`.
Radius: 8 px cards, 6 px controls, 5 px kbd. Borders 1 px. No shadows, no blur, no gradients, no noise overlay.
Motion: 120 ms ease-out on background and color; press is `scale(0.98)` over 80 ms. Hover is a background step, never a lift.

## Type

UI: Geist 13 px, line-height 1.45. Labels 12 px. Section titles 14 px / 600. Page title 20 px / 600, tracking -0.02em.
Numbers: Geist Mono, tabular, 22 px / 500 for stat values, 12 px for times and axis labels.
Both from Google Fonts today; bundle them under `ui/assets/fonts` for the shipped app so the dashboard does not depend on the network.

## Controls

Button: 28 px tall, 6 px radius, 1 px line, background step on hover. Primary: solid pink, white text.
Toggle: 34 x 20, pink when on. Segmented control for Appearance. Slider: 3 px track, 14 px thumb.
kbd caps: mono, 1 px border with a 2 px bottom edge.

## Implementation split (one agent each)

1. Tokens and type: replace `styles.css` `:root` themes with the two above, remove every gradient, blur, shadow and the body noise overlay, load Geist and Geist Mono.
2. Shell: sidebar, nav, listening indicator, remove the toolbar row and window buttons, remove the mobile breakpoint's horizontal nav (window is 1100 px now).
3. Home: stat cards from `Bridge.stats`, the 14-day graph from `getChartData(14)`, recent dictations list. Fix the chart reading zero while the feed has data.
4. Snippets and Dictionary views restyled on the new tokens, forms at the top.
5. Settings page with tabs, replacing the modal; hide Ollama rows when unreachable.
6. Removal: achievements and challenges views, their nav entries, XP and level rendering, the related polling.
7. QA: relaunch, screenshot every view at 1100 x 740 in both themes, compare against the canvas, fix drift.
