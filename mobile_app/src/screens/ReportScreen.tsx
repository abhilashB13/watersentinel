/**
 * Module: src/screens/ReportScreen.tsx
 * Purpose: Home screen. Citizen selects water source, picks symptoms,
 *          describes issue in text, optionally uploads photo, submits.
 * Component: Screen 1 — Report
 */

import React, { useState } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, ScrollView,
  StyleSheet, Alert, ActivityIndicator, Image, Platform,
} from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import { submitWaterReport, WaterReportResponse } from '../api/watersentinel';

// ── Types ──────────────────────────────────────────────────────────────────────

interface ReportScreenProps {
  onReportComplete: (result: WaterReportResponse) => void;
}

// ── Constants ──────────────────────────────────────────────────────────────────

const SOURCE_TYPES = [
  { id: 'borewell',          label: 'Borewell',         icon: '⛏️' },
  { id: 'municipal_pipeline', label: 'Municipal Pipe',   icon: '🚰' },
  { id: 'hand_pump',         label: 'Hand Pump',        icon: '💧' },
  { id: 'open_well',         label: 'Open Well',        icon: '🪣' },
];

const SYMPTOM_OPTIONS = [
  { id: 'egg_smell',        label: 'Egg / Sulphur Smell' },
  { id: 'yellow_colour',    label: 'Yellow / Brown Water' },
  { id: 'black_colour',     label: 'Black / Dark Water' },
  { id: 'white_deposits',   label: 'White Deposits on Taps' },
  { id: 'blue_green_stain', label: 'Blue-Green Staining' },
  { id: 'metallic_taste',   label: 'Metallic Taste' },
  { id: 'salty_taste',      label: 'Salty / Bitter Taste' },
  { id: 'milky_appearance', label: 'Milky / Cloudy Water' },
  { id: 'stomach_issues',   label: 'Stomach Issues in Family' },
  { id: 'no_visible_symptom', label: 'No Visible Symptom' },
];

// ── Component ──────────────────────────────────────────────────────────────────

