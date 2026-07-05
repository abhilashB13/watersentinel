/**
 * Module: src/api/watersentinel.ts
 * Purpose: API client for WaterSentinel backend.
 * UPDATED: TopologyPoint now includes source_type field.
 *          getTopologyData() accepts optional sourceType param to filter
 *          by water source (municipal_pipeline, borewell, hand_pump, open_well).
 */

export const API_BASE_URL =
  (import.meta as any).env?.VITE_API_BASE_URL || 'http://localhost:8000';

// ── Types ──────────────────────────────────────────────────────────────────────

export interface WaterReportRequest {
  user_message: string;
  pincode: string;
  area_name?: string;
  colony_name?: string;
  source_type?: string;
  symptoms?: string[];
  photo_base64?: string;
  tds_value?: number;
  diagnosed_disease?: boolean;
  frequent_sickness?: boolean;
  algae_in_filters?: boolean;
  tank_sludge?: boolean;
  affected_count?: '1' | '2-3' | '4+';
  since_when?: 'days' | 'weeks' | 'months';
}

export interface WaterReportResponse {
  success: boolean;
  session_id: string;
  timestamp: string;
  quality_score: number;
  colour_band: 'green' | 'yellow' | 'orange' | 'red';
  contaminants: string[];
  safe_for_drinking: boolean;
  safe_for_bathing: boolean;
  advisory_text: string;
  immediate_actions: string[];
  long_term_actions: string[];
  filter_recommendation: string;
  cluster_detected: boolean;
  cluster_count: number;
  community_alert: string;
  escalation_required: boolean;
  complaint_draft: string;
  authority_name: string;
  authority_email: string;
  authority_portal: string;
  map_data_point: object;
  rag_citations: string[];
  full_response: string;
  rag_source: string;
  mcp_calls: string[];
  score_deductions: { factor: string; points: number; note: string }[];
}

export interface TopologyPoint {
  pincode: string;
  area_name: string;
  colony_name: string;
  source_type: string;
  avg_score: number;
  report_count: number;
  primary_contaminant: string;
  colour_band: string;
  lat: number;
  lng: number;
  heat_intensity: number;
  last_updated: string;
}

export interface HealthStatus {
  status: string;
  timestamp: string;
  components: {
    google_api_key: string;
    chroma_db: string;
    sqlite_db: string;
  };
  agents_ready: boolean;
  message: string;
}

// ── API Functions ──────────────────────────────────────────────────────────────

