/**
 * Module: src/api/watersentinel.ts
 * Purpose: API client for all WaterSentinel backend calls.
 *          Single source of truth for API URLs and request shapes.
 * Component: Mobile App — API Layer
 * Key Design Decisions:
 *   - API_BASE_URL from env or localhost default: change to ngrok URL
 *     when testing on physical device (localhost won't work on phone).
 *   - Typed request/response interfaces: prevents runtime shape errors.
 *   - Timeout on all requests: 120s matches backend pipeline timeout.
 *   - Fallback mock data for /map/topology: map still renders even if
 *     backend is offline (useful for demo recording).
 */

import { Platform } from 'react-native';

// ── API Base URL ───────────────────────────────────────────────────────────────
// IMPORTANT: Change this when testing on physical device.
// localhost works on Android emulator and iOS simulator.
// For physical device: use ngrok URL e.g. https://abc123.ngrok.io
// For Cloud Run deployment: use your Cloud Run URL

const getBaseUrl = (): string => {
  // Android emulator uses 10.0.2.2 to reach host machine localhost
  if (Platform.OS === 'android') {
    return 'http://10.0.2.2:8000';
  }
  return 'http://localhost:8000';
};

export const API_BASE_URL = getBaseUrl();

// ── Request Types ──────────────────────────────────────────────────────────────

export interface WaterReportRequest {
  user_message: string;
  pincode: string;
  area_name?: string;
  source_type?: string;
  symptoms?: string[];
  photo_base64?: string;
}

// ── Response Types ─────────────────────────────────────────────────────────────

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
}

