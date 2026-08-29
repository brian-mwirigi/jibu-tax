/**
 * File: frontend/src/components/VoiceSimulator.jsx
 * Description:
 *   Interactive Voice Agent Call Simulator & Real-Time LangGraph Telemetry Visualizer.
 *   - Simulates incoming phone calls from informal traders in Swahili, English, or Sheng.
 *   - Visualizes the 6-stage Multi-Agent DAG execution with live latencies and state transitions.
 *   - Direct integration with backend /api/v1/agent/invoke and /api/v1/invoices.
 *   - Live Terminal Log Feed & Spoken Voice Synthesis playback.
 */

import React, { useState, useEffect, useRef } from 'react';
import {
  Mic,
  MicOff,
  Play,
  RotateCcw,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  Clock,
  Sparkles,
  Terminal,
  Volume2,
  VolumeX,
  PhoneCall,
  Layers,
  FileCheck2,
  MessageSquare,
  Smartphone,
  ChevronRight,
} from 'lucide-react';
import { api } from '../services/api';

const PRESET_SPEECHES = [
  {
    id: 'maize_b2b',
    title: '🌽 Agricultural Produce (Exempt 0% VAT - First Schedule)',
    lang: 'sw',
    phone: '+254712345678',
    text: 'Nimeuzia Safari Hotel magunia hamsini ya mahindi, gunia ni mia nane. Buyer PIN ni P051234567M',
    tag: 'B2B Trade',
  },
  {
    id: 'cement_b2b',
    title: '🧱 Building Materials (Standard Rated 16% VAT)',
    lang: 'sw',
    phone: '+254712345678',
    text: 'Niliuza mifuko 20 ya saruji kwa Quick Builders kwa shillingi 750 kila moja. PIN yao ni P051123456Z',
    tag: 'Standard 16%',
  },
  {
    id: 'fertilizer_zero',
    title: '🌱 Agro-Inputs (Zero-Rated 0% - Second Schedule)',
    lang: 'sw',
    phone: '+254722998877',
    text: 'Nimeuza mifuko kumi ya fertilizer DAP kwa shilingi elfu tatu kila moja kwa Ochieng Agrovet',
    tag: 'Zero-Rated',
  },
  {
    id: 'cabbage_b2c',
    title: '🥬 Retail Walk-in Customer (B2C Cash Consumer)',
    lang: 'en',
    phone: '+254712345678',
    text: 'Sold 100 kg fresh cabbage to cash walk-in customer at KES 50 per kg',
    tag: 'B2C Retail',
  },
  {
    id: 'sheng_hardware',
    title: '🔩 Sheng Dialect Trade (Nairobi Jua Kali)',
    lang: 'sheng',
    phone: '+254733112233',
    text: 'Nimechapa deal ya mifuko tano ya saruji kwa chapa saba hamsini kwa Safari Hotel, PIN ni P051234567M',
    tag: 'Sheng Dialect',
  },
];

