/**
 * AgentProgress — v5
 * Uses setInterval instead of chained setTimeout.
 * Interval-based approach survives React StrictMode double-mount
 * because cleanup properly clears the interval.
 * Steps advance every 9 seconds via a single persistent interval.
 */

import React, { useState, useEffect, useRef } from 'react';

const STEPS = [
  { name: 'SourceSense',     sub: 'Classifying water source and symptoms...',            done: 'Source classified · Symptoms mapped',        icon: '🔍' },
  { name: 'WaterProfiler',   sub: 'Retrieving BIS IS 10500 knowledge base via RAG...',  done: 'BIS IS 10500 standards retrieved',            icon: '📚' },
  { name: 'WaterProfiler',   sub: 'Diagnosing contaminants · Calculating WQS score...', done: 'Contaminants diagnosed · Score calculated',   icon: '🧪' },
  { name: 'CommunityMapper', sub: 'Checking cluster data for your pincode...',           done: 'Community cluster check complete',            icon: '🏘️' },
  { name: 'ActionForge',     sub: 'Generating advisory and complaint draft...',          done: 'Advisory ready · Complaint drafted',          icon: '📋' },
];

const STEP_DURATION = 9000;

interface AgentProgressProps {
  isActive: boolean;
  onViewResults: () => void;
}

const AgentProgress: React.FC<AgentProgressProps> = ({ isActive, onViewResults }) => {
  const [doneCount, setDoneCount] = useState(0); // how many steps are done (0-5)
  const [elapsed, setElapsed] = useState(0);
  const doneCountRef = useRef(0);

  // Elapsed clock — separate interval, always runs
  useEffect(() => {
    const t = setInterval(() => setElapsed(s => s + 1), 1000);
    return () => clearInterval(t);
  }, []);

  // Step advancement — single interval, clears itself when all done
  useEffect(() => {
    doneCountRef.current = 0;
    setDoneCount(0);

    const t = setInterval(() => {
      doneCountRef.current += 1;
      setDoneCount(doneCountRef.current);
      if (doneCountRef.current >= STEPS.length) {
        clearInterval(t);
      }
    }, STEP_DURATION);

    return () => clearInterval(t);
  }, []);

  if (!isActive) return null;

  const finished = doneCount >= STEPS.length;
  const activeStep = Math.min(doneCount, STEPS.length - 1);
  const pct = Math.round((doneCount / STEPS.length) * 100);
  const fmt = (s: number) => s >= 60 ? `${Math.floor(s / 60)}m ${s % 60}s` : `${s}s`;

  return (
    <div style={{ background: '#fff', borderRadius: 16, padding: 20, marginBottom: 12, border: '1px solid #E0E0E0', boxShadow: '0 2px 8px rgba(0,0,0,0.08)' }}>

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
        <div style={{ fontSize: 14, fontWeight: 700, color: '#1A237E' }}>
          {finished ? '✅ Analysis Complete' : '🤖 AI Agents Working...'}
        </div>
        <div style={{ fontSize: 13, fontWeight: 600, color: '#1565C0', background: '#E3F2FD', padding: '3px 10px', borderRadius: 12 }}>
          ⏱ {fmt(elapsed)}
        </div>
      </div>

      {/* Progress bar */}
      <div style={{ height: 6, background: '#E0E0E0', borderRadius: 3, marginBottom: 16, overflow: 'hidden' }}>
        <div style={{
          height: '100%', width: `${pct}%`, borderRadius: 3, transition: 'width 0.6s ease',
          background: finished
            ? 'linear-gradient(90deg,#2E7D32,#66BB6A)'
            : 'linear-gradient(90deg,#1565C0,#42A5F5)',
        }} />
      </div>

      {/* Steps */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {STEPS.map((step, i) => {
          const done = i < doneCount;
          const active = i === doneCount && !finished;
          const pending = i > doneCount;

          return (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 12, opacity: pending ? 0.35 : 1, transition: 'opacity 0.4s' }}>
              <div style={{
                width: 32, height: 32, borderRadius: 16, flexShrink: 0,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                background: done ? '#E8F5E9' : active ? '#E3F2FD' : '#F5F5F5',
                border: `2px solid ${done ? '#2E7D32' : active ? '#1565C0' : '#E0E0E0'}`,
                fontSize: 15, transition: 'all 0.3s',
              }}>
                {done
                  ? <span style={{ color: '#2E7D32', fontWeight: 700, fontSize: 16 }}>✓</span>
                  : active
                    ? <span style={{ display: 'inline-block', width: 10, height: 10, borderRadius: 5, background: '#1565C0', animation: 'wsPulse 1s infinite' }} />
                    : step.icon}
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 13, fontWeight: 700, color: done ? '#2E7D32' : active ? '#1565C0' : '#9E9E9E' }}>
                  {step.name}{done && <span style={{ fontSize: 11, fontWeight: 400, marginLeft: 6 }}>— Done</span>}
                </div>
                <div style={{ fontSize: 11, color: '#757575', marginTop: 1 }}>
                  {done ? step.done : active ? step.sub : 'Waiting...'}
                </div>
              </div>
              {active && (
                <div style={{ width: 16, height: 16, borderRadius: 8, border: '2px solid #E0E0E0', borderTop: '2px solid #1565C0', animation: 'wsSpin 0.7s linear infinite', flexShrink: 0 }} />
              )}
            </div>
          );
        })}
      </div>

      {/* Message */}
      <div style={{ marginTop: 14, padding: '10px 14px', borderRadius: 8, fontSize: 12, lineHeight: 1.5, background: finished ? '#E8F5E9' : '#F8F9FA', color: finished ? '#2E7D32' : '#555' }}>
        {finished
          ? '✅ All 5 agents completed. Your water quality report is ready.'
          : elapsed < 15 ? '💡 Agents are reading BIS IS 10500 Indian water standards...'
          : elapsed < 30 ? '🏘️ Checking if your neighbours reported similar issues...'
          : '📋 Almost done — preparing your advisory and complaint...'}
      </div>

      {/* View Results button */}
      {finished && (
        <button
          onClick={onViewResults}
          style={{ marginTop: 12, width: '100%', padding: 14, background: '#2E7D32', color: 'white', border: 'none', borderRadius: 10, fontSize: 15, fontWeight: 700, cursor: 'pointer' }}
          type="button"
        >
          🎯 View My Results →
        </button>
      )}

      {!finished && (
        <div style={{ textAlign: 'center', fontSize: 12, color: '#9E9E9E', marginTop: 8 }}>
          Please keep this tab open. Analysis takes 45–60 seconds.
        </div>
      )}

      <style>{`
        @keyframes wsPulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:0.4;transform:scale(0.75)}}
        @keyframes wsSpin{to{transform:rotate(360deg)}}
      `}</style>
    </div>
  );
};

export default AgentProgress;
