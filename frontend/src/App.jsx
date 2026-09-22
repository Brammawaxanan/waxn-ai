import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowDown,
  ArrowRight,
  ArrowUp,
  CalendarDays,
  Check,
  ChevronDown,
  Clock3,
  Compass,
  Download,
  Heart,
  Leaf,
  MapPin,
  Mountain,
  Navigation,
  Plus,
  Route,
  Search,
  Sparkles,
  Star,
  Sun,
  Trees,
  Utensils,
  X,
} from "lucide-react";
import TripMap from "./components/TripMap";
import {
  buildTrip,
  directionsUrl,
  featuredIds,
  interests,
  rankPlaces,
  readSaved,
} from "./lib/planner";
import { useRoute } from "./lib/useRoute";
import "./App.css";

const defaultDays = [
  featuredIds.slice(0, 3),
  [featuredIds[3]],
  [featuredIds[4]],
];
const photos = {
  PLC0003729: "/images/bridge.jpg",
  PLC0008963: "/images/peak.jpg",
  PLC0012824: "/images/falls.jpg",
};
const descriptions = {
  PLC0003729: "A little architecture. A whole lot of wonder.",
  PLC0008963: "Take the scenic route above the clouds.",
  PLC0012824: "Follow the sound of the hill country.",
};
const label = (district) =>
  district === "Badulla" ? "Ella & the hill country" : district;
const categoryLabels = {
  attraction: "Places to see",
  activity: "Experiences",
  food: "Food & cafés",
  accommodation: "Places to stay",
  shopping: "Local finds",
};

