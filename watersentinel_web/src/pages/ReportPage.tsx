/**
 * Module: src/pages/ReportPage.tsx
 * Changes from previous version:
 *   - AgentProgress component shown during loading instead of spinner
 *   - PATCHED: AgentProgress now receives resultRef + lang so it can show
 *     honest photo/voice analysis status lines once finished. No other
 *     logic changes.
 */

import React, { useState, useRef, useEffect } from 'react';
import { submitWaterReport, WaterReportResponse } from '../api/watersentinel';
import AgentProgress from '../components/AgentProgress';
import { t, Lang } from '../i18n/translations';

interface ReportPageProps {
  onReportComplete: (result: WaterReportResponse, pincode: string) => void;
  prefillPincode?: string;
  prefillArea?: string;
  lang?: Lang;
  onLangChange?: (lang: Lang) => void;
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
  // NEW — conditional follow-ups, only meaningful when frequentSickness is true
  const [affectedCount, setAffectedCount] = useState<'1' | '2-3' | '4+' | ''>('');
  const [sinceWhen, setSinceWhen] = useState<'days' | 'weeks' | 'months' | ''>('');
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
  const [colonyName, setColonyName] = useState('');
  const [detectingLocation, setDetectingLocation] = useState(false);
  const [gpsDetectMessage, setGpsDetectMessage] = useState('');
  const [gpsDetectSuccess, setGpsDetectSuccess] = useState(false);
  const [photoBase64, setPhotoBase64] = useState('');
  const [photoPreview, setPhotoPreview] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [listening, setListening] = useState(false);
  const [pendingResult, setPendingResult] = useState<WaterReportResponse | null>(null);
  const [pendingPincode, setPendingPincode] = useState('');
  const pendingResultRef = useRef<WaterReportResponse | null>(null);
  const pendingPincodeRef = useRef<string>('');

  const fileInputRef = useRef<HTMLInputElement>(null);
  const [locationSuggestions, setLocationSuggestions] = useState<{ pincodes: string[]; areas: string[]; colonies: string[] }>({
    pincodes: [], areas: [], colonies: [],
  });

  useEffect(() => {
    if (prefillPincode) setPincode(prefillPincode);
    if (prefillArea) setAreaName(prefillArea);
  }, [prefillPincode, prefillArea]);

  // NEW — cascading autocomplete: re-fetches suggestions whenever pincode
  // (or pincode+area) changes, so area suggestions narrow to that
  // pincode's real areas, and colony suggestions narrow to that specific
  // pincode+area's real colonies. Citizens can still freely type anything
  // new at any level — this only narrows SUGGESTIONS, never blocks input.
  useEffect(() => {
    const timer = setTimeout(() => {
      import('../api/watersentinel').then(({ API_BASE_URL }) => {
        const params = new URLSearchParams();
        if (pincode && pincode.length === 6) params.set('pincode', pincode);
        if (pincode && pincode.length === 6 && areaName.trim()) params.set('area_name', areaName.trim());
        const qs = params.toString();
        fetch(`${API_BASE_URL}/location-suggestions${qs ? '?' + qs : ''}`)
          .then(r => r.json())
          .then(data => setLocationSuggestions(data))
          .catch(() => {}); // silent fail — form works fine without suggestions
      });
    }, 300); // debounced — avoids firing a request on every single keystroke
    return () => clearTimeout(timer);
  }, [pincode, areaName]);



