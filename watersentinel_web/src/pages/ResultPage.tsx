/**
 * Module: src/pages/ResultPage.tsx
 * WOW-FACTOR ADDITIONS:
 *   - RAG citation badge showing exact BIS/WHO source retrieved
 *   - MCP call trail showing which tools fired for this request
 *   - Score breakdown now shows real point deductions, not raw symptom names
 */

import React, { useState } from 'react';
import { WaterReportResponse, getBandColour, getBandBackground, getBandLabel } from '../api/watersentinel';

interface ResultPageProps {
  result: WaterReportResponse;
  onNewReport: () => void;
  onViewMap: () => void;
  pincode?: string;
  lang?: 'en' | 'hi';
  onLangChange?: (lang: 'en' | 'hi') => void;
}

const RO_PRODUCTS = [
  { name: 'Kent Grand Plus 9L RO+UV+UF', price: '₹14,500', rating: '4.3 ★', tag: 'Best for High TDS', link: 'https://www.amazon.in/s?k=kent+grand+plus+ro', color: '#E3F2FD' },
  { name: 'Aquaguard Enhance 7L RO+UV', price: '₹11,999', rating: '4.1 ★', tag: 'Best for Iron Removal', link: 'https://www.amazon.in/s?k=aquaguard+enhance+ro+uv', color: '#E8F5E9' },
  { name: 'Pureit Copper+ Mineral RO+UV', price: '₹9,999', rating: '4.2 ★', tag: 'Best Value', link: 'https://www.amazon.in/s?k=pureit+copper+ro', color: '#FFF8E1' },
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

  const scoreDeductions = (result as any).score_deductions || [];
  const ragSource = (result as any).rag_source || '';
  const mcpCalls = (result as any).mcp_calls || [];

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
      {/* Slim context strip */}
      <div style={{ background: '#F0F4F8', borderBottom: '1px solid #E0E0E0', padding: '8px 16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ fontSize: 13, color: '#555' }}>
          <span style={{ color: '#1565C0', fontWeight: 600 }}>📍 Pincode {pincode}</span>
          <span style={{ margin: '0 8px', color: '#BDBDBD' }}>·</span>
          <span>Analysis & Next Steps</span>
        </div>
        <div style={{ fontSize: 11, color: '#9E9E9E' }}>{new Date().toLocaleTimeString()}</div>
      </div>

      {/* Score Card */}
      <div className="score-card" style={{ background: bandBackground, borderColor: bandColour }}>
        <div className="text-muted">WQS Score</div>
        <div>
          <span className="score-number" style={{ color: bandColour }}>{result.quality_score}</span>
          <span className="score-max"> / 100</span>
        </div>
        <div className="band-badge" style={{ background: bandColour }}>{bandLabel}</div>

        <div style={{ display: 'flex', justifyContent: 'center', gap: 32, marginTop: 14 }}>
          <div className="text-center">
            <div style={{ fontSize: 22 }}>{result.safe_for_drinking ? '✅' : '❌'}</div>
            <div className="text-muted">Drinking</div>
          </div>
          <div className="text-center">
            <div style={{ fontSize: 22 }}>{result.safe_for_bathing ? '✅' : '❌'}</div>
            <div className="text-muted">Bathing</div>
          </div>
        </div>

        {/* RAG Citation Badge — WOW FACTOR */}
        {ragSource && (
          <div style={{
            marginTop: 14, display: 'inline-flex', alignItems: 'center', gap: 6,
            background: 'rgba(255,255,255,0.85)', borderRadius: 20, padding: '6px 14px',
            fontSize: 11, color: '#1565C0', fontWeight: 600,
          }}>
            📚 Retrieved via RAG: {ragSource}
          </div>
        )}

        <button
          onClick={() => setScoreExpanded(!scoreExpanded)}
          style={{ display: 'block', margin: '10px auto 0', color: bandColour, fontSize: 13, fontWeight: 600, textDecoration: 'underline' }}
          type="button"
        >
          {scoreExpanded ? '▲ Hide Score Explanation' : '▼ "Explain My Score?"'}
        </button>

        {scoreExpanded && (
          <div style={{ background: 'rgba(255,255,255,0.9)', borderRadius: 10, padding: 14, marginTop: 10, textAlign: 'left' }}>
            <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 8, color: '#1A237E' }}>
              WQS Scoring Framework (BIS IS 10500:2012)
            </div>
            <div style={{ fontSize: 12, color: '#333', marginBottom: 8 }}>📊 Baseline Score: 100/100</div>

            {/* Real point deductions — not raw symptom names */}
            <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 6, color: '#333' }}>Deductions applied:</div>
            {scoreDeductions.length > 0 ? (
              scoreDeductions.map((d: any, i: number) => (
                <div key={i} style={{
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  padding: '6px 0', borderBottom: i < scoreDeductions.length - 1 ? '1px solid #F0F0F0' : 'none',
                }}>
                  <div>
                    <div style={{ fontSize: 12, color: '#333', fontWeight: 500 }}>{d.factor}</div>
                    <div style={{ fontSize: 10, color: '#888' }}>{d.note}</div>
                  </div>
                  <div style={{
                    fontSize: 13, fontWeight: 700,
                    color: d.points < 0 ? '#B71C1C' : '#2E7D32',
                    flexShrink: 0, marginLeft: 12,
                  }}>
                    {d.points === 0 ? '—' : d.points}
                  </div>
                </div>
              ))
            ) : (
              <div style={{ fontSize: 12, color: '#555' }}>No specific deductions recorded.</div>
            )}

            <div style={{ marginTop: 10, borderTop: '1px solid #ddd', paddingTop: 8, fontSize: 11, color: '#555' }}>
              <div><b>Sewage smell</b> → Score 0 (stop all use)</div>
              <div><b>Black water</b> → Score 10</div>
              <div><b>Iron / yellow water</b> → Score 25 (safe to bathe)</div>
              <div><b>H2S / egg smell</b> → Score 45 (safe to bathe)</div>
              <div><b>TDS &gt; 200/500/800 ppm</b> → Score 40/30/20</div>
            </div>

            <div style={{ marginTop: 8, fontSize: 11, color: '#1565C0', fontStyle: 'italic' }}>
              The AI agent reasons over retrieved BIS IS 10500 knowledge chunks. Safe for bathing
              vs drinking is determined by whether contamination is microbial/sewage (unsafe both)
              or mineral-only (safe to bathe).
            </div>
          </div>
        )}
      </div>

      {/* Contaminants */}
      {result.contaminants.length > 0 && (
        <div className="card">
          <div className="card-title">🔬 Household Diagnostic Summary</div>
          {result.contaminants.map((c, i) => (
            <div key={i} style={{ display: 'flex', gap: 8, marginBottom: 6 }}>
              <span style={{ color: '#F44336' }}>●</span>
              <span style={{ fontSize: 14 }}>{c}</span>
            </div>
          ))}
        </div>
      )}

      {/* Antigravity Community Alert + MCP trail — WOW FACTOR */}
      {result.cluster_detected && result.community_alert && (
        <div className="card" style={{ background: '#FFF3E0', borderLeft: '4px solid #E65100' }}>
          <div style={{ fontSize: 22 }}>🚨</div>
          <div style={{ fontSize: 15, fontWeight: 700, color: '#E65100', margin: '6px 0' }}>Community Alert</div>
          <div style={{ fontSize: 14, lineHeight: 1.5 }}>{result.community_alert}</div>

          {/* MCP call trail badges */}
          {mcpCalls.length > 0 && (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 10 }}>
              {mcpCalls.map((call: string, i: number) => (
                <span key={i} style={{
                  fontSize: 10, background: '#FFFFFF', border: '1px solid #E65100',
                  color: '#E65100', borderRadius: 12, padding: '3px 9px', fontWeight: 600,
                }}>
                  🔌 MCP: {call}
                </span>
              ))}
            </div>
          )}

          <button onClick={onViewMap} style={{ color: '#1565C0', fontSize: 13, fontWeight: 600, marginTop: 10 }} type="button">
            View Community Map →
          </button>
        </div>
      )}

      {/* Immediate Actions */}
      {result.immediate_actions.length > 0 && (
        <div className="card">
          <div className="card-title">⚡ Immediate Action Points</div>
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
          <div className="card-title">🛡️ Long-Term Solution</div>
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
          <div className="card-title">📋 Escalation Protocol</div>
          <div style={{ fontSize: 13, color: '#555', marginBottom: 8 }}>To: {result.authority_name}</div>
          {result.authority_email && (
            <div style={{ fontSize: 12, color: '#1565C0', marginBottom: 4 }}>✉️ {result.authority_email}</div>
          )}
          <button className="btn-primary" style={{ background: '#E65100' }} onClick={() => setComplaintExpanded(!complaintExpanded)} type="button">
            📨 Submit Official Grievance to HMWSSB
            <div style={{ fontSize: 11, fontWeight: 400, marginTop: 2 }}>Pre-filled by Agent · Includes diagnosis & data packet</div>
          </button>
          {complaintExpanded && (
            <>
              <div style={{ background: '#F5F5F5', borderRadius: 8, padding: 12, marginTop: 10, fontSize: 12, lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
                {result.complaint_draft}
              </div>
              <button className="btn-primary mt-8" onClick={copyComplaint} type="button">
                {copied ? '✓ Copied!' : '📋 Copy Complaint Text'}
              </button>
            </>
          )}
        </div>
      )}

      {/* Local Safe Water Alternatives */}
      <div className="card">
        <div className="card-title">💧 Local Safe Water Alternatives</div>
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
        <div style={{ fontSize: 13, fontWeight: 600, color: '#1A237E', margin: '12px 0 8px' }}>🛒 Recommended RO Purifiers</div>
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
        <div className="card-title">⭐ Rate our Agent</div>
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
            <textarea className="text-input" placeholder="Any other feedback? (optional)"
              value={feedbackText} onChange={e => setFeedbackText(e.target.value)} rows={2} />
            <button className="btn-primary mt-8" onClick={() => { if (rating > 0) setFeedbackSubmitted(true); }}
              disabled={rating === 0} type="button">Submit Feedback</button>
          </>
        ) : (
          <div style={{ textAlign: 'center', padding: 16 }}>
            <div style={{ fontSize: 32 }}>🙏</div>
            <div style={{ fontSize: 15, fontWeight: 600, color: '#2E7D32', marginTop: 8 }}>Thank you for your feedback!</div>
          </div>
        )}
      </div>

      <div style={{ display: 'flex', gap: 12, margin: 12 }}>
        <button className="btn-secondary" style={{ flex: 1 }} onClick={onViewMap} type="button">🗺️ View Map</button>
        <button className="btn-primary" style={{ flex: 1 }} onClick={onNewReport} type="button">+ New Report</button>
      </div>
    </div>
  );
};

export default ResultPage;
