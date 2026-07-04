/**
 * Module: src/components/LeafletMap.tsx
 * Purpose: Renders the Leaflet.js water quality heatmap inside a
 *          React Native WebView. 100% free — uses OpenStreetMap tiles,
 *          no Google Maps API key required.
 * Component: Map UI Component
 * Key Design Decisions:
 *   - WebView with injectedJavaScript: Leaflet runs as a web page
 *     inside a WebView. Data is passed from React Native to Leaflet
 *     via injectedJavaScript string replacement before injection.
 *   - OpenStreetMap tiles: completely free, no API key, no usage limits.
 *   - leaflet.heat plugin: renders heatmap overlay. Intensity = (100-score)/100
 *     so contaminated areas (low score) have HIGH heat intensity (red).
 *   - Circle markers with popups: show area name, score, report count
 *     when tapped. More informative than heatmap alone.
 *   - onMessage bridge: Leaflet sends tapped pincode back to React Native
 *     for navigation to detail screen.
 */

import React, { useRef, useCallback } from 'react';
import { StyleSheet, View, ActivityIndicator } from 'react-native';
import { WebView, WebViewMessageEvent } from 'react-native-webview';
import { TopologyPoint } from '../api/watersentinel';

// ── Props ──────────────────────────────────────────────────────────────────────

interface LeafletMapProps {
  topologyData: TopologyPoint[];
  onPincodeSelected?: (pincode: string, areaName: string) => void;
  initialLat?: number;
  initialLng?: number;
  initialZoom?: number;
}

// ── Colour Map (score band → Leaflet marker colour) ───────────────────────────

const BAND_COLOURS: Record<string, string> = {
  green: '#2E7D32',
  yellow: '#F9A825',
  orange: '#E65100',
  red: '#B71C1C',
};

// ── Leaflet HTML Template ──────────────────────────────────────────────────────

const buildLeafletHTML = (
  topologyData: TopologyPoint[],
  initialLat: number,
  initialLng: number,
  initialZoom: number
): string => {
  // Build heatmap data: [lat, lng, intensity]
  const heatData = topologyData.map(p => [p.lat, p.lng, p.heat_intensity]);

  // Build marker data for circle markers with popups
  const markers = topologyData.map(p => ({
    lat: p.lat,
    lng: p.lng,
    pincode: p.pincode,
    area: p.area_name,
    score: p.avg_score,
    count: p.report_count,
    contaminant: p.primary_contaminant || 'None detected',
    colour: BAND_COLOURS[p.colour_band] || '#757575',
  }));

  return `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0"/>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script src="https://unpkg.com/leaflet.heat@0.2.0/dist/leaflet-heat.js"></script>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    html, body { height: 100%; width: 100%; }
    #map { height: 100vh; width: 100vw; }
    .leaflet-popup-content { font-family: -apple-system, sans-serif; }
    .popup-title { font-weight: bold; font-size: 14px; margin-bottom: 4px; }
    .popup-score { font-size: 13px; margin-bottom: 2px; }
    .popup-detail { font-size: 12px; color: #555; }
  </style>
</head>
<body>
  <div id="map"></div>
  <script>
    // ── Initialise Map ─────────────────────────────────────────────
    var map = L.map('map', {
      center: [${initialLat}, ${initialLng}],
      zoom: ${initialZoom},
      zoomControl: true,
    });

    // Free OpenStreetMap tiles — no API key required
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      maxZoom: 18,
    }).addTo(map);

    // ── Heatmap Layer ──────────────────────────────────────────────
    // Gradient: green (safe) → yellow → orange → red (contaminated)
    var heatData = ${JSON.stringify(heatData)};
    L.heatLayer(heatData, {
      radius: 35,
      blur: 20,
      maxZoom: 14,
      max: 1.0,
      gradient: {
        0.0: '#2E7D32',   // green — safe
        0.3: '#F9A825',   // yellow — monitor
        0.6: '#E65100',   // orange — caution
        1.0: '#B71C1C',   // red — do not drink
      }
    }).addTo(map);

    // ── Circle Markers with Popups ─────────────────────────────────
    var markers = ${JSON.stringify(markers)};
    markers.forEach(function(m) {
      var circle = L.circleMarker([m.lat, m.lng], {
        radius: 10,
        color: m.colour,
        fillColor: m.colour,
        fillOpacity: 0.7,
        weight: 2,
      }).addTo(map);

      // Popup with area details
      circle.bindPopup(
        '<div class="popup-title">' + m.area + '</div>' +
        '<div class="popup-score">Score: <b>' + m.score + '/100</b></div>' +
        '<div class="popup-detail">Reports: ' + m.count + '</div>' +
        '<div class="popup-detail">Issue: ' + m.contaminant + '</div>' +
        '<div class="popup-detail">Pincode: ' + m.pincode + '</div>'
      );

      // Send pincode to React Native when marker tapped
      circle.on('click', function() {
        window.ReactNativeWebView.postMessage(JSON.stringify({
          type: 'pincode_selected',
          pincode: m.pincode,
          area_name: m.area,
        }));
      });
    });

    // ── Legend ─────────────────────────────────────────────────────
    var legend = L.control({ position: 'bottomright' });
    legend.onAdd = function() {
      var div = L.DomUtil.create('div');
      div.style.cssText = 'background:white;padding:8px;border-radius:6px;font-size:11px;box-shadow:0 2px 4px rgba(0,0,0,0.2);';
      div.innerHTML =
        '<b style="display:block;margin-bottom:4px;">Water Quality</b>' +
        '<span style="color:#2E7D32">●</span> Safe (80-100)<br/>' +
        '<span style="color:#F9A825">●</span> Monitor (60-79)<br/>' +
        '<span style="color:#E65100">●</span> Caution (40-59)<br/>' +
        '<span style="color:#B71C1C">●</span> Do Not Drink (0-39)';
      return div;
    };
    legend.addTo(map);
  </script>
</body>
</html>`;
};

// ── LeafletMap Component ───────────────────────────────────────────────────────

const LeafletMap: React.FC<LeafletMapProps> = ({
  topologyData,
  onPincodeSelected,
  initialLat = 17.4532,   // Hyderabad centre
  initialLng = 78.3800,
  initialZoom = 11,
}) => {
  const webViewRef = useRef<WebView>(null);

  const html = buildLeafletHTML(
    topologyData,
    initialLat,
    initialLng,
    initialZoom
  );

  const handleMessage = useCallback(
    (event: WebViewMessageEvent) => {
      try {
        const data = JSON.parse(event.nativeEvent.data);
        if (data.type === 'pincode_selected' && onPincodeSelected) {
          onPincodeSelected(data.pincode, data.area_name);
        }
      } catch (e) {
        // Non-JSON message from Leaflet — ignore
      }
    },
    [onPincodeSelected]
  );

  return (
    <View style={styles.container}>
      <WebView
        ref={webViewRef}
        source={{ html }}
        style={styles.webview}
        onMessage={handleMessage}
        javaScriptEnabled
        domStorageEnabled
        startInLoadingState
        renderLoading={() => (
          <View style={styles.loading}>
            <ActivityIndicator size="large" color="#1565C0" />
          </View>
        )}
        // Allow loading CDN resources (Leaflet JS/CSS from unpkg.com)
        mixedContentMode="compatibility"
        allowsInlineMediaPlayback
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  webview: {
    flex: 1,
  },
  loading: {
    position: 'absolute',
    top: 0, left: 0, right: 0, bottom: 0,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#F5F5F5',
  },
});

export default LeafletMap;
