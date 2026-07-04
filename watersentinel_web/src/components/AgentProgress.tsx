/**
 * Module: src/components/AgentProgress.tsx
 * Purpose: Shows live agent pipeline progress while report is being analysed.
 *   - Each agent step appears sequentially with a tick when complete
 *   - Elapsed time counter shows total time taken
 *   - Progress bar fills as agents complete
 *   - Calming message shown while user waits
 */

import React, { useState, useEffect } from 'react';

interface AgentStep {
  name: string;
  description: string;
  icon: string;
  durationMs: number; // simulated minimum time for this step
}

const AGENT_STEPS: AgentStep[] = [
  {
    name: 'SourceSense',
    description: 'Classifying water source and symptoms...',
    icon: '🔍',
    durationMs: 8000,
  },
  {
    name: 'WaterProfiler',
    description: 'Retrieving BIS IS 10500 knowledge base via RAG...',
    icon: '📚',
    durationMs: 12000,
  },
  {
    name: 'WaterProfiler',
    description: 'Diagnosing contaminants and calculating WQS score...',
    icon: '🧪',
    durationMs: 10000,
  },
  {
    name: 'CommunityMapper',
    description: 'Checking cluster data for your pincode...',
    icon: '🏘️',
    durationMs: 8000,
  },
  {
    name: 'ActionForge',
    description: 'Generating personalised advisory and complaint...',
    icon: '📋',
    durationMs: 10000,
  },
];

interface AgentProgressProps {
  isActive: boolean;
  onComplete?: () => void;
}

const AgentProgress: React.FC<AgentProgressProps> = ({ isActive, onComplete }) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [completedSteps, setCompletedSteps] = useState<number[]>([]);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [done, setDone] = useState(false);

  // Elapsed time counter
  useEffect(() => {
    if (!isActive) return;
    const timer = setInterval(() => {
      setElapsedSeconds(s => s + 1);
    }, 1000);
    return () => clearInterval(timer);
  }, [isActive]);

  // Sequential step progression
  useEffect(() => {
    if (!isActive) return;

    let stepIndex = 0;
    const runStep = () => {
      if (stepIndex >= AGENT_STEPS.length) {
        setDone(true);
        return;
      }
      setCurrentStep(stepIndex);
      const duration = AGENT_STEPS[stepIndex].durationMs;
      setTimeout(() => {
        setCompletedSteps(prev => [...prev, stepIndex]);
        stepIndex++;
        // Small delay between steps — reduces RPM burst
        setTimeout(runStep, 1500);
      }, duration);
    };

    runStep();
  }, [isActive]);

  if (!isActive) return null;

  const progressPercent = Math.round(
    (completedSteps.length / AGENT_STEPS.length) * 100
  );

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return m > 0 ? `${m}m ${s}s` : `${s}s`;
  };

  return (
    <div style={{
      background: '#FFFFFF',
      borderRadius: 16,
      padding: 20,
      margin: '12px 0',
      border: '1px solid #E0E0E0',
      boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div style={{ fontSize: 14, fontWeight: 700, color: '#1A237E' }}>
          🤖 AI Agents Working...
        </div>
        <div style={{
          fontSize: 13, fontWeight: 600,
          color: '#1565C0',
          background: '#E3F2FD',
          padding: '3px 10px',
          borderRadius: 12,
        }}>
          ⏱ {formatTime(elapsedSeconds)}
        </div>
      </div>

      {/* Progress Bar */}
      <div style={{
        height: 6, background: '#E0E0E0',
        borderRadius: 3, marginBottom: 16, overflow: 'hidden',
      }}>
        <div style={{
          height: '100%',
          width: `${progressPercent}%`,
          background: 'linear-gradient(90deg, #1565C0, #42A5F5)',
          borderRadius: 3,
          transition: 'width 0.8s ease',
        }} />
      </div>

      {/* Agent Steps */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {AGENT_STEPS.map((step, i) => {
          const isCompleted = completedSteps.includes(i);
          const isCurrent = currentStep === i && !isCompleted;
          const isPending = i > currentStep;

          return (
            <div key={i} style={{
              display: 'flex', alignItems: 'center', gap: 12,
              opacity: isPending ? 0.4 : 1,
              transition: 'opacity 0.4s',
            }}>
              {/* Status indicator */}
              <div style={{
                width: 28, height: 28, borderRadius: 14, flexShrink: 0,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                background: isCompleted ? '#E8F5E9' : isCurrent ? '#E3F2FD' : '#F5F5F5',
                border: `2px solid ${isCompleted ? '#2E7D32' : isCurrent ? '#1565C0' : '#E0E0E0'}`,
                fontSize: 13,
                transition: 'all 0.3s',
              }}>
                {isCompleted ? '✓' : isCurrent ? (
                  <span style={{
                    display: 'inline-block',
                    width: 10, height: 10,
                    borderRadius: 5,
                    background: '#1565C0',
                    animation: 'pulse 1s infinite',
                  }} />
                ) : step.icon}
              </div>

              {/* Step info */}
              <div style={{ flex: 1 }}>
                <div style={{
                  fontSize: 12, fontWeight: 700,
                  color: isCompleted ? '#2E7D32' : isCurrent ? '#1565C0' : '#9E9E9E',
                }}>
                  {step.name}
                  {isCompleted && (
                    <span style={{ fontSize: 11, fontWeight: 400, marginLeft: 6, color: '#2E7D32' }}>
                      — Done
                    </span>
                  )}
                </div>
                <div style={{ fontSize: 11, color: '#757575', marginTop: 1 }}>
                  {isCompleted
                    ? step.description.replace('...', '')
                    : isCurrent
                      ? step.description
                      : 'Waiting...'}
                </div>
              </div>

              {/* Spinner for active step */}
              {isCurrent && (
                <div className="spinner" style={{
                  borderTopColor: '#1565C0',
                  borderColor: '#E0E0E0',
                  borderTopColor: '#1565C0',
                  width: 16, height: 16,
                  border: '2px solid #E0E0E0',
                  borderTop: '2px solid #1565C0',
                  borderRadius: 8,
                  animation: 'spin 0.7s linear infinite',
                }} />
              )}
            </div>
          );
        })}
      </div>

      {/* Reassuring message */}
      <div style={{
        marginTop: 16, padding: '10px 14px',
        background: '#F8F9FA', borderRadius: 8,
        fontSize: 12, color: '#555', lineHeight: 1.5,
      }}>
        {elapsedSeconds < 20
          ? '💡 Agents are reading BIS IS 10500 Indian water standards before diagnosing...'
          : elapsedSeconds < 40
            ? '🏘️ Checking if your neighbours reported similar issues this week...'
            : '📋 Almost done — preparing your personalised advisory and complaint if needed...'}
      </div>

      {/* Pulse animation style */}
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.5; transform: scale(0.8); }
        }
      `}</style>
    </div>
  );
};

export default AgentProgress;
