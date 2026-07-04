/**
 * Module: src/pages/AboutPage.tsx
 * Purpose: How WaterSentinel works, privacy policy, competition credits.
 *          Ported from mobile AboutScreen.tsx.
 */

import React from 'react';

const AboutPage: React.FC = () => {
  return (
    <div>
      <div className="header" style={{ textAlign: 'center', padding: '32px 20px' }}>
        <div style={{ fontSize: 48, marginBottom: 8 }}>💧</div>
        <div style={{ fontSize: 26, fontWeight: 700 }}>WaterSentinel</div>
        <div style={{ fontSize: 13, color: '#90CAF9', marginTop: 6 }}>
          The water quality intelligence map India never had
        </div>
      </div>

      {/* How It Works */}
      <div className="card">
        <div className="card-title">How It Works</div>
        {[
          { icon: '📝', title: 'You Report', desc: 'Describe what you observe — smell, colour, taste. No sensor needed.' },
          { icon: '🤖', title: 'AI Analyses', desc: '5 AI agents diagnose your water against BIS IS 10500 Indian standards.' },
          { icon: '🏘️', title: 'Community Alerts', desc: 'If neighbours report the same issue, WaterSentinel detects it automatically.' },
          { icon: '📋', title: 'Action Taken', desc: 'Get a personal advisory and, if needed, a ready-to-file municipal complaint.' },
        ].map((item, i) => (
          <div key={i} style={{ display: 'flex', gap: 12, marginBottom: 14 }}>
            <div style={{
              width: 40, height: 40, borderRadius: 20, background: '#E3F2FD',
              display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18, flexShrink: 0,
            }}>
              {item.icon}
            </div>
            <div>
              <div style={{ fontSize: 14, fontWeight: 600 }}>{item.title}</div>
              <div style={{ fontSize: 13, color: '#555', marginTop: 2, lineHeight: 1.4 }}>{item.desc}</div>
            </div>
          </div>
        ))}
      </div>

      {/* AI Architecture */}
      <div className="card">
        <div className="card-title">🧠 AI Architecture</div>
        {[
          { name: 'Orchestrator', desc: 'Coordinates all agents' },
          { name: 'SourceSense', desc: 'Classifies water source and symptoms' },
          { name: 'WaterProfiler', desc: 'Diagnoses contaminants using BIS/WHO knowledge' },
          { name: 'CommunityMapper', desc: 'Detects community clusters' },
          { name: 'ActionForge', desc: 'Generates advisories and complaints' },
        ].map((agent, i) => (
          <div key={i} style={{ display: 'flex', gap: 10, marginBottom: 10 }}>
            <div style={{ width: 8, height: 8, borderRadius: 4, background: '#1565C0', marginTop: 5, flexShrink: 0 }} />
            <div>
              <div style={{ fontSize: 14, fontWeight: 600 }}>{agent.name}</div>
              <div className="text-muted">{agent.desc}</div>
            </div>
          </div>
        ))}
        <div style={{ fontSize: 11, color: '#9E9E9E', marginTop: 10, fontStyle: 'italic', lineHeight: 1.5 }}>
          Built with Google ADK · Gemini 2.0 Flash · BIS IS 10500:2012 · WHO Guidelines · CGWB Data
        </div>
      </div>

      {/* Privacy */}
      <div className="card">
        <div className="card-title">🔒 Privacy</div>
        {[
          'Only your pincode is stored — never your street address or GPS coordinates',
          'Photos are analysed in memory and immediately discarded',
          'No user account or login required — fully anonymous reporting',
          'No data is sold or shared with advertisers',
        ].map((item, i) => (
          <div key={i} style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
            <span style={{ color: '#2E7D32', fontSize: 16 }}>✓</span>
            <span style={{ fontSize: 13, lineHeight: 1.4 }}>{item}</span>
          </div>
        ))}
      </div>

      {/* Useful Contacts */}
      <div className="card">
        <div className="card-title">📞 Useful Contacts</div>
        {[
          { label: 'HMWSSB Helpline (Hyderabad)', value: '155313', href: 'tel:155313' },
          { label: 'VWSS Helpline (Vijayawada)', value: '0866-2578888', href: 'tel:08662578888' },
          { label: 'CGWB Groundwater Queries', value: '040-23220892', href: 'tel:04023220892' },
          { label: 'National Water Quality Helpline', value: '1800-180-1551', href: 'tel:18001801551' },
          { label: 'HMWSSB Online Complaints', value: 'hmwssb.telangana.gov.in', href: 'https://hmwssb.telangana.gov.in' },
        ].map((contact, i) => (
          <a
            key={i}
            href={contact.href}
            target="_blank"
            rel="noreferrer"
            style={{ display: 'block', padding: '10px 0', borderBottom: '1px solid #F0F0F0' }}
          >
            <div style={{ fontSize: 13, color: '#555' }}>{contact.label}</div>
            <div style={{ fontSize: 14, fontWeight: 600, color: '#1565C0', marginTop: 2 }}>{contact.value}</div>
          </a>
        ))}
      </div>

      {/* Competition Credits */}
      <div className="card">
        <div className="card-title">🏆 Competition</div>
        <div style={{ fontSize: 13, color: '#555', lineHeight: 1.7 }}>
          Submitted to: Kaggle AI Agents Intensive Capstone 2026<br />
          Track: Agents for Good<br />
          Built with: Google ADK, FastMCP, ChromaDB, React, Leaflet.js<br />
          Knowledge: BIS IS 10500:2012 · WHO 2022 · CGWB Telangana/AP 2023<br />
          Map: OpenStreetMap (© contributors)
        </div>
      </div>
    </div>
  );
};

export default AboutPage;
