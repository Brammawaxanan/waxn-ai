# Waxn — Sri Lanka trip planner

A responsive React 19 / Vite frontend for the project's Sri Lanka travel dataset. Leaflet renders an interactive OpenStreetMap map. No Google Maps SDK, billing account, or API token is required.

## Run

```sh
cd frontend
npm install
npm run dev
```

Open the URL printed by Vite. Requires a Node version supported by Vite 8 (Node 20.19+ or 22.12+).

```sh
npm run build       # production output in dist/
npm run preview     # preview the production build
npm run lint
npm test
npm run data:export # refresh public/data/places.json from the Python pipeline output
```

The implementation environment had a certificate problem with registry.npmjs.org. Installation succeeded using the HTTPS mirror with `npm install --registry=https://registry.npmmirror.com`. No certificate checks were disabled and no global npm configuration was changed.

## What works

- Browse 16,799 eligible, geographically validated places from the existing dataset.
- Search by place, category, or district name within the current destination; filter sights, food, stays, or all places.
- Create a one-to-seven-day itinerary for any district represented in the data, with optional dates and eight interests.
- Rank candidates using the Python recommender's cosine similarity and 65/20/15 preference/quality/data-quality weights. Daily grouping uses a browser-side proximity heuristic, not Python KMeans or the constrained replanner.
- Save favorite places, add up to five stops per day, remove and reorder stops, switch days, and export the full itinerary as JSON.
- Persist the current trip and saved places to localStorage, with graceful recovery from malformed state and a storage failure notice.
- View numbered interactive map markers, select stops, zoom, fit all stops, and open a whole day or individual place in Google Maps.
- Fetch OSRM driving geometry, distance, and travel time. Requests are debounced, aborted when stale, timed out after ten seconds, and cached in memory.
- If routing fails, show a dashed line and clearly labeled travel estimates (Haversine × 1.3, at 35 km/h, matching the existing Python fallback).
- Native accessible planning dialog, keyboard controls, focus indicators, reduced-motion support, loading/error/empty states, and mobile layouts.

## Data and integration

`python3 scripts/export-data.py` reads `../data/processed/waxn_final_candidates.csv` using only Python's standard library. It exports public destination fields, verifies Sri Lanka coordinate bounds, and excludes records marked ineligible or bad-name. Review scores are shown only when present; missing ratings are never manufactured.

The app currently works without a backend. It does **not** execute Python models, enforce the Python 70 km / 150 min daily constraints, provide live availability, validate opening hours, or make bookings. Existing CSV/JSON artifacts and Python scripts are unchanged. See `../docs/project-analysis.md` for integration findings and follow-up work.

Destination photography is bundled locally; source/license credits are in `public/images/credits.html`. Only specifically photographed destinations use photos; other places use a deliberate scenic placeholder.

## Maps and external services

- [Leaflet](https://leafletjs.com/reference.html) provides browser map controls.
- [OpenStreetMap standard tiles](https://operations.osmfoundation.org/policies/tiles/) are requested over HTTPS with visible attribution. No tile prefetching, bulk downloading, or offline tile cache is implemented. Public tiles are best-effort, not an unlimited production hosting service; select a suitable provider before scaling usage.
- [OSRM](https://project-osrm.org/docs/v5.24.0/api/) is used for driving estimates. The public demo server has no availability guarantee. Self-host or configure a supported service for production traffic.
- [Google Maps URLs](https://developers.google.com/maps/documentation/urls/guide) provide directions without an API key. Five stops keep intermediate waypoints to three, including mobile URL compatibility. Single-place links allow Google Maps to determine the starting point.
- Google Fonts serves DM Sans and Manrope, with system font fallbacks.

Map tiles and driving routes require internet access. Basemap failures leave the itinerary and directions links available. An estimate is not turn-by-turn navigation; confirm road access and final walking approaches in a navigation app.

## Verification

`npm test` checks exported IDs/coordinates/features, itinerary constraints across all districts, interest ranking, directions encoding, estimate behavior, and corrupt-storage recovery. `npm run lint` and `npm run build` verify code and production bundling. Interactive browser QA was blocked by unavailable browser automation in the implementation environment; manually verify desktop/mobile rendering and live tiles before deployment.
