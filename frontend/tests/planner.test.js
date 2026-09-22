import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import {
  buildTrip,
  directionsUrl,
  distance,
  estimateRoute,
  rankPlaces,
  readSaved,
} from "../src/lib/planner.js";

const places = JSON.parse(
  readFileSync(new URL("../public/data/places.json", import.meta.url)),
);
const byId = new Map(places.map((p) => [p.id, p]));

test("all exported places have unique IDs, valid coordinates and feature vectors", () => {
  assert.equal(places.length, byId.size);
  for (const p of places) {
    assert.ok(p.lat >= 5 && p.lat <= 10 && p.lng >= 79 && p.lng <= 83);
    assert.equal(p.scores.length, 8);
    assert.ok(p.scores.every((n) => Number.isFinite(n) && n >= 0 && n <= 1));
  }
});

test("trip generation stays in its district, avoids duplicate stops and respects daily capacity", () => {
  for (const district of new Set(places.map((p) => p.district))) {
    const days = buildTrip(places, district, 7, ["Nature", "Adventure"]);
    assert.equal(days.length, 7);
    assert.equal(days.flat().length, new Set(days.flat()).size);
    days.forEach((day) => {
      assert.ok(day.length <= 5);
      assert.ok(day.every((id) => byId.get(id)?.district === district));
      if (day.length)
        assert.ok(
          ["attraction", "activity"].includes(byId.get(day[0]).category),
        );
    });
  }
});

test("preference ranking promotes matching places without inventing ratings", () => {
  const fixture = [
    {
      id: "nature",
      scores: [1, 0, 0, 0, 0, 0, 0, 0],
      quality: 0,
      dataQuality: 1,
      rating: null,
    },
    {
      id: "history",
      scores: [0, 0, 1, 0, 0, 0, 0, 0],
      quality: 0,
      dataQuality: 1,
      rating: null,
    },
  ];
  assert.equal(rankPlaces(fixture, ["History"])[0].id, "history");
  assert.equal(rankPlaces(fixture, ["Nature"])[0].id, "nature");
  assert.equal(rankPlaces(fixture, [])[0].rating, null);
});

test("directions preserve stop order and support single destinations", () => {
  const stops = places.slice(0, 5);
  const url = new URL(directionsUrl(stops));
  assert.equal(url.searchParams.get("api"), "1");
  assert.equal(
    url.searchParams.get("origin"),
    `${stops[0].lat},${stops[0].lng}`,
  );
  assert.equal(
    url.searchParams.get("destination"),
    `${stops[4].lat},${stops[4].lng}`,
  );
  assert.equal(url.searchParams.get("waypoints").split("|").length, 3);
  assert.equal(
    new URL(directionsUrl([stops[0]])).searchParams.has("origin"),
    false,
  );
  assert.equal(directionsUrl([]), "");
});

test("fallback is explicitly estimated and has zero travel for zero or one stop", () => {
  assert.equal(estimateRoute([]).km, 0);
  assert.equal(estimateRoute([places[0]]).minutes, 0);
  assert.equal(estimateRoute(places.slice(0, 3)).estimated, true);
  assert.equal(distance(places[0], places[0]), 0);
});

test("corrupt browser state is ignored rather than crashing the planner", () => {
  const old = globalThis.localStorage;
  for (const value of [
    "oops",
    "{}",
    '{"days":[null],"saved":[],"district":"Badulla"}',
  ]) {
    globalThis.localStorage = { getItem: () => value };
    assert.equal(readSaved(), null);
  }
  globalThis.localStorage = {
    getItem: () =>
      JSON.stringify({ days: [[]], saved: [], district: "Badulla" }),
  };
  assert.equal(readSaved().district, "Badulla");
  globalThis.localStorage = old;
});
