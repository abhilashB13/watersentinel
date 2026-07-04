/**
 * Module: src/screens/AboutScreen.tsx
 * Purpose: Explains how WaterSentinel works, privacy policy,
 *          competition credits, and links to authorities.
 * Component: Screen 4 — About
 */

import React from 'react';
import {
  View, Text, ScrollView, StyleSheet,
  TouchableOpacity, Linking, Platform,
} from 'react-native';

const AboutScreen: React.FC = () => {
  const openLink = (url: string) => {
    Linking.openURL(url).catch(() => {});
  };

  return (
    <ScrollView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerEmoji}>💧</Text>
        <Text style={styles.headerTitle}>WaterSentinel</Text>
        <Text style={styles.headerTagline}>
          The water quality intelligence map India never had
        </Text>
      </View>

      {/* How It Works */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>How It Works</Text>

        {[
          { step: '1', icon: '📝', title: 'You Report', desc: 'Describe what you observe — smell, colour, taste. No sensor needed.' },
          { step: '2', icon: '🤖', title: 'AI Analyses', desc: '5 AI agents diagnose your water against BIS IS 10500 Indian standards.' },
          { step: '3', icon: '🏘️', title: 'Community Alerts', desc: 'If neighbours report the same issue, WaterSentinel detects it automatically.' },
          { step: '4', icon: '📋', title: 'Action Taken', desc: 'Get a personal advisory and, if needed, a ready-to-file municipal complaint.' },
        ].map(item => (
          <View key={item.step} style={styles.stepRow}>
            <View style={styles.stepCircle}>
              <Text style={styles.stepIcon}>{item.icon}</Text>
            </View>
            <View style={styles.stepContent}>
              <Text style={styles.stepTitle}>{item.title}</Text>
              <Text style={styles.stepDesc}>{item.desc}</Text>
            </View>
          </View>
        ))}
      </View>

      {/* AI Architecture */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>🧠 AI Architecture</Text>
        {[
          { name: 'Orchestrator', desc: 'Coordinates all agents' },
          { name: 'SourceSense', desc: 'Classifies water source and symptoms' },
          { name: 'WaterProfiler', desc: 'Diagnoses contaminants using BIS/WHO knowledge' },
          { name: 'CommunityMapper', desc: 'Detects community clusters' },
          { name: 'ActionForge', desc: 'Generates advisories and complaints' },
        ].map((agent, i) => (
          <View key={i} style={styles.agentRow}>
            <View style={styles.agentDot} />
            <View>
              <Text style={styles.agentName}>{agent.name}</Text>
              <Text style={styles.agentDesc}>{agent.desc}</Text>
            </View>
          </View>
        ))}
        <Text style={styles.techNote}>
          Built with Google ADK · Gemini 2.0 Flash · BIS IS 10500:2012 · WHO Guidelines · CGWB Data
        </Text>
      </View>

      {/* Privacy */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>🔒 Privacy</Text>
        {[
          'Only your pincode is stored — never your street address or GPS coordinates',
          'Photos are analysed in memory and immediately discarded',
          'No user account or login required — fully anonymous reporting',
          'No data is sold or shared with advertisers',
        ].map((item, i) => (
          <View key={i} style={styles.privacyRow}>
            <Text style={styles.privacyCheck}>✓</Text>
            <Text style={styles.privacyText}>{item}</Text>
          </View>
        ))}
      </View>

      {/* Useful Contacts */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>📞 Useful Contacts</Text>
        {[
          { label: 'HMWSSB Helpline (Hyderabad)', value: '155313', type: 'phone' },
          { label: 'VWSS Helpline (Vijayawada)', value: '0866-2578888', type: 'phone' },
          { label: 'CGWB Groundwater Queries', value: '040-23220892', type: 'phone' },
          { label: 'National Water Quality Helpline', value: '1800-180-1551', type: 'phone' },
          { label: 'HMWSSB Online Complaints', value: 'hmwssb.telangana.gov.in', type: 'link' },
        ].map((contact, i) => (
          <TouchableOpacity
            key={i}
            style={styles.contactRow}
            onPress={() => {
              if (contact.type === 'phone') {
                openLink(`tel:${contact.value.replace(/-/g, '')}`);
              } else {
                openLink(`https://${contact.value}`);
              }
            }}
          >
            <Text style={styles.contactLabel}>{contact.label}</Text>
            <Text style={styles.contactValue}>{contact.value}</Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Competition Credits */}
      <View style={[styles.card, styles.creditsCard]}>
        <Text style={styles.cardTitle}>🏆 Competition</Text>
        <Text style={styles.creditsText}>
          Submitted to: Kaggle AI Agents Intensive Capstone 2026{'\n'}
          Track: Agents for Good{'\n'}
          Built with: Google ADK, FastMCP, ChromaDB, React Native, Leaflet.js{'\n'}
          Knowledge: BIS IS 10500:2012 · WHO 2022 · CGWB Telangana/AP 2023{'\n'}
          Map: OpenStreetMap (© contributors)
        </Text>
      </View>

      <View style={{ height: 40 }} />
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F5F7FA' },
  header: {
    backgroundColor: '#1565C0',
    padding: 32,
    paddingTop: Platform.OS === 'ios' ? 60 : 40,
    alignItems: 'center',
  },
  headerEmoji: { fontSize: 48, marginBottom: 8 },
  headerTitle: { fontSize: 28, fontWeight: 'bold', color: '#fff' },
  headerTagline: {
    fontSize: 13, color: '#90CAF9', textAlign: 'center',
    marginTop: 6, paddingHorizontal: 20,
  },
  card: {
    backgroundColor: '#fff',
    margin: 12,
    marginBottom: 0,
    borderRadius: 12,
    padding: 16,
    elevation: 2,
  },
  cardTitle: { fontSize: 15, fontWeight: '600', color: '#1A237E', marginBottom: 14 },
  stepRow: { flexDirection: 'row', marginBottom: 14, alignItems: 'flex-start' },
  stepCircle: {
    width: 40, height: 40, borderRadius: 20,
    backgroundColor: '#E3F2FD', justifyContent: 'center',
    alignItems: 'center', marginRight: 12,
  },
  stepIcon: { fontSize: 18 },
  stepContent: { flex: 1 },
  stepTitle: { fontSize: 14, fontWeight: '600', color: '#333' },
  stepDesc: { fontSize: 13, color: '#555', marginTop: 2, lineHeight: 18 },
  agentRow: { flexDirection: 'row', alignItems: 'flex-start', marginBottom: 10 },
  agentDot: {
    width: 8, height: 8, borderRadius: 4,
    backgroundColor: '#1565C0', marginRight: 10, marginTop: 5,
  },
  agentName: { fontSize: 14, fontWeight: '600', color: '#333' },
  agentDesc: { fontSize: 12, color: '#757575' },
  techNote: {
    fontSize: 11, color: '#9E9E9E', marginTop: 10,
    fontStyle: 'italic', lineHeight: 16,
  },
  privacyRow: { flexDirection: 'row', marginBottom: 8, alignItems: 'flex-start' },
  privacyCheck: { color: '#2E7D32', fontSize: 16, marginRight: 8, lineHeight: 20 },
  privacyText: { flex: 1, fontSize: 13, color: '#333', lineHeight: 18 },
  contactRow: {
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#F0F0F0',
  },
  contactLabel: { fontSize: 13, color: '#555' },
  contactValue: { fontSize: 14, fontWeight: '600', color: '#1565C0', marginTop: 2 },
  creditsCard: { marginBottom: 12 },
  creditsText: { fontSize: 13, color: '#555', lineHeight: 22 },
});

export default AboutScreen;
