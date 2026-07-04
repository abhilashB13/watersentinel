/**
 * Module: src/pages/MapPage.tsx
 * Changes:
 *   - Blue header block removed
 *   - Slim white metadata bar: location left, updated time right
 *   - Map height increased to 420px (full width now)
 *   - Area list icons larger
 */

import React, { useState, useEffect, useCallback } from 'react';
import LeafletMap from '../components/LeafletMap';
import { getTopologyData, TopologyPoint, getBandColour } from '../api/watersentinel';

interface MapPageProps {
  onReportFromMap?: (pincode: string, areaName: string) => void;
}

const CONTAMINANT_FILTERS = ['All', 'High TDS', 'Iron', 'H2S', 'Fecal Coliform'];
const TIME_FILTERS = ['Today', 'Last 7d', 'Last 30d'];

function getContaminantDisplay(contaminant: string): { icon: string; color: string } {
  const c = (contaminant || '').toLowerCase();
  if (c.includes('h2s') || c.includes('sulph') || c.includes('egg')) return { icon: '💨', color: '#7B1FA2' };
  if (c.includes('iron') || c.includes('fe')) return { icon: '🟤', color: '#E65100' };
  if (c.includes('tds') || c.includes('hardness')) return { icon: '⬜', color: '#1565C0' };
  if (c.includes('fluoride')) return { icon: '⚗️', color: '#2E7D32' };
  if (c.includes('sewage') || c.includes('coliform')) return { icon: '🚨', color: '#B71C1C' };
  if (c.includes('nitrate')) return { icon: '🌾', color: '#F57F17' };
  if (c.includes('none') || c === '') return { icon: '✅', color: '#2E7D32' };
  return { icon: '💧', color: '#1565C0' };
}

const ScoreBar: React.FC<{ score: number; colour: string }> = ({ score, colour }) => {
  const filled = Math.round((score / 100) * 5);
  return (
    <div style={{ display: 'flex', gap: 2, alignItems: 'flex-end' }}>
      {[1, 2, 3, 4, 5].map(i => (
        <div key={i} style={{
          width: 6,
          height: i <= filled ? 6 + (i * 2) : 6,
          borderRadius: 2,
          background: i <= filled ? colour : '#E0E0E0',
        }} />
      ))}
    </div>
  );
};

