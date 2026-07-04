/**
 * Module: src/App.tsx
 * Tab order: Home (default) → Map → Report → About
 * Home tab opens by default on first load.
 */

import React, { useState } from 'react';
import HomePage from './pages/HomePage';
import ReportPage from './pages/ReportPage';
import ResultPage from './pages/ResultPage';
import MapPage from './pages/MapPage';
import AboutPage from './pages/AboutPage';
import { WaterReportResponse } from './api/watersentinel';
import './index.css';

type Tab = 'home' | 'map' | 'report' | 'about';

const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<Tab>('home'); // Home is default
  const [reportResult, setReportResult] = useState<WaterReportResponse | null>(null);
  const [resultPincode, setResultPincode] = useState('');
  const [prefillPincode, setPrefillPincode] = useState('');
  const [prefillArea, setPrefillArea] = useState('');
  const [lang, setLang] = useState<'en' | 'hi'>('en');

  const goToMap = () => { setReportResult(null); setActiveTab('map'); };
  const goToReport = () => { setActiveTab('report'); };
  const newReport = () => { setReportResult(null); };

  const handleReportComplete = (result: WaterReportResponse, pincode: string) => {
    setReportResult(result);
    setResultPincode(pincode);
  };

  const handleReportFromMap = (pincode: string, areaName: string) => {
    setPrefillPincode(pincode);
    setPrefillArea(areaName);
    setReportResult(null);
    setActiveTab('report');
  };

  const renderContent = () => {
    if (activeTab === 'home') {
      return (
        <HomePage
          onGoToReport={goToReport}
          onGoToMap={goToMap}
        />
      );
    }
    if (activeTab === 'report') {
      if (reportResult) {
        return (
          <ResultPage
            result={reportResult}
            onNewReport={newReport}
            onViewMap={goToMap}
            pincode={resultPincode}
            lang={lang}
            onLangChange={setLang}
          />
        );
      }
      return (
        <ReportPage
          onReportComplete={handleReportComplete}
          prefillPincode={prefillPincode}
          prefillArea={prefillArea}
          lang={lang}
          onLangChange={setLang}
        />
      );
    }
    if (activeTab === 'map') return <MapPage onReportFromMap={handleReportFromMap} />;
    if (activeTab === 'about') return <AboutPage />;
    return null;
  };

  return (
    <div className="app-shell">

      {/* Permanent Brand Banner */}
      <div className="brand-banner">
        <div className="brand-banner-left">
          <span className="brand-logo">💧</span>
          <div>
            <div className="brand-name">WaterSentinel</div>
            <div className="brand-tagline">
              India's citizen-powered water quality intelligence
            </div>
          </div>
        </div>
        {(activeTab === 'report' || activeTab === 'about') && (
          <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            <button onClick={() => setLang('en')}
              style={{ color: lang === 'en' ? 'white' : '#90CAF9', fontWeight: lang === 'en' ? 700 : 400, fontSize: 13 }}
              type="button">EN</button>
            <span style={{ color: '#90CAF9' }}>|</span>
            <button onClick={() => setLang('hi')}
              style={{ color: lang === 'hi' ? 'white' : '#90CAF9', fontWeight: lang === 'hi' ? 700 : 400, fontSize: 13 }}
              type="button">HI</button>
          </div>
        )}
      </div>

      {/* Tab Navigation */}
      <nav className="top-nav">
        <button className={`nav-item ${activeTab === 'home' ? 'active' : ''}`}
          onClick={() => setActiveTab('home')} type="button">
          <span className="nav-icon">🏠</span><span>Home</span>
        </button>
        <button className={`nav-item ${activeTab === 'map' ? 'active' : ''}`}
          onClick={() => setActiveTab('map')} type="button">
          <span className="nav-icon">🗺️</span><span>Map</span>
        </button>
        <button className={`nav-item ${activeTab === 'report' ? 'active' : ''}`}
          onClick={() => setActiveTab('report')} type="button">
          <span className="nav-icon">📊</span><span>Report</span>
        </button>
        <button className={`nav-item ${activeTab === 'about' ? 'active' : ''}`}
          onClick={() => setActiveTab('about')} type="button">
          <span className="nav-icon">ℹ️</span><span>About</span>
        </button>
      </nav>

      <div className="app-content">{renderContent()}</div>
    </div>
  );
};

export default App;