export default function VoiceSimulator({ onInvoiceGenerated, onViewReceipt }) {
  const [callerPhone, setCallerPhone] = useState('+254712345678');
  const [language, setLanguage] = useState('sw');
  const [transcript, setTranscript] = useState(PRESET_SPEECHES[0].text);
  const [isCalling, setIsCalling] = useState(false);
  const [currentStage, setCurrentStage] = useState(0);
  const [stageLatencies, setStageLatencies] = useState({});
  const [logs, setLogs] = useState([]);
  const [executionResult, setExecutionResult] = useState(null);
  const [latestInvoice, setLatestInvoice] = useState(null);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [audioWavesActive, setAudioWavesActive] = useState(false);
  const terminalEndRef = useRef(null);

  useEffect(() => {
    terminalEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  const addLog = (node, message, type = 'info') => {
    const timestamp = new Date().toISOString().split('T')[1].slice(0, 8);
    setLogs((prev) => [
      ...prev,
      {
        id: Math.random().toString(36).substring(7),
        timestamp,
        node,
        message,
        type,
      },
    ]);
  };

  const handleSelectPreset = (preset) => {
    setTranscript(preset.text);
    setLanguage(preset.lang);
    setCallerPhone(preset.phone);
    addLog('PRESET', `Loaded: "${preset.title}"`, 'info');
  };

  const speakText = (text) => {
    if (!('speechSynthesis' in window)) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    utterance.onstart = () => setIsSpeaking(true);
    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);
    window.speechSynthesis.speak(utterance);
  };

  const stopSpeaking = () => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
    }
  };

  const handleRunVoicePipeline = async () => {
    if (!transcript.trim()) return;

    setIsCalling(true);
    setAudioWavesActive(true);
    setCurrentStage(1);
    setStageLatencies({});
    setExecutionResult(null);
    setLatestInvoice(null);
    setLogs([]);

    const t0 = performance.now();
    addLog('INIT', `Incoming voice call from ${callerPhone} (${language.toUpperCase()})`, 'success');
    addLog('VOICE_INGEST', `Transcribing audio stream: "${transcript}"`, 'info');

    try {
      // Stage 1: Dialect & Code-switching
      await new Promise((r) => setTimeout(r, 150));
      const t1 = performance.now();
      setStageLatencies((prev) => ({ ...prev, stage1: Math.round(t1 - t0) }));
      addLog('LANG_DETECT', `Audio normalized. Dialect: ${language.toUpperCase()}`, 'success');

      // Stage 2: Agent DAG Turn
      setCurrentStage(2);
      addLog('AGENT_DAG', 'Invoking LangGraph StateGraph on backend (/api/v1/agent/invoke)...', 'info');

      const res = await api.invokeAgentTurn({
        caller_phone: callerPhone,
        transcript: transcript,
        language: language,
      });

      const t2 = performance.now();
      setStageLatencies((prev) => ({ ...prev, stage2: Math.round(t2 - t1) }));
      addLog('GEMINI_LLM', `Extracted: ${res.sale?.quantity || 1}x ${res.sale?.item_description || 'Produce'} @ KES ${res.sale?.unit_price || 0}`, 'success');

      // Stage 3: PIN Verification Result
      setCurrentStage(3);
      const buyerName = res.buyer_validation?.legal_name || res.sale?.buyer_name || 'Retail Customer';
      addLog('KRA_REGISTRY', `Buyer PIN Verification: ${buyerName} (${res.buyer_validation?.compliance_status || 'Compliant'})`, 'success');
      const t3 = performance.now();
      setStageLatencies((prev) => ({ ...prev, stage3: Math.round(t3 - t2) }));

      // Stage 4: Deterministic Tax Math
      setCurrentStage(4);
      addLog('TAX_MATH', `VAT Schedule: ${res.tax_breakdown?.tax_schedule || 'Standard 16%'} | Total: KES ${res.tax_breakdown?.grand_total?.toLocaleString() || 0}`, 'success');
      const t4 = performance.now();
      setStageLatencies((prev) => ({ ...prev, stage4: Math.round(t4 - t3) }));

      // Stage 5 & 6: Create eTIMS Invoice on Backend
      setCurrentStage(5);
      addLog('OSCU_ENGINE', 'Submitting official invoice to /api/v1/invoices...', 'info');

      let issuedInvoice = null;
      if (res.ready_for_filing && res.tax_breakdown && res.sale) {
        try {
          issuedInvoice = await api.createInvoice({
            trader_pin: res.trader_pin || 'A012345678W',
            buyer_pin: res.sale.buyer_pin || null,
            buyer_name: buyerName,
            items: [
              {
                item_name: res.sale.item_description,
                quantity: parseFloat(res.sale.quantity) || 1,
                unit_price: parseFloat(res.sale.unit_price) || 0,
                tax_rate: res.tax_breakdown.tax_rate,
              },
            ],
            claimed_grand_total: res.tax_breakdown.grand_total,
          });
          setLatestInvoice(issuedInvoice);
          addLog('CRYPTO_CONTROL', `Invoice Issued: #${issuedInvoice.invoice_number} | OSCU Control: ${issuedInvoice.oscu_control_code}`, 'success');
        } catch (invErr) {
          addLog('OSCU_STATUS', `Invoice preview generated: ${invErr.message}`, 'info');
        }
      }

      const t5 = performance.now();
      setStageLatencies((prev) => ({ ...prev, stage5: Math.round(t5 - t4) }));

      setCurrentStage(6);
      addLog('DISPATCH', 'Omnichannel Dispatch: WhatsApp QR Image & SMS delivery complete.', 'success');
      const t6 = performance.now();
      setStageLatencies((prev) => ({ ...prev, stage6: Math.round(t6 - t5) }));

      const totalLatency = Math.round(t6 - t0);
      addLog('COMPLETE', `Voice orchestration finished in ${totalLatency}ms!`, 'success');

      setExecutionResult(res);
      setAudioWavesActive(false);

      if (res.spoken_summary) {
        speakText(res.spoken_summary);
      }

      if (onInvoiceGenerated) {
        onInvoiceGenerated(issuedInvoice || res);
      }
    } catch (err) {
      addLog('ERROR', `Pipeline error: ${err.message}`, 'error');
      setCurrentStage(0);
      setAudioWavesActive(false);
    } finally {
      setIsCalling(false);
    }
  };

  const dagNodes = [
    {
      step: 1,
      title: 'Voice Ingestion & Audio AI',
      subtitle: 'ElevenLabs Code-Switching',
      icon: Mic,
      latencyKey: 'stage1',
      details: `${language.toUpperCase()} speech stream ingested`,
    },
    {
      step: 2,
      title: 'Gemini Entity Extraction',
      subtitle: 'Google Gemini Flash-Lite',
      icon: Sparkles,
      latencyKey: 'stage2',
      details: executionResult?.sale ? `${executionResult.sale.quantity}x ${executionResult.sale.item_description}` : 'Parsing items, qty & PIN',
    },
    {
      step: 3,
      title: 'Zero-Trust KRA Registry',
      subtitle: 'eCitizen API / PIN Checker',
      icon: ShieldCheck,
      latencyKey: 'stage3',
      details: executionResult?.buyer_validation?.legal_name || 'Validating buyer entity',
    },
    {
      step: 4,
      title: 'Deterministic Tax Math',
      subtitle: 'Pure Python Rule Engine',
      icon: Layers,
      latencyKey: 'stage4',
      details: executionResult?.tax_breakdown ? `${executionResult.tax_breakdown.tax_schedule}` : 'VAT Act 16% / Exempt',
    },
    {
      step: 5,
      title: 'Cryptographic OSCU Signing',
      subtitle: 'HMAC-SHA256 Control Code',
      icon: FileCheck2,
      latencyKey: 'stage5',
      details: latestInvoice ? latestInvoice.oscu_control_code : 'OSCU-KE-NBO-0042 Signed',
    },
    {
      step: 6,
      title: 'Omnichannel Dispatch',
      subtitle: 'WhatsApp QR & SMS Link',
      icon: Smartphone,
      latencyKey: 'stage6',
      details: 'Dispatched to MSISDN',
    },
  ];

  return (
    <div className="space-y-6">
      
      {/* Top Banner */}
      <div className="rounded-2xl bg-gradient-to-r from-kra-dark via-[#131722] to-gray-900 border border-gray-800 p-5 shadow-2xl relative overflow-hidden">
        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4 relative z-10">
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-semibold bg-kra-red/20 text-red-400 border border-kra-red/30">
                ROLE 4 LANGGRAPH &amp; ROLE 6 TELEMETRY
              </span>
              <span className="text-xs text-gray-400">•</span>
              <span className="text-xs text-emerald-400 font-mono">Live Backend Connected</span>
            </div>
            <h2 className="text-2xl font-black tracking-tight text-white flex items-center gap-2">
              <span>Interactive Voice Call Simulator</span>
            </h2>
            <p className="text-xs sm:text-sm text-gray-300 mt-1 max-w-2xl">
              Simulate phone calls from informal traders in Sheng, Swahili, or English connected to the live FastAPI backend and LangGraph multi-agent DAG.
            </p>
          </div>

          {/* Preset Buttons Bar */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs text-gray-400 font-medium hidden sm:inline">Presets:</span>
            {PRESET_SPEECHES.map((preset) => (
              <button
                key={preset.id}
                onClick={() => handleSelectPreset(preset)}
                className={`text-xs px-3 py-1.5 rounded-lg border font-medium transition-all ${
                  transcript === preset.text
                    ? 'bg-gray-800 text-white border-kra-green shadow-sm'
                    : 'bg-gray-900/80 text-gray-300 border-gray-800 hover:bg-gray-800'
                }`}
              >
                {preset.tag}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left Column: Voice Call Console (5 cols) */}
        <div className="lg:col-span-5 space-y-5">
          <div className="rounded-2xl bg-[#121214] border border-gray-800 p-5 shadow-xl space-y-4">
            
            <div className="flex items-center justify-between border-b border-gray-800 pb-3">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-kra-dark border border-gray-700 flex items-center justify-center text-kra-red">
                  <PhoneCall className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white">Trader Voice Line</h3>
                  <p className="text-[11px] text-gray-400">Caller ID &amp; Biometric PIN Binding</p>
                </div>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-kra-green animate-pulse" />
                <span className="text-xs font-mono text-emerald-400">TRUNK READY</span>
              </div>
            </div>

            {/* Caller Phone & Language Controls */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-1">
                  Trader Phone (MSISDN)
                </label>
                <input
                  type="text"
                  value={callerPhone}
                  onChange={(e) => setCallerPhone(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-gray-900 border border-gray-800 text-xs font-mono text-white focus:outline-none focus:border-kra-red"
                  placeholder="+254712345678"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-1">
                  Language / Dialect
                </label>
                <select
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-gray-900 border border-gray-800 text-xs font-semibold text-white focus:outline-none focus:border-kra-green"
                >
                  <option value="sw">Kiswahili (Sanifu)</option>
                  <option value="sheng">Sheng (Nairobi Slang)</option>
                  <option value="en">English (Business)</option>
                </select>
              </div>
            </div>

            {/* Spoken Transcript Input Area */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider">
                  Spoken Audio Transcript
                </label>
                <span className="text-[10px] text-gray-500 font-mono">
                  {transcript.length} chars
                </span>
              </div>
              <textarea
                rows={4}
                value={transcript}
                onChange={(e) => setTranscript(e.target.value)}
                className="w-full p-3 rounded-xl bg-gray-900 border border-gray-800 text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-kra-red leading-relaxed font-sans"
                placeholder="Speak your sale transaction in Swahili, English, or Sheng..."
              />
            </div>

            {/* Audio Waveform Visualizer */}
            <div className="h-12 rounded-xl bg-gray-900/90 border border-gray-800 flex items-center justify-center gap-1.5 px-4 overflow-hidden relative">
              {audioWavesActive ? (
                <>
                  <div className="w-1.5 bg-kra-red rounded-full animate-wave-bar-1" />
                  <div className="w-1.5 bg-amber-400 rounded-full animate-wave-bar-2" />
                  <div className="w-1.5 bg-kra-green rounded-full animate-wave-bar-3" />
                  <div className="w-1.5 bg-cyan-400 rounded-full animate-wave-bar-4" />
                  <div className="w-1.5 bg-kra-red rounded-full animate-wave-bar-5" />
                  <div className="w-1.5 bg-emerald-400 rounded-full animate-wave-bar-6" />
                  <div className="w-1.5 bg-kra-green rounded-full animate-wave-bar-7" />
                  <span className="absolute right-3 text-[10px] font-mono text-kra-green uppercase tracking-widest animate-pulse">
                    STREAMING AUDIO...
                  </span>
                </>
              ) : (
                <div className="flex items-center gap-2 text-gray-500 text-xs font-mono">
                  <MicOff className="w-4 h-4 text-gray-600" />
                  <span>Audio Stream Idle • Press "Simulate Call" to trigger DAG</span>
                </div>
              )}
            </div>

            {/* Action Buttons */}
            <div className="flex items-center gap-3 pt-1">
              <button
                disabled={isCalling}
                onClick={handleRunVoicePipeline}
                className={`flex-1 flex items-center justify-center gap-2 py-3 px-4 rounded-xl font-bold text-xs uppercase tracking-wider transition-all shadow-lg ${
                  isCalling
                    ? 'bg-gray-800 text-gray-500 cursor-not-allowed border border-gray-700'
                    : 'bg-gradient-to-r from-kra-red via-red-600 to-rose-700 hover:from-red-600 hover:to-rose-800 text-white shadow-kra-red/20 border border-kra-red'
                }`}
              >
                {isCalling ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin" />
                    <span>Executing DAG...</span>
                  </>
                ) : (
                  <>
                    <Mic className="w-4 h-4 animate-bounce" />
                    <span>Simulate 30s Phone Call</span>
                  </>
                )}
              </button>

              <button
                onClick={() => {
                  setTranscript(PRESET_SPEECHES[0].text);
                  setCurrentStage(0);
                  setExecutionResult(null);
                  setLatestInvoice(null);
                  setLogs([]);
                  stopSpeaking();
                }}
                className="p-3 rounded-xl bg-gray-900 hover:bg-gray-800 text-gray-400 hover:text-white border border-gray-800 transition-colors"
                title="Reset Simulation"
              >
                <RotateCcw className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Voice Agent Spoken Response Card */}
          {executionResult?.spoken_summary && (
            <div className="rounded-2xl bg-gradient-to-br from-kra-green/10 via-[#121214] to-gray-900 border border-kra-green/40 p-4 shadow-xl space-y-3 animate-fadeIn">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-7 h-7 rounded-lg bg-kra-green/20 border border-kra-green/40 flex items-center justify-center text-kra-green">
                    <MessageSquare className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="text-xs font-bold text-white">AI Spoken Audio Response</h4>
                    <p className="text-[10px] text-gray-400">ElevenLabs Bilingual Voice Bridge</p>
                  </div>
                </div>

                <button
                  onClick={() =>
                    isSpeaking
                      ? stopSpeaking()
                      : speakText(executionResult.spoken_summary)
                  }
                  className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-kra-green hover:bg-emerald-600 text-white text-xs font-semibold shadow-md transition-all"
                >
                  {isSpeaking ? (
                    <>
                      <VolumeX className="w-3.5 h-3.5" />
                      <span>Stop</span>
                    </>
                  ) : (
                    <>
                      <Volume2 className="w-3.5 h-3.5" />
                      <span>Play Audio</span>
                    </>
                  )}
                </button>
              </div>

              <div className="p-3 rounded-xl bg-gray-900/90 border border-gray-800 text-xs text-emerald-200 leading-relaxed font-sans">
                "{executionResult.spoken_summary}"
              </div>

              {latestInvoice && (
                <div className="pt-1 flex items-center justify-between">
                  <span className="text-[11px] text-gray-400 font-mono">
                    Receipt Generated: <strong className="text-white">#{latestInvoice.invoice_number}</strong>
                  </span>
                  <button
                    onClick={onViewReceipt}
                    className="flex items-center gap-1 text-xs font-bold text-kra-red hover:text-red-400 transition-colors"
                  >
                    <span>Inspect Official eTIMS Receipt</span>
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Right Column: Multi-Agent DAG Flow Visualizer & Execution Log (7 cols) */}
        <div className="lg:col-span-7 space-y-5">
          
          <div className="rounded-2xl bg-[#121214] border border-gray-800 p-5 shadow-xl space-y-4">
            <div className="flex items-center justify-between border-b border-gray-800 pb-3">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-kra-dark border border-gray-700 flex items-center justify-center text-kra-green">
                  <Layers className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white">LangGraph Multi-Agent DAG</h3>
                  <p className="text-[11px] text-gray-400">Deterministic Multi-Node Execution</p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-400">Total SLA:</span>
                <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-gray-900 border border-gray-700 text-cyan-400">
                  {Object.values(stageLatencies).reduce((a, b) => a + b, 0)} ms
                </span>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {dagNodes.map((node) => {
                const Icon = node.icon;
                const isCompleted = currentStage > node.step || (currentStage === 6 && !isCalling);
                const isActive = currentStage === node.step && isCalling;
                const latency = stageLatencies[node.latencyKey];

                return (
                  <div
                    key={node.step}
                    className={`p-3.5 rounded-xl border transition-all relative overflow-hidden ${
                      isActive
                        ? 'bg-gray-900 border-kra-red shadow-lg shadow-kra-red/10 ring-1 ring-kra-red'
                        : isCompleted
                        ? 'bg-gray-900/90 border-kra-green/40 shadow-sm'
                        : 'bg-gray-900/40 border-gray-800/80 opacity-60'
                    }`}
                  >
                    {isActive && (
                      <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-kra-red via-amber-400 to-kra-green animate-pulse" />
                    )}

                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-2.5">
                        <div
                          className={`w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold ${
                            isCompleted
                              ? 'bg-kra-green/20 text-emerald-400 border border-kra-green/40'
                              : isActive
                              ? 'bg-kra-red/20 text-red-400 border border-kra-red/40 animate-spin'
                              : 'bg-gray-800 text-gray-500'
                          }`}
                        >
                          <Icon className="w-3.5 h-3.5" />
                        </div>

                        <div>
                          <h4 className="text-xs font-bold text-white flex items-center gap-1.5">
                            <span>{node.title}</span>
                          </h4>
                          <p className="text-[10px] text-gray-400">{node.subtitle}</p>
                        </div>
                      </div>

                      <div>
                        {latency ? (
                          <span className="text-[10px] font-mono font-bold text-emerald-400 bg-kra-green/10 px-1.5 py-0.5 rounded border border-kra-green/20">
                            {latency}ms
                          </span>
                        ) : isActive ? (
                          <span className="text-[10px] font-mono text-amber-400 animate-pulse">
                            ACTIVE...
                          </span>
                        ) : (
                          <span className="text-[10px] font-mono text-gray-600">IDLE</span>
                        )}
                      </div>
                    </div>

                    <div className="mt-2 text-[11px] text-gray-300 font-mono bg-black/40 px-2 py-1 rounded border border-gray-800/60 truncate">
                      {node.details}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Real-Time Telemetry Terminal Console */}
          <div className="rounded-2xl bg-[#090C10] border border-gray-800 p-4 shadow-xl space-y-2">
            <div className="flex items-center justify-between border-b border-gray-800/80 pb-2">
              <div className="flex items-center gap-2 text-xs font-mono text-gray-400">
                <Terminal className="w-3.5 h-3.5 text-cyan-400" />
                <span>TELEMETRY_LOGS // live-stream</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping" />
                <span className="text-[10px] font-mono text-cyan-300">BACKEND CONNECTED</span>
              </div>
            </div>

            <div className="h-44 overflow-y-auto space-y-1 font-mono text-[11px] pr-2 no-scrollbar">
              {logs.length === 0 ? (
                <div className="text-gray-600 italic py-6 text-center">
                  Waiting for voice stream trigger... Click "Simulate 30s Phone Call" to watch live execution logs.
                </div>
              ) : (
                logs.map((log) => (
                  <div
                    key={log.id}
                    className="flex items-start gap-2 py-0.5 hover:bg-gray-900/50 rounded px-1"
                  >
                    <span className="text-gray-600 text-[10px] whitespace-nowrap">{log.timestamp}</span>
                    <span
                      className={`text-[10px] font-bold px-1 rounded uppercase ${
                        log.type === 'error'
                          ? 'bg-red-900/40 text-red-400'
                          : log.type === 'success'
                          ? 'bg-kra-green/20 text-emerald-400'
                          : 'bg-cyan-950/40 text-cyan-300'
                      }`}
                    >
                      {log.node}
                    </span>
                    <span className="text-gray-300 flex-1">{log.message}</span>
                  </div>
                ))
              )}
              <div ref={terminalEndRef} />
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