function App() {
  const [initial] = useState(readSaved);
  const [places, setPlaces] = useState([]);
  const [loadState, setLoadState] = useState("loading");
  const [attempt, setAttempt] = useState(0);
  const [district, setDistrict] = useState(initial?.district || "Badulla");
  const [days, setDays] = useState(initial?.days || defaultDays);
  const [saved, setSaved] = useState(initial?.saved || []);
  const [date, setDate] = useState(initial?.date || "");
  const [preferences, setPreferences] = useState(["Nature", "Adventure"]);
  const [day, setDay] = useState(0);
  const [selected, setSelected] = useState(null);
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("attraction");
  const [view, setView] = useState("explore");
  const [limit, setLimit] = useState(3);
  const [toast, setToast] = useState("");
  const [dialog, setDialog] = useState(false);
  const [draftDistrict, setDraftDistrict] = useState(district);
  const [draftDays, setDraftDays] = useState(days.length);
  const [draftDate, setDraftDate] = useState(date);
  const [storageError, setStorageError] = useState(false);
  const dialogRef = useRef(null);
  const routeRef = useRef(null);
  const discoverRef = useRef(null);

  useEffect(() => {
    const controller = new AbortController();
    fetch(`${import.meta.env.BASE_URL}data/places.json`, {
      signal: controller.signal,
    })
      .then((r) => {
        if (!r.ok) throw new Error("Data unavailable");
        return r.json();
      })
      .then((data) => {
        setPlaces(data);
        setLoadState("ready");
      })
      .catch((error) => {
        if (error.name !== "AbortError") setLoadState("error");
      });
    return () => controller.abort();
  }, [attempt]);
  useEffect(() => {
    try {
      localStorage.setItem(
        "waxn-trip-v1",
        JSON.stringify({ district, days, saved, date }),
      );
    } catch {
      queueMicrotask(() => setStorageError(true));
    }
  }, [district, days, saved, date]);
  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(""), 4000);
    return () => clearTimeout(timer);
  }, [toast]);
  useEffect(() => {
    if (dialog) dialogRef.current?.showModal();
    else dialogRef.current?.close();
  }, [dialog]);

  const byId = useMemo(
    () => new globalThis.Map(places.map((p) => [p.id, p])),
    [places],
  );
  const stops = useMemo(
    () => (days[day] || []).map((id) => byId.get(id)).filter(Boolean),
    [days, day, byId],
  );
  const route = useRoute(stops);
  const districts = useMemo(
    () => [...new Set(places.map((p) => p.district))].sort(),
    [places],
  );
  const filtered = useMemo(() => {
    let list = places.filter((p) =>
      view === "saved" ? saved.includes(p.id) : p.district === district,
    );
    if (query.trim())
      list = list.filter((p) =>
        `${p.name} ${p.kind} ${p.district}`
          .toLowerCase()
          .includes(query.toLowerCase().trim()),
      );
    if (view !== "saved")
      list = list.filter(
        (p) =>
          category === "all" ||
          p.category === category ||
          (category === "attraction" && p.category === "activity"),
      );
    const ranked = rankPlaces(list, preferences);
    if (
      !query &&
      view !== "saved" &&
      district === "Badulla" &&
      category === "attraction"
    )
      ranked.sort((a, b) => {
        const ai = featuredIds.indexOf(a.id),
          bi = featuredIds.indexOf(b.id);
        return (ai < 0 ? 99 : ai) - (bi < 0 ? 99 : bi);
      });
    return ranked;
  }, [places, saved, district, view, query, category, preferences]);
  const selectStop = useCallback((id) => setSelected(id), []);
  const selectedPlace = byId.get(selected);

  function openPlanner() {
    setDraftDistrict(district);
    setDraftDays(days.length);
    setDraftDate(date);
    setDialog(true);
  }
  function goTo(target) {
    target.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }
  function navigate(next) {
    setView(next);
    setQuery("");
    setLimit(3);
    if (next === "trip") goTo(routeRef);
    else goTo(discoverRef);
  }
  function toggleSaved(id) {
    setSaved((current) =>
      current.includes(id) ? current.filter((p) => p !== id) : [...current, id],
    );
  }
  function addPlace(place) {
    if (days[day].includes(place.id)) {
      setToast("This place is already in your day.");
      return;
    }
    if (days[day].length >= 5) {
      setToast(
        "Keep it unhurried: up to 5 stops per day. Remove a stop or choose another day.",
      );
      return;
    }
    if (place.district !== district) {
      setToast(
        `Start a new trip to ${place.district} to add this saved place.`,
      );
      return;
    }
    setDays((current) =>
      current.map((ids, i) => (i === day ? [...ids, place.id] : ids)),
    );
    setSelected(place.id);
    setToast(`Added to day ${day + 1}: ${place.name}`);
  }
  function removeStop(id) {
    setDays((current) =>
      current.map((ids, i) =>
        i === day ? ids.filter((item) => item !== id) : ids,
      ),
    );
    setSelected(null);
  }
  function moveStop(index, direction) {
    setDays((current) =>
      current.map((ids, i) => {
        if (i !== day) return ids;
        const next = [...ids];
        [next[index], next[index + direction]] = [
          next[index + direction],
          next[index],
        ];
        return next;
      }),
    );
  }
  function generate(event) {
    event.preventDefault();
    const next = buildTrip(
      places,
      draftDistrict,
      Number(draftDays),
      preferences,
    );
    if (!next.some((ids) => ids.length)) {
      setToast(
        "No attractions found for this destination. Try another district.",
      );
      return;
    }
    setDays(next);
    setDistrict(draftDistrict);
    setDate(draftDate);
    setDay(0);
    setSelected(null);
    setDialog(false);
    setView("trip");
    setQuery("");
    setLimit(3);
    setToast("Your itinerary is ready. Make it your own.");
    setTimeout(() => goTo(routeRef), 100);
  }
  function exportTrip() {
    const trip = {
      destination: district,
      startDate: date || null,
      days: days.map((ids, i) => ({
        day: i + 1,
        stops: ids
          .map((id) => byId.get(id))
          .filter(Boolean)
          .map(({ id, name, lat, lng, category }) => ({
            id,
            name,
            lat,
            lng,
            category,
          })),
      })),
    };
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(trip, null, 2)], { type: "application/json" }),
    );
    const a = document.createElement("a");
    a.href = url;
    a.download = `waxn-${district.toLowerCase().replaceAll(" ", "-")}-trip.json`;
    a.click();
    URL.revokeObjectURL(url);
    setToast("Your itinerary has been downloaded.");
  }
  const totalStops = days.reduce((sum, ids) => sum + ids.length, 0);
  const dayDate = (index) => {
    if (!date) return "";
    const d = new Date(`${date}T12:00:00`);
    d.setDate(d.getDate() + index);
    return d.toLocaleDateString("en-GB", { day: "numeric", month: "short" });
  };

  return (
    <>
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <header className="topbar">
        <a className="brand" href="#" aria-label="Waxn home">
          <span className="brand-symbol">
            <Compass size={25} />
          </span>
          waxn<span className="brand-ai">AI</span>
        </a>
        <nav aria-label="Main navigation">
          <button
            className={view === "explore" ? "active" : ""}
            onClick={() => navigate("explore")}
          >
            Explore
          </button>
          <button
            className={view === "trip" ? "active" : ""}
            onClick={() => navigate("trip")}
          >
            My itinerary
          </button>
          <button
            className={view === "saved" ? "active" : ""}
            onClick={() => navigate("saved")}
          >
            Saved places{" "}
            {saved.length > 0 && (
              <span className="nav-count">{saved.length}</span>
            )}
          </button>
        </nav>
        <button
          className="header-cta"
          onClick={openPlanner}
          disabled={loadState !== "ready"}
        >
          <Plus size={17} /> Plan a trip
        </button>
      </header>
      <main id="main">
        <section className="hero">
          <img
            src="/images/bridge.jpg"
            alt="Nine Arch Bridge curving through the green hills of Ella, Sri Lanka"
            className="hero-image"
            fetchPriority="high"
          />
          <div className="hero-shade" />
          <div className="hero-copy">
            <div className="eyebrow">
              <span /> SMALL ISLAND. ENDLESS DISCOVERIES.
            </div>
            <h1>
              A little less planning.
              <br />A little more <em>wonder.</em>
            </h1>
            <p>Find your kind of Sri Lanka. We’ll help connect the dots.</p>
            <button
              className="hero-cta"
              onClick={openPlanner}
              disabled={loadState !== "ready"}
            >
              Find my next adventure <ArrowRight size={18} />
            </button>
          </div>
          <div className="hero-location">
            <MapPin size={17} />
            <div>
              <strong>Nine Arch Bridge</strong>
              <span>Ella, Sri Lanka</span>
            </div>
            <span className="photo-index">01 / 01</span>
          </div>
          <div className="hero-stamp">
            <Trees size={27} />
            <span>
              GO SLOW.
              <br />
              FEEL MORE.
            </span>
          </div>
        </section>
        <div className="content-wrap">
          <section className="trip-strip" aria-label="Your trip overview">
            <div className="trip-destination">
              <span className="soft-icon">
                <MapPin size={21} />
              </span>
              <div>
                <span className="field-label">YOUR NEXT CHAPTER</span>
                <strong>{label(district)}</strong>
              </div>
            </div>
            <div className="strip-detail">
              <CalendarDays size={19} />
              <div>
                <span className="field-label">WHEN</span>
                <strong>
                  {date
                    ? `${dayDate(0)} – ${dayDate(days.length - 1)}`
                    : "Whenever you’re ready"}
                </strong>
              </div>
            </div>
            <div className="strip-detail">
              <Route size={19} />
              <div>
                <span className="field-label">THE PLAN</span>
                <strong>
                  {days.length} days · {totalStops} places
                </strong>
              </div>
            </div>
            <button
              className="text-button"
              onClick={openPlanner}
              disabled={loadState !== "ready"}
            >
              Make it yours <ArrowRight size={17} />
            </button>
          </section>
          {loadState === "loading" && (
            <div className="status-panel" role="status">
              <span className="spinner" /> Finding your next favorite place…
            </div>
          )}
          {loadState === "error" && (
            <div className="status-panel" role="alert">
              We couldn’t load the destinations.{" "}
              <button
                className="text-button"
                onClick={() => {
                  setLoadState("loading");
                  setAttempt((a) => a + 1);
                }}
              >
                Try again
              </button>
            </div>
          )}
          {loadState === "ready" && (
            <>
              <section className="discovery" ref={discoverRef}>
                <div className="section-heading">
                  <div>
                    <div className="eyebrow green">
                      {view === "saved"
                        ? "KEEP THE GOOD ONES CLOSE"
                        : "A FEW PLACES TO FALL IN LOVE WITH"}
                    </div>
                    <h2>
                      {view === "saved"
                        ? "Your someday starts here."
                        : "Made for your kind of exploring."}
                    </h2>
                    <p>
                      {view === "saved"
                        ? "All your saved discoveries, ready for the next adventure."
                        : "Big views, hidden corners, and a few beautiful detours."}
                    </p>
                  </div>
                  <span className="editorial-note">
                    <Sparkles size={16} /> Inspired by your interests
                  </span>
                </div>
                <div className="discovery-tools">
                  <div className="filter-tabs" aria-label="Place categories">
                    {[
                      ["attraction", "Sights & nature", Mountain],
                      ["food", "Food & cafés", Utensils],
                      ["accommodation", "Stays", Sun],
                      ["all", "All places", Compass],
                    ].map(([value, text, Icon]) => (
                      <button
                        key={value}
                        className={
                          category === value && view !== "saved"
                            ? "selected"
                            : ""
                        }
                        onClick={() => {
                          setCategory(value);
                          setView("explore");
                          setLimit(3);
                        }}
                      >
                        <Icon size={16} />
                        {text}
                      </button>
                    ))}
                  </div>
                  <label className="search-box">
                    <Search size={17} />
                    <input
                      aria-label="Search places"
                      value={query}
                      placeholder="Find a place…"
                      onChange={(e) => {
                        setQuery(e.target.value);
                        setLimit(3);
                      }}
                    />
                    {query && (
                      <button
                        onClick={() => setQuery("")}
                        aria-label="Clear search"
                      >
                        <X size={15} />
                      </button>
                    )}
                  </label>
                </div>
                <div className="place-grid">
                  {filtered.slice(0, limit).map((place, index) => (
                    <article className="place-card" key={place.id}>
                      <div
                        className={`place-photo ${photos[place.id] ? "" : "illustrated"}`}
                      >
                        {photos[place.id] ? (
                          <img
                            src={photos[place.id]}
                            alt={
                              place.id === "PLC0008946"
                                ? "Sri Lanka hill country scenery"
                                : place.id === "PLC0004046"
                                  ? "Sri Lanka waterfall scenery"
                                  : place.name
                            }
                            loading="lazy"
                          />
                        ) : (
                          <>
                            <Mountain size={58} strokeWidth={0.7} />
                            <span>{place.district}, Sri Lanka</span>
                          </>
                        )}
                        {index === 0 && view !== "saved" && (
                          <span className="photo-tag">
                            <Sparkles size={12} /> A good place to start
                          </span>
                        )}
                        <button
                          className={`save-place ${saved.includes(place.id) ? "is-saved" : ""}`}
                          aria-label={`${saved.includes(place.id) ? "Unsave" : "Save"} ${place.name}`}
                          aria-pressed={saved.includes(place.id)}
                          onClick={() => toggleSaved(place.id)}
                        >
                          <Heart
                            size={18}
                            fill={
                              saved.includes(place.id) ? "currentColor" : "none"
                            }
                          />
                        </button>
                        <span className="photo-category">{place.kind}</span>
                      </div>
                      <div className="place-body">
                        <div className="place-meta">
                          <span>
                            <MapPin size={12} />
                            {place.district}
                          </span>
                          {place.rating ? (
                            <span className="rating">
                              <Star size={12} fill="currentColor" />
                              {place.rating.toFixed(1)}{" "}
                              <small>({place.reviews})</small>
                            </span>
                          ) : (
                            <span className="unrated">Ready to discover</span>
                          )}
                        </div>
                        <h3>{place.name}</h3>
                        <p>
                          {descriptions[place.id] ||
                            `${categoryLabels[place.category] || "Discover something new"} in ${place.district}.`}
                        </p>
                        <div className="card-bottom">
                          <a
                            href={directionsUrl([place])}
                            target="_blank"
                            rel="noreferrer"
                          >
                            <Navigation size={13} /> Directions
                          </a>
                          <button
                            onClick={() => addPlace(place)}
                            className={
                              days[day].includes(place.id) ? "added" : ""
                            }
                          >
                            {days[day].includes(place.id) ? (
                              <Check size={15} />
                            ) : (
                              <Plus size={15} />
                            )}{" "}
                            {days[day].includes(place.id)
                              ? "In your day"
                              : "Add to trip"}
                          </button>
                        </div>
                      </div>
                    </article>
                  ))}
                </div>
                {!filtered.length && (
                  <div className="empty-state">
                    <Search size={28} />
                    <h3>
                      {view === "saved"
                        ? "Your collection is waiting."
                        : "No places found."}
                    </h3>
                    <p>
                      {view === "saved"
                        ? "Tap a heart on any place to keep it here."
                        : "Try a different name or category."}
                    </p>
                    <button
                      className="text-button"
                      onClick={() => {
                        setView("explore");
                        setQuery("");
                        setCategory("all");
                      }}
                    >
                      Explore places <ArrowRight size={16} />
                    </button>
                  </div>
                )}
                {filtered.length > limit && (
                  <button
                    className="more-button"
                    onClick={() => setLimit((n) => n + 6)}
                  >
                    A few more discoveries <ChevronDown size={16} />
                    <span>{filtered.length} places</span>
                  </button>
                )}
              </section>
              <section className="planner-section" ref={routeRef}>
                <div className="section-heading">
                  <div>
                    <div className="eyebrow green">
                      LESS BACKTRACKING. MORE EXPLORING.
                    </div>
                    <h2>Your days, beautifully connected.</h2>
                    <p>
                      A little structure. Plenty of room for the unexpected.
                    </p>
                  </div>
                  <button className="outline-button" onClick={exportTrip}>
                    <Download size={15} /> Export itinerary
                  </button>
                </div>
                <div className="planner-layout">
                  <div className="itinerary-panel">
                    <div className="itinerary-title">
                      <div>
                        <h3>{label(district)}</h3>
                        <span>{days.length} days of possibility</span>
                      </div>
                      <span className="soft-icon small">
                        <Route size={18} />
                      </span>
                    </div>
                    <div className="day-tabs" aria-label="Itinerary days">
                      {days.map((_, index) => (
                        <button
                          key={index}
                          className={day === index ? "active" : ""}
                          onClick={() => {
                            setDay(index);
                            setSelected(null);
                          }}
                        >
                          Day {index + 1}
                          {date && <small>{dayDate(index)}</small>}
                        </button>
                      ))}
                    </div>
                    <div className="day-caption">
                      <span>
                        {day === 0
                          ? "Let the adventure begin"
                          : "Another day, another discovery"}
                      </span>
                      <span>{stops.length} stops</span>
                    </div>
                    <div className="stop-list">
                      {stops.map((place, index) => (
                        <div
                          className={`stop-row ${selected === place.id ? "selected" : ""}`}
                          key={place.id}
                        >
                          <button
                            className="stop-number"
                            onClick={() => setSelected(place.id)}
                            aria-label={`Show ${place.name} on map`}
                          >
                            {index + 1}
                          </button>
                          <button
                            className="stop-info"
                            onClick={() => setSelected(place.id)}
                          >
                            <span>
                              {place.category === "food"
                                ? "A LITTLE PAUSE"
                                : `STOP ${String(index + 1).padStart(2, "0")}`}
                            </span>
                            <strong>{place.name}</strong>
                            <small>{place.kind}</small>
                          </button>
                          <div className="stop-actions">
                            <button
                              disabled={index === 0}
                              onClick={() => moveStop(index, -1)}
                              aria-label={`Move ${place.name} up`}
                            >
                              <ArrowUp size={13} />
                            </button>
                            <button
                              disabled={index === stops.length - 1}
                              onClick={() => moveStop(index, 1)}
                              aria-label={`Move ${place.name} down`}
                            >
                              <ArrowDown size={13} />
                            </button>
                            <button
                              onClick={() => removeStop(place.id)}
                              aria-label={`Remove ${place.name}`}
                            >
                              <X size={14} />
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                    {!stops.length && (
                      <div className="empty-day">
                        <MapPin size={25} />
                        <p>A blank page for your next adventure.</p>
                        <span>Add a discovery to start this day.</span>
                      </div>
                    )}
                    <button
                      className="add-stop"
                      onClick={() => {
                        setView("explore");
                        goTo(discoverRef);
                      }}
                    >
                      <Plus size={15} /> Add a little detour
                    </button>
                    <div className="route-summary">
                      <span>
                        <Route size={15} />
                        <strong>{route.km.toFixed(1)} km</strong>
                      </span>
                      <span>
                        <Clock3 size={15} />
                        <strong>{Math.round(route.minutes)} min</strong> travel
                      </span>
                      <small>
                        {route.estimated
                          ? "Approximate travel · route not verified"
                          : "Driving route · excludes stops and live traffic"}
                      </small>
                    </div>
                    {stops.length > 0 && (
                      <a
                        className="directions-button"
                        href={directionsUrl(stops)}
                        target="_blank"
                        rel="noreferrer"
                      >
                        <Navigation size={16} /> Open in Google Maps{" "}
                        <ArrowRight size={16} />
                      </a>
                    )}
                  </div>
                  <div className="map-panel">
                    <TripMap
                      stops={stops}
                      route={route}
                      selected={selected}
                      onSelect={selectStop}
                    />
                    <div className="map-footer">
                      <span>
                        <i className="route-line" />
                        {route.estimated
                          ? "Approximate connection between stops"
                          : "Your driving route"}
                      </span>
                      <span>
                        <MapPin size={13} /> {district}, Sri Lanka
                      </span>
                    </div>
                    {selectedPlace && stops.some((p) => p.id === selected) && (
                      <div className="selected-place">
                        <div>
                          <span>
                            STOP {stops.findIndex((p) => p.id === selected) + 1}
                          </span>
                          <strong>{selectedPlace.name}</strong>
                        </div>
                        <a
                          href={directionsUrl([selectedPlace])}
                          target="_blank"
                          rel="noreferrer"
                          aria-label={`Directions to ${selectedPlace.name}`}
                        >
                          <Navigation size={18} />
                        </a>
                        <button
                          onClick={() => setSelected(null)}
                          aria-label="Close selected place"
                        >
                          <X size={17} />
                        </button>
                      </div>
                    )}
                  </div>
                </div>
                <div className="planner-note">
                  <Leaf size={17} />
                  <p>
                    Good trips leave room to wander. Travel times are estimates;
                    check access and opening hours before you go.
                  </p>
                  <span>
                    {storageError ? (
                      "Browser storage unavailable · export to save"
                    ) : (
                      <>
                        <Check size={13} /> Saved on this device
                      </>
                    )}
                  </span>
                </div>
              </section>
              <section className="closing-note">
                <span className="closing-icon">
                  <Compass size={34} strokeWidth={1} />
                </span>
                <div>
                  <h2>The best part? You haven’t been there yet.</h2>
                  <p>Your next favorite memory is somewhere out there.</p>
                </div>
                <button className="text-button" onClick={openPlanner}>
                  Let’s find it <ArrowRight size={18} />
                </button>
              </section>
            </>
          )}
        </div>
      </main>
      <footer>
        <a className="brand" href="#">
          waxn<span className="brand-ai">AI</span>
        </a>
        <span>A little curiosity goes a long way.</span>
        <a href="/images/credits.html" target="_blank" rel="noreferrer">
          Photo credits
        </a>
        <span>
          Made for discovering Sri Lanka <Leaf size={13} />
        </span>
      </footer>
      {toast && (
        <div className="toast" role="status">
          <Check size={18} />
          {toast}
          <button
            onClick={() => setToast("")}
            aria-label="Dismiss notification"
          >
            <X size={16} />
          </button>
        </div>
      )}
      <dialog
        ref={dialogRef}
        onCancel={() => setDialog(false)}
        onClose={() => setDialog(false)}
        aria-labelledby="planner-title"
      >
        <form onSubmit={generate}>
          <div className="dialog-heading">
            <span className="soft-icon">
              <Sparkles size={23} />
            </span>
            <button
              type="button"
              className="icon-button"
              onClick={() => setDialog(false)}
              aria-label="Close trip planner"
            >
              <X size={22} />
            </button>
          </div>
          <div className="eyebrow green">YOUR TRIP, YOUR WAY</div>
          <h2 id="planner-title">Where will curiosity take you?</h2>
          <p>Pick a place and a pace. We’ll put a starting plan together.</p>
          <label className="form-label">
            Your destination
            <select
              value={draftDistrict}
              onChange={(e) => setDraftDistrict(e.target.value)}
            >
              {districts.map((d) => (
                <option key={d} value={d}>
                  {label(d)}
                  {d === "Badulla" ? " · Badulla" : ""}
                </option>
              ))}
            </select>
          </label>
          <div className="form-row">
            <label className="form-label">
              How many days?
              <select
                value={draftDays}
                onChange={(e) => setDraftDays(Number(e.target.value))}
              >
                {Array.from({ length: 7 }, (_, i) => (
                  <option key={i} value={i + 1}>
                    {i + 1} {i ? "days" : "day"}
                  </option>
                ))}
              </select>
            </label>
            <label className="form-label">
              Start date <small>(optional)</small>
              <input
                type="date"
                value={draftDate}
                onChange={(e) => setDraftDate(e.target.value)}
              />
            </label>
          </div>
          <fieldset>
            <legend>What draws you in?</legend>
            <div className="interest-options">
              {interests.map((interest) => (
                <button
                  type="button"
                  key={interest}
                  aria-pressed={preferences.includes(interest)}
                  className={preferences.includes(interest) ? "selected" : ""}
                  onClick={() =>
                    setPreferences((current) =>
                      current.includes(interest)
                        ? current.filter((i) => i !== interest)
                        : [...current, interest],
                    )
                  }
                >
                  {preferences.includes(interest) && <Check size={13} />}{" "}
                  {interest}
                </button>
              ))}
            </div>
          </fieldset>
          <div className="form-note">
            <Leaf size={17} />
            <span>
              Nearby places, matched to your interests. You can add, remove, and
              reorder every stop.
            </span>
          </div>
          <button type="submit" className="primary-button">
            <Sparkles size={17} /> Create my itinerary <ArrowRight size={17} />
          </button>
          <small className="replace-note">
            Creates a new itinerary. Export your current trip first if you want
            to keep it.
          </small>
        </form>
      </dialog>
    </>
  );
}
export default App;
