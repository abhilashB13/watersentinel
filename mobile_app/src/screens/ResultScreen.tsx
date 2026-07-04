/**
 * Module: src/screens/ResultScreen.tsx
 * Purpose: Shows full agent pipeline output to citizen.
 *          Quality score gauge, contaminants, advisory, community
 *          alert (ANTIGRAVITY MOMENT), and complaint draft.
 * Component: Screen 2 — Result
 */

import React, { useState } from 'react';
import {
  View, Text, ScrollView, TouchableOpacity,
  StyleSheet, Alert, Clipboard, Platform,
} from 'react-native';
import { WaterReportResponse, getBandColour, getBandBackground, getBandLabel } from '../api/watersentinel';

interface ResultScreenProps {
  result: WaterReportResponse;
  onNewReport: () => void;
  onViewMap: () => void;
}

const ResultScreen: React.FC<ResultScreenProps> = ({ result, onNewReport, onViewMap }) => {
  const [complaintExpanded, setComplaintExpanded] = useState(false);

  const bandColour = getBandColour(result.colour_band);
  const bandBackground = getBandBackground(result.colour_band);
  const bandLabel = getBandLabel(result.colour_band);

  const copyComplaint = () => {
    Clipboard.setString(result.complaint_draft);
    Alert.alert('Copied!', 'Complaint text copied to clipboard. Paste it in the authority portal or email.');
  };

  return (
    <ScrollView style={styles.container}>

      {/* Quality Score Card */}
      <View style={[styles.scoreCard, { backgroundColor: bandBackground, borderColor: bandColour }]}>
        <Text style={styles.scoreLabel}>Water Quality Score</Text>
        <View style={styles.scoreRow}>
          <Text style={[styles.scoreNumber, { color: bandColour }]}>
            {result.quality_score}
          </Text>
          <Text style={styles.scoreMax}>/100</Text>
        </View>
        <View style={[styles.bandBadge, { backgroundColor: bandColour }]}>
          <Text style={styles.bandText}>{bandLabel}</Text>
        </View>

        {/* Safe to drink/bathe indicators */}
        <View style={styles.safetyRow}>
          <View style={styles.safetyItem}>
            <Text style={styles.safetyIcon}>
              {result.safe_for_drinking ? '✅' : '❌'}
            </Text>
            <Text style={styles.safetyLabel}>Drinking</Text>
          </View>
          <View style={styles.safetyItem}>
            <Text style={styles.safetyIcon}>
              {result.safe_for_bathing ? '✅' : '⚠️'}
            </Text>
            <Text style={styles.safetyLabel}>Bathing</Text>
          </View>
        </View>
      </View>

      {/* Contaminants */}
      {result.contaminants.length > 0 && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>🔬 Identified Issues</Text>
          {result.contaminants.map((c, i) => (
            <View key={i} style={styles.contaminantRow}>
              <Text style={styles.contaminantDot}>●</Text>
              <Text style={styles.contaminantText}>{c}</Text>
            </View>
          ))}
          {result.rag_citations.length > 0 && (
            <Text style={styles.citation}>
              Source: {result.rag_citations[0]}
            </Text>
          )}
        </View>
      )}

      {/* ANTIGRAVITY MOMENT — Community Alert */}
      {result.cluster_detected && result.community_alert ? (
        <View style={styles.communityAlertCard}>
          <Text style={styles.communityAlertIcon}>🚨</Text>
          <Text style={styles.communityAlertTitle}>Community Alert</Text>
          <Text style={styles.communityAlertText}>{result.community_alert}</Text>
          <TouchableOpacity style={styles.mapButton} onPress={onViewMap}>
            <Text style={styles.mapButtonText}>View on Map →</Text>
          </TouchableOpacity>
        </View>
      ) : null}

      {/* Immediate Actions */}
      {result.immediate_actions.length > 0 && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>⚡ Do This Now</Text>
          {result.immediate_actions.map((action, i) => (
            <View key={i} style={styles.actionRow}>
              <Text style={styles.actionNumber}>{i + 1}.</Text>
              <Text style={styles.actionText}>{action}</Text>
            </View>
          ))}
        </View>
      )}

      {/* Long Term Actions */}
      {result.long_term_actions.length > 0 && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>🛡️ Long-Term Solution</Text>
          {result.long_term_actions.map((action, i) => (
            <View key={i} style={styles.actionRow}>
              <Text style={styles.actionNumber}>{i + 1}.</Text>
              <Text style={styles.actionText}>{action}</Text>
            </View>
          ))}
          {result.filter_recommendation ? (
            <View style={styles.filterCard}>
              <Text style={styles.filterTitle}>Recommended Filter</Text>
              <Text style={styles.filterText}>{result.filter_recommendation}</Text>
            </View>
          ) : null}
        </View>
      )}

      {/* Municipal Complaint */}
      {result.escalation_required && result.complaint_draft ? (
        <View style={styles.complaintCard}>
          <Text style={styles.complaintTitle}>📋 Municipal Complaint Ready</Text>
          <Text style={styles.complaintAuthority}>
            To: {result.authority_name}
          </Text>
          {result.authority_email ? (
            <Text style={styles.complaintContact}>✉️ {result.authority_email}</Text>
          ) : null}
          {result.authority_portal ? (
            <Text style={styles.complaintContact}>🌐 {result.authority_portal}</Text>
          ) : null}

          <TouchableOpacity
            style={styles.expandButton}
            onPress={() => setComplaintExpanded(!complaintExpanded)}
          >
            <Text style={styles.expandButtonText}>
              {complaintExpanded ? 'Hide complaint ▲' : 'View complaint ▼'}
            </Text>
          </TouchableOpacity>

          {complaintExpanded && (
            <View style={styles.complaintTextContainer}>
              <Text style={styles.complaintText}>{result.complaint_draft}</Text>
            </View>
          )}

          <TouchableOpacity style={styles.copyButton} onPress={copyComplaint}>
            <Text style={styles.copyButtonText}>📋 Copy Complaint to Clipboard</Text>
          </TouchableOpacity>
        </View>
      ) : null}

      {/* Full Response (collapsed) */}
      {result.full_response && result.full_response.length > 50 && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>📝 Full Analysis</Text>
          <Text style={styles.fullResponseText} numberOfLines={8}>
            {result.advisory_text || result.full_response}
          </Text>
        </View>
      )}

      {/* Action Buttons */}
      <View style={styles.buttonRow}>
        <TouchableOpacity style={styles.secondaryButton} onPress={onViewMap}>
          <Text style={styles.secondaryButtonText}>🗺️ View Map</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.primaryButton} onPress={onNewReport}>
          <Text style={styles.primaryButtonText}>+ New Report</Text>
        </TouchableOpacity>
      </View>

      <View style={{ height: 40 }} />
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F5F7FA' },
  scoreCard: {
    margin: 12,
    borderRadius: 16,
    padding: 20,
    alignItems: 'center',
    borderWidth: 2,
  },
  scoreLabel: { fontSize: 14, color: '#555', marginBottom: 8 },
  scoreRow: { flexDirection: 'row', alignItems: 'flex-end' },
  scoreNumber: { fontSize: 64, fontWeight: 'bold', lineHeight: 72 },
  scoreMax: { fontSize: 20, color: '#888', marginBottom: 10 },
  bandBadge: {
    paddingHorizontal: 16,
    paddingVertical: 6,
    borderRadius: 20,
    marginTop: 8,
  },
  bandText: { color: '#fff', fontWeight: 'bold', fontSize: 14 },
  safetyRow: { flexDirection: 'row', marginTop: 16, gap: 32 },
  safetyItem: { alignItems: 'center' },
  safetyIcon: { fontSize: 24 },
  safetyLabel: { fontSize: 12, color: '#555', marginTop: 4 },
  card: {
    backgroundColor: '#fff',
    margin: 12,
    marginTop: 0,
    borderRadius: 12,
    padding: 16,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 3,
  },
  cardTitle: { fontSize: 15, fontWeight: '600', color: '#1A237E', marginBottom: 12 },
  contaminantRow: { flexDirection: 'row', alignItems: 'flex-start', marginBottom: 6 },
  contaminantDot: { color: '#F44336', marginRight: 8, fontSize: 16 },
  contaminantText: { flex: 1, fontSize: 14, color: '#333' },
  citation: { fontSize: 11, color: '#9E9E9E', marginTop: 8, fontStyle: 'italic' },
  communityAlertCard: {
    backgroundColor: '#FFF3E0',
    margin: 12,
    marginTop: 0,
    borderRadius: 12,
    padding: 16,
    borderLeftWidth: 4,
    borderLeftColor: '#E65100',
  },
  communityAlertIcon: { fontSize: 24, marginBottom: 4 },
  communityAlertTitle: { fontSize: 16, fontWeight: 'bold', color: '#E65100', marginBottom: 8 },
  communityAlertText: { fontSize: 14, color: '#333', lineHeight: 20 },
  mapButton: { marginTop: 12 },
  mapButtonText: { color: '#1565C0', fontSize: 14, fontWeight: '600' },
  actionRow: { flexDirection: 'row', marginBottom: 8, alignItems: 'flex-start' },
  actionNumber: { fontSize: 14, color: '#1565C0', fontWeight: 'bold', marginRight: 8, width: 20 },
  actionText: { flex: 1, fontSize: 14, color: '#333', lineHeight: 20 },
  filterCard: {
    backgroundColor: '#E8F5E9',
    borderRadius: 8,
    padding: 12,
    marginTop: 12,
  },
  filterTitle: { fontSize: 12, color: '#2E7D32', fontWeight: '600' },
  filterText: { fontSize: 14, color: '#1B5E20', marginTop: 2 },
  complaintCard: {
    backgroundColor: '#fff',
    margin: 12,
    marginTop: 0,
    borderRadius: 12,
    padding: 16,
    borderLeftWidth: 4,
    borderLeftColor: '#1565C0',
    elevation: 2,
  },
  complaintTitle: { fontSize: 15, fontWeight: '600', color: '#1A237E', marginBottom: 8 },
  complaintAuthority: { fontSize: 13, color: '#333', marginBottom: 4 },
  complaintContact: { fontSize: 12, color: '#1565C0', marginBottom: 2 },
  expandButton: { marginTop: 12, marginBottom: 4 },
  expandButtonText: { fontSize: 13, color: '#1565C0' },
  complaintTextContainer: {
    backgroundColor: '#F5F5F5',
    borderRadius: 8,
    padding: 12,
    marginTop: 8,
    marginBottom: 8,
  },
  complaintText: { fontSize: 12, color: '#333', lineHeight: 18 },
  copyButton: {
    backgroundColor: '#1565C0',
    borderRadius: 8,
    padding: 12,
    alignItems: 'center',
    marginTop: 8,
  },
  copyButtonText: { color: '#fff', fontSize: 14, fontWeight: '600' },
  fullResponseText: { fontSize: 13, color: '#555', lineHeight: 20 },
  buttonRow: { flexDirection: 'row', margin: 12, gap: 12 },
  primaryButton: {
    flex: 1, backgroundColor: '#1565C0',
    borderRadius: 10, padding: 14, alignItems: 'center',
  },
  primaryButtonText: { color: '#fff', fontWeight: 'bold', fontSize: 15 },
  secondaryButton: {
    flex: 1, borderWidth: 2, borderColor: '#1565C0',
    borderRadius: 10, padding: 14, alignItems: 'center',
  },
  secondaryButtonText: { color: '#1565C0', fontWeight: 'bold', fontSize: 15 },
});

export default ResultScreen;
