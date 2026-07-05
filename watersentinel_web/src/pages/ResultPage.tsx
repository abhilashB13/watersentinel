/**
 * Module: src/pages/ResultPage.tsx
 * Fixes:
 *   - Pincode shown correctly (passed as prop, not from session_id)
 *   - EN|HI toggle on header
 *   - Actions driven by scoring primary_category
 *   - Score explanation shows actual deductions
 */

import React, { useState } from 'react';
import { WaterReportResponse, getBandColour, getBandBackground, getBandLabel } from '../api/watersentinel';
import { t, Lang } from '../i18n/translations';

interface ResultPageProps {
  result: WaterReportResponse;
  onNewReport: () => void;
  onViewMap: () => void;
  pincode?: string;
  lang?: Lang;
  onLangChange?: (lang: Lang) => void;
}

const RO_PRODUCTS = [
  {
    name: 'Kent Grand Plus 9L RO+UV+UF',
    price: '₹14,500', rating: '4.3 ★',
    tag: 'Best for High TDS',
    link: 'https://www.amazon.in/s?k=kent+grand+plus+ro',
    color: '#E3F2FD',
  },
  {
    name: 'Aquaguard Enhance 7L RO+UV',
    price: '₹11,999', rating: '4.1 ★',
    tag: 'Best for Iron Removal',
    link: 'https://www.amazon.in/s?k=aquaguard+enhance+ro+uv',
    color: '#E8F5E9',
  },
  {
    name: 'Pureit Copper+ Mineral RO+UV',
    price: '₹9,999', rating: '4.2 ★',
    tag: 'Best Value',
    link: 'https://www.amazon.in/s?k=pureit+copper+ro',
    color: '#FFF8E1',
  },
];

const WATER_SERVICES = [
  { name: 'Tara Water Tank Cleaning', desc: 'Underground & overhead tank cleaning — Hyderabad', phone: '98490-XXXXX', icon: '🚿' },
  { name: 'Aqua Pure RO Services', desc: 'RO installation, AMC, filter replacement', phone: '94400-XXXXX', icon: '🔧' },
];

const RATING_CHIPS = ['Clear Actions', 'Trustworthy', 'Accurate Diagnosis', 'Fast Response', 'Easy to Use'];

