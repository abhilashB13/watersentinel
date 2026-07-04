/**
 * Module: src/screens/MapScreen.tsx
 * Purpose: Community water quality topology map. Shows Hyderabad
 *          heatmap with colour-coded quality zones. Citizen can tap
 *          any area to see report count and primary contaminant.
 * Component: Screen 3 — Community Map
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  View, Text, StyleSheet, TouchableOpacity,
  ActivityIndicator, ScrollView, RefreshControl, Platform,
} from 'react-native';
import LeafletMap from '../components/LeafletMap';
import { getTopologyData, TopologyPoint, getBandColour } from '../api/watersentinel';

const MapScreen: React.FC = () => {
  const [topologyData, setTopologyData] = useState<TopologyPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedArea, setSelectedArea] = useState<TopologyPoint | null>(null);
  const [lastUpdated, setLastUpdated] = useState('');

  const loadTopology = useCallback(async () => {
    try {
      const data = await getTopologyData();
      setTopologyData(data);
      setLastUpdated(new Date().toLocaleTimeString());
    } catch (error) {
      console.warn('Map load error:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadTopology();
  }, [loadTopology]);

  const onRefresh = () => {
    setRefreshing(true);
    loadTopology();
  };

  const handlePincodeSelected = (pincode: string, areaName: string) => {
    const point = topologyData.find(p => p.pincode === pincode);
    if (point) setSelectedArea(point);
  };

  // Stats for header
  const redCount = topologyData.filter(p => p.colour_band === 'red').length;
  const totalReports = topologyData.reduce((sum, p) => sum + (p.report_count || 0), 0);

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>🗺️ Water Quality Map</Text>
        <Text style={styles.headerSubtitle}>Hyderabad — Citizen Reports</Text>
        {lastUpdated ? (
          <Text style={styles.lastUpdated}>Updated: {lastUpdated}</Text>
        ) : null}
      </View>

      {/* Stats Bar */}
      <View style={styles.statsBar}>
        <View style={styles.statItem}>
          <Text style={styles.statNumber}>{topologyData.length}</Text>
          <Text style={styles.statLabel}>Areas</Text>
        </View>
        <View style={styles.statDivider} />
        <View style={styles.statItem}>
          <Text style={[styles.statNumber, { color: '#B71C1C' }]}>{redCount}</Text>
          <Text style={styles.statLabel}>Critical Zones</Text>
        </View>
        <View style={styles.statDivider} />
        <View style={styles.statItem}>
          <Text style={styles.statNumber}>{totalReports}</Text>
          <Text style={styles.statLabel}>Total Reports</Text>
        </View>
        <TouchableOpacity style={styles.refreshButton} onPress={onRefresh}>
          <Text style={styles.refreshText}>↻</Text>
        </TouchableOpacity>
      </View>

      {/* Map */}
      {loading ? (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#1565C0" />
          <Text style={styles.loadingText}>Loading community map...</Text>
        </View>
      ) : (
        <View style={styles.mapContainer}>
          <LeafletMap
            topologyData={topologyData}
            onPincodeSelected={handlePincodeSelected}
            initialLat={17.4532}
            initialLng={78.3800}
            initialZoom={11}
          />
        </View>
      )}

      {/* Selected Area Panel */}
      {selectedArea && (
        <View style={[styles.areaPanel, { borderLeftColor: getBandColour(selectedArea.colour_band) }]}>
          <View style={styles.areaPanelHeader}>
            <Text style={styles.areaPanelTitle}>{selectedArea.area_name}</Text>
            <TouchableOpacity onPress={() => setSelectedArea(null)}>
              <Text style={styles.closePanelText}>✕</Text>
            </TouchableOpacity>
          </View>
          <View style={styles.areaPanelDetails}>
            <Text style={styles.areaPanelScore}>
              Score: <Text style={{ color: getBandColour(selectedArea.colour_band), fontWeight: 'bold' }}>
                {selectedArea.avg_score}/100
              </Text>
            </Text>
            <Text style={styles.areaPanelDetail}>
              Reports: {selectedArea.report_count}
            </Text>
            <Text style={styles.areaPanelDetail}>
              Primary issue: {selectedArea.primary_contaminant || 'None detected'}
            </Text>
            <Text style={styles.areaPanelDetail}>
              Pincode: {selectedArea.pincode}
            </Text>
          </View>
        </View>
      )}

      {/* Recent Reports List */}
      {!loading && topologyData.length > 0 && (
        <ScrollView
          style={styles.reportsList}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
          }
        >
          <Text style={styles.reportsListTitle}>Recent Activity</Text>
          {topologyData
            .sort((a, b) => (a.avg_score || 100) - (b.avg_score || 100))
            .slice(0, 8)
            .map((point, i) => (
              <TouchableOpacity
                key={i}
                style={styles.reportItem}
                onPress={() => setSelectedArea(point)}
              >
                <View style={[
                  styles.reportDot,
                  { backgroundColor: getBandColour(point.colour_band) }
                ]} />
                <View style={styles.reportItemContent}>
                  <Text style={styles.reportAreaName}>{point.area_name}</Text>
                  <Text style={styles.reportDetail}>
                    {point.primary_contaminant || 'No issue'} · {point.report_count} report{point.report_count !== 1 ? 's' : ''}
                  </Text>
                </View>
                <Text style={[
                  styles.reportScore,
                  { color: getBandColour(point.colour_band) }
                ]}>
                  {point.avg_score}
                </Text>
              </TouchableOpacity>
            ))}
        </ScrollView>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F5F7FA' },
  header: {
    backgroundColor: '#1565C0',
    padding: 16,
    paddingTop: Platform.OS === 'ios' ? 60 : 40,
  },
  headerTitle: { fontSize: 20, fontWeight: 'bold', color: '#fff' },
  headerSubtitle: { fontSize: 13, color: '#90CAF9', marginTop: 2 },
  lastUpdated: { fontSize: 11, color: '#90CAF9', marginTop: 2 },
  statsBar: {
    flexDirection: 'row',
    backgroundColor: '#fff',
    paddingVertical: 10,
    paddingHorizontal: 16,
    alignItems: 'center',
    borderBottomWidth: 1,
    borderBottomColor: '#E0E0E0',
  },
  statItem: { flex: 1, alignItems: 'center' },
  statNumber: { fontSize: 18, fontWeight: 'bold', color: '#1A237E' },
  statLabel: { fontSize: 11, color: '#757575', marginTop: 2 },
  statDivider: { width: 1, height: 30, backgroundColor: '#E0E0E0' },
  refreshButton: { padding: 8 },
  refreshText: { fontSize: 20, color: '#1565C0' },
  loadingContainer: {
    flex: 1, justifyContent: 'center', alignItems: 'center',
  },
  loadingText: { marginTop: 12, color: '#757575', fontSize: 14 },
  mapContainer: { height: 280 },
  areaPanel: {
    backgroundColor: '#fff',
    margin: 12,
    borderRadius: 10,
    padding: 12,
    borderLeftWidth: 4,
    elevation: 3,
  },
  areaPanelHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  areaPanelTitle: { fontSize: 15, fontWeight: 'bold', color: '#1A237E' },
  closePanelText: { fontSize: 16, color: '#9E9E9E', padding: 4 },
  areaPanelDetails: { gap: 4 },
  areaPanelScore: { fontSize: 14, color: '#333' },
  areaPanelDetail: { fontSize: 13, color: '#555' },
  reportsList: { flex: 1, paddingHorizontal: 12 },
  reportsListTitle: {
    fontSize: 13, fontWeight: '600', color: '#757575',
    paddingVertical: 8, paddingHorizontal: 4,
  },
  reportItem: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    padding: 12,
    marginBottom: 6,
    borderRadius: 8,
    elevation: 1,
  },
  reportDot: { width: 10, height: 10, borderRadius: 5, marginRight: 10 },
  reportItemContent: { flex: 1 },
  reportAreaName: { fontSize: 14, fontWeight: '500', color: '#333' },
  reportDetail: { fontSize: 12, color: '#757575', marginTop: 2 },
  reportScore: { fontSize: 16, fontWeight: 'bold' },
});

export default MapScreen;
