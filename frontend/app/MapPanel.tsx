// ── MapPanel — Mapbox GL JS map with route polylines ──────────────────────
import { createElement, useEffect, useRef, useCallback } from 'react';
import * as mapboxgl from 'mapbox-gl/esm';
import { useRouteStore } from '../lib/store';
import { LiveStatusBar } from '../components/LiveStatusBar';

// Use the public token from env or a safe fallback placeholder
mapboxgl.setAccessToken(import.meta.env.VITE_MAPBOX_TOKEN || '');

const MAP_STYLE = 'mapbox://styles/mapbox/light-v11';

const LABEL_OFFSETS: Record<string, [number, number]> = {
  A: [0, -18],
  B: [0,  18],
  C: [30,   0],
};

export function MapPanel() {
  const USE_MOCK = true;
  if (USE_MOCK) {
    return (
      <>
        {createElement(
          'div',
          { className: 'flex items-center justify-center w-full h-full bg-gray-200' },
          createElement('span', { className: 'text-lg font-medium text-gray-700' }, 'Mock Map Placeholder'),
        )}
        {/* You can still render LiveStatusBar if needed */}
        <LiveStatusBar />
      </>
    );
  }

  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<mapboxgl.Map | null>(null);
  const markersRef = useRef<mapboxgl.Marker[]>([]);
  const popupsRef = useRef<mapboxgl.Popup[]>([]);
  const routeOptions = useRouteStore((s) => s.routeOptions);
  const selectedId = useRouteStore((s) => s.selectedRouteId);
  const setSelected = useRouteStore((s) => s.setSelectedRoute);

  // ── Initialize map ──────────────────────────────────────────────────
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = new mapboxgl.Map({
      container: containerRef.current,
      style: MAP_STYLE,
      center: [-0.1880, 5.5990],
      zoom: 11.5,
      attributionControl: false,
      logoPosition: 'bottom-left',
    });

    map.addControl(new mapboxgl.NavigationControl({ showCompass: false }), 'top-right');

    map.on('load', () => {
      mapRef.current = map;
      renderRoutes(map);
    });

    return () => {
      map.remove();
      mapRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Render / update routes ──────────────────────────────────────────
  const renderRoutes = useCallback(
    (map: mapboxgl.Map) => {
      if (!map.isStyleLoaded()) return;

      // Clear old markers and popups
      markersRef.current.forEach((m) => m.remove());
      popupsRef.current.forEach((p) => p.remove());
      markersRef.current = [];
      popupsRef.current  = [];

      // Draw in reverse so selected route paints on top
      const ordered = [...routeOptions].sort((a, b) =>
        a.id === selectedId ? 1 : b.id === selectedId ? -1 : 0,
      );

      ordered.forEach((route) => {
        const sourceId = `route-${route.id}`;
        const layerId  = `line-${route.id}`;

        const geojson = {
          type: 'Feature',
          properties: {},
          geometry: { type: 'LineString', coordinates: route.coordinates },
        };

        if (map.getSource(sourceId)) {
          (map.getSource(sourceId) as mapboxgl.GeoJSONSource).setData(geojson);
        } else {
          map.addSource(sourceId, { type: 'geojson', data: geojson });
        }

        const isSelected = route.id === selectedId;

        // Ensure old layer and source are removed to prevent duplicates and memory leaks
        if (map.getLayer(layerId)) {
          map.removeLayer(layerId);
        }
        if (map.getSource(sourceId)) {
          map.removeSource(sourceId);
        }
        // Add fresh source and layer
        map.addSource(sourceId, { type: 'geojson', data: geojson });
        map.addLayer({
          id: layerId,
          type: 'line',
          source: sourceId,
          layout: { 'line-cap': 'round', 'line-join': 'round' },
          paint: {
            'line-color': route.color,
            'line-width': isSelected ? 7 : 4,
            'line-opacity': isSelected ? 1 : 0.55,
          },
        });
        // Attach interaction listeners
        map.on('click', layerId, () => setSelected(route.id));
        map.on('mouseenter', layerId, () => { map.getCanvas().style.cursor = 'pointer'; });
        map.on('mouseleave', layerId, () => { map.getCanvas().style.cursor = ''; });

        // Route label popup (mid-point)
        const mid = route.coordinates[Math.floor(route.coordinates.length / 2)];
        const popup = new mapboxgl.Popup({
          closeButton: false,
          closeOnClick: false,
          anchor: 'center',
          offset: LABEL_OFFSETS[route.id] ?? [0, 0],
          className: 'route-label-popup',
        })
          .setLngLat(mid)
          .setHTML(
            `<div class="route-label ${isSelected ? 'selected' : ''}">${route.id} · ${route.durationMin} min</div>`,
          )
          .addTo(map);
        popupsRef.current.push(popup);
      });

      // Origin marker
      const originCoord = routeOptions[0]?.coordinates[0];
      const destCoord   = routeOptions[0]?.coordinates.at(-1);

      if (originCoord) {
        const el = document.createElement('div');
        el.className = 'origin-marker';
        el.innerHTML = `<div class="origin-dot"></div>`;
        markersRef.current.push(new mapboxgl.Marker(el).setLngLat(originCoord).addTo(map));
      }
      if (destCoord) {
        const el = document.createElement('div');
        el.className = 'dest-marker';
        el.innerHTML = `<div class="dest-dot"><svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M2 7L5.5 10.5L12 3.5" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg></div>`;
        markersRef.current.push(new mapboxgl.Marker(el).setLngLat(destCoord).addTo(map));
      }
    },
    [routeOptions, selectedId, setSelected],
  );

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;
    renderRoutes(map);
  }, [renderRoutes]);

  return (
    <>
      {/* Inline styles for Mapbox custom elements (can't use Tailwind for these) */}
      <style>{`
        .route-label-popup .mapboxgl-popup-content {
          padding: 0;
          background: transparent;
          box-shadow: none;
          border-radius: 0;
        }
        .route-label-popup .mapboxgl-popup-tip { display: none; }
        .route-label {
          background: white;
          border: 1.5px solid #e5e7eb;
          border-radius: 20px;
          padding: 3px 10px;
          font-size: 12px;
          font-weight: 600;
          color: #374151;
          font-family: Inter, sans-serif;
          white-space: nowrap;
          box-shadow: 0 2px 8px rgba(0,0,0,0.12);
        }
        .route-label.selected {
          background: #111827;
          border-color: #111827;
          color: white;
        }
        .origin-marker { cursor: default; }
        .origin-dot {
          width: 28px; height: 28px;
          background: white;
          border: 3px solid #111827;
          border-radius: 50%;
          box-shadow: 0 2px 8px rgba(0,0,0,0.2);
          display: flex; align-items: center; justify-content: center;
        }
        .origin-dot::after {
          content: '';
          width: 8px; height: 8px;
          background: #111827;
          border-radius: 50%;
        }
        .dest-dot {
          width: 32px; height: 32px;
          background: #111827;
          border-radius: 8px;
          display: flex; align-items: center; justify-content: center;
          box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        }
        .dest-marker { cursor: default; }
      `}</style>

      {/* Map notice */}
      <div className="absolute top-3 left-1/2 -translate-x-1/2 z-10 bg-white/90 backdrop-blur-sm rounded-full px-4 py-1.5 text-xs text-gray-500 font-medium shadow-sm border border-gray-100 whitespace-nowrap pointer-events-none">
        Illustrative map, not to scale · simulated data
      </div>

      <div ref={containerRef} className="w-full h-full" />
    </>
  );
}