const MapPage: React.FC<MapPageProps> = ({ onReportFromMap }) => {
  const [topologyData, setTopologyData] = useState<TopologyPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedArea, setSelectedArea] = useState<TopologyPoint | null>(null);
  const [lastUpdated, setLastUpdated] = useState('');
  const [contaminantFilter, setContaminantFilter] = useState('All');
  const [timeFilter, setTimeFilter] = useState('Today');

  const loadTopology = useCallback(async () => {
    try {
      const data = await getTopologyData();
      setTopologyData(data);
      setLastUpdated(new Date().toLocaleTimeString());
    } catch (err) {
      console.warn('Map load error:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadTopology(); }, [loadTopology]);

  const handlePincodeSelected = (pincode: string, areaName: string) => {
    const point = topologyData.find(p => p.pincode === pincode);
    if (point) setSelectedArea(point);
  };

  const filteredData = contaminantFilter === 'All'
    ? topologyData
    : topologyData.filter(p =>
        (p.primary_contaminant || '').toLowerCase()
          .includes(contaminantFilter.replace('High ', '').toLowerCase())
      );

  const redCount = topologyData.filter(p => p.colour_band === 'red').length;
  const totalReports = topologyData.reduce((sum, p) => sum + (p.report_count || 0), 0);

  const authorityAlerts = topologyData
    .filter(p => p.colour_band === 'red' && p.report_count >= 2)
    .slice(0, 2)
    .map(p => ({
      area: p.area_name,
      action: (p.primary_contaminant || '').includes('H2S')
        ? 'Water Softener Plant: Testing scheduled'
        : 'Pipeline repair under review',
    }));

  return (
    <div>

      {/* ── Slim white metadata bar — replaces old blue header ── */}
      <div className="map-meta-bar">
        <div>
          <div className="map-meta-location">🗺️ Hyderabad — Citizen Reports</div>
          <div style={{ display: 'flex', gap: 16, marginTop: 4 }}>
            <span style={{ fontSize: 12, color: '#555' }}>
              📍 <b style={{ color: '#1A237E' }}>{topologyData.length}</b> Areas
            </span>
            <span style={{ fontSize: 12, color: '#555' }}>
              🔴 <b style={{ color: '#B71C1C' }}>{redCount}</b> Critical
            </span>
            <span style={{ fontSize: 12, color: '#555' }}>
              📊 <b style={{ color: '#1A237E' }}>{totalReports}</b> Reports
            </span>
          </div>
        </div>
        <div className="map-meta-updated">
          {lastUpdated && <span>Updated: {lastUpdated}</span>}
          <button onClick={loadTopology} style={{ fontSize: 18, color: '#1565C0' }} type="button">↻</button>
        </div>
      </div>

      {/* Community Health Alert Bar */}
      <div style={{
        background: '#FFF8E1', padding: '10px 16px',
        borderBottom: '1px solid #FFE082',
        display: 'flex', alignItems: 'center', gap: 10,
      }}>
        <span style={{ fontSize: 20 }}>🔔</span>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: '#F57F17' }}>Community Health Alert Bar</div>
          <div style={{ fontSize: 12, color: '#555' }}>Proactive Geo-fencing Alerts Active: Your area is being monitored</div>
        </div>
        <span style={{ fontSize: 20 }}>🔕</span>
      </div>

      {/* Filter row */}
      <div style={{ padding: '10px 16px', background: 'white', borderBottom: '1px solid #E0E0E0' }}>
        <div style={{ display: 'flex', gap: 6, marginBottom: 8, alignItems: 'center' }}>
          <span style={{ fontSize: 12, color: '#555' }}>Filter:</span>
          {TIME_FILTERS.map(tf => (
            <button key={tf} onClick={() => setTimeFilter(tf)}
              style={{
                padding: '4px 10px', borderRadius: 12, fontSize: 12, border: 'none',
                background: timeFilter === tf ? '#1565C0' : '#F5F5F5',
                color: timeFilter === tf ? 'white' : '#555', cursor: 'pointer',
              }}
              type="button">{tf}</button>
          ))}
        </div>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
          <span style={{ fontSize: 12, color: '#555' }}>Contaminants:</span>
          {CONTAMINANT_FILTERS.map(cf => (
            <button key={cf} onClick={() => setContaminantFilter(cf)}
              style={{
                padding: '4px 10px', borderRadius: 12, fontSize: 12, border: 'none',
                background: contaminantFilter === cf ? '#1565C0' : '#F5F5F5',
                color: contaminantFilter === cf ? 'white' : '#555', cursor: 'pointer',
              }}
              type="button">{cf}</button>
          ))}
        </div>
      </div>

      {/* Map */}
      {loading ? (
        <div style={{ height: 420, display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 12 }}>
          <div className="spinner-lg" />
          <div className="text-muted">Loading community map...</div>
        </div>
      ) : (
        <LeafletMap
          topologyData={filteredData}
          onPincodeSelected={handlePincodeSelected}
          initialLat={17.4532}
          initialLng={78.3800}
          initialZoom={11}
        />
      )}

      {/* Authority Alerts */}
      {authorityAlerts.length > 0 && (
        <div style={{ background: '#FFF3E0', padding: '10px 16px', borderBottom: '1px solid #FFE082' }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: '#E65100', marginBottom: 6 }}>
            🏛️ GHMC Authority Action Alerts
          </div>
          {authorityAlerts.map((alert, i) => (
            <div key={i} style={{ fontSize: 12, color: '#555', marginBottom: 3 }}>
              Alert {i + 1}: {alert.area} ({alert.action})
            </div>
          ))}
        </div>
      )}

      {/* Selected Area Panel */}
      {selectedArea && (
        <div className="card" style={{ borderLeft: `4px solid ${getBandColour(selectedArea.colour_band)}` }}>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <div>
              <div style={{ fontSize: 15, fontWeight: 700, color: '#1A237E' }}>{selectedArea.area_name}</div>
              <div style={{ fontSize: 13, color: '#555' }}>
                Score: <b style={{ color: getBandColour(selectedArea.colour_band) }}>{selectedArea.avg_score}/100</b>
                {' · '}{selectedArea.report_count} reports
              </div>
              <div style={{ fontSize: 12, color: '#777' }}>Issue: {selectedArea.primary_contaminant || 'None'}</div>
            </div>
            <button onClick={() => setSelectedArea(null)} style={{ fontSize: 18, color: '#9E9E9E' }} type="button">✕</button>
          </div>
          {onReportFromMap && (
            <button
              onClick={() => { onReportFromMap(selectedArea.pincode, selectedArea.area_name); setSelectedArea(null); }}
              style={{ marginTop: 10, fontSize: 13, color: '#1565C0', fontWeight: 600 }}
              type="button"
            >
              + Report issue in this area →
            </button>
          )}
        </div>
      )}

      {/* Area list */}
      {!loading && filteredData.length > 0 && (
        <div style={{ padding: '0 12px' }}>
          <div className="text-muted" style={{ padding: '8px 4px', fontWeight: 600 }}>Recent Activity</div>
          {[...filteredData]
            .sort((a, b) => (a.avg_score || 100) - (b.avg_score || 100))
            .slice(0, 12)
            .map((point, i) => {
              const { icon, color } = getContaminantDisplay(point.primary_contaminant || '');
              const bandColour = getBandColour(point.colour_band);
              return (
                <button
                  key={i}
                  onClick={() => setSelectedArea(point)}
                  style={{
                    display: 'flex', alignItems: 'center', width: '100%',
                    background: 'white', padding: '12px', marginBottom: 6,
                    borderRadius: 10, boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
                    textAlign: 'left', gap: 12, cursor: 'pointer',
                  }}
                  type="button"
                >
                  {/* Larger contaminant icon */}
                  <div style={{
                    width: 44, height: 44, borderRadius: 12,
                    background: color + '18',
                    border: `1.5px solid ${color}44`,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 22, flexShrink: 0,
                  }}>
                    {icon}
                  </div>

                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 14, fontWeight: 600, color: '#1A237E' }}>
                      {point.area_name}
                    </div>
                    <div style={{ fontSize: 11, color: '#777', marginTop: 2 }}>
                      {point.primary_contaminant || 'No issue'} · {point.report_count} report{point.report_count !== 1 ? 's' : ''}
                      {point.report_count >= 3 ? ' · Health reports rising' : ''}
                    </div>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4, flexShrink: 0 }}>
                    <ScoreBar score={Math.round(point.avg_score)} colour={bandColour} />
                    <div style={{ fontSize: 16, fontWeight: 700, color: bandColour }}>
                      {Math.round(point.avg_score)}
                    </div>
                  </div>
                </button>
              );
            })}
        </div>
      )}
    </div>
  );
};

export default MapPage;
