# CityTrack AI — Command Center Frontend

React 19 + TypeScript + Vite + Tailwind CSS 4 frontend for the CityTrack AI traffic intelligence platform.

---

## Stack

| Technology | Version | Purpose |
|---|---|---|
| React | 19.x | UI framework with concurrent rendering |
| TypeScript | 5.x | Type safety + API contract enforcement |
| Vite | 8.x | Dev server + rolldown bundler (2498 modules, ~1.2s build) |
| Tailwind CSS | 4.x | Zero-config CSS engine + Apple design tokens |
| Leaflet + React-Leaflet | 4.x | GIS map, camera markers, trajectory polylines |
| Recharts | 2.x | Area charts, bar charts, pie charts |
| Lucide React | latest | Icon library |
| Axios | 1.x | HTTP API client |

---

## Development

```bash
npm install
npm run dev       # Vite dev server on http://localhost:3000
npm run build     # Production build (tsc -b && vite build)
npm run preview   # Preview production build
```

**Requires** backend running at `http://localhost:8000` (proxied via Vite config). All API calls fall back to rich mock data if the backend is unavailable.

---

## Views

| Route / Tab | Component | Description |
|---|---|---|
| Overview | `OverviewView.tsx` | Live KPI cards, congestion hotspot list, recent activity stream |
| Map | `MapView.tsx` | Leaflet GIS with cameras, roads, trajectories, alerts + CCTV drawer |
| Investigate | `InvestigationView.tsx` | Vehicle forensic dossier + Markov trajectory prediction |
| Alerts | `AlertsView.tsx` | Security alert console with forensic case files |
| Analytics | `AnalyticsView.tsx` | Volume chart, OD matrix, route chains, Greenshields LOS |
| Watchlist | `WatchlistView.tsx` | Vehicle blacklist management |
| Benchmarks | `BenchmarkView.tsx` | Synthetic city + real Indian dataset evaluation |

---

## Design System

Defined in [`src/index.css`](src/index.css):

| Class | Usage |
|---|---|
| `apple-card` | Primary content card — specular bevel, hover lift, spring easing |
| `apple-glass` | Heavy frosted glass panel (`backdrop-blur-2xl`) |
| `apple-subcard` | Nested data group panel |
| `apple-button-primary` | Emerald gradient action button with tactile spring |
| `apple-button-secondary` | Ghost outline button |

**Palette**: Obsidian (`#0e0e12`) + Zinc Charcoal + Tech Emerald (`#10b981`) + Precision Cyan (`#06b6d4`) + Precision Amber (`#f59e0b`) + Security Rose (`#f43f5e`)

**Animations**: `slideUp`, `scaleIn`, `fadeIn`, `shimmer`, `glowPulse` — all using `cubic-bezier(0.16, 1, 0.3, 1)` spring easing

---

## API Client

[`src/services/api.ts`](src/services/api.ts) — Axios singleton with:
- Base URL: `/api/v1` (proxied by Vite to `http://localhost:8000/api/v1`)
- All methods return typed data or fall back to mock data on error
- Field name normalization for backend response differences (e.g. `overall_system_score`, `f1_score`, `average_character_accuracy`)

---

## Types

[`src/types/api.ts`](src/types/api.ts) — Complete TypeScript interfaces matching the FastAPI backend response schemas.