const ReportScreen: React.FC<ReportScreenProps> = ({ onReportComplete }) => {
  const [sourceType, setSourceType] = useState('');
  const [selectedSymptoms, setSelectedSymptoms] = useState<string[]>([]);
  const [description, setDescription] = useState('');
  const [pincode, setPincode] = useState('');
  const [areaName, setAreaName] = useState('');
  const [photoBase64, setPhotoBase64] = useState('');
  const [photoUri, setPhotoUri] = useState('');
  const [loading, setLoading] = useState(false);

  // ── Symptom Toggle ───────────────────────────────────────────────────────────

  const toggleSymptom = (id: string) => {
    setSelectedSymptoms(prev =>
      prev.includes(id) ? prev.filter(s => s !== id) : [...prev, id]
    );
  };

  // ── Photo Picker ─────────────────────────────────────────────────────────────

  const pickPhoto = async () => {
    const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (status !== 'granted') {
      Alert.alert('Permission needed', 'Please allow photo access to upload a water sample image.');
      return;
    }

    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsEditing: true,
      aspect: [4, 3],
      quality: 0.7,
      base64: true, // Get base64 for API upload
    });

    if (!result.canceled && result.assets[0]) {
      setPhotoUri(result.assets[0].uri);
      setPhotoBase64(result.assets[0].base64 || '');
    }
  };

  const takePhoto = async () => {
    const { status } = await ImagePicker.requestCameraPermissionsAsync();
    if (status !== 'granted') {
      Alert.alert('Permission needed', 'Please allow camera access to take a water sample photo.');
      return;
    }

    const result = await ImagePicker.launchCameraAsync({
      allowsEditing: true,
      aspect: [4, 3],
      quality: 0.7,
      base64: true,
    });

    if (!result.canceled && result.assets[0]) {
      setPhotoUri(result.assets[0].uri);
      setPhotoBase64(result.assets[0].base64 || '');
    }
  };

  // ── Submit ───────────────────────────────────────────────────────────────────

  const handleSubmit = async () => {
    // Validation
    if (!sourceType) {
      Alert.alert('Select source', 'Please select your water source type.');
      return;
    }
    if (!pincode || pincode.length !== 6 || !pincode.match(/^\d{6}$/)) {
      Alert.alert('Invalid pincode', 'Please enter a valid 6-digit pincode.');
      return;
    }
    if (selectedSymptoms.length === 0 && description.trim().length < 10) {
      Alert.alert(
        'Add details',
        'Please select at least one symptom or describe the issue (min 10 characters).'
      );
      return;
    }

    // Build user message from selections + description
    const symptomLabels = selectedSymptoms.map(
      id => SYMPTOM_OPTIONS.find(s => s.id === id)?.label || id
    );
    const sourceLabel = SOURCE_TYPES.find(s => s.id === sourceType)?.label || sourceType;

    let userMessage = `Water source: ${sourceLabel}. `;
    if (symptomLabels.length > 0) {
      userMessage += `Symptoms: ${symptomLabels.join(', ')}. `;
    }
    if (description.trim()) {
      userMessage += description.trim();
    }
    if (areaName.trim()) {
      userMessage += ` Location: ${areaName.trim()}.`;
    }

    setLoading(true);

    try {
      const result = await submitWaterReport({
        user_message: userMessage,
        pincode,
        area_name: areaName.trim(),
        source_type: sourceType,
        symptoms: selectedSymptoms,
        photo_base64: photoBase64 || undefined,
      });

      onReportComplete(result);
    } catch (error: any) {
      Alert.alert(
        'Submission failed',
        error.message || 'Could not reach WaterSentinel server. Check your connection.',
        [{ text: 'OK' }]
      );
    } finally {
      setLoading(false);
    }
  };

  // ── Render ───────────────────────────────────────────────────────────────────

  return (
    <ScrollView style={styles.container} keyboardShouldPersistTaps="handled">
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>💧 WaterSentinel</Text>
        <Text style={styles.headerSubtitle}>Report your water quality issue</Text>
      </View>

      {/* Source Type */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Water Source *</Text>
        <View style={styles.sourceGrid}>
          {SOURCE_TYPES.map(source => (
            <TouchableOpacity
              key={source.id}
              style={[
                styles.sourceCard,
                sourceType === source.id && styles.sourceCardSelected,
              ]}
              onPress={() => setSourceType(source.id)}
            >
              <Text style={styles.sourceIcon}>{source.icon}</Text>
              <Text style={[
                styles.sourceLabel,
                sourceType === source.id && styles.sourceLabelSelected,
              ]}>
                {source.label}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>

      {/* Symptoms */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>What do you observe?</Text>
        <View style={styles.symptomsContainer}>
          {SYMPTOM_OPTIONS.map(symptom => (
            <TouchableOpacity
              key={symptom.id}
              style={[
                styles.symptomChip,
                selectedSymptoms.includes(symptom.id) && styles.symptomChipSelected,
              ]}
              onPress={() => toggleSymptom(symptom.id)}
            >
              <Text style={[
                styles.symptomLabel,
                selectedSymptoms.includes(symptom.id) && styles.symptomLabelSelected,
              ]}>
                {symptom.label}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>

      {/* Description */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Describe the issue</Text>
        <TextInput
          style={styles.textInput}
          placeholder="E.g. My water smells like rotten eggs and the taps have yellowish stains..."
          multiline
          numberOfLines={4}
          value={description}
          onChangeText={setDescription}
          maxLength={500}
        />
        <Text style={styles.charCount}>{description.length}/500</Text>
      </View>

      {/* Location */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Location *</Text>
        <TextInput
          style={styles.textInputSingle}
          placeholder="6-digit Pincode (e.g. 500032)"
          value={pincode}
          onChangeText={text => setPincode(text.replace(/\D/g, '').slice(0, 6))}
          keyboardType="numeric"
          maxLength={6}
        />
        <TextInput
          style={[styles.textInputSingle, { marginTop: 8 }]}
          placeholder="Area / Colony name (e.g. Nallagandla)"
          value={areaName}
          onChangeText={setAreaName}
          maxLength={100}
        />
        <Text style={styles.privacyNote}>
          🔒 Only your pincode is stored — no street address, no GPS
        </Text>
      </View>

      {/* Photo */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Add a photo (optional)</Text>
        <Text style={styles.photoHint}>
          Fill a white vessel with your water and photograph it for better diagnosis
        </Text>
        <View style={styles.photoButtons}>
          <TouchableOpacity style={styles.photoButton} onPress={takePhoto}>
            <Text style={styles.photoButtonText}>📷 Take Photo</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.photoButton} onPress={pickPhoto}>
            <Text style={styles.photoButtonText}>🖼️ Choose Photo</Text>
          </TouchableOpacity>
        </View>
        {photoUri ? (
          <View style={styles.photoPreview}>
            <Image source={{ uri: photoUri }} style={styles.photoImage} />
            <TouchableOpacity
              style={styles.removePhoto}
              onPress={() => { setPhotoUri(''); setPhotoBase64(''); }}
            >
              <Text style={styles.removePhotoText}>✕ Remove</Text>
            </TouchableOpacity>
          </View>
        ) : null}
      </View>

      {/* Submit */}
      <TouchableOpacity
        style={[styles.submitButton, loading && styles.submitButtonDisabled]}
        onPress={handleSubmit}
        disabled={loading}
      >
        {loading ? (
          <View style={styles.loadingContainer}>
            <ActivityIndicator color="#fff" size="small" />
            <Text style={styles.submitButtonText}>  Analysing with AI agents...</Text>
          </View>
        ) : (
          <Text style={styles.submitButtonText}>🔍 Analyse My Water</Text>
        )}
      </TouchableOpacity>

      {loading && (
        <Text style={styles.loadingNote}>
          5 AI agents are working on your report. This takes 30–60 seconds.
        </Text>
      )}

      <View style={{ height: 40 }} />
    </ScrollView>
  );
};

// ── Styles ─────────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F5F7FA' },
  header: {
    backgroundColor: '#1565C0',
    padding: 24,
    paddingTop: Platform.OS === 'ios' ? 60 : 40,
  },
  headerTitle: { fontSize: 24, fontWeight: 'bold', color: '#fff' },
  headerSubtitle: { fontSize: 14, color: '#90CAF9', marginTop: 4 },
  section: {
    backgroundColor: '#fff',
    margin: 12,
    marginBottom: 0,
    borderRadius: 12,
    padding: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 3,
    elevation: 2,
  },
  sectionTitle: { fontSize: 15, fontWeight: '600', color: '#1A237E', marginBottom: 12 },
  sourceGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  sourceCard: {
    width: '47%',
    borderWidth: 2,
    borderColor: '#E0E0E0',
    borderRadius: 10,
    padding: 12,
    alignItems: 'center',
    backgroundColor: '#FAFAFA',
  },
  sourceCardSelected: { borderColor: '#1565C0', backgroundColor: '#E3F2FD' },
  sourceIcon: { fontSize: 28, marginBottom: 6 },
  sourceLabel: { fontSize: 13, color: '#555', textAlign: 'center' },
  sourceLabelSelected: { color: '#1565C0', fontWeight: '600' },
  symptomsContainer: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  symptomChip: {
    borderWidth: 1,
    borderColor: '#BDBDBD',
    borderRadius: 20,
    paddingHorizontal: 12,
    paddingVertical: 6,
    backgroundColor: '#FAFAFA',
  },
  symptomChipSelected: { borderColor: '#1565C0', backgroundColor: '#E3F2FD' },
  symptomLabel: { fontSize: 13, color: '#555' },
  symptomLabelSelected: { color: '#1565C0', fontWeight: '500' },
  textInput: {
    borderWidth: 1,
    borderColor: '#E0E0E0',
    borderRadius: 8,
    padding: 12,
    fontSize: 14,
    color: '#333',
    minHeight: 100,
    textAlignVertical: 'top',
  },
  textInputSingle: {
    borderWidth: 1,
    borderColor: '#E0E0E0',
    borderRadius: 8,
    padding: 12,
    fontSize: 14,
    color: '#333',
  },
  charCount: { fontSize: 11, color: '#9E9E9E', textAlign: 'right', marginTop: 4 },
  privacyNote: { fontSize: 11, color: '#4CAF50', marginTop: 8 },
  photoHint: { fontSize: 12, color: '#757575', marginBottom: 10 },
  photoButtons: { flexDirection: 'row', gap: 10 },
  photoButton: {
    flex: 1,
    borderWidth: 1,
    borderColor: '#1565C0',
    borderRadius: 8,
    padding: 10,
    alignItems: 'center',
  },
  photoButtonText: { fontSize: 13, color: '#1565C0' },
  photoPreview: { marginTop: 12, alignItems: 'center' },
  photoImage: { width: '100%', height: 150, borderRadius: 8, resizeMode: 'cover' },
  removePhoto: { marginTop: 6 },
  removePhotoText: { fontSize: 12, color: '#F44336' },
  submitButton: {
    backgroundColor: '#1565C0',
    margin: 16,
    marginTop: 20,
    borderRadius: 12,
    padding: 18,
    alignItems: 'center',
  },
  submitButtonDisabled: { backgroundColor: '#90A4AE' },
  submitButtonText: { fontSize: 16, fontWeight: 'bold', color: '#fff' },
  loadingContainer: { flexDirection: 'row', alignItems: 'center' },
  loadingNote: {
    textAlign: 'center',
    fontSize: 12,
    color: '#757575',
    marginHorizontal: 20,
    marginTop: -8,
  },
});

export default ReportScreen;