export async function submitWaterReport(
  report: WaterReportRequest
): Promise<WaterReportResponse> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 120000);

  try {
    const response = await fetch(`${API_BASE_URL}/report`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(report),
      signal: controller.signal,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Server error: ${response.status}`);
    }

    return await response.json();
  } catch (error: any) {
    if (error.name === 'AbortError') {
      throw new Error('Request timed out. The agent pipeline is taking too long. Please try again.');
    }
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

/**
 * Fetch topology data for the community map.
 * @param sourceType - optional filter: 'municipal_pipeline' | 'borewell' | 'hand_pump' | 'open_well' | 'all'
 *                      Omit or pass 'all' to get aggregated scores across all sources per area.
 */
export async function getTopologyData(sourceType?: string): Promise<TopologyPoint[]> {
  try {
    const url = sourceType && sourceType !== 'all'
      ? `${API_BASE_URL}/map/topology?source_type=${encodeURIComponent(sourceType)}`
      : `${API_BASE_URL}/map/topology`;

    const response = await fetch(url, {
      headers: { Accept: 'application/json' },
    });
    if (!response.ok) throw new Error(`Status ${response.status}`);
    return await response.json();
  } catch (error) {
    console.warn('Backend offline — using mock topology data:', error);
    return getMockTopologyData();
  }
}

export async function getPincodeHistory(pincode: string, days: number = 30): Promise<any> {
  const response = await fetch(
    `${API_BASE_URL}/map/pincode/${pincode}/history?days=${days}`,
    { headers: { Accept: 'application/json' } }
  );
  if (!response.ok) throw new Error(`Status ${response.status}`);
  return response.json();
}

export async function checkHealth(): Promise<HealthStatus> {
  const response = await fetch(`${API_BASE_URL}/health`, {
    headers: { Accept: 'application/json' },
  });
  if (!response.ok) throw new Error(`Status ${response.status}`);
  return response.json();
}

// ── Mock Topology Data (fallback when backend offline) ─────────────────────────
// Now includes source_type variety — demonstrates the same area having
// different scores depending on water source (municipal vs borewell etc.)

export function getMockTopologyData(): TopologyPoint[] {
  return [
    // Nallagandla — MIG/LIG/HIG colony-level variety demonstration
    { pincode: '500032', area_name: 'Nallagandla', colony_name: 'MIG Colony Phase 1', source_type: 'borewell', avg_score: 42, report_count: 3, primary_contaminant: 'H2S', colour_band: 'orange', lat: 17.4620, lng: 78.3150, heat_intensity: 0.55, last_updated: new Date().toISOString() },
    { pincode: '500032', area_name: 'Nallagandla', colony_name: 'LIG Colony', source_type: 'borewell', avg_score: 26, report_count: 2, primary_contaminant: 'Iron', colour_band: 'red', lat: 17.4635, lng: 78.3165, heat_intensity: 0.72, last_updated: new Date().toISOString() },
    { pincode: '500032', area_name: 'Nallagandla', colony_name: 'HIG Colony', source_type: 'municipal_pipeline', avg_score: 84, report_count: 1, primary_contaminant: 'None', colour_band: 'green', lat: 17.4610, lng: 78.3140, heat_intensity: 0.15, last_updated: new Date().toISOString() },

    // Gachibowli — municipal good, borewell has H2S
    { pincode: '500032', area_name: 'Gachibowli', colony_name: 'Unspecified', source_type: 'municipal_pipeline', avg_score: 82, report_count: 1, primary_contaminant: 'None', colour_band: 'green', lat: 17.4400, lng: 78.3489, heat_intensity: 0.2, last_updated: new Date().toISOString() },
    { pincode: '500032', area_name: 'Gachibowli', colony_name: 'Unspecified', source_type: 'borewell', avg_score: 44, report_count: 2, primary_contaminant: 'H2S', colour_band: 'orange', lat: 17.4402, lng: 78.3491, heat_intensity: 0.55, last_updated: new Date().toISOString() },

    // Kondapur — municipal good, borewell high TDS
    { pincode: '500084', area_name: 'Kondapur', colony_name: 'Unspecified', source_type: 'municipal_pipeline', avg_score: 87, report_count: 2, primary_contaminant: 'None', colour_band: 'green', lat: 17.4590, lng: 78.3670, heat_intensity: 0.15, last_updated: new Date().toISOString() },
    { pincode: '500084', area_name: 'Kondapur', colony_name: 'Unspecified', source_type: 'borewell', avg_score: 32, report_count: 3, primary_contaminant: 'High_TDS', colour_band: 'red', lat: 17.4592, lng: 78.3672, heat_intensity: 0.7, last_updated: new Date().toISOString() },

    // Madhapur — municipal moderate, hand pump bad
    { pincode: '500081', area_name: 'Madhapur', colony_name: 'Unspecified', source_type: 'municipal_pipeline', avg_score: 68, report_count: 1, primary_contaminant: 'None', colour_band: 'yellow', lat: 17.4483, lng: 78.3915, heat_intensity: 0.35, last_updated: new Date().toISOString() },
    { pincode: '500081', area_name: 'Madhapur', colony_name: 'Unspecified', source_type: 'hand_pump', avg_score: 25, report_count: 1, primary_contaminant: 'Sewage_Contamination', colour_band: 'red', lat: 17.4485, lng: 78.3917, heat_intensity: 0.78, last_updated: new Date().toISOString() },

    // Kukatpally — municipal moderate, open well critical
    { pincode: '500072', area_name: 'Kukatpally', colony_name: 'Unspecified', source_type: 'municipal_pipeline', avg_score: 79, report_count: 1, primary_contaminant: 'None', colour_band: 'yellow', lat: 17.4849, lng: 78.3994, heat_intensity: 0.29, last_updated: new Date().toISOString() },
    { pincode: '500072', area_name: 'Kukatpally', colony_name: 'Unspecified', source_type: 'open_well', avg_score: 18, report_count: 1, primary_contaminant: 'Fecal_Coliform', colour_band: 'red', lat: 17.4851, lng: 78.3996, heat_intensity: 0.81, last_updated: new Date().toISOString() },

    // Remaining single-source areas
    { pincode: '500019', area_name: 'Tellapur', colony_name: 'Unspecified', source_type: 'borewell', avg_score: 33, report_count: 2, primary_contaminant: 'Iron', colour_band: 'red', lat: 17.4701, lng: 78.2801, heat_intensity: 0.67, last_updated: new Date().toISOString() },
    { pincode: '500086', area_name: 'Patancheru', colony_name: 'Unspecified', source_type: 'borewell', avg_score: 22, report_count: 1, primary_contaminant: 'Iron', colour_band: 'red', lat: 17.5280, lng: 78.2648, heat_intensity: 0.78, last_updated: new Date().toISOString() },
    { pincode: '502001', area_name: 'Sangareddy', colony_name: 'Unspecified', source_type: 'borewell', avg_score: 19, report_count: 1, primary_contaminant: 'Fluoride', colour_band: 'red', lat: 17.6200, lng: 78.0900, heat_intensity: 0.81, last_updated: new Date().toISOString() },
    { pincode: '500074', area_name: 'LB Nagar', colony_name: 'Unspecified', source_type: 'municipal_pipeline', avg_score: 67, report_count: 1, primary_contaminant: 'None', colour_band: 'yellow', lat: 17.3547, lng: 78.5524, heat_intensity: 0.33, last_updated: new Date().toISOString() },
  ];
}

// ── Colour Utilities ───────────────────────────────────────────────────────────

export function getBandColour(band: string): string {
  const colours: Record<string, string> = {
    green: '#2E7D32', yellow: '#F9A825', orange: '#E65100', red: '#B71C1C',
  };
  return colours[band] || '#757575';
}

export function getBandBackground(band: string): string {
  const backgrounds: Record<string, string> = {
    green: '#E8F5E9', yellow: '#FFF8E1', orange: '#FBE9E7', red: '#FFEBEE',
  };
  return backgrounds[band] || '#F5F5F5';
}

export function getBandLabel(band: string): string {
  const labels: Record<string, string> = {
    green: 'Safe', yellow: 'Monitor', orange: 'Caution', red: 'Do Not Drink',
  };
  return labels[band] || 'Unknown';
}