  const handleDetectLocation = () => {
    if (!navigator.geolocation) {
      setGpsDetectSuccess(false);
      setGpsDetectMessage('GPS is not available on this device/browser. Please enter your location manually.');
      return;
    }

    setDetectingLocation(true);
    setGpsDetectMessage('');

    navigator.geolocation.getCurrentPosition(
      async (position) => {
        const { latitude, longitude } = position.coords;
        try {
          const { API_BASE_URL } = await import('../api/watersentinel');
          const response = await fetch(
            `${API_BASE_URL}/geolocation/reverse?lat=${latitude}&lng=${longitude}`
          );
          const data = await response.json();

          // NOTE: latitude/longitude exist only in this local closure and
          // are never stored, logged, or sent anywhere beyond this single
          // reverse-geocoding request — matching the privacy commitment
          // shown to the citizen above the button.
          if (data.success) {
            setPincode(data.pincode || '');
            if (data.area_name) setAreaName(data.area_name);
            setGpsDetectSuccess(true);
            setGpsDetectMessage('✅ ' + data.message);
          } else {
            setGpsDetectSuccess(false);
            setGpsDetectMessage('⚠️ ' + data.message);
          }
        } catch (err) {
          setGpsDetectSuccess(false);
          setGpsDetectMessage('⚠️ Could not detect location right now. Please enter it manually.');
        } finally {
          setDetectingLocation(false);
        }
      },
      (error) => {
        setDetectingLocation(false);
        setGpsDetectSuccess(false);
        if (error.code === error.PERMISSION_DENIED) {
          setGpsDetectMessage('⚠️ Location permission denied. Please enter your pincode and area manually.');
        } else {
          setGpsDetectMessage('⚠️ Could not access your location. Please enter it manually.');
        }
      },
      { timeout: 10000, maximumAge: 0 }
    );
  };

