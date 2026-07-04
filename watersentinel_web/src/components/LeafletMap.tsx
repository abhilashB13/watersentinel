/**
 * Module: src/components/LeafletMap.tsx
 * Purpose: Renders the water quality topology heatmap using react-leaflet.
 *          MUCH simpler than the mobile WebView version — Leaflet runs
 *          natively in the browser DOM, no HTML injection or postMessage
 *          bridge required.
 */

import React, { useEffect, useRef } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet.heat';
import { TopologyPoint } from '../api/watersentinel';

interface LeafletMapProps {
  topologyData: TopologyPoint[];
  onPincodeSelected?: (pincode: string, areaName: string) => void;
  initialLat?: number;
  initialLng?: number;
  initialZoom?: number;
}

const BAND_COLOURS: Record<string, string> = {
  green: '#2E7D32',
  yellow: '#F9A825',
  orange: '#E65100',
  red: '#B71C1C',
};

// ── Heatmap layer sub-component ─────────────────────────────────────────────────
// Leaflet.heat is an imperative plugin, so we access the map instance directly
// via useMap() and add the heat layer as a side effect.

const HeatmapLayer: React.FC<{ points: TopologyPoint[] }> = ({ points }) => {
  const map = useMap();
  const layerRef = useRef<any>(null);

  useEffect(() => {
    if (layerRef.current) {
      map.removeLayer(layerRef.current);
    }

    const heatData: [number, number, number][] = points.map(p => [
      p.lat, p.lng, p.heat_intensity,
    ]);

    // @ts-ignore — leaflet.heat extends L with heatLayer, no official types
    const heatLayer = L.heatLayer(heatData, {
      radius: 35,
      blur: 20,
      maxZoom: 14,
      max: 1.0,
      gradient: {
        0.0: '#2E7D32',
        0.3: '#F9A825',
        0.6: '#E65100',
        1.0: '#B71C1C',
      },
    });

    heatLayer.addTo(map);
    layerRef.current = heatLayer;

    return () => {
      if (layerRef.current) map.removeLayer(layerRef.current);
    };
  }, [points, map]);

  return null;
};

// ── Legend control ─────────────────────────────────────────────────────────────

const Legend: React.FC = () => (
  <div className="map-legend">
    <b>Water Quality</b>
    <div><span style={{ color: '#2E7D32' }}>●</span> Safe (80-100)</div>
    <div><span style={{ color: '#F9A825' }}>●</span> Monitor (60-79)</div>
    <div><span style={{ color: '#E65100' }}>●</span> Caution (40-59)</div>
    <div><span style={{ color: '#B71C1C' }}>●</span> Do Not Drink (0-39)</div>
  </div>
);

// ── Main Component ──────────────────────────────────────────────────────────────

const LeafletMap: React.FC<LeafletMapProps> = ({
  topologyData,
  onPincodeSelected,
  initialLat = 17.4532,
  initialLng = 78.3800,
  initialZoom = 11,
}) => {
  return (
    <div className="map-container" style={{ position: 'relative' }}>
      <MapContainer
        center={[initialLat, initialLng]}
        zoom={initialZoom}
        style={{ height: '100%', width: '100%' }}
      >
        <TileLayer
          url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        />

        <HeatmapLayer points={topologyData} />

        {topologyData.map((point, i) => (
          <CircleMarker
            key={`${point.pincode}-${i}`}
            center={[point.lat, point.lng]}
            radius={10}
            pathOptions={{
              color: BAND_COLOURS[point.colour_band] || '#757575',
              fillColor: BAND_COLOURS[point.colour_band] || '#757575',
              fillOpacity: 0.75,
              weight: 2,
            }}
            eventHandlers={{
              click: () => onPincodeSelected?.(point.pincode, point.area_name),
            }}
          >
            <Popup>
              <div style={{ fontSize: 13 }}>
                <b>{point.area_name}</b><br />
                Score: <b>{point.avg_score}/100</b><br />
                Reports: {point.report_count}<br />
                Issue: {point.primary_contaminant || 'None detected'}<br />
                Pincode: {point.pincode}
              </div>
            </Popup>
          </CircleMarker>
        ))}
      </MapContainer>

      <div className="map-legend-wrapper">
        <Legend />
      </div>
    </div>
  );
};

export default LeafletMap;
