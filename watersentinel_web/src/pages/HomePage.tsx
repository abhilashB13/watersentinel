/**
 * Module: src/pages/HomePage.tsx
 * Changes:
 *   - Stats moved inside hero gradient (white text on blue)
 *   - 3 columns only (dropped Hyderabad — obvious from context)
 *   - Larger emoji in intent cards (36px)
 *   - Removed standalone stats bar below hero
 */

import React, { useState, useEffect } from 'react';
import { getTopologyData } from '../api/watersentinel';

interface HomePageProps {
  onGoToReport: () => void;
  onGoToMap: () => void;
}

const HomePage: React.FC<HomePageProps> = ({ onGoToReport, onGoToMap }) => {
  const [stats, setStats] = useState({ areas: 15, critical: 6, reports: 24 });

  useEffect(() => {
    getTopologyData().then(data => {
      setStats({
        areas: data.length,
        critical: data.filter(p => p.colour_band === 'red').length,
        reports: data.reduce((sum, p) => sum + (p.report_count || 0), 0),
      });
    }).catch(() => {});
  }, []);

  return (
    <div>

      {/* ── Hero + Stats combined ── */}
      <div style={{
        background: 'linear-gradient(160deg, #0D47A1 0%, #1565C0 60%, #1976D2 100%)',
        padding: '36px 24px 0',
        textAlign: 'center',
      }}>
        <div style={{ fontSize: 44, marginBottom: 10 }}>💧</div>
        <h1 style={{
          fontSize: 26, fontWeight: 800, color: '#FFFFFF',
          margin: '0 0 10px', lineHeight: 1.25,
        }}>
          Understand Your Water.<br />Protect Your Community.
        </h1>
        <p style={{
          fontSize: 14, color: '#90CAF9',
          margin: '0 0 24px', lineHeight: 1.6,
        }}>
          600 million Indians drink unverified water daily.<br />
          WaterSentinel changes that — one citizen report at a time.
        </p>

        {/* CTA Buttons */}
        <div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap', marginBottom: 32 }}>
          <button
            onClick={onGoToReport}
            style={{
              background: '#FFFFFF', color: '#1565C0',
              border: 'none', borderRadius: 24,
              padding: '13px 28px', fontSize: 14, fontWeight: 700, cursor: 'pointer',
            }}
            type="button"
          >
            🔍 Analyse My Water
          </button>
          <button
            onClick={onGoToMap}
            style={{
              background: 'transparent', color: '#FFFFFF',
              border: '2px solid rgba(255,255,255,0.6)', borderRadius: 24,
              padding: '13px 28px', fontSize: 14, fontWeight: 600, cursor: 'pointer',
            }}
            type="button"
          >
            🗺️ View Live Map
          </button>
        </div>

        {/* Live stats — inside hero, white text, 3 columns */}
        <div style={{
          display: 'flex',
          borderTop: '1px solid rgba(255,255,255,0.15)',
          paddingTop: 16,
          paddingBottom: 20,
        }}>
          {[
            { icon: '📍', value: stats.areas, label: 'Areas Monitored' },
            { icon: '🔴', value: stats.critical, label: 'Critical Zones' },
            { icon: '📊', value: stats.reports, label: 'Reports Filed' },
          ].map((stat, i, arr) => (
            <React.Fragment key={i}>
              <div style={{ flex: 1, textAlign: 'center' }}>
                <span style={{ fontSize: 22, display: 'block', marginBottom: 4 }}>{stat.icon}</span>
                <div style={{ fontSize: 24, fontWeight: 800, color: 'white', lineHeight: 1 }}>
                  {stat.value}
                </div>
                <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.7)', marginTop: 4 }}>
                  {stat.label}
                </div>
              </div>
              {i < arr.length - 1 && (
                <div style={{ width: 1, background: 'rgba(255,255,255,0.2)', margin: '4px 0' }} />
              )}
            </React.Fragment>
          ))}
        </div>
      </div>

      {/* ── Intent Cards ── */}
      <div style={{ padding: '16px 12px 0' }}>
        <div style={{ fontSize: 15, fontWeight: 700, color: '#1A237E', marginBottom: 12 }}>
          What do you want to analyse?
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
          {[
            {
              icon: '🏥', title: 'Health Risk Detection',
              desc: 'AI diagnosis for Cholera, Typhoid, stomach issues linked to water',
              color: '#E3F2FD', border: '#1565C0',
            },
            {
              icon: '🔧', title: 'RO Intelligence',
              desc: 'Personalise your RO filter settings based on your water profile',
              color: '#E8F5E9', border: '#2E7D32',
            },
            {
              icon: '🏠', title: 'Daily Use & Tank Health',
              desc: 'Chlorine levels, tank cleaning schedule, pipe condition check',
              color: '#FFF8E1', border: '#F57F17',
            },
            {
              icon: '💧', title: 'General Water Safety',
              desc: 'Full water quality score with BIS IS 10500 standard benchmarks',
              color: '#F3E5F5', border: '#7B1FA2',
            },
          ].map((card, i) => (
            <button
              key={i}
              onClick={onGoToReport}
              style={{
                background: card.color,
                border: `2px solid ${card.border}22`,
                borderRadius: 12, padding: 14,
                textAlign: 'left', cursor: 'pointer',
              }}
              onMouseEnter={e => (e.currentTarget.style.borderColor = card.border)}
              onMouseLeave={e => (e.currentTarget.style.borderColor = `${card.border}22`)}
              type="button"
            >
              {/* Larger icon — 36px */}
              <div style={{ fontSize: 36, marginBottom: 8 }}>{card.icon}</div>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#1A237E', marginBottom: 4, lineHeight: 1.3 }}>
                {card.title}
              </div>
              <div style={{ fontSize: 11, color: '#555', lineHeight: 1.4 }}>
                {card.desc}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* ── Standards We Use ── */}
      <div style={{ margin: '16px 12px 0' }}>
        <div style={{ fontSize: 15, fontWeight: 700, color: '#1A237E', marginBottom: 4 }}>
          Built on authoritative standards
        </div>
        <div style={{ fontSize: 12, color: '#757575', marginBottom: 12 }}>
          Every score and recommendation is grounded in real Indian and international data
        </div>
        {[
          {
            badge: 'BIS IS 10500:2012', badgeColor: '#1565C0',
            title: 'Bureau of Indian Standards — Drinking Water',
            desc: 'Sets the legal limits we score against. H2S: 0.05 mg/L · Iron: 0.3 mg/L · TDS: 500 mg/L. Every WQS deduction is cited against a specific BIS parameter.',
          },
          {
            badge: 'WHO 2022', badgeColor: '#2E7D32',
            title: 'WHO Guidelines for Drinking-water Quality',
            desc: 'Global health-based targets used to classify contaminant risk severity. Provides health impact context that BIS limits alone do not capture.',
          },
          {
            badge: 'CGWB 2023', badgeColor: '#E65100',
            title: 'Central Ground Water Board — Telangana & AP',
            desc: 'Regional groundwater quality data for Hyderabad and Andhra Pradesh. Explains why H2S is common in BHEL-area borewells at 300+ feet.',
          },
        ].map((std, i) => (
          <div key={i} style={{
            background: '#FFFFFF', border: '1px solid #E0E0E0',
            borderRadius: 10, padding: 14, marginBottom: 10,
          }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
              <div style={{
                background: std.badgeColor, color: 'white',
                borderRadius: 6, padding: '3px 8px',
                fontSize: 10, fontWeight: 700, flexShrink: 0, marginTop: 2,
              }}>
                {std.badge}
              </div>
              <div>
                <div style={{ fontSize: 13, fontWeight: 600, color: '#1A237E', marginBottom: 3 }}>
                  {std.title}
                </div>
                <div style={{ fontSize: 12, color: '#555', lineHeight: 1.5 }}>
                  {std.desc}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* ── Mission & Government Outreach ── */}
      <div style={{ margin: '16px 12px 0' }}>
        <div style={{ fontSize: 15, fontWeight: 700, color: '#1A237E', marginBottom: 4 }}>
          Mission & National Scaling
        </div>
        <div style={{ fontSize: 12, color: '#757575', marginBottom: 12 }}>
          Citizen data automates municipal response and empowers communities nationwide
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10, marginBottom: 16 }}>
          {[
            { icon: '🏛️', title: 'HMWSSB Integration', desc: 'Real-time data flow to optimise city planning', color: '#E3F2FD' },
            { icon: '🌐', title: '10 Indian Cities', desc: 'Pan-India network expansion underway', color: '#E8F5E9' },
            { icon: '📡', title: 'Jal Jeevan Mission', desc: 'Validating last-mile coverage data nationally', color: '#FFF8E1' },
          ].map((tile, i) => (
            <div key={i} style={{ background: tile.color, borderRadius: 10, padding: 12, textAlign: 'center' }}>
              <div style={{ fontSize: 28, marginBottom: 6 }}>{tile.icon}</div>
              <div style={{ fontSize: 11, fontWeight: 700, color: '#1A237E', marginBottom: 4, lineHeight: 1.3 }}>
                {tile.title}
              </div>
              <div style={{ fontSize: 10, color: '#555', lineHeight: 1.4 }}>{tile.desc}</div>
            </div>
          ))}
        </div>

        <div style={{
          background: '#E8F4FD', borderLeft: '4px solid #1565C0',
          borderRadius: 8, padding: 14, marginBottom: 16,
        }}>
          <div style={{ fontSize: 13, color: '#1A237E', lineHeight: 1.7 }}>
            <b>Our Vision:</b> WaterSentinel is building India's first citizen-powered water
            quality intelligence network. Every report you file becomes a data point that
            protects your neighbourhood. When enough citizens report, we automatically alert
            the municipality — so you don't have to.
          </div>
        </div>
      </div>

      {/* ── CTA Bottom ── */}
      <div style={{ padding: '0 12px 24px' }}>
        <button
          onClick={onGoToReport}
          style={{
            background: '#1565C0', color: 'white',
            border: 'none', borderRadius: 12,
            padding: '16px', fontSize: 15, fontWeight: 700,
            width: '100%', cursor: 'pointer',
          }}
          type="button"
        >
          💧 Contribute Your Data. Protect Your City.
        </button>
        <div style={{ textAlign: 'center', fontSize: 11, color: '#9E9E9E', marginTop: 8 }}>
          * Our AI Agent supports Voice, Text, and Photo evidence
        </div>
      </div>

    </div>
  );
};

export default HomePage;
