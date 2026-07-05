/**
 * Module: src/pages/MapPage.tsx
 * FINAL VERSION — combines all fixes:
 *   - Source-type filter (Municipal/Borewell/Hand Pump/Open Well)
 *   - Contaminant icon reflects real colour_band (not hardcoded green)
 *   - readableContaminant() parses JSON-array symptom strings into text
 *   - NEW: Colony-level granularity — area list groups by area_name,
 *     expandable to show individual colonies (MIG/LIG/HIG etc.) each
 *     with their own score, since the same area can have very different
 *     water quality colony-to-colony, not just source-to-source.
 */

import React, { useState, useEffect, useCallback } from 'react';
import LeafletMap from '../components/LeafletMap';
import { getTopologyData, TopologyPoint, getBandColour } from '../api/watersentinel';
import { t, Lang } from '../i18n/translations';

interface MapPageProps {
  onReportFromMap?: (pincode: string, areaName: string, colonyName?: string) => void;
  lang?: Lang;
}

const CONTAMINANT_FILTERS = ['All', 'High TDS', 'Iron', 'H2S', 'Fecal Coliform'];
const TIME_FILTERS = ['Today', 'Last 7d', 'Last 30d'];

const SOURCE_FILTERS = [
  { id: 'all', label: 'All Sources', icon: '💧' },
  { id: 'municipal_pipeline', label: 'Municipal Pipe', icon: '🚰' },
  { id: 'borewell', label: 'Borewell', icon: '⛏️' },
  { id: 'hand_pump', label: 'Hand Pump', icon: '💧' },
  { id: 'open_well', label: 'Open Well', icon: '🪣' },
];