export interface TopologyPoint {
  pincode: string;
  area_name: string;
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

/**
 * Submit a water quality report and run the 5-agent pipeline.
 * Returns full diagnosis, advisory, community intelligence and complaint.
 */
export async function submitWaterReport(
  report: WaterReportRequest
): Promise<WaterReportResponse> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 120000); // 120s timeout

  try {
    const response = await fetch(`${API_BASE_URL}/report`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify(report),
      signal: controller.signal,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(
        errorData.detail || `Server error: ${response.status}`
      );
    }

    return await response.json();
  } catch (error: any) {
    if (error.name === 'AbortError') {
      throw new Error(
        'Request timed out. The agent pipeline is taking too long. Please try again.'
      );
    }
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

/**
 * Fetch all pincode topology scores for the Leaflet heatmap.
 * Falls back to mock data if backend is offline (for demo recording).
 */
export async function getTopologyData(): Promise<TopologyPoint[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/map/topology`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
    });

    if (!response.ok) throw new Error(`Status ${response.status}`);
    return await response.json();
  } catch (error) {
    console.warn('Backend offline — using mock topology data:', error);
    // Return mock data so map always renders during demo
    return getMockTopologyData();
  }
}

/**
 * Get water quality history for a specific pincode.
 */
export async function getPincodeHistory(
  pincode: string,
  days: number = 30
): Promise<any> {
  const response = await fetch(
    `${API_BASE_URL}/map/pincode/${pincode}/history?days=${days}`,
    { headers: { Accept: 'application/json' } }
  );
  if (!response.ok) throw new Error(`Status ${response.status}`);
  return response.json();
}

/**
 * Check backend health status.
 */
export async function checkHealth(): Promise<HealthStatus> {
  const response = await fetch(`${API_BASE_URL}/health`, {
    headers: { Accept: 'application/json' },
  });
  if (!response.ok) throw new Error(`Status ${response.status}`);
  return response.json();
}

// ── Mock Topology Data (fallback when backend offline) ─────────────────────────

export function getMockTopologyData(): TopologyPoint[] {
  return [
    { pincode: '500032', area_name: 'Nallagandla', avg_score: 28, report_count: 4, primary_contaminant: 'H2S', colour_band: 'red', lat: 17.4532, lng: 78.3241, heat_intensity: 0.72, last_updated: new Date().toISOString() },
    { pincode: '500032', area_name: 'BHEL MIG Colony', avg_score: 32, report_count: 2, primary_contaminant: 'H2S', colour_band: 'red', lat: 17.4620, lng: 78.3150, heat_intensity: 0.68, last_updated: new Date().toISOString() },
    { pincode: '500032', area_name: 'BHEL LIG Colony', avg_score: 35, report_count: 1, primary_contaminant: 'Iron', colour_band: 'red', lat: 17.4580, lng: 78.3200, heat_intensity: 0.65, last_updated: new Date().toISOString() },
    { pincode: '500055', area_name: 'Ramachandrapuram', avg_score: 48, report_count: 1, primary_contaminant: 'High_TDS', colour_band: 'orange', lat: 17.4400, lng: 78.3600, heat_intensity: 0.52, last_updated: new Date().toISOString() },
    { pincode: '500084', area_name: 'Kondapur', avg_score: 71, report_count: 1, primary_contaminant: 'None', colour_band: 'yellow', lat: 17.4900, lng: 78.3900, heat_intensity: 0.29, last_updated: new Date().toISOString() },
    { pincode: '500081', area_name: 'Madhapur', avg_score: 65, report_count: 1, primary_contaminant: 'None', colour_band: 'yellow', lat: 17.4479, lng: 78.3882, heat_intensity: 0.35, last_updated: new Date().toISOString() },
    { pincode: '500049', area_name: 'Miyapur', avg_score: 55, report_count: 1, primary_contaminant: 'Iron', colour_band: 'yellow', lat: 17.4960, lng: 78.3549, heat_intensity: 0.45, last_updated: new Date().toISOString() },
    { pincode: '500019', area_name: 'Tellapur', avg_score: 33, report_count: 2, primary_contaminant: 'Iron', colour_band: 'red', lat: 17.4701, lng: 78.2801, heat_intensity: 0.67, last_updated: new Date().toISOString() },
    { pincode: '500086', area_name: 'Patancheru', avg_score: 22, report_count: 1, primary_contaminant: 'Iron', colour_band: 'red', lat: 17.5280, lng: 78.2648, heat_intensity: 0.78, last_updated: new Date().toISOString() },
    { pincode: '502001', area_name: 'Sangareddy', avg_score: 19, report_count: 1, primary_contaminant: 'Fluoride', colour_band: 'red', lat: 17.6200, lng: 78.0900, heat_intensity: 0.81, last_updated: new Date().toISOString() },
    { pincode: '500072', area_name: 'Kukatpally', avg_score: 52, report_count: 1, primary_contaminant: 'TDS', colour_band: 'yellow', lat: 17.4849, lng: 78.3994, heat_intensity: 0.48, last_updated: new Date().toISOString() },
    { pincode: '500074', area_name: 'LB Nagar', avg_score: 67, report_count: 1, primary_contaminant: 'None', colour_band: 'yellow', lat: 17.3547, lng: 78.5524, heat_intensity: 0.33, last_updated: new Date().toISOString() },
  ];
}

// ── Colour Utilities ───────────────────────────────────────────────────────────

export function getBandColour(band: string): string {
  const colours: Record<string, string> = {
    green: '#2E7D32',
    yellow: '#F9A825',
    orange: '#E65100',
    red: '#B71C1C',
  };
  return colours[band] || '#757575';
}

export function getBandBackground(band: string): string {
  const backgrounds: Record<string, string> = {
    green: '#E8F5E9',
    yellow: '#FFF8E1',
    orange: '#FBE9E7',
    red: '#FFEBEE',
  };
  return backgrounds[band] || '#F5F5F5';
}

export function getBandLabel(band: string): string {
  const labels: Record<string, string> = {
    green: 'Safe',
    yellow: 'Monitor',
    orange: 'Caution',
    red: 'Do Not Drink',
  };
  return labels[band] || 'Unknown';
}
