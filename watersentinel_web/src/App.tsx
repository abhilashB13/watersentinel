/**
 * Module: src/App.tsx
 * Fixes:
 *   - pincode state passed from ReportPage → ResultPage
 *   - lang state shared across all tabs
 *   - Map is default tab
 */

import React, { useState } from 'react';
import ReportPage from './pages/ReportPage';
import ResultPage from './pages/ResultPage';
import MapPage from './pages/MapPage';
import AboutPage from './pages/AboutPage';
import { WaterReportResponse } from './api/watersentinel';
import './index.css';

type Tab = 'report' | 'map' | 'about';

const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<Tab>('map');
  const [reportResult, setReportResult] = useState<WaterReportResponse | null>(null);
  const [resultPincode, setResultPincode] = useState('');
  const [prefillPincode, setPrefillPincode] = useState('');
  const [prefillArea, setPrefillArea] = useState('');
  const [lang, setLang] = useState<'en' | 'hi'>('en');

  const goToMap = () => { setReportResult(null); setActiveTab('map'); };
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
      <nav className="top-nav">
        <button className={`nav-item ${activeTab === 'report' ? 'active' : ''}`}
          onClick={() => setActiveTab('report')} type="button">
          <span className="nav-icon">📊</span><span>Report</span>
        </button>
        <button className={`nav-item ${activeTab === 'map' ? 'active' : ''}`}
          onClick={() => setActiveTab('map')} type="button">
          <span className="nav-icon">🗺️</span><span>Community Map</span>
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
