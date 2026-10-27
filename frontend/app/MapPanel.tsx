
import { useCallback, useEffect, useRef, useState } from 'react';
import * as mapboxgl from 'mapbox-gl/esm';
import { useRouteStore } from '../lib/store';



const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN as
  | string
  | undefined;

const MAP_STYLE = 'mapbox://styles/mapbox/light-v11';

const ROUTE_IDS = ['recommended', 'A', 'B', 'C'] as const;

type RouteLine = {
  id: (typeof ROUTE_IDS)[number];
  label: string;
  coordinates: [number, number][];
  color: string;
  durationMin: number;
};

type LayerHandlers = {
  click: (event: mapboxgl.MapMouseEvent) => void;
  enter: () => void;
  leave: () => void;
};

type RouteFeature = {
  type: 'Feature';
  properties: {
    routeId: (typeof ROUTE_IDS)[number];
    label: string;
    durationMin: number;
  };
  geometry: {
    type: 'LineString';
    coordinates: [number, number][];
  };
};

mapboxgl.setAccessToken(MAPBOX_TOKEN || '');

export function MapPanel() {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<mapboxgl.Map | null>(null);
  const markersRef = useRef<mapboxgl.Marker[]>([]);
  const popupsRef = useRef<mapboxgl.Popup[]>([]);
  const layerHandlersRef = useRef<Map<string, LayerHandlers>>(new Map());

  const [mapLoaded, setMapLoaded] = useState(false);
  const [mapError, setMapError] = useState<string | null>(null);

  const routeOptions = useRouteStore((state) => state.routeOptions);
  const selectedId = useRouteStore((state) => state.selectedRouteId);
  const setSelected = useRouteStore((state) => state.setSelectedRoute);
  const planningResult = useRouteStore((state) => state.planningResult);

  const hasApiGeometry =
    Array.isArray(planningResult?.recommended?.coordinates) &&
    planningResult.recommended.coordinates.length >= 2;

  const renderRoutes = useCallback(
    (map: mapboxgl.Map) => {
      if (!map.isStyleLoaded()) return;

      // Remove old event handlers before removing their layers.
      layerHandlersRef.current.forEach((handlers, layerId) => {
        if (map.getLayer(layerId)) {
          map.off('click', layerId, handlers.click);
          map.off('mouseenter', layerId, handlers.enter);
          map.off('mouseleave', layerId, handlers.leave);
        }
      });
      layerHandlersRef.current.clear();

      // Remove existing markers and labels.
      markersRef.current.forEach((marker) => marker.remove());
      popupsRef.current.forEach((popup) => popup.remove());
      markersRef.current = [];
      popupsRef.current = [];

      // Remove old layers before removing their sources.
      ROUTE_IDS.forEach((id) => {
        const layerId = `line-${id}`;
        const sourceId = `route-${id}`;

        if (map.getLayer(layerId)) {
          map.removeLayer(layerId);
        }

        if (map.getSource(sourceId)) {
          map.removeSource(sourceId);
        }
      });

      let routes: RouteLine[] = [];

      if (planningResult) {
        // Once a plan exists, show its recommended route only.
        // Never silently substitute a mock route for a failed API geometry.
        const recommended = planningResult.recommended;
        const coordinates = recommended?.coordinates;

        if (
          recommended &&
          Array.isArray(coordinates) &&
          coordinates.length >= 2
        ) {
          routes = [
            {
              id: 'recommended',
              label: 'Recommended',
              coordinates,
              color: '#16a34a',
              durationMin: Math.round(recommended.duration_min),
            },
          ];
        }
      } else {
        // Before the first plan, retain the existing mock-route preview.
        routes = routeOptions
          .filter((route) => route.coordinates.length >= 2)
          .map((route) => ({
            id: route.id,
            label: route.id,
            coordinates: route.coordinates,
            color: route.color,
            durationMin: route.durationMin,
          }));
      }

      const allCoordinates: [number, number][] = [];

      routes.forEach((route) => {
        const sourceId = `route-${route.id}`;
        const layerId = `line-${route.id}`;
        const isSelected =
          route.id === 'recommended' || route.id === selectedId;

        const feature: RouteFeature = {
          type: 'Feature',
          properties: {
            routeId: route.id,
            label: route.label,
            durationMin: route.durationMin,
          },
          geometry: {
            type: 'LineString',
            coordinates: route.coordinates,
          },
        };

        map.addSource(sourceId, {
          type: 'geojson',
          data: feature,
        });

        map.addLayer({
          id: layerId,
          type: 'line',
          source: sourceId,
          layout: {
            'line-cap': 'round',
            'line-join': 'round',
          },
          paint: {
            'line-color': route.color,
            'line-width': isSelected ? 7 : 4,
            'line-opacity': isSelected ? 1 : 0.55,
          },
        });

        // Preserve route selection for the mock preview.
        // The API plan itself has one recommended route.
        const mockRouteId = route.id;
        if (mockRouteId === 'A' || mockRouteId === 'B' || mockRouteId === 'C') {
          const handlers: LayerHandlers = {
            click: () => setSelected(mockRouteId),
            enter: () => {
              map.getCanvas().style.cursor = 'pointer';
            },
            leave: () => {
              map.getCanvas().style.cursor = '';
            },
          };

          map.on('click', layerId, handlers.click);
          map.on('mouseenter', layerId, handlers.enter);
          map.on('mouseleave', layerId, handlers.leave);

          layerHandlersRef.current.set(layerId, handlers);
        }

        allCoordinates.push(...route.coordinates);

        const middleIndex = Math.floor(route.coordinates.length / 2);
        const middleCoordinate = route.coordinates[middleIndex];

        const popup = new mapboxgl.Popup({
          closeButton: false,
          closeOnClick: false,
          anchor: 'center',
          offset: [0, -12],
          className: 'route-label-popup',
        })
          .setLngLat(middleCoordinate)
          .setHTML(
            `<div class="route-label ${isSelected ? 'selected' : ''}">${route.label} · ${route.durationMin} min</div>`,
          )
          .addTo(map);

        popupsRef.current.push(popup);
      });

      // Mark the start and end of the displayed route.
      const firstRoute = routes.find(
        (route) => route.coordinates.length >= 2,
      );

      if (firstRoute) {
        const originCoordinate = firstRoute.coordinates[0];
        const destinationCoordinate =
          firstRoute.coordinates[firstRoute.coordinates.length - 1];

        const originElement = document.createElement('div');
        originElement.className = 'origin-marker';
        originElement.innerHTML = '<div class="origin-dot"></div>';

        markersRef.current.push(
          new mapboxgl.Marker(originElement)
            .setLngLat(originCoordinate)
            .addTo(map),
        );

        const destinationElement = document.createElement('div');
        destinationElement.className = 'dest-marker';
        destinationElement.innerHTML =
          '<div class="dest-dot"><svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M2 7L5.5 10.5L12 3.5" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg></div>';

        markersRef.current.push(
          new mapboxgl.Marker(destinationElement)
            .setLngLat(destinationCoordinate)
            .addTo(map),
        );
      }

      // Zoom to the displayed route.
      if (allCoordinates.length > 0) {
        const bounds = new mapboxgl.LngLatBounds();

        allCoordinates.forEach((coordinate) => {
          bounds.extend(coordinate);
        });

        map.fitBounds(bounds, {
          padding: 70,
          maxZoom: 14,
          duration: 700,
        });
      }
    },
    [planningResult, routeOptions, selectedId, setSelected],
  );

  // Initialize Mapbox once and clean up on unmount.
  useEffect(() => {
    if (!MAPBOX_TOKEN) {
      setMapError('Mapbox token is missing.');
      return;
    }

    if (!containerRef.current || mapRef.current) return;

    let map: mapboxgl.Map;

    try {
      map = new mapboxgl.Map({
        container: containerRef.current,
        style: MAP_STYLE,
        center: [-0.188, 5.599],
        zoom: 11.5,
        attributionControl: true,
        logoPosition: 'bottom-left',
      });
    } catch {
      setMapError('The map could not be initialized.');
      return;
    }

    mapRef.current = map;

    map.addControl(
      new mapboxgl.NavigationControl({ showCompass: false }),
      'top-right',
    );

    const handleLoad = () => {
      setMapError(null);
      setMapLoaded(true);
    };

    const handleError = (event: mapboxgl.ErrorEvent) => {
      console.error('Mapbox error:', event.error);

      // Don't replace a working map because an individual tile failed.
      if (!map.isStyleLoaded()) {
        setMapError(
          'Map tiles could not be loaded. Check your Mapbox token and network connection.',
        );
      }
    };

    map.on('load', handleLoad);
    map.on('error', handleError);

    return () => {
      map.off('load', handleLoad);
      map.off('error', handleError);

      layerHandlersRef.current.forEach((handlers, layerId) => {
        if (map.getLayer(layerId)) {
          map.off('click', layerId, handlers.click);
          map.off('mouseenter', layerId, handlers.enter);
          map.off('mouseleave', layerId, handlers.leave);
        }
      });

      layerHandlersRef.current.clear();

      markersRef.current.forEach((marker) => marker.remove());
      popupsRef.current.forEach((popup) => popup.remove());
      markersRef.current = [];
      popupsRef.current = [];

      map.remove();
      mapRef.current = null;
      setMapLoaded(false);
    };
  }, []);

  // Update the route whenever the plan or selected mock route changes.
  useEffect(() => {
    const map = mapRef.current;

    if (!map || !mapLoaded || !map.isStyleLoaded()) return;

    renderRoutes(map);
  }, [mapLoaded, renderRoutes]);

  return (
    <>
      <style>{`
        .route-label-popup .mapboxgl-popup-content {
          padding: 0;
          background: transparent;
          box-shadow: none;
          border-radius: 0;
        }

        .route-label-popup .mapboxgl-popup-tip {
          display: none;
        }

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
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);
        }

        .route-label.selected {
          background: #111827;
          border-color: #111827;
          color: white;
        }

        .origin-marker {
          cursor: default;
        }

        .origin-dot {
          width: 28px;
          height: 28px;
          background: white;
          border: 3px solid #111827;
          border-radius: 50%;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .origin-dot::after {
          content: '';
          width: 8px;
          height: 8px;
          background: #111827;
          border-radius: 50%;
        }

        .dest-dot {
          width: 32px;
          height: 32px;
          background: #111827;
          border-radius: 8px;
          display: flex;
          align-items: center;
          justify-content: center;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
        }

        .dest-marker {
          cursor: default;
        }
      `}</style>

      <div className="absolute top-3 left-1/2 -translate-x-1/2 z-10 bg-white/90 backdrop-blur-sm rounded-full px-4 py-1.5 text-xs text-gray-600 font-medium shadow-sm border border-gray-100 whitespace-nowrap pointer-events-none">
        {mapError
          ? mapError
          : hasApiGeometry
            ? 'Recommended route · backend geometry'
            : planningResult
              ? 'Route geometry unavailable for this plan'
              : 'Preview route · mock data'}
      </div>

      {!MAPBOX_TOKEN || mapError ? (
        <div className="flex h-full w-full items-center justify-center bg-gray-100 px-6 text-center text-sm text-gray-600">
          {mapError || 'Add VITE_MAPBOX_TOKEN to frontend/.env.local to enable the map.'}
        </div>
      ) : (
        <div ref={containerRef} className="h-full w-full" />
      )}
    </>
  );
}