// Parses a raw contaminant string that may be a JSON array like
// '["sewage_smell", "salty_taste"]' or '[]' into readable text.
function readableContaminant(raw: string): string {
  if (!raw || raw === '[]' || raw.trim() === '') return 'No issue';
  try {
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed)) {
      if (parsed.length === 0) return 'No issue';
      return parsed
        .map(s => String(s).replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()))
        .join(', ');
    }
  } catch {
    // Not JSON — already a plain string
  }
  return raw.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function getContaminantDisplay(contaminant: string, colourBand?: string): { icon: string; color: string } {
  const c = (contaminant || '').toLowerCase();
  if (c.includes('h2s') || c.includes('sulph') || c.includes('egg')) return { icon: '💨', color: '#7B1FA2' };
  if (c.includes('iron') || c.includes('fe')) return { icon: '🟤', color: '#E65100' };
  if (c.includes('tds') || c.includes('hardness')) return { icon: '⬜', color: '#1565C0' };
  if (c.includes('fluoride')) return { icon: '⚗️', color: '#2E7D32' };
  if (c.includes('sewage') || c.includes('coliform')) return { icon: '🚨', color: '#B71C1C' };
  if (c.includes('nitrate')) return { icon: '🌾', color: '#F57F17' };
  if (c.includes('none') || c === '') {
    if (colourBand === 'green') return { icon: '✅', color: '#2E7D32' };
    if (colourBand === 'yellow') return { icon: '🟡', color: '#F9A825' };
    if (colourBand === 'orange') return { icon: '🟠', color: '#E65100' };
    if (colourBand === 'red') return { icon: '🔴', color: '#B71C1C' };
    return { icon: '💧', color: '#1565C0' };
  }
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

const getSourceAction = (contaminant: string): string => {
  const c = (contaminant || '').toLowerCase();
  if (c.includes('h2s') || c.includes('sulph')) return 'Water Softener Plant: Testing scheduled';
  if (c.includes('iron')) return 'Iron Removal Plant: Inspection requested';
  if (c.includes('tds')) return 'RO Treatment Unit: Feasibility study underway';
  if (c.includes('sewage') || c.includes('coliform')) return 'Pipeline Repair: Emergency crew dispatched';
  if (c.includes('fluoride')) return 'Defluoridation Plant: Under evaluation';
  return 'Pipeline repair under review';
};

// Groups flat topology points by area_name, producing an ordered list where
// each group's "headline score" is its worst (lowest) colony score — so an
// area with one badly contaminated colony still surfaces as a priority,
// even if other colonies within it are fine.
interface AreaGroup {
  areaName: string;
  worstScore: number;
  worstBand: string;
  totalReports: number;
  colonies: TopologyPoint[];
}

function groupByArea(points: TopologyPoint[]): AreaGroup[] {
  const groups = new Map<string, TopologyPoint[]>();
  for (const p of points) {
    const key = p.area_name;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(p);
  }

  const result: AreaGroup[] = [];
  groups.forEach((colonies, areaName) => {
    const sorted = [...colonies].sort((a, b) => a.avg_score - b.avg_score);
    const worst = sorted[0];
    result.push({
      areaName,
      worstScore: worst.avg_score,
      worstBand: worst.colour_band,
      totalReports: colonies.reduce((sum, c) => sum + c.report_count, 0),
      colonies: sorted,
    });
  });

  return result.sort((a, b) => a.worstScore - b.worstScore);
}

const MapPage: React.FC<MapPageProps> = ({ onReportFromMap, lang = 'en' }) => {
  const [topologyData, setTopologyData] = useState<TopologyPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedArea, setSelectedArea] = useState<TopologyPoint | null>(null);
  const [lastUpdated, setLastUpdated] = useState('');
  const [contaminantFilter, setContaminantFilter] = useState('All');
  const [timeFilter, setTimeFilter] = useState('Today');
  const [sourceFilter, setSourceFilter] = useState('all');
  const [expandedAreas, setExpandedAreas] = useState<Set<string>>(new Set());

  const loadTopology = useCallback(async (source: string = sourceFilter) => {
    setLoading(true);
    try {
      const data = await getTopologyData(source);
      setTopologyData(data);
      setLastUpdated(new Date().toLocaleTimeString());
    } catch (err) {
      console.warn('Map load error:', err);
    } finally {
      setLoading(false);
    }
  }, [sourceFilter]);

  useEffect(() => { loadTopology(sourceFilter); }, [sourceFilter]);

  const handleSourceChange = (source: string) => {
    setSourceFilter(source);
    setSelectedArea(null);
    setExpandedAreas(new Set());
  };

  const handlePincodeSelected = (pincode: string, areaName: string) => {
    // Map marker click — find the FIRST matching colony point for this area/pincode
    // (in a future iteration with real per-colony marker positions, this would
    // match the specific colony clicked rather than the first one found)
    const point = topologyData.find(p => p.pincode === pincode && p.area_name === areaName);
    if (point) setSelectedArea(point);
  };

  const toggleAreaExpanded = (areaName: string) => {
    setExpandedAreas(prev => {
      const next = new Set(prev);
      if (next.has(areaName)) next.delete(areaName);
      else next.add(areaName);
      return next;
    });
  };

  const filteredData = contaminantFilter === 'All'
    ? topologyData
    : topologyData.filter(p =>
        (p.primary_contaminant || '').toLowerCase()
          .includes(contaminantFilter.replace('High ', '').toLowerCase())
      );

  const redCount = topologyData.filter(p => p.colour_band === 'red').length;
  const totalReports = topologyData.reduce((sum, p) => sum + (p.report_count || 0), 0);
  const areaGroups = groupByArea(filteredData);

  const authorityAlerts = topologyData
    .filter(p => p.colour_band === 'red' && p.report_count >= 2)
    .slice(0, 3)
    .map(p => ({ area: p.area_name, action: getSourceAction(p.primary_contaminant || '') }));

  const currentSourceLabel = SOURCE_FILTERS.find(s => s.id === sourceFilter)?.label || 'All Sources';

  return (
    <div>

      {/* Slim metadata bar */}
      <div className="map-meta-bar">
        <div>
          <div className="map-meta-location">🗺️ {t(lang, 'citizenReports')}</div>
          <div style={{ display: 'flex', gap: 16, marginTop: 4 }}>
            <span style={{ fontSize: 12, color: '#555' }}>📍 <b style={{ color: '#1A237E' }}>{areaGroups.length}</b> {t(lang, 'statAreas')}</span>
            <span style={{ fontSize: 12, color: '#555' }}>🔴 <b style={{ color: '#B71C1C' }}>{redCount}</b> {t(lang, 'statCritical')}</span>
            <span style={{ fontSize: 12, color: '#555' }}>📊 <b style={{ color: '#1A237E' }}>{totalReports}</b> {t(lang, 'statReports')}</span>
          </div>
        </div>
        <div className="map-meta-updated">
          {lastUpdated && <span>Updated: {lastUpdated}</span>}
          <button onClick={() => loadTopology(sourceFilter)} style={{ fontSize: 18, color: '#1565C0' }} type="button">↻</button>
        </div>
      </div>

      {/* Community Health Alert Bar */}
      <div style={{ background: '#FFF8E1', padding: '10px 16px', borderBottom: '1px solid #FFE082', display: 'flex', alignItems: 'center', gap: 10 }}>
        <span style={{ fontSize: 20 }}>🔔</span>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: '#F57F17' }}>{t(lang, 'communityHealthAlert')}</div>
          <div style={{ fontSize: 12, color: '#555' }}>{t(lang, 'geofencingActive')}</div>
        </div>
      </div>

      {/* Source Type Filter */}
      <div style={{ padding: '10px 16px', background: '#FAFBFF', borderBottom: '2px solid #1565C0' }}>
        <div style={{ fontSize: 12, fontWeight: 700, color: '#1A237E', marginBottom: 8 }}>
          {t(lang, 'filterBySource')}
        </div>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {SOURCE_FILTERS.map(sf => (
            <button
              key={sf.id}
              onClick={() => handleSourceChange(sf.id)}
              style={{
                display: 'flex', alignItems: 'center', gap: 5,
                padding: '6px 12px', borderRadius: 16, fontSize: 12, fontWeight: 600,
                border: sourceFilter === sf.id ? '2px solid #1565C0' : '1px solid #E0E0E0',
                background: sourceFilter === sf.id ? '#E3F2FD' : 'white',
                color: sourceFilter === sf.id ? '#1565C0' : '#555',
              }}
              type="button"
            >
              <span>{sf.icon}</span>{sf.label}
            </button>
          ))}
        </div>
        {sourceFilter !== 'all' && (
          <div style={{ fontSize: 11, color: '#1565C0', marginTop: 8, fontStyle: 'italic' }}>
            Showing scores for <b>{currentSourceLabel}</b> only — same area may score differently
            for other sources.
          </div>
        )}
      </div>

      {/* Filter row */}
      <div style={{ padding: '10px 16px', background: 'white', borderBottom: '1px solid #E0E0E0' }}>
        <div style={{ display: 'flex', gap: 6, marginBottom: 8, alignItems: 'center' }}>
          <span style={{ fontSize: 12, color: '#555' }}>{t(lang, 'filter')}</span>
          {TIME_FILTERS.map(tf => (
            <button key={tf} onClick={() => setTimeFilter(tf)}
              style={{ padding: '4px 10px', borderRadius: 12, fontSize: 12, border: 'none',
                background: timeFilter === tf ? '#1565C0' : '#F5F5F5', color: timeFilter === tf ? 'white' : '#555' }}
              type="button">{tf}</button>
          ))}
        </div>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
          <span style={{ fontSize: 12, color: '#555' }}>{t(lang, 'contaminants')}</span>
          {CONTAMINANT_FILTERS.map(cf => (
            <button key={cf} onClick={() => setContaminantFilter(cf)}
              style={{ padding: '4px 10px', borderRadius: 12, fontSize: 12, border: 'none',
                background: contaminantFilter === cf ? '#1565C0' : '#F5F5F5', color: contaminantFilter === cf ? 'white' : '#555' }}
              type="button">{cf}</button>
          ))}
        </div>
      </div>

      {/* Map */}
      {loading ? (
        <div style={{ height: 420, display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 12 }}>
          <div className="spinner-lg" />
          <div className="text-muted">Loading {currentSourceLabel.toLowerCase()} data...</div>
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
          <div style={{ fontSize: 13, fontWeight: 700, color: '#E65100', marginBottom: 6 }}>{t(lang, 'authorityAlerts')}</div>
          {authorityAlerts.map((alert, i) => (
            <div key={i} style={{ fontSize: 12, color: '#555', marginBottom: 3 }}>
              Alert {i + 1}: {alert.area} ({alert.action})
            </div>
          ))}
        </div>
      )}

      {/* Selected Area/Colony Panel */}
      {selectedArea && (
        <div className="card" style={{ borderLeft: `4px solid ${getBandColour(selectedArea.colour_band)}` }}>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <div>
              {selectedArea.colony_name && selectedArea.colony_name !== 'Unspecified' ? (
                <>
                  <div style={{ fontSize: 15, fontWeight: 700, color: '#1A237E' }}>{selectedArea.colony_name}</div>
                  <div style={{ fontSize: 12, color: '#888' }}>{selectedArea.area_name} · Pincode {selectedArea.pincode}</div>
                </>
              ) : (
                <div style={{ fontSize: 15, fontWeight: 700, color: '#1A237E' }}>{selectedArea.area_name}</div>
              )}
              <div style={{ fontSize: 13, color: '#555', marginTop: 4 }}>
                Score: <b style={{ color: getBandColour(selectedArea.colour_band) }}>{Math.round(selectedArea.avg_score)}/100</b>
                {' · '}{selectedArea.report_count} reports
              </div>
              <div style={{ fontSize: 12, color: '#777' }}>Issue: {readableContaminant(selectedArea.primary_contaminant || '')}</div>
            </div>
            <button onClick={() => setSelectedArea(null)} style={{ fontSize: 18, color: '#9E9E9E' }} type="button">✕</button>
          </div>
          {onReportFromMap && (
            <button
              onClick={() => {
                onReportFromMap(selectedArea.pincode, selectedArea.area_name, selectedArea.colony_name);
                setSelectedArea(null);
              }}
              style={{ marginTop: 10, fontSize: 13, color: '#1565C0', fontWeight: 600 }}
              type="button"
            >
              {t(lang, 'reportIssueHere')}
            </button>
          )}
        </div>
      )}

      {/* Area list — grouped by area, expandable to show colony breakdown */}
      {!loading && areaGroups.length > 0 && (
        <div style={{ padding: '0 12px' }}>
          <div className="text-muted" style={{ padding: '8px 4px', fontWeight: 600 }}>
            {t(lang, 'recentActivity')} {sourceFilter !== 'all' && `— ${currentSourceLabel}`}
          </div>
          {areaGroups.slice(0, 12).map((group, i) => {
            const { icon, color } = getContaminantDisplay(
              group.colonies[0]?.primary_contaminant || '', group.worstBand
            );
            const bandColour = getBandColour(group.worstBand);
            const hasMultipleColonies = group.colonies.length > 1 ||
              (group.colonies[0]?.colony_name && group.colonies[0].colony_name !== 'Unspecified');
            const isExpanded = expandedAreas.has(group.areaName);

            return (
              <div key={i} style={{ marginBottom: 6 }}>
                {/* Area-level row */}
                <button
                  onClick={() => hasMultipleColonies ? toggleAreaExpanded(group.areaName) : setSelectedArea(group.colonies[0])}
                  style={{
                    display: 'flex', alignItems: 'center', width: '100%',
                    background: 'white', padding: '12px',
                    borderRadius: isExpanded ? '10px 10px 0 0' : 10,
                    boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
                    textAlign: 'left', gap: 12, cursor: 'pointer',
                  }}
                  type="button"
                >
                  <div style={{
                    width: 44, height: 44, borderRadius: 12,
                    background: color + '18', border: `1.5px solid ${color}44`,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 22, flexShrink: 0,
                  }}>
                    {icon}
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 14, fontWeight: 600, color: '#1A237E', display: 'flex', alignItems: 'center', gap: 6 }}>
                      {group.areaName}
                      {hasMultipleColonies && (
                        <span style={{ fontSize: 10, color: '#1565C0', background: '#E3F2FD', borderRadius: 8, padding: '1px 7px' }}>
                          {group.colonies.length} {group.colonies.length === 1 ? t(lang, 'colony') : t(lang, 'colonies')} {isExpanded ? '▲' : '▼'}
                        </span>
                      )}
                    </div>
                    <div className="text-muted" style={{ fontSize: 11, marginTop: 2 }}>
                      {readableContaminant(group.colonies[0]?.primary_contaminant || '')} · {group.totalReports} report{group.totalReports !== 1 ? 's' : ''}
                      {group.totalReports >= 3 ? ' · Health reports rising' : ''}
                    </div>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4, flexShrink: 0 }}>
                    <ScoreBar score={Math.round(group.worstScore)} colour={bandColour} />
                    <div style={{ fontSize: 16, fontWeight: 700, color: bandColour }}>
                      {Math.round(group.worstScore)}
                    </div>
                  </div>
                </button>

                {/* Expanded colony breakdown */}
                {isExpanded && hasMultipleColonies && (
                  <div style={{
                    background: '#FAFBFF', borderRadius: '0 0 10px 10px',
                    boxShadow: '0 1px 3px rgba(0,0,0,0.08)', padding: '4px 8px 8px',
                  }}>
                    {group.colonies.map((colony, ci) => {
                      const colonyIcon = getContaminantDisplay(colony.primary_contaminant || '', colony.colour_band);
                      const colonyBandColour = getBandColour(colony.colour_band);
                      return (
                        <button
                          key={ci}
                          onClick={() => setSelectedArea(colony)}
                          style={{
                            display: 'flex', alignItems: 'center', width: '100%',
                            background: 'white', padding: '10px 12px', marginTop: 4,
                            borderRadius: 8, border: '1px solid #E8ECF4',
                            textAlign: 'left', gap: 10, cursor: 'pointer',
                          }}
                          type="button"
                        >
                          <div style={{
                            width: 32, height: 32, borderRadius: 8,
                            background: colonyIcon.color + '18', border: `1px solid ${colonyIcon.color}44`,
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            fontSize: 15, flexShrink: 0,
                          }}>
                            {colonyIcon.icon}
                          </div>
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <div style={{ fontSize: 13, fontWeight: 600, color: '#333' }}>
                              {colony.colony_name && colony.colony_name !== 'Unspecified' ? colony.colony_name : t(lang, 'generalAreaReport')}
                            </div>
                            <div style={{ fontSize: 10, color: '#888' }}>
                              {readableContaminant(colony.primary_contaminant || '')} · {colony.report_count} report{colony.report_count !== 1 ? 's' : ''}
                            </div>
                          </div>
                          <div style={{ fontSize: 14, fontWeight: 700, color: colonyBandColour }}>
                            {Math.round(colony.avg_score)}
                          </div>
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default MapPage;
