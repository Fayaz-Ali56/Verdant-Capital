# Verdant Capital — Studio Design System

## User-facing purpose
A decision-support workspace where judges and analysts can inspect the evidence, model limits and portfolio constraints behind an investment simulation. The system does not execute trades and makes no claims of real-world fraud detection.

## Visual direction
**Editorial decision studio.** A dark, slate-toned operational workspace with restrained mint accents, warm sand for reservations, and coral for risks. Dense technical evidence is presented as a readable editorial finance report, never as a wall of model JSON.

### Tokens

| Role | Color | Purpose |
|---|---|---|
| Canvas | `#0B1416` | Main app background |
| Sidebar | `#101B23` | Controls and configuration |
| Panel | `#16272B` | Important data grouping |
| Main text | `#F0F5EE` | Primary information |
| Secondary text | `#BACCC3` | Supporting details |
| Accent | `#A4E8BF` | Interactive actions and selected state |
| Reserve | `#E9C38D` | Cash reserves, cautions |
| Risk | `#F0A8A8` | Suspicion-raising feature attribution |
| Divider | `rgba(197,222,211,.13)` | Structural separation |

- Display: Georgia / Cambria / serif. UI: Segoe UI / system sans. No remote font is required.
- Corner radius: 9–16px, based on control vs panel.
- Data numerals use tabular-nums to avoid jitter.
- Charts: Plotly dark palettes in `ui/charts.py`, transparent backgrounds.
- CSS: `ui/theme.css`, plus Streamlit dark theme in `.streamlit/config.toml`.

## Information architecture

1. **Investment boardroom** — overview, allocation weights, decision rationale, three specialist cards, material disagreements.
2. **Risk Lab (C02/C06/C13)** — class imbalance, per-seed PR metrics, confusion matrix, three held-out SHAP cases, and editable decision economics with validation-loss curve and held-out policy comparisons.
3. **Market intelligence** — time-stamped historical signals, carbon-ETF forecast and explicitly simulated feedback.
4. **Audit trail** — persisted recommendations, policy reason codes, evidence citations and reproducible commands.

## Accessibility and reliability
- Colored results always include textual labels.
- Dark/light semantic contrast uses a predominantly monochrome vocabulary plus accents.
- Real form controls stay native to Streamlit for keyboard and screen-reader compatibility.
- Visible focus rings, at least 44px primary action height, reduced-motion styling.
- Content stacks on small viewports; charts use Plotly responsivity.
- No external CDN, font dependency, JavaScript injection or third-party UI service.
- `docs/screenshots/` contains actual runtime captures; obsolete static specimens were removed.

## Truth-in-design
- Synthetic data and previews are labeled; there is no market-data API behind a static screenshot.
- Only optimization outputs supply weights and estimates.
- Source limitations and unverified ESG status appear near decisions, not buried in documentation.
- Real and synthetic feedback sources remain distinct.

## Main interaction

A prominent review action leads from mandate to constraints to audit export.
Native workspace radio controls render one view at a time; C13 is selected
independently inside Risk Lab. A real-work skeleton and polite live status
announce review progress. The hero has a short entrance; all motion is removed
under prefers-reduced-motion. Allocation uses a lightweight labeled data graphic
and exact ledger rather than loading a large interactive chart on entry.
