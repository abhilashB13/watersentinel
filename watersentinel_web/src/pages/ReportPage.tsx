/**
 * Module: src/pages/ReportPage.tsx
 * Changes from previous version:
 *   - AgentProgress component shown during loading instead of spinner
 *   - No other logic changes
 */

import React, { useState, useRef, useEffect } from 'react';
import { submitWaterReport, WaterReportResponse } from '../api/watersentinel';
import AgentProgress from '../components/AgentProgress';

interface ReportPageProps {
  onReportComplete: (result: WaterReportResponse, pincode: string) => void;
  prefillPincode?: string;
  prefillArea?: string;
  lang?: 'en' | 'hi';
  onLangChange?: (lang: 'en' | 'hi') => void;
}

type Step = 'intent' | 'questionnaire' | 'evidence';

const INTENTS = [
  { id: 'health', icon: '🏥', title: 'Health & Sickness at Home', desc: 'Custom diagnosis for health risks — Cholera, Typhoid, stomach pains' },
  { id: 'ro', icon: '💧', title: 'Understand RO Selection', desc: 'Optimise RO filter stages and parameters for your water' },
  { id: 'general', icon: '🏠', title: 'General Water Quality', desc: 'Assess daily use — chlorine steps, tank cleaning, pipe condition' },
];

const SOURCE_TYPES = [
  { id: 'borewell', label: 'Borewell', icon: '⛏️' },
  { id: 'municipal_pipeline', label: 'Municipal Pipe', icon: '🚰' },
  { id: 'hand_pump', label: 'Hand Pump', icon: '💧' },
  { id: 'open_well', label: 'Open Well', icon: '🪣' },
];

const SYMPTOM_OPTIONS = [
  { id: 'egg_smell', label: 'Egg / Sulphur Smell' },
  { id: 'sewage_smell', label: 'Sewage / Faecal Smell' },
  { id: 'yellow_colour', label: 'Yellow / Brown Water' },
  { id: 'black_colour', label: 'Black / Dark Water' },
  { id: 'white_deposits', label: 'White Deposits on Taps' },
  { id: 'blue_green_stain', label: 'Blue-Green Staining' },
  { id: 'metallic_taste', label: 'Metallic Taste' },
  { id: 'salty_taste', label: 'Salty / Bitter Taste' },
  { id: 'milky_appearance', label: 'Milky / Cloudy Water' },
  { id: 'stomach_issues', label: 'Stomach Issues in Family' },
  { id: 'no_visible_symptom', label: 'No Visible Symptom' },
];

