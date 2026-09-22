# Project analysis and frontend integration

## Existing architecture

The repository is a Sri Lanka travel recommendation and itinerary prototype. Its main assets are the offline Python pipeline and locally generated data. The `backend/`, `docs/`, and `notebooks/` directories initially had no implementation. The frontend started as the Vite/React welcome page, with empty itinerary/map component files.

| Area | Existing purpose | Frontend integration |
| --- | --- | --- |
| `data/raw/` | Tourism accommodation/activity spreadsheets, place/review CSVs, OSM GeoJSON | Original inputs retained; no direct browser parsing |
| `ml/data_cleaning/` | Normalize source fields, unify places, validate data, fuzzy-match reviews, enrich coordinates | Use the completed candidate export |
| `ml/feature_engineering/` | Keyword-derived interest scores, quality filters, coordinate and eligibility checks | Export eight interest scores and quality fields |
| `ml/recommendation/` | District/city/category filters; cosine similarity plus weighted quality ranking | Equivalent ranking formula implemented in browser |
| `ml/trip_planner/` | Scheduling, KMeans grouping, nearest-neighbor route order, constrained replacement, OSRM routing | Browser proximity planner and live map; Python pipelines remain independent |
| `data/processed/` | Intermediate tables, candidate inventory, itinerary and routing outputs | `waxn_final_candidates.csv` is the single browser data source |
| `frontend/` | React 19 / Vite app | Complete destination discovery, editable trip planning, favorites, maps, directions, export |

## Important findings

1. **There is no backend API.** Python modules load CSVs directly, some at import time; the app cannot call them as HTTP services. The frontend is deliberately useful as a static deployment, using a repeatable data-export step and client-side ranking. It does not imply that an online AI service is running.
2. **The candidate inventory has 16,799 eligible records.** Categories include attractions, activities, accommodation, food, and shopping. Coordinates and eight interest features support map and recommendation functions. Many places have no reviews; the UI shows honest unrated states.
3. **The recommendation model is primarily rule-based features with cosine similarity.** Nature/adventure/history/etc. features are keyword-derived; recommendation weights are 0.65 preference similarity, 0.20 quality, 0.15 data quality. The frontend preserves those weights, while its grouping heuristic is distinct from the Python KMeans planner.
4. **Routing artifacts are inconsistent in freshness and provenance.** The old `frontend/public/data/waxn_osrm_routes.json` contains a different itinerary from `data/processed/waxn_final_routes.json`. The latter has `haversine_fallback` geometry. The constrained report contains road-distance figures that differ from these fallback figures. Treating those lines as verified roads would mislead users. The new frontend instead requests a route for the actual current stop order, identifies estimates, and exports places rather than stale route metrics.
5. **The Python requirements file is incomplete for the full pipeline.** `requests` and `scikit-learn` are imported by routing/recommendation/planning modules but not listed in `requirements.txt`. This does not affect the independent frontend export script, which uses the Python standard library.
6. **Some data quality issues survive eligibility filtering.** There are generic place names, duplicate-looking attractions, and inconsistent district spellings such as Monaragala/Moneragala. Coordinates do not establish exact entrances or road accessibility. These deserve a separate data-cleaning pass before promising fully verified recommendations.
7. **There was pre-existing local work.** Python, route, and candidate changes were present at the start. This task preserves that work and adds frontend integration rather than rewriting the pipeline.

## Implemented frontend

The design uses warm ivory surfaces, green accents, destination photography, a concise trip overview, a discovery section, and a split itinerary/map planner. Responsive layouts stack the map and itinerary on small screens. Users can create trips for available districts, specify dates and interests, save favorites, search/filter, add/remove/reorder places, view daily route estimates, open Google Maps navigation links, and export JSON.

Persistence is local to the browser. There is no account system or server-side synchronization. The UI includes data-load retry, empty search/day states, malformed saved-state recovery, map tile failure messaging, routing timeouts/fallbacks, and accessible modal/keyboard controls.

OpenStreetMap/Leaflet avoids API-key setup. Google Maps is used through ordinary directions URLs. OSRM provides best-effort driving geometry; straight-line fallback connections are visibly dashed and labeled approximate.

## Next integration steps

- Expose the Python recommender and constrained planner behind a small API with validated request/response schemas, deterministic data versions, and background route caching.
- Complete and verify Python dependencies in an isolated environment; add integration tests for empty districts, scarce candidates, constraint failures, and OSRM outages.
- Reconcile district aliases, deduplicate destinations, and verify coordinates/entrances before adding stronger travel guarantees.
- Return route provenance and constraint status alongside each itinerary. Do not silently substitute straight lines for road routes.
- For larger deployments, replace public demo map/routing endpoints with suitable hosting and move the 3.9 MB full inventory to indexed/paginated API search or district bundles.
- Add account-based trip synchronization only when a backend/auth scope is defined. Keep local export available.

## Validation performed

Production bundling, ESLint, and six Node test cases pass. Tests cover all exported locations and all available districts. The local development server starts successfully. Browser automation was unavailable (no connected browser and a failed native UI connection), so interactive visual/browser verification remains a documented limitation rather than an asserted result.
