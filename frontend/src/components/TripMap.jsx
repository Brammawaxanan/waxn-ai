import { useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { LocateFixed, Maximize2, Minus, Plus } from 'lucide-react'

export default function TripMap({ stops, route, selected, onSelect }) {
  const element = useRef(null)
  const map = useRef(null)
  const layers = useRef(null)
  const [tileError, setTileError] = useState(false)

  useEffect(() => {
    const instance = L.map(element.current, { zoomControl: false, scrollWheelZoom: false }).setView([6.87, 81.05], 12)
    map.current = instance
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).on('tileerror', () => setTileError(true)).addTo(instance)
    layers.current = L.layerGroup().addTo(instance)
    const observer = new ResizeObserver(() => instance.invalidateSize())
    observer.observe(element.current)
    return () => { observer.disconnect(); instance.remove(); map.current = null }
  }, [])

  useEffect(() => {
    if (!map.current) return
    layers.current.clearLayers()
    stops.forEach((place, index) => {
      const icon = L.divIcon({ className: 'map-pin-wrapper', html: `<span class="map-pin ${selected === place.id ? 'selected' : ''}">${index + 1}</span>`, iconSize: [34, 42], iconAnchor: [17, 40] })
      const marker = L.marker([place.lat, place.lng], { icon, title: place.name, keyboard: true }).addTo(layers.current)
      const label = document.createElement('span')
      label.textContent = place.name
      marker.bindTooltip(label, { direction: 'top', offset: [0, -35] }).on('click', () => onSelect(place.id))
    })
    if (route?.coordinates?.length > 1) L.polyline(route.coordinates, { color: '#256e54', weight: 4, opacity: 0.8, dashArray: route.estimated ? '8 9' : null }).addTo(layers.current)
  }, [stops, route, selected, onSelect])

  useEffect(() => {
    if (stops.length) map.current.fitBounds(L.latLngBounds(stops.map(p => [p.lat, p.lng])), { padding: [55, 65], maxZoom: 14 })
  }, [stops])

  function fit() {
    if (stops.length) map.current.fitBounds(L.latLngBounds(stops.map(p => [p.lat, p.lng])), { padding: [55, 65], maxZoom: 14 })
  }
  return <div className="map-shell">
    <div ref={element} className="map-canvas" aria-label="Interactive map of your daily itinerary" />
    <div className="map-badge"><span className="live-dot" /> Your day, mapped out</div>
    <div className="map-controls">
      <button onClick={() => map.current.zoomIn()} aria-label="Zoom in"><Plus size={18}/></button>
      <button onClick={() => map.current.zoomOut()} aria-label="Zoom out"><Minus size={18}/></button>
      <button onClick={fit} aria-label="Fit all stops"><Maximize2 size={17}/></button>
    </div>
    <button className="map-fit" onClick={fit}><LocateFixed size={16}/> Recenter</button>
    {tileError && <div className="map-error" role="status">Map tiles couldn’t load. Your stops and Google Maps directions are still available.</div>}
  </div>
}