const ReportPage: React.FC<ReportPageProps> = ({
  onReportComplete, prefillPincode = '', prefillArea = '',
  lang = 'en', onLangChange,
}) => {
  const [step, setStep] = useState<Step>('intent');
  const [intent, setIntent] = useState('');
  // Questionnaire
  const [diagnosedDisease, setDiagnosedDisease] = useState(false);
  const [frequentSickness, setFrequentSickness] = useState(false);
  const [stomachPains, setStomachPains] = useState(false);
  const [swallowingIssue, setSwallowingIssue] = useState(false);
  const [algaeInFilters, setAlgaeInFilters] = useState(false);
  const [tankBottomDeposits, setTankBottomDeposits] = useState(false);
  const [tankWallSmudge, setTankWallSmudge] = useState(false);
  const [poorLather, setPoorLather] = useState<boolean | null>(null);
  const [pipeDeposits, setPipeDeposits] = useState(false);
  const [tdsValue, setTdsValue] = useState('');
  const [waterFlow, setWaterFlow] = useState('');

  // Evidence
  const [sourceType, setSourceType] = useState('');
  const [selectedSymptoms, setSelectedSymptoms] = useState<string[]>([]);
  const [description, setDescription] = useState('');
  const [pincode, setPincode] = useState(prefillPincode);
  const [areaName, setAreaName] = useState(prefillArea);
  const [photoBase64, setPhotoBase64] = useState('');
  const [photoPreview, setPhotoPreview] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [listening, setListening] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (prefillPincode) setPincode(prefillPincode);
    if (prefillArea) setAreaName(prefillArea);
  }, [prefillPincode, prefillArea]);



  const startVoice = () => {
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SR) { alert('Voice input requires Chrome browser.'); return; }
    const r = new SR();
    r.lang = lang === 'hi' ? 'hi-IN' : 'en-IN';
    r.onstart = () => setListening(true);
    r.onend = () => setListening(false);
    r.onresult = (e: any) => {
      const t = e.results[0][0].transcript;
      setDescription(prev => prev ? prev + ' ' + t : t);
    };
    r.start();
  };

  const handlePhotoSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setPhotoPreview(URL.createObjectURL(file));
    const reader = new FileReader();
    reader.onloadend = () => setPhotoBase64((reader.result as string).split(',')[1]);
    reader.readAsDataURL(file);
  };

  const toggleSymptom = (id: string) =>
    setSelectedSymptoms(prev => prev.includes(id) ? prev.filter(s => s !== id) : [...prev, id]);

  const buildQuestionnaireContext = () => {
    const parts: string[] = [];
    if (diagnosedDisease) parts.push('Doctor diagnosed Cholera/Typhoid/Dysentery');
    if (frequentSickness || stomachPains) parts.push('Frequent sickness and stomach pains');
    if (swallowingIssue) parts.push('Difficulty swallowing water');
    if (algaeInFilters) parts.push('Tap filter has algae/rust/sand');
    if (tankBottomDeposits) parts.push('Tank bottom has black/brown deposits');
    if (tankWallSmudge) parts.push('Tank walls have soil smudge');
    if (pipeDeposits) parts.push('White deposits on pipes');
    if (poorLather === false) parts.push('Water does NOT produce lather (hard water)');
    if (tdsValue) parts.push(`TDS: ${tdsValue} ppm`);
    if (waterFlow) parts.push(`Water flow: ${waterFlow}`);
    return parts.join('. ');
  };

  const handleSubmit = async () => {
    setError('');
    if (!sourceType) { setError('Please select your water source type.'); return; }
    if (!pincode || pincode.length !== 6 || !/^\d{6}$/.test(pincode)) {
      setError('Please enter a valid 6-digit pincode.'); return;
    }
    if (selectedSymptoms.length === 0 && description.trim().length < 5) {
      setError('Please select at least one symptom or describe the issue.'); return;
    }
    const questionnaireContext = buildQuestionnaireContext();
    const symptomLabels = selectedSymptoms.map(id => SYMPTOM_OPTIONS.find(s => s.id === id)?.label || id);
    const sourceLabel = SOURCE_TYPES.find(s => s.id === sourceType)?.label || sourceType;
    const intentLabel = INTENTS.find(i => i.id === intent)?.title || 'General Water Analysis';
    let userMessage = `Analysis intent: ${intentLabel}. Water source: ${sourceLabel}. `;
    if (symptomLabels.length > 0) userMessage += `Symptoms: ${symptomLabels.join(', ')}. `;
    if (questionnaireContext) userMessage += `Pre-analysis: ${questionnaireContext}. `;
    if (description.trim()) userMessage += description.trim();
    if (areaName) userMessage += ` Location: ${areaName}.`;
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
      onReportComplete(result, pincode);
    } catch (err: any) {
      setError(err.message || 'Could not reach WaterSentinel server.');
    } finally {
      setLoading(false);
    }
  };

  const LangToggle = () => onLangChange ? (
    <div style={{ display: 'flex', gap: 6 }}>
      <button onClick={() => onLangChange('en')} style={{ color: lang === 'en' ? 'white' : '#90CAF9', fontWeight: lang === 'en' ? 700 : 400, fontSize: 13 }} type="button">EN</button>
      <span style={{ color: '#90CAF9' }}>|</span>
      <button onClick={() => onLangChange('hi')} style={{ color: lang === 'hi' ? 'white' : '#90CAF9', fontWeight: lang === 'hi' ? 700 : 400, fontSize: 13 }} type="button">HI</button>
    </div>
  ) : null;

  const CheckItem = ({ label, checked, onChange }: { label: string; checked: boolean; onChange: (v: boolean) => void }) => (
    <label style={{ display: 'flex', alignItems: 'flex-start', gap: 10, marginBottom: 10, cursor: 'pointer', fontSize: 14, lineHeight: 1.4 }}>
      <input type="checkbox" checked={checked} onChange={e => onChange(e.target.checked)}
        style={{ marginTop: 2, accentColor: '#1565C0', width: 16, height: 16, flexShrink: 0 }} />
      {label}
    </label>
  );

  // ═══════════ STEP 1 — INTENT ═══════════
  if (step === 'intent') return (
    <div>
      <div className="card" style={{ marginTop: 12 }}>
        <div style={{ fontSize: 17, fontWeight: 700, color: '#1A237E', marginBottom: 14 }}>
          Why do you want to analyse your water?
        </div>
        {INTENTS.map(item => (
          <button key={item.id}
            onClick={() => { setIntent(item.id); setStep('questionnaire'); }}
            style={{ display: 'flex', alignItems: 'center', gap: 14, width: '100%', padding: 14, marginBottom: 10, border: '2px solid #E0E0E0', borderRadius: 12, background: '#FAFAFA', textAlign: 'left' }}
            onMouseEnter={e => (e.currentTarget.style.borderColor = '#1565C0')}
            onMouseLeave={e => (e.currentTarget.style.borderColor = '#E0E0E0')}
            type="button">
            <span style={{ fontSize: 36, flexShrink: 0 }}>{item.icon}</span>
            <div>
              <div style={{ fontSize: 14, fontWeight: 700, color: '#1A237E' }}>{item.title}</div>
              <div style={{ fontSize: 12, color: '#666', marginTop: 2, lineHeight: 1.4 }}>{item.desc}</div>
            </div>
          </button>
        ))}
      </div>

      <div className="card">
        <div style={{ fontSize: 13, color: '#666', marginBottom: 8 }}>Or describe your concern directly:</div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <button onClick={startVoice}
            style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 14px', border: '2px solid #1565C0', borderRadius: 20, color: '#1565C0', fontSize: 13, fontWeight: 600, background: listening ? '#E3F2FD' : 'white' }}
            type="button">
            🎤 {listening ? 'Listening...' : 'Describe by Voice'}
          </button>
          <input className="text-input" style={{ flex: 1 }} placeholder="or type briefly..."
            value={description} onChange={e => setDescription(e.target.value)} />
        </div>
        {description && (
          <button className="btn-primary" style={{ marginTop: 10 }}
            onClick={() => { setIntent('general'); setStep('questionnaire'); }} type="button">
            Continue →
          </button>
        )}
      </div>

      <div className="card" style={{ background: '#E8F4FD', borderLeft: '4px solid #1565C0' }}>
        <div style={{ fontSize: 13, lineHeight: 1.7, color: '#1A237E' }}>
          <b>Our Mission:</b> WaterSentinel is building India's first citizen-powered water quality
          intelligence network. Every report you file becomes a data point that protects your
          neighbourhood. When enough citizens report, we automatically alert the municipality —
          so you don't have to.
        </div>
      </div>

      <div style={{ textAlign: 'center', padding: 12 }} className="text-muted">
        * Our AI Agent supports Voice and Photo evidence
      </div>
    </div>
  );

  // ═══════════ STEP 2 — QUESTIONNAIRE ═══════════
  if (step === 'questionnaire') return (
    <div>
      <div style={{ background: '#1565C0', padding: '12px 16px', color: 'white', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <button onClick={() => setStep('intent')} style={{ color: '#90CAF9', fontSize: 12, marginBottom: 4 }} type="button">← Back</button>
          <div style={{ fontSize: 17, fontWeight: 700 }}>Diagnostic Deep-Dive</div>
          <div style={{ fontSize: 12, color: '#90CAF9' }}>Pre-analysis check questions</div>
        </div>
        <LangToggle />
      </div>
      <div style={{ height: 4, background: '#E0E0E0' }}>
        <div style={{ height: 4, background: '#1565C0', width: '50%' }} />
      </div>

      <div className="card">
        <div className="card-title">🏥 Health Questions</div>
        <CheckItem label="Someone constantly sick at home?" checked={frequentSickness} onChange={setFrequentSickness} />
        <CheckItem label="Doctor diagnosed Cholera, Typhoid, Dysentery?" checked={diagnosedDisease} onChange={setDiagnosedDisease} />
        <CheckItem label="Frequent stomach pains in family?" checked={stomachPains} onChange={setStomachPains} />
        <CheckItem label="Water swallowing is a problem?" checked={swallowingIssue} onChange={setSwallowingIssue} />
      </div>

      <div className="card">
        <div className="card-title">🔧 Hardware & Use Questions</div>
        <CheckItem label="Is water having deposits on pipes?" checked={pipeDeposits} onChange={setPipeDeposits} />
        <div style={{ marginBottom: 10 }}>
          <div style={{ fontSize: 14, marginBottom: 6 }}>Does water produce lather easily?</div>
          <div style={{ display: 'flex', gap: 10 }}>
            {[true, false].map(val => (
              <button key={String(val)} onClick={() => setPoorLather(val)}
                style={{ padding: '6px 16px', borderRadius: 20, border: '1px solid', fontSize: 13,
                  borderColor: poorLather === val ? '#1565C0' : '#BDBDBD',
                  background: poorLather === val ? '#E3F2FD' : '#FAFAFA',
                  color: poorLather === val ? '#1565C0' : '#555',
                  fontWeight: poorLather === val ? 600 : 400 }}
                type="button">{val ? 'Yes' : 'No'}</button>
            ))}
          </div>
          {poorLather === false && (
            <div style={{ fontSize: 12, color: '#E65100', marginTop: 4 }}>⚠️ Poor lather = hard water indicator</div>
          )}
        </div>
        <label style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10, fontSize: 14 }}>
          <span>Water flow in pipes:</span>
          <select value={waterFlow} onChange={e => setWaterFlow(e.target.value)}
            style={{ border: '1px solid #E0E0E0', borderRadius: 6, padding: '4px 8px', fontSize: 13 }}>
            <option value="">Select</option>
            <option value="strong">Strong</option>
            <option value="normal">Normal</option>
            <option value="weak">Weak</option>
          </select>
        </label>
        <label style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 14 }}>
          <span style={{ flexShrink: 0 }}>TDS if known (ppm):</span>
          <input type="number" placeholder="e.g. 450" value={tdsValue} onChange={e => setTdsValue(e.target.value)}
            style={{ border: '1px solid #E0E0E0', borderRadius: 6, padding: '6px 10px', width: 90, fontSize: 13 }} />
        </label>
      </div>

      <div className="card">
        <div className="card-title">🔍 Specific Observations</div>
        <CheckItem label="Tap filter has algae, rust, or sand?" checked={algaeInFilters} onChange={setAlgaeInFilters} />
        <CheckItem label="Overhead tank bottom has black/brown deposits?" checked={tankBottomDeposits} onChange={setTankBottomDeposits} />
        <CheckItem label="Overhead tank inner walls have soil smudge?" checked={tankWallSmudge} onChange={setTankWallSmudge} />
      </div>

      <div style={{ padding: '0 16px 16px' }}>
        <div className="text-muted text-center" style={{ marginBottom: 10 }}>
          * Our AI agent can process Photo and Voice evidence in the next stage
        </div>
        <button className="btn-primary" onClick={() => setStep('evidence')} type="button">
          Confirm and Proceed to AI Analysis
        </button>
      </div>
    </div>
  );

  // ═══════════ STEP 3 — EVIDENCE ═══════════
  return (
    <div>
      <div style={{ background: '#1565C0', padding: '12px 16px', color: 'white', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <button onClick={() => setStep('questionnaire')} style={{ color: '#90CAF9', fontSize: 12, marginBottom: 4 }} type="button">← Back</button>
          <div style={{ fontSize: 17, fontWeight: 700 }}>Evidence Input</div>
          <div style={{ fontSize: 12, color: '#90CAF9' }}>Identify your source and symptoms</div>
        </div>
        <LangToggle />
      </div>
      <div style={{ height: 4, background: '#E0E0E0' }}>
        <div style={{ height: 4, background: '#1565C0', width: '100%' }} />
      </div>

      <div className="card">
        <div className="card-title">Water Source *</div>
        <div className="source-grid">
          {SOURCE_TYPES.map(source => (
            <button key={source.id}
              className={`source-card ${sourceType === source.id ? 'selected' : ''}`}
              onClick={() => setSourceType(source.id)} type="button">
              <span className="source-icon">{source.icon}</span>
              <span className="source-label">{source.label}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="card">
        <div className="card-title">What do you observe?</div>
        <div className="chip-container">
          {SYMPTOM_OPTIONS.map(symptom => (
            <button key={symptom.id}
              className={`chip ${selectedSymptoms.includes(symptom.id) ? 'selected' : ''}`}
              onClick={() => toggleSymptom(symptom.id)} type="button">{symptom.label}</button>
          ))}
        </div>
      </div>

      <div className="card" style={{ border: '1px solid #1565C0' }}>
        <div className="card-title">📎 Evidence Submission for AI Agent</div>
        <div className="text-muted" style={{ marginBottom: 10 }}>Supports multi-modality: Photo + Voice</div>
        <div style={{ display: 'flex', gap: 10, marginBottom: 10 }}>
          <button onClick={() => fileInputRef.current?.click()}
            style={{ flex: 1, border: photoBase64 ? '2px solid #2E7D32' : '2px dashed #BDBDBD', borderRadius: 10, padding: '12px 8px', textAlign: 'center', background: photoBase64 ? '#E8F5E9' : '#FAFAFA', fontSize: 12 }}
            type="button">
            <div style={{ fontSize: 22 }}>📷</div>
            <div style={{ fontWeight: 600, marginTop: 4 }}>{photoBase64 ? '✓ Photo Added' : 'Add Photo'}</div>
            <div className="text-muted">White vessel photo</div>
          </button>
          <button onClick={startVoice}
            style={{ flex: 1, border: listening ? '2px solid #1565C0' : '2px dashed #BDBDBD', borderRadius: 10, padding: '12px 8px', textAlign: 'center', background: listening ? '#E3F2FD' : '#FAFAFA', fontSize: 12 }}
            type="button">
            <div style={{ fontSize: 22 }}>🎤</div>
            <div style={{ fontWeight: 600, marginTop: 4 }}>{listening ? 'Listening...' : 'Describe by Voice'}</div>
            <div className="text-muted">Speak symptoms</div>
          </button>
        </div>
        <input ref={fileInputRef} type="file" accept="image/*" onChange={handlePhotoSelect} style={{ display: 'none' }} />
        {photoPreview && <img src={photoPreview} alt="Water sample" style={{ width: '100%', height: 100, objectFit: 'cover', borderRadius: 8, marginBottom: 8 }} />}
        {description && <div style={{ background: '#F5F5F5', borderRadius: 8, padding: 10, fontSize: 13, marginBottom: 8 }}>🎤 "{description}"</div>}
        <textarea className="text-input" placeholder="Or type your description here..."
          value={description} onChange={e => setDescription(e.target.value.slice(0, 500))} rows={3} />
      </div>

      <div className="card">
        <div className="card-title">Location *</div>
        <input className="text-input" placeholder="6-digit Pincode (e.g. 500032)"
          value={pincode} onChange={e => setPincode(e.target.value.replace(/\D/g, '').slice(0, 6))} inputMode="numeric" />
        <input className="text-input mt-8" placeholder="Pin / Area name (e.g. Kondapur)"
          value={areaName} onChange={e => setAreaName(e.target.value.slice(0, 100))} />
        <div className="text-muted mt-8" style={{ color: '#4CAF50' }}>
          🔒 Only your pincode is stored — no street address, no GPS
        </div>
      </div>

      {/* Submit section */}
      <div style={{ padding: '0 16px 24px' }}>
        {error && (
          <div style={{ background: '#FFEBEE', color: '#B71C1C', fontSize: 13, padding: 12, borderRadius: 8, marginBottom: 12 }}>
            {error}
          </div>
        )}

        {/* Button hidden while loading */}
        {!loading && (
          <button className="btn-primary" onClick={handleSubmit} type="button">
            ✨ Continue to Deep AI Agent Analysis
          </button>
        )}

        {/* AgentProgress shown while loading */}
        {loading && (
          <>
            <AgentProgress isActive={loading} />
            <div style={{ textAlign: 'center', fontSize: 12, color: '#9E9E9E', marginTop: 8 }}>
              Please keep this tab open. Analysis takes 45–60 seconds.
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default ReportPage;