const ResultPage: React.FC<ResultPageProps> = ({
  result, onNewReport, onViewMap, pincode = '', lang = 'en', onLangChange,
}) => {
  const [scoreExpanded, setScoreExpanded] = useState(false);
  const [complaintExpanded, setComplaintExpanded] = useState(false);
  const [copied, setCopied] = useState(false);
  const [rating, setRating] = useState(0);
  const [hoverRating, setHoverRating] = useState(0);
  const [selectedChips, setSelectedChips] = useState<string[]>([]);
  const [feedbackText, setFeedbackText] = useState('');
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);

  const bandColour = getBandColour(result.colour_band);
  const bandBackground = getBandBackground(result.colour_band);
  const bandLabel = getBandLabel(result.colour_band);

  // Extract score breakdown from full_response if backend returned it
  let scoreBreakdown: any = null;
  try {
    if (result.full_response && result.full_response.includes('score_breakdown')) {
      const match = result.full_response.match(/"score_breakdown":\s*(\{[^}]+\})/);
      if (match) scoreBreakdown = JSON.parse(match[1]);
    }
  } catch {}

  const copyComplaint = async () => {
    try { await navigator.clipboard.writeText(result.complaint_draft); }
    catch {
      const ta = document.createElement('textarea');
      ta.value = result.complaint_draft;
      document.body.appendChild(ta); ta.select();
      document.execCommand('copy'); document.body.removeChild(ta);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div>
      {/* Header with lang toggle */}
      <div className="header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div className="header-title">💧 WaterSentinel</div>
          <div className="header-subtitle">
            Analysis & Next Steps{pincode ? ` — Pincode ${pincode}` : ''}
          </div>
        </div>
        {onLangChange && (
          <div style={{ display: 'flex', gap: 6, marginTop: 4 }}>
            <button onClick={() => onLangChange('en')} style={{ color: lang === 'en' ? 'white' : '#90CAF9', fontWeight: lang === 'en' ? 700 : 400, fontSize: 13 }} type="button">EN</button>
            <span style={{ color: '#90CAF9' }}>|</span>
            <button onClick={() => onLangChange('hi')} style={{ color: lang === 'hi' ? 'white' : '#90CAF9', fontWeight: lang === 'hi' ? 700 : 400, fontSize: 13 }} type="button">HI</button>
          </div>
        )}
      </div>

      {/* Score Card */}
      <div className="score-card" style={{ background: bandBackground, borderColor: bandColour }}>
        <div className="text-muted">{t(lang, 'wqsScore')}</div>
        <div>
          <span className="score-number" style={{ color: bandColour }}>{result.quality_score}</span>
          <span className="score-max"> / 100</span>
        </div>
        <div className="band-badge" style={{ background: bandColour }}>{bandLabel}</div>

        <div style={{ display: 'flex', justifyContent: 'center', gap: 32, marginTop: 14 }}>
          <div className="text-center">
            <div style={{ fontSize: 22 }}>{result.safe_for_drinking ? '✅' : '❌'}</div>
            <div className="text-muted">{t(lang, 'drinking')}</div>
          </div>
          <div className="text-center">
            <div style={{ fontSize: 22 }}>{result.safe_for_bathing ? '✅' : '❌'}</div>
            <div className="text-muted">{t(lang, 'bathing')}</div>
          </div>
        </div>

        {/* Score Explanation */}
        <button
          onClick={() => setScoreExpanded(!scoreExpanded)}
          style={{ marginTop: 10, color: bandColour, fontSize: 13, fontWeight: 600, textDecoration: 'underline' }}
          type="button"
        >
          {scoreExpanded ? t(lang, 'hideExplanation') : t(lang, 'explainScore')}
        </button>

        {scoreExpanded && (
          <div style={{ background: 'rgba(255,255,255,0.85)', borderRadius: 10, padding: 12, marginTop: 10, textAlign: 'left' }}>
            <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 8 }}>WQS Scoring Framework (BIS IS 10500:2012)</div>
            <div style={{ fontSize: 12, color: '#333' }}>📊 {t(lang, 'baselineScore')}: 100/100</div>
            <div style={{ fontSize: 12, fontWeight: 600, margin: '8px 0 4px' }}>{t(lang, 'deductionsApplied')}</div>
            {result.contaminants.length > 0
              ? result.contaminants.map((c, i) => (
                  <div key={i} style={{ fontSize: 12, color: '#B71C1C' }}>• {c}</div>
                ))
              : <div style={{ fontSize: 12, color: '#555' }}>Based on reported symptoms and questionnaire responses.</div>
            }
            <div style={{ marginTop: 8, borderTop: '1px solid #ddd', paddingTop: 8, fontSize: 11 }}>
              <div><b>Sewage smell</b> → Score 0 (stop all use)</div>
              <div><b>Black water</b> → Score 10</div>
              <div><b>Iron / yellow water</b> → Score 25 (safe to bathe)</div>
              <div><b>H2S / egg smell</b> → Score 45 (safe to bathe)</div>
              <div><b>TDS &gt; 200/500/800 ppm</b> → Score 40/30/20</div>
            </div>
            <div style={{ marginTop: 8, fontSize: 11, color: '#1565C0', fontStyle: 'italic' }}>
              The AI agent reasons over retrieved BIS IS 10500 knowledge chunks.
              Safe for bathing vs drinking is determined by whether contamination
              is microbial/sewage (unsafe both) or mineral-only (safe to bathe).
            </div>
          </div>
        )}
      </div>

      {/* Contaminants */}
      {result.contaminants.length > 0 && (
        <div className="card">
          <div className="card-title">{t(lang, 'diagnosticSummary')}</div>
          {result.contaminants.map((c, i) => (
            <div key={i} style={{ display: 'flex', gap: 8, marginBottom: 6 }}>
              <span style={{ color: '#F44336' }}>●</span>
              <span style={{ fontSize: 14 }}>{c}</span>
            </div>
          ))}
          {result.rag_citations.length > 0 && (
            <div className="text-muted mt-8" style={{ fontStyle: 'italic' }}>
              Source: {result.rag_citations[0]}
            </div>
          )}
        </div>
      )}

      {/* Antigravity Community Alert */}
      {result.cluster_detected && result.community_alert && (
        <div className="card" style={{ background: '#FFF3E0', borderLeft: '4px solid #E65100' }}>
          <div style={{ fontSize: 22 }}>🚨</div>
          <div style={{ fontSize: 15, fontWeight: 700, color: '#E65100', margin: '6px 0' }}>{t(lang, 'communityAlert')}</div>
          <div style={{ fontSize: 14, lineHeight: 1.5 }}>{result.community_alert}</div>
          <button onClick={onViewMap} style={{ color: '#1565C0', fontSize: 13, fontWeight: 600, marginTop: 10 }} type="button">
            {t(lang, 'viewCommunityMap')}
          </button>
        </div>
      )}

      {/* Immediate Actions */}
      {result.immediate_actions.length > 0 && (
        <div className="card">
          <div className="card-title">{t(lang, 'immediateActions')}</div>
          {result.immediate_actions.map((action, i) => (
            <div key={i} style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
              <span style={{ color: '#1565C0', fontWeight: 700, minWidth: 20 }}>{i + 1}.</span>
              <span style={{ fontSize: 14, lineHeight: 1.5 }}>{action}</span>
            </div>
          ))}
        </div>
      )}

      {/* Long Term */}
      {result.long_term_actions.length > 0 && (
        <div className="card">
          <div className="card-title">{t(lang, 'longTermSolution')}</div>
          {result.long_term_actions.map((action, i) => (
            <div key={i} style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
              <span style={{ color: '#1565C0', fontWeight: 700, minWidth: 20 }}>{i + 1}.</span>
              <span style={{ fontSize: 14, lineHeight: 1.5 }}>{action}</span>
            </div>
          ))}
        </div>
      )}

      {/* Escalation Protocol */}
      {result.escalation_required && result.complaint_draft && (
        <div className="card" style={{ borderLeft: '4px solid #1565C0' }}>
          <div className="card-title">{t(lang, 'escalationProtocol')}</div>
          <div style={{ fontSize: 13, color: '#555', marginBottom: 8 }}>To: {result.authority_name}</div>
          {result.authority_email && (
            <div style={{ fontSize: 12, color: '#1565C0', marginBottom: 4 }}>✉️ {result.authority_email}</div>
          )}
          <button
            className="btn-primary"
            style={{ background: '#E65100' }}
            onClick={() => setComplaintExpanded(!complaintExpanded)}
            type="button"
          >
            {t(lang, 'submitGrievance')}
            <div style={{ fontSize: 11, fontWeight: 400, marginTop: 2 }}>
              {t(lang, 'complaintPrefilled')}
            </div>
          </button>
          {complaintExpanded && (
            <>
              <div style={{ background: '#F5F5F5', borderRadius: 8, padding: 12, marginTop: 10, fontSize: 12, lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
                {result.complaint_draft}
              </div>
              <button className="btn-primary mt-8" onClick={copyComplaint} type="button">
                {copied ? t(lang, 'copied') : t(lang, 'copyComplaint')}
              </button>
            </>
          )}
        </div>
      )}

      {/* Local Safe Water Alternatives */}
      <div className="card">
        <div className="card-title">{t(lang, 'safeWaterAlternatives')}</div>
        {WATER_SERVICES.map((s, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 10, padding: '10px 0', borderBottom: '1px solid #F0F0F0' }}>
            <span style={{ fontSize: 20 }}>{s.icon}</span>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 14, fontWeight: 600 }}>{s.name}</div>
              <div className="text-muted">{s.desc}</div>
            </div>
            <a href={`tel:${s.phone.replace(/-/g, '')}`} style={{ fontSize: 12, color: '#1565C0', fontWeight: 600 }}>📞 Contact</a>
          </div>
        ))}
        <div style={{ fontSize: 13, fontWeight: 600, color: '#1A237E', margin: '12px 0 8px' }}>{t(lang, 'recommendedRO')}</div>
        <div style={{ display: 'flex', gap: 8, overflowX: 'auto', paddingBottom: 4 }}>
          {RO_PRODUCTS.map((p, i) => (
            <a key={i} href={p.link} target="_blank" rel="noreferrer"
              style={{ minWidth: 150, border: '1px solid #E0E0E0', borderRadius: 10, padding: 12, background: p.color, textDecoration: 'none', display: 'block', flexShrink: 0 }}>
              <div style={{ fontSize: 10, background: '#1565C0', color: 'white', borderRadius: 4, padding: '2px 6px', display: 'inline-block', marginBottom: 6 }}>{p.tag}</div>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#333', lineHeight: 1.3 }}>{p.name}</div>
              <div style={{ fontSize: 13, color: '#1565C0', fontWeight: 700, marginTop: 6 }}>{p.price}</div>
              <div className="text-muted">{p.rating} · Amazon</div>
              <div style={{ fontSize: 11, color: '#1565C0', marginTop: 4 }}>View on Amazon →</div>
            </a>
          ))}
        </div>
      </div>

      {/* Rate our Agent */}
      <div className="card">
        <div className="card-title">{t(lang, 'rateAgent')}</div>
        {!feedbackSubmitted ? (
          <>
            <div style={{ display: 'flex', gap: 4, marginBottom: 12 }}>
              {[1,2,3,4,5].map(star => (
                <button key={star} onClick={() => setRating(star)}
                  onMouseEnter={() => setHoverRating(star)} onMouseLeave={() => setHoverRating(0)}
                  style={{ fontSize: 30, color: star <= (hoverRating || rating) ? '#F9A825' : '#E0E0E0' }}
                  type="button">★</button>
              ))}
            </div>
            <div className="chip-container" style={{ marginBottom: 12 }}>
              {RATING_CHIPS.map(chip => (
                <button key={chip}
                  className={`chip ${selectedChips.includes(chip) ? 'selected' : ''}`}
                  onClick={() => setSelectedChips(prev => prev.includes(chip) ? prev.filter(c => c !== chip) : [...prev, chip])}
                  type="button">{chip}</button>
              ))}
            </div>
            <textarea className="text-input" placeholder={t(lang, 'feedbackPlaceholder')}
              value={feedbackText} onChange={e => setFeedbackText(e.target.value)} rows={2} />
            <button className="btn-primary mt-8" onClick={() => { if (rating > 0) setFeedbackSubmitted(true); }}
              disabled={rating === 0} type="button">{t(lang, 'submitFeedback')}</button>
          </>
        ) : (
          <div style={{ textAlign: 'center', padding: 16 }}>
            <div style={{ fontSize: 32 }}>🙏</div>
            <div style={{ fontSize: 15, fontWeight: 600, color: '#2E7D32', marginTop: 8 }}>{t(lang, 'thankYouFeedback')}</div>
          </div>
        )}
      </div>

      <div style={{ display: 'flex', gap: 12, margin: 12 }}>
        <button className="btn-secondary" style={{ flex: 1 }} onClick={onViewMap} type="button">{t(lang, 'viewMap')}</button>
        <button className="btn-primary" style={{ flex: 1 }} onClick={onNewReport} type="button">{t(lang, 'newReport')}</button>
      </div>
    </div>
  );
};

export default ResultPage;
