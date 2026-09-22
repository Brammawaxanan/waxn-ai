import { useEffect, useState } from "react";
import { estimateRoute } from "./planner";

const cache = new Map();
export function useRoute(stops) {
  const key = stops.map((p) => `${p.lng},${p.lat}`).join(";");
  const [result, setResult] = useState(null);
  useEffect(() => {
    if (stops.length < 2 || cache.has(key)) return;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 10000);
    const debounce = setTimeout(async () => {
      try {
        const response = await fetch(
          `https://router.project-osrm.org/route/v1/driving/${key}?overview=full&geometries=geojson`,
          { signal: controller.signal },
        );
        if (!response.ok) throw new Error("Route unavailable");
        const data = await response.json();
        if (
          data.code !== "Ok" ||
          !data.routes?.[0]?.geometry?.coordinates?.length
        )
          throw new Error("Route unavailable");
        const route = data.routes[0];
        const value = {
          km: route.distance / 1000,
          minutes: route.duration / 60,
          estimated: false,
          coordinates: route.geometry.coordinates.map(([lng, lat]) => [
            lat,
            lng,
          ]),
        };
        cache.set(key, value);
        setResult({ key, value });
      } catch {
        /* Keep clearly labeled local estimates when the public router is unavailable. */
      } finally {
        clearTimeout(timeout);
      }
    }, 500);
    return () => {
      clearTimeout(debounce);
      clearTimeout(timeout);
      controller.abort();
    };
  }, [key, stops]);
  return (
    cache.get(key) ||
    (result?.key === key ? result.value : estimateRoute(stops))
  );
}