  const startVoice = () => {
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SR) { alert('Voice input requires Chrome browser.'); return; }
    const r = new SR();
    r.lang = lang === 'hi' ? 'hi-IN' : lang === 'te' ? 'te-IN' : 'en-IN';
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
    // NEW — area name is now mandatory. This is validated as "must be
    // non-empty text," NOT "must match an existing suggestion" — citizens
    // can always type a genuinely new area/colony freely; the requirement
    // is only that the field isn't left blank, since a blank area/colony
    // is what caused most of the data fragmentation issues found tonight.
    if (!areaName.trim()) {
      setError('Please enter your area/locality name (required — helps us map your report correctly).'); return;
    }
    // NEW — colony name is mandatory too, but ONLY as non-empty free text.
    // Colony data has no government source anywhere — it exists only
    // because citizens type it in — so this must never require matching
    // an existing suggestion, or every "first report from a new colony"
    // scenario would be blocked entirely, working against the very
    // crowdsourced-growth model the colony feature depends on.
    if (!colonyName.trim()) {
      setError('Please enter your colony/street name (required — even if it\'s not in the suggestions, please type it).'); return;
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
        colony_name: colonyName.trim(),
        source_type: sourceType,
        symptoms: selectedSymptoms,
        photo_base64: photoBase64 || undefined,
        tds_value: tdsValue ? parseInt(tdsValue, 10) : undefined,
        // FIXED: send actual checkbox state directly — this is the fix for
        // the bug where the word "diagnosed" appearing in free text (even
        // just describing an unchecked option) was mistaken for a confirmed
        // Yes answer, fabricating a faecal/coliform score-0 result the
        // citizen never actually selected.
        diagnosed_disease: diagnosedDisease,
        frequent_sickness: frequentSickness || stomachPains,
        affected_count: affectedCount || undefined,
        since_when: sinceWhen || undefined,
        algae_in_filters: algaeInFilters,
        tank_sludge: tankBottomDeposits || tankWallSmudge,
      });
      // Store in ref — does NOT trigger re-render, animation continues uninterrupted
      pendingResultRef.current = result;
      pendingPincodeRef.current = pincode;
      // NOTE: loading stays TRUE here on purpose.
      // AgentProgress keeps running until user clicks "View My Results".
      // loading is only set false on error (below) or when user proceeds.
    } catch (err: any) {
      setError(err.message || 'Could not reach WaterSentinel server.');
      setLoading(false); // Only reset loading on actual failure
    }
  };

  const LangToggle = () => onLangChange ? (
    <div style={{ display: 'flex', gap: 6 }}>
      <button onClick={() => onLangChange('en')} style={{ color: lang === 'en' ? 'white' : '#90CAF9', fontWeight: lang === 'en' ? 700 : 400, fontSize: 13 }} type="button">EN</button>
      <span style={{ color: '#90CAF9' }}>|</span>
      <button onClick={() => onLangChange('hi')} style={{ color: lang === 'hi' ? 'white' : '#90CAF9', fontWeight: lang === 'hi' ? 700 : 400, fontSize: 13 }} type="button">HI</button>
      <span style={{ color: '#90CAF9' }}>|</span>
      <button onClick={() => onLangChange('te')} style={{ color: lang === 'te' ? 'white' : '#90CAF9', fontWeight: lang === 'te' ? 700 : 400, fontSize: 13 }} type="button">TE</button>
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
  if (step === 'intent') {
    const localizedIntents = [
      { id: 'health', icon: '🏥', title: t(lang, 'intentHealthTitle'), desc: t(lang, 'intentHealthDesc') },
      { id: 'ro', icon: '💧', title: t(lang, 'intentROTitle'), desc: t(lang, 'intentRODesc') },
      { id: 'general', icon: '🏠', title: t(lang, 'intentGeneralTitle'), desc: t(lang, 'intentDailyDesc') },
    ];
    return (
    <div>
      <div className="card" style={{ marginTop: 12 }}>
        <div style={{ fontSize: 17, fontWeight: 700, color: '#1A237E', marginBottom: 14 }}>
          {t(lang, 'whyAnalyse')}
        </div>
        {localizedIntents.map(item => (
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
        <div style={{ fontSize: 13, color: '#666', marginBottom: 8 }}>{t(lang, 'orDescribe')}</div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <button onClick={startVoice}
            style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 14px', border: '2px solid #1565C0', borderRadius: 20, color: '#1565C0', fontSize: 13, fontWeight: 600, background: listening ? '#E3F2FD' : 'white' }}
            type="button">
            🎤 {listening ? t(lang, 'listening') : t(lang, 'describeByVoice')}
          </button>
          <input className="text-input" style={{ flex: 1 }} placeholder={t(lang, 'typeBriefly')}
            value={description} onChange={e => setDescription(e.target.value)} />
        </div>
        {description && (
          <button className="btn-primary" style={{ marginTop: 10 }}
            onClick={() => { setIntent('general'); setStep('questionnaire'); }} type="button">
            {t(lang, 'continueArrow')}
          </button>
        )}
      </div>

      <div className="card" style={{ background: '#E8F4FD', borderLeft: '4px solid #1565C0' }}>
        <div style={{ fontSize: 13, lineHeight: 1.7, color: '#1A237E' }}>
          <b>{t(lang, 'ourMission')}</b> {lang === 'hi' ? t(lang, 'visionText') :
          "WaterSentinel is building India's first citizen-powered water quality intelligence network. Every report you file becomes a data point that protects your neighbourhood. When enough citizens report, we automatically alert the municipality — so you don't have to."}
        </div>
      </div>

      <div style={{ textAlign: 'center', padding: 12 }} className="text-muted">
        {t(lang, 'aiNote').replace('Voice, Text, and Photo', 'Voice and Photo')}
      </div>
    </div>
  );
  }

  // ═══════════ STEP 2 — QUESTIONNAIRE ═══════════
  if (step === 'questionnaire') return (
    <div>
      <div style={{ background: '#1565C0', padding: '12px 16px', color: 'white', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <button onClick={() => setStep('intent')} style={{ color: '#90CAF9', fontSize: 12, marginBottom: 4 }} type="button">{t(lang, 'back')}</button>
          <div style={{ fontSize: 17, fontWeight: 700 }}>{t(lang, 'diagnosticDeepDive')}</div>
          <div style={{ fontSize: 12, color: '#90CAF9' }}>{t(lang, 'preAnalysisQuestions')}</div>
        </div>
        <LangToggle />
      </div>
      <div style={{ height: 4, background: '#E0E0E0' }}>
        <div style={{ height: 4, background: '#1565C0', width: '50%' }} />
      </div>

      <div className="card">
        <div className="card-title">{t(lang, 'healthQuestions')}</div>
        <CheckItem
          label={t(lang, 'qSickHome')}
          checked={frequentSickness}
          onChange={(val) => {
            setFrequentSickness(val);
            if (!val) {
              // Clear stale follow-up answers if the parent question is unticked
              setAffectedCount('');
              setSinceWhen('');
            }
          }}
        />

        {/* Conditional follow-ups — only shown when sickness is ticked.
            This is the smart-form pattern: don't clutter the questionnaire
            with fields that are meaningless when the parent answer is No. */}
        {frequentSickness && (
          <div style={{
            marginLeft: 26, marginBottom: 14, padding: '10px 12px',
            background: '#FFF8E1', borderRadius: 8, borderLeft: '3px solid #F9A825',
          }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#8A4A1E', marginBottom: 8 }}>
              {t(lang, 'qHowManyAffected')}
            </div>
            <div style={{ display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap' }}>
              {(['1', '2-3', '4+'] as const).map(val => (
                <button key={val} onClick={() => setAffectedCount(val)}
                  style={{
                    padding: '5px 14px', borderRadius: 16, fontSize: 12, border: '1px solid',
                    borderColor: affectedCount === val ? '#E65100' : '#BDBDBD',
                    background: affectedCount === val ? '#FBE9E7' : 'white',
                    color: affectedCount === val ? '#E65100' : '#555',
                    fontWeight: affectedCount === val ? 600 : 400,
                  }}
                  type="button">
                  {val === '1' ? t(lang, 'affectedJustOne') : val === '2-3' ? t(lang, 'affected2to3') : t(lang, 'affected4plus')}
                </button>
              ))}
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#8A4A1E', marginBottom: 8 }}>
              {t(lang, 'qSinceWhen')}
            </div>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              {(['days', 'weeks', 'months'] as const).map(val => (
                <button key={val} onClick={() => setSinceWhen(val)}
                  style={{
                    padding: '5px 14px', borderRadius: 16, fontSize: 12, border: '1px solid',
                    borderColor: sinceWhen === val ? '#E65100' : '#BDBDBD',
                    background: sinceWhen === val ? '#FBE9E7' : 'white',
                    color: sinceWhen === val ? '#E65100' : '#555',
                    fontWeight: sinceWhen === val ? 600 : 400,
                  }}
                  type="button">
                  {val === 'days' ? t(lang, 'sinceFewDays') : val === 'weeks' ? t(lang, 'sinceFewWeeks') : t(lang, 'sinceMonths')}
                </button>
              ))}
            </div>
          </div>
        )}

        <CheckItem label={t(lang, 'qDiagnosed')} checked={diagnosedDisease} onChange={setDiagnosedDisease} />
        <CheckItem label={t(lang, 'qStomachPains')} checked={stomachPains} onChange={setStomachPains} />
        <CheckItem label={t(lang, 'qSwallowing')} checked={swallowingIssue} onChange={setSwallowingIssue} />
      </div>

      <div className="card">
        <div className="card-title">{t(lang, 'hardwareQuestions')}</div>
        <CheckItem label={t(lang, 'qDeposits')} checked={pipeDeposits} onChange={setPipeDeposits} />
        <div style={{ marginBottom: 10 }}>
          <div style={{ fontSize: 14, marginBottom: 6 }}>{t(lang, 'qLather')}</div>
          <div style={{ display: 'flex', gap: 10 }}>
            {[true, false].map(val => (
              <button key={String(val)} onClick={() => setPoorLather(val)}
                style={{ padding: '6px 16px', borderRadius: 20, border: '1px solid', fontSize: 13,
                  borderColor: poorLather === val ? '#1565C0' : '#BDBDBD',
                  background: poorLather === val ? '#E3F2FD' : '#FAFAFA',
                  color: poorLather === val ? '#1565C0' : '#555',
                  fontWeight: poorLather === val ? 600 : 400 }}
                type="button">{val ? t(lang, 'yes') : t(lang, 'no')}</button>
            ))}
          </div>
          {poorLather === false && (
            <div style={{ fontSize: 12, color: '#E65100', marginTop: 4 }}>{t(lang, 'latherWarning')}</div>
          )}
        </div>
        <label style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10, fontSize: 14 }}>
          <span>{t(lang, 'waterFlow')}</span>
          <select value={waterFlow} onChange={e => setWaterFlow(e.target.value)}
            style={{ border: '1px solid #E0E0E0', borderRadius: 6, padding: '4px 8px', fontSize: 13 }}>
            <option value="">{t(lang, 'selectOption')}</option>
            <option value="strong">{t(lang, 'flowStrong')}</option>
            <option value="normal">{t(lang, 'flowNormal')}</option>
            <option value="weak">{t(lang, 'flowWeak')}</option>
          </select>
        </label>
        <label style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 14 }}>
          <span style={{ flexShrink: 0 }}>{t(lang, 'tdsLabel')}</span>
          <input type="number" placeholder="e.g. 450" value={tdsValue} onChange={e => setTdsValue(e.target.value)}
            style={{ border: '1px solid #E0E0E0', borderRadius: 6, padding: '6px 10px', width: 90, fontSize: 13 }} />
        </label>
      </div>

      <div className="card">
        <div className="card-title">{t(lang, 'specificObservations')}</div>
        <CheckItem label={t(lang, 'qAlgae')} checked={algaeInFilters} onChange={setAlgaeInFilters} />
        <CheckItem label={t(lang, 'qTankBottom')} checked={tankBottomDeposits} onChange={setTankBottomDeposits} />
        <CheckItem label={t(lang, 'qTankWalls')} checked={tankWallSmudge} onChange={setTankWallSmudge} />
      </div>

      <div style={{ padding: '0 16px 16px' }}>
        <div className="text-muted text-center" style={{ marginBottom: 10 }}>
          {t(lang, 'proceedNote')}
        </div>
        <button className="btn-primary" onClick={() => setStep('evidence')} type="button">
          {t(lang, 'confirmProceed')}
        </button>
      </div>
    </div>
  );

  // ═══════════ STEP 3 — EVIDENCE ═══════════
  const localizedSources = [
    { id: 'borewell', label: t(lang, 'sourceBorewell'), icon: '⛏️' },
    { id: 'municipal_pipeline', label: t(lang, 'sourceMunicipal'), icon: '🚰' },
    { id: 'hand_pump', label: t(lang, 'sourceHandPump'), icon: '💧' },
    { id: 'open_well', label: t(lang, 'sourceOpenWell'), icon: '🪣' },
  ];

  const localizedSymptoms = [
    { id: 'egg_smell', label: t(lang, 'symptomEgg') },
    { id: 'sewage_smell', label: t(lang, 'symptomSewage') },
    { id: 'yellow_colour', label: t(lang, 'symptomYellow') },
    { id: 'black_colour', label: t(lang, 'symptomBlack') },
    { id: 'white_deposits', label: t(lang, 'symptomWhiteDeposits') },
    { id: 'blue_green_stain', label: t(lang, 'symptomBlueGreen') },
    { id: 'metallic_taste', label: t(lang, 'symptomMetallic') },
    { id: 'salty_taste', label: t(lang, 'symptomSalty') },
    { id: 'milky_appearance', label: t(lang, 'symptomMilky') },
    { id: 'stomach_issues', label: t(lang, 'symptomStomach') },
    // NEW — research-backed additions (BIS sensory-check protocol +
    // documented contamination indicators)
    { id: 'chlorine_smell', label: t(lang, 'symptomChlorine') },
    { id: 'colour_after_standing', label: t(lang, 'symptomColourAfterStanding') },
    { id: 'gritty_texture', label: t(lang, 'symptomGritty') },
    { id: 'foamy_water', label: t(lang, 'symptomFoamy') },
    { id: 'oily_sheen', label: t(lang, 'symptomOilySheen') },
    { id: 'insects_visible', label: t(lang, 'symptomInsects') },
    { id: 'skin_irritation', label: t(lang, 'symptomSkinIrritation') },
    { id: 'vessel_staining', label: t(lang, 'symptomVesselStaining') },
    { id: 'no_visible_symptom', label: t(lang, 'symptomNone') },
  ];

  return (
    <div>
      <div style={{ background: '#1565C0', padding: '12px 16px', color: 'white', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <button onClick={() => setStep('questionnaire')} style={{ color: '#90CAF9', fontSize: 12, marginBottom: 4 }} type="button">{t(lang, 'back')}</button>
          <div style={{ fontSize: 17, fontWeight: 700 }}>{t(lang, 'evidenceInput')}</div>
          <div style={{ fontSize: 12, color: '#90CAF9' }}>{t(lang, 'identifySource')}</div>
        </div>
        <LangToggle />
      </div>
      <div style={{ height: 4, background: '#E0E0E0' }}>
        <div style={{ height: 4, background: '#1565C0', width: '100%' }} />
      </div>

      <div className="card">
        <div className="card-title">{t(lang, 'waterSource')}</div>
        <div className="source-grid">
          {localizedSources.map(source => (
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
        <div className="card-title">{t(lang, 'whatObserve')}</div>
        <div className="chip-container">
          {localizedSymptoms.map(symptom => (
            <button key={symptom.id}
              className={`chip ${selectedSymptoms.includes(symptom.id) ? 'selected' : ''}`}
              onClick={() => toggleSymptom(symptom.id)} type="button">{symptom.label}</button>
          ))}
        </div>
      </div>

      <div className="card" style={{ border: '1px solid #1565C0' }}>
        <div className="card-title">{t(lang, 'evidenceSubmission')}</div>
        <div className="text-muted" style={{ marginBottom: 10 }}>{t(lang, 'supportsMultimodal')}</div>
        <div style={{ display: 'flex', gap: 10, marginBottom: 10 }}>
          <button onClick={() => fileInputRef.current?.click()}
            style={{ flex: 1, border: photoBase64 ? '2px solid #2E7D32' : '2px dashed #BDBDBD', borderRadius: 10, padding: '12px 8px', textAlign: 'center', background: photoBase64 ? '#E8F5E9' : '#FAFAFA', fontSize: 12 }}
            type="button">
            <div style={{ fontSize: 22 }}>📷</div>
            <div style={{ fontWeight: 600, marginTop: 4 }}>{photoBase64 ? t(lang, 'photoAdded') : t(lang, 'addPhoto')}</div>
            <div className="text-muted">{t(lang, 'whiteVesselPhoto')}</div>
          </button>
          <button onClick={startVoice}
            style={{ flex: 1, border: listening ? '2px solid #1565C0' : '2px dashed #BDBDBD', borderRadius: 10, padding: '12px 8px', textAlign: 'center', background: listening ? '#E3F2FD' : '#FAFAFA', fontSize: 12 }}
            type="button">
            <div style={{ fontSize: 22 }}>🎤</div>
            <div style={{ fontWeight: 600, marginTop: 4 }}>{listening ? t(lang, 'listening') : t(lang, 'describeByVoice')}</div>
            <div className="text-muted">{t(lang, 'speakSymptoms')}</div>
          </button>
        </div>
        <input ref={fileInputRef} type="file" accept="image/*" onChange={handlePhotoSelect} style={{ display: 'none' }} />
        {photoPreview && <img src={photoPreview} alt="Water sample" style={{ width: '100%', height: 100, objectFit: 'cover', borderRadius: 8, marginBottom: 8 }} />}
        {description && <div style={{ background: '#F5F5F5', borderRadius: 8, padding: 10, fontSize: 13, marginBottom: 8 }}>🎤 "{description}"</div>}
        <textarea className="text-input" placeholder={t(lang, 'typeDescriptionHere')}
          value={description} onChange={e => setDescription(e.target.value.slice(0, 500))} rows={3} />
      </div>

      <div className="card">
        <div className="card-title">{t(lang, 'locationRequired')}</div>

        {/* GPS auto-detect — compact pill, not a full-width bar, since this
            is a single small optional action, not a primary form control */}
        <div style={{ display: 'flex', justifyContent: 'flex-start', marginBottom: 8 }}>
          <button
            onClick={handleDetectLocation}
            disabled={detectingLocation}
            style={{
              display: 'inline-flex', alignItems: 'center', gap: 6,
              padding: '6px 12px', borderRadius: 20,
              border: '1.5px solid #1565C0',
              background: detectingLocation ? '#E3F2FD' : 'white',
              color: '#1565C0', fontSize: 12, fontWeight: 600,
            }}
            type="button"
          >
            📍 {detectingLocation ? 'Detecting...' : 'Use my GPS location'}
          </button>
        </div>

        {/* Explicit privacy message — always visible near the GPS button,
            not just after clicking, so the citizen sees the commitment
            BEFORE deciding whether to use this feature at all. */}
        <div style={{
          fontSize: 11, color: '#2E7D32', background: '#E8F5E9', borderRadius: 8,
          padding: '8px 10px', marginBottom: 12, lineHeight: 1.5,
        }}>
          🔒 Your GPS location is <b>not linked to your identity or profile</b>.
          It is used only once, to detect your pincode and area, then discarded
          immediately. Only the pincode/area — the same detail you could type
          yourself — is used for water quality classification.
        </div>

        {gpsDetectMessage && (
          <div style={{ fontSize: 12, color: gpsDetectSuccess ? '#2E7D32' : '#E65100', marginBottom: 10 }}>
            {gpsDetectMessage}
          </div>
        )}

        <input className="text-input" placeholder={t(lang, 'pincodePlaceholder')}
          value={pincode} onChange={e => setPincode(e.target.value.replace(/\D/g, '').slice(0, 6))}
          inputMode="numeric" list="pincode-suggestions" />
        <datalist id="pincode-suggestions">
          {locationSuggestions.pincodes.map(p => <option key={p} value={p} />)}
        </datalist>

        <input className="text-input mt-8" placeholder={t(lang, 'areaPlaceholder')}
          value={areaName} onChange={e => setAreaName(e.target.value.slice(0, 100))}
          list="area-suggestions" />
        <datalist id="area-suggestions">
          {locationSuggestions.areas.map(a => <option key={a} value={a} />)}
        </datalist>

        <input className="text-input mt-8" placeholder={t(lang, 'colonyPlaceholder')}
          value={colonyName} onChange={e => setColonyName(e.target.value.slice(0, 100))}
          list="colony-suggestions" />
        <datalist id="colony-suggestions">
          {locationSuggestions.colonies.map(c => <option key={c} value={c} />)}
        </datalist>

        <div className="text-muted mt-8" style={{ color: '#1565C0' }}>
          {t(lang, 'colonyHint')}
        </div>
        <div className="text-muted mt-8" style={{ color: '#4CAF50' }}>
          {t(lang, 'privacyNote')}
        </div>
      </div>

      {/* Submit section */}
      <div style={{ padding: '0 16px 24px' }}>
        {error && (
          <div style={{ background: '#FFEBEE', color: '#B71C1C', fontSize: 13, padding: 12, borderRadius: 8, marginBottom: 12 }}>
            {error}
          </div>
        )}

        {!loading && (
          <button className="btn-primary" onClick={handleSubmit} type="button">
            {t(lang, 'continueToAnalysis')}
          </button>
        )}

        {loading && (
          <AgentProgress
            isActive={loading}
            resultRef={pendingResultRef}
            lang={lang}
            onViewResults={() => {
              const result = pendingResultRef.current;
              const pin = pendingPincodeRef.current;
              if (result) {
                setLoading(false); // clean state before navigating
                onReportComplete(result, pin);
              }
            }}
          />
        )}
      </div>
    </div>
  );
};

export default ReportPage;
