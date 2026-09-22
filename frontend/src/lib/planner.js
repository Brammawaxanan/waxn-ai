export const interests = [
  "Nature",
  "Adventure",
  "History",
  "Photography",
  "Food",
  "Relaxation",
  "Family",
  "Shopping",
];
export const featuredIds = [
  "PLC0003729",
  "PLC0008963",
  "PLC0012824",
  "PLC0008946",
  "PLC0004046",
];

export function rankPlaces(places, selected) {
  const vector = interests.map((name) => (selected.includes(name) ? 1 : 0.15));
  const magnitude = Math.hypot(...vector);
  return places
    .map((place) => {
      const norm = Math.hypot(...place.scores);
      const similarity = norm
        ? place.scores.reduce((sum, value, i) => sum + value * vector[i], 0) /
          (norm * magnitude)
        : 0;
      return {
        ...place,
        match: similarity,
        score:
          similarity * 0.65 + place.quality * 0.2 + place.dataQuality * 0.15,
      };
    })
    .sort((a, b) => b.score - a.score);
}

export function distance(a, b) {
  const rad = Math.PI / 180;
  const h =
    Math.sin(((b.lat - a.lat) * rad) / 2) ** 2 +
    Math.cos(a.lat * rad) *
      Math.cos(b.lat * rad) *
      Math.sin(((b.lng - a.lng) * rad) / 2) ** 2;
  return 6371 * 2 * Math.asin(Math.sqrt(Math.min(1, h)));
}

export function estimateRoute(stops) {
  const km =
    stops.slice(1).reduce((sum, stop, i) => sum + distance(stops[i], stop), 0) *
    1.3;
  return {
    km,
    minutes: (km / 35) * 60,
    estimated: true,
    coordinates: stops.map((p) => [p.lat, p.lng]),
  };
}

export function buildTrip(places, district, days, preferences) {
  const ranked = rankPlaces(
    places.filter((p) => p.district === district),
    preferences,
  );
  const available = ranked.filter((p) =>
    ["attraction", "activity"].includes(p.category),
  );
  const result = [];
  const used = new Set();
  for (let day = 0; day < days; day++) {
    const seed = available.find((p) => !used.has(p.id));
    if (!seed) {
      result.push([]);
      continue;
    }
    const stops = [seed];
    used.add(seed.id);
    for (let slot = 0; slot < 2; slot++) {
      const next = available
        .filter((p) => !used.has(p.id) && distance(seed, p) <= 25)
        .sort(
          (a, b) =>
            b.score -
            distance(stops.at(-1), b) / 70 -
            (a.score - distance(stops.at(-1), a) / 70),
        )[0];
      if (next) {
        stops.push(next);
        used.add(next.id);
      }
    }
    const food = ranked
      .filter(
        (p) =>
          p.category === "food" && !used.has(p.id) && distance(seed, p) < 10,
      )
      .sort((a, b) => distance(seed, a) - distance(seed, b))[0];
    if (food) {
      stops.splice(2, 0, food);
      used.add(food.id);
    }
    result.push(stops.map((p) => p.id));
  }
  return result;
}

export function directionsUrl(stops, mode = "driving") {
  if (!stops.length) return "";
  const coordinate = (p) => `${p.lat},${p.lng}`;
  const params = new URLSearchParams({
    api: "1",
    destination: coordinate(stops.at(-1)),
    travelmode: mode,
  });
  if (stops.length > 1) params.set("origin", coordinate(stops[0]));
  if (stops.length > 2)
    params.set("waypoints", stops.slice(1, -1).map(coordinate).join("|"));
  return `https://www.google.com/maps/dir/?${params}`;
}

export function readSaved() {
  try {
    const data = JSON.parse(localStorage.getItem("waxn-trip-v1"));
    if (
      data &&
      Array.isArray(data.days) &&
      data.days.length >= 1 &&
      data.days.length <= 7 &&
      data.days.every(
        (day) =>
          Array.isArray(day) &&
          day.length <= 5 &&
          day.every((id) => typeof id === "string"),
      ) &&
      Array.isArray(data.saved) &&
      data.saved.every((id) => typeof id === "string") &&
      typeof data.district === "string"
    )
      return {
        ...data,
        date:
          typeof data.date === "string" &&
          /^\d{4}-\d{2}-\d{2}$/.test(data.date) &&
          Number.isFinite(Date.parse(`${data.date}T12:00:00`))
            ? data.date
            : "",
      };
  } catch {
    /* Unavailable storage or an old/corrupt saved trip starts fresh. */
  }
  return null;
}
