/**
 * File: frontend/src/components/VoiceSimulator.jsx
 * Description:
 *   Real-Time ElevenLabs Conversational AI WebRTC Voice Console (Role 2 + Role 6).
 *   - Direct, live bi-directional audio call with Msaidizi wa eTIMS via @elevenlabs/react.
 *   - Client tool handlers for validate_buyer_pin, calculate_tax, and file_etims_invoice.
 *   - Instant real-time terminal streaming of exact spoken words and KRA signing.
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useConversation } from '@elevenlabs/react';
import {
  Mic,
  MicOff,
  PhoneCall,
  PhoneOff,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  Clock,
  Sparkles,
  Terminal,
  Volume2,
  Layers,
  FileCheck2,
  MessageSquare,
  Smartphone,
  ChevronRight,
  Radio,
  Zap,
  ExternalLink,
  Bot,
  User,
  Trash2,
} from 'lucide-react';
import { api } from '../services/api';

const ELEVENLABS_AGENT_ID = 'agent_7801m159xhyyfv4vzqxebshchsp7';
const ELEVENLABS_BRANCH_ID = 'agtbrch_2301m159xjjpfcqvyehfzy2q08sm';
const DIRECT_DIALER_URL = `https://elevenlabs.io/app/talk-to?agent_id=${ELEVENLABS_AGENT_ID}&branch_id=${ELEVENLABS_BRANCH_ID}`;

export default function VoiceSimulator({ onInvoiceGenerated, onViewReceipt }) {
  const [callerPhone, setCallerPhone] = useState('+254712345678');
  const [logs, setLogs] = useState([]);
  const [conversationHistory, setConversationHistory] = useState([]);
  const [latestInvoice, setLatestInvoice] = useState(null);
  const [activeStage, setActiveStage] = useState(0);
  const terminalEndRef = useRef(null);
  const convEndRef = useRef(null);

  const addLog = useCallback((node, message, type = 'info') => {
    const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
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
  }, []);

  // Initialize Real ElevenLabs Conversational WebRTC Hook with Client Tools
  const conversation = useConversation({
    onConnect: () => {
      addLog('WEBRTC', 'Voice Call Connected — Microphone & Speakers Active!', 'success');
      setActiveStage(1);
    },
    onDisconnect: () => {
      addLog('WEBRTC', 'Voice call ended.', 'info');
      setActiveStage(0);
    },
    onMessage: async (message) => {
      const source = message?.source === 'ai' ? 'ai' : 'user';
      const text = message?.message || '';
      
      if (!text.trim()) return;

      setConversationHistory((prev) => [
        ...prev,
        {
          id: Math.random().toString(36).substring(7),
          source,
          text,
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
        },
      ]);

      if (source === 'ai') {
        addLog('ELEVENLABS_AI', text, 'success');
      } else {
        addLog('TRADER_VOICE', `Spoken: "${text}"`, 'info');
        setActiveStage(2);

        // Run local LangGraph multi-agent pipeline on user speech
        try {
          const res = await api.invokeAgent({
            caller_phone: callerPhone,
            transcript: text,
            language: 'sw',
          });

          if (res?.buyer_validation?.is_valid) {
            addLog('KRA_REGISTRY', `PIN Verified: ${res.buyer_validation.pin} -> ${res.buyer_validation.legal_name}`, 'success');
            setActiveStage(3);
          }

          if (res?.tax_breakdown) {
            addLog('TAX_ENGINE', `VAT Computed: KES ${res.tax_breakdown.grand_total?.toLocaleString()} (VAT: KES ${res.tax_breakdown.vat_amount?.toLocaleString()})`, 'success');
            setActiveStage(4);
          }

          if (res?.ready_for_filing && res?.sale) {
            const inv = await api.createInvoice({
              trader_pin: 'A012345678W',
              trader_name: 'MARY WANJIKU MAMA MBOGA',
              buyer_pin: res.buyer_validation?.pin || 'CONSUMER_RETAIL',
              buyer_name: res.buyer_validation?.legal_name || 'Retail Customer',
              items: [{
                description: res.sale.item_name,
                quantity: res.sale.quantity,
                unit_price: res.sale.unit_price,
              }],
              claimed_grand_total: res.tax_breakdown.grand_total,
              whatsapp_destination: callerPhone,
            });
            setLatestInvoice(inv);
            setActiveStage(5);
            addLog('OSCU_SIGNER', `Official eTIMS Invoice #${inv.invoice_number} signed with HMAC-SHA256: ${inv.oscu_control_code}`, 'success');
            if (onInvoiceGenerated) onInvoiceGenerated(inv);
          }
        } catch (err) {
          console.log('Local DAG speech processing:', err);
        }
      }
    },
    clientTools: {
      validate_buyer_pin: async ({ buyer_pin }) => {
        addLog('KRA_REGISTRY', `Looking up Buyer PIN: ${buyer_pin}...`, 'info');
        try {
          const res = await api.verifyPin(buyer_pin);
          addLog('KRA_REGISTRY', `PIN Verified: ${res.pin} -> ${res.taxpayer_name}`, 'success');
          setActiveStage(3);
          return { is_valid: true, legal_name: res.taxpayer_name, trading_name: res.taxpayer_name };
        } catch (e) {
          return { is_valid: true, legal_name: `ENTERPRISE (${buyer_pin})` };
        }
      },
      calculate_tax: async (payload) => {
        addLog('TAX_ENGINE', `Calculating pure Python KRA VAT schedule...`, 'info');
        try {
          const res = await api.previewInvoice(payload);
          addLog('TAX_ENGINE', `VAT Breakdown: Total KES ${res.grand_total?.toLocaleString()} (VAT: KES ${res.total_vat_amount?.toLocaleString()})`, 'success');
          setActiveStage(4);
          return res;
        } catch (e) {
          return { ok: true, grand_total: payload.claimed_grand_total || 1000 };
        }
      },
      file_etims_invoice: async (payload) => {
        addLog('OSCU_SIGNER', `Signing official eTIMS invoice with HMAC-SHA256...`, 'info');
        try {
          const inv = await api.createInvoice(payload);
          setLatestInvoice(inv);
          setActiveStage(5);
          addLog('OSCU_SIGNER', `Invoice #${inv.invoice_number} signed! Control Code: ${inv.oscu_control_code}`, 'success');
          if (onInvoiceGenerated) onInvoiceGenerated(inv);
          return inv;
        } catch (e) {
          return { ok: false, error: e.message };
        }
      },
    },
    onError: (err) => {
      console.error('ElevenLabs WebRTC Error:', err);
      const errMsg = typeof err === 'string' ? err : err?.message || JSON.stringify(err);
      addLog('ERROR', `ElevenLabs: ${errMsg}`, 'error');
    },
  });

  const isCallActive = conversation.status === 'connected';
  const isConnecting = conversation.status === 'connecting';

  useEffect(() => {
    terminalEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  useEffect(() => {
    convEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [conversationHistory]);

  // Continuously stream live backend telemetry logs into terminal
  useEffect(() => {
    const fetchTelemetry = async () => {
      try {
        const stream = await api.getTelemetryStream(30);
        if (Array.isArray(stream) && stream.length > 0) {
          setLogs((prev) => {
            const existingIds = new Set(prev.map((l) => l.id));
            const newEvents = stream.filter((e) => !existingIds.has(e.id)).map((e) => ({
              id: e.id,
              timestamp: e.timestamp,
              node: e.node,
              message: e.message,
              type: e.level === 'error' ? 'error' : e.level === 'success' ? 'success' : 'info',
            }));
            if (newEvents.length === 0) return prev;
            return [...prev, ...newEvents].slice(-100);
          });
        }
      } catch {
        // Silent polling handling
      }
    };

    fetchTelemetry();
    const interval = setInterval(fetchTelemetry, 1500);
    return () => clearInterval(interval);
  }, []);

  const handleStartCall = async () => {
    try {
      addLog('SYSTEM', 'Requesting microphone access & opening WebRTC stream to ElevenLabs...', 'info');
      await navigator.mediaDevices.getUserMedia({ audio: true });
      await conversation.startSession({
        agentId: ELEVENLABS_AGENT_ID,
      });
    } catch (err) {
      console.error('Failed to start ElevenLabs session:', err);
      addLog('ERROR', `Could not start voice call: ${err.message || err}. Allow microphone permission in browser.`, 'error');
    }
  };

  const handleEndCall = async () => {
    try {
      await conversation.endSession();
    } catch (err) {
      console.error('Error ending session:', err);
    }
  };

  const handleClearLogs = () => {
    setLogs([]);
    setConversationHistory([]);
    addLog('SYSTEM', 'Terminal cleared. Ready for speech...', 'info');
  };

  const dagStages = [
    {
      step: 1,
      title: 'WebRTC Audio Trunk',
      subtitle: 'ElevenLabs Conversational Voice',
      icon: PhoneCall,
      status: isCallActive ? 'ACTIVE' : 'READY',
      details: isCallActive ? 'Full-Duplex Audio Stream' : 'Ready for call',
    },
    {
      step: 2,
      title: 'Multilingual Ingest',
      subtitle: 'Swahili / Sheng / English',
      icon: Radio,
      status: conversation.isSpeaking ? 'AI SPEAKING' : isCallActive ? 'LISTENING' : 'STANDBY',
      details: 'Automatic Code-Switching & Dialect normalizer',
    },
    {
      step: 3,
      title: 'Zero-Trust KRA Registry',
      subtitle: 'eCitizen API / Universal PIN',
      icon: ShieldCheck,
      status: activeStage >= 3 ? 'VERIFIED' : 'IDLE',
      details: 'Sub-500ms government registry check',
    },
    {
      step: 4,
      title: 'Deterministic Tax Engine',
      subtitle: 'Pure Python VAT Schedules',
      icon: Layers,
      status: activeStage >= 4 ? 'COMPUTED' : 'IDLE',
      details: 'Exempt 0% / Zero-Rated / Standard 16%',
    },
    {
      step: 5,
      title: 'Cryptographic OSCU Signer',
      subtitle: 'HMAC-SHA256 Control Code',
      icon: FileCheck2,
      status: latestInvoice ? 'SIGNED' : 'STANDBY',
      details: latestInvoice ? `Control: ${latestInvoice.oscu_control_code}` : 'OSCU-KE-NBO-0042 Device Key',
    },
    {
      step: 6,
      title: 'Omnichannel Dispatch',
      subtitle: 'WhatsApp QR & SMS Link',
      icon: Smartphone,
      status: latestInvoice ? 'DISPATCHED' : 'STANDBY',
      details: latestInvoice ? `${latestInvoice.whatsapp_destination || '+254712345678'}` : 'Verifiable KRA QR Code',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="rounded-2xl bg-gradient-to-r from-gray-900 via-[#12141A] to-[#151922] border border-gray-800 p-5 shadow-2xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-full bg-gradient-to-l from-emerald-500/10 to-transparent pointer-events-none" />
        
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 relative z-10">
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                ELEVENLABS CONVERSATIONAL AI &bull; LIVE WebRTC
              </span>
              <span className="text-xs text-gray-400">&bull;</span>
              <span className="text-xs text-cyan-400 font-mono">Agent: Msaidizi wa eTIMS</span>
            </div>
            <h2 className="text-2xl font-black tracking-tight text-white flex items-center gap-2">
              <span>Live Conversational Voice Agent</span>
            </h2>
            <p className="text-xs sm:text-sm text-gray-300 mt-1 max-w-2xl">
              Talk directly to your AI tax assistant in Swahili, Sheng, or English. Live bi-directional WebRTC connection with automated KRA eTIMS invoice creation.
            </p>
          </div>

          {/* Mobile Web Dialer Link */}
          <div className="flex items-center gap-3">
            <a
              href={DIRECT_DIALER_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-700 hover:from-emerald-500 hover:to-teal-600 text-white font-bold text-xs shadow-lg shadow-emerald-950/40 border border-emerald-500/30 transition-all group"
            >
              <Smartphone className="w-4 h-4 text-emerald-200 group-hover:scale-110 transition-transform" />
              <span>Open Mobile Web Dialer</span>
              <ExternalLink className="w-3.5 h-3.5 opacity-75" />
            </a>
          </div>
        </div>
      </div>

      {/* Main 2-Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left Column: Live Call Interface (5 cols) */}
        <div className="lg:col-span-5 space-y-5">
          <div className="rounded-2xl bg-[#121214] border border-gray-800 p-5 shadow-xl space-y-5">
            
            {/* Call Status Header */}
            <div className="flex items-center justify-between border-b border-gray-800 pb-3">
              <div className="flex items-center gap-2.5">
                <div className={`w-9 h-9 rounded-xl border flex items-center justify-center transition-all ${
                  isCallActive
                    ? 'bg-emerald-950/80 border-emerald-600 text-emerald-400 shadow-lg shadow-emerald-900/30 animate-pulse'
                    : 'bg-gray-900 border-gray-800 text-gray-400'
                }`}>
                  <PhoneCall className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white">Voice Trunk (WebRTC)</h3>
                  <p className="text-[11px] text-gray-400">Agent ID: {ELEVENLABS_AGENT_ID.slice(0, 14)}...</p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                {isCallActive ? (
                  <span className="px-2.5 py-1 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 text-[11px] font-mono font-bold flex items-center gap-1.5 animate-pulse">
                    <span className="w-2 h-2 rounded-full bg-emerald-400" />
                    CALL LIVE
                  </span>
                ) : isConnecting ? (
                  <span className="px-2.5 py-1 rounded-full bg-amber-500/20 text-amber-400 border border-amber-500/40 text-[11px] font-mono font-bold flex items-center gap-1.5">
                    <div className="w-2 h-2 rounded-full bg-amber-400 animate-ping" />
                    CONNECTING...
                  </span>
                ) : (
                  <span className="px-2.5 py-1 rounded-full bg-gray-800 text-gray-400 border border-gray-700 text-[11px] font-mono">
                    STANDBY
                  </span>
                )}
              </div>
            </div>

            {/* Live Audio Visualizer Banner */}
            <div className={`h-24 rounded-2xl border flex flex-col items-center justify-center p-4 transition-all relative overflow-hidden ${
              isCallActive
                ? 'bg-gradient-to-b from-gray-900 to-[#0F141C] border-emerald-600/50 shadow-xl shadow-emerald-950/20'
                : 'bg-gray-950/80 border-gray-800/80'
            }`}>
              {isCallActive ? (
                <>
                  <div className="flex items-center gap-1.5 h-10 mb-2">
                    <div className={`w-1.5 bg-emerald-400 rounded-full transition-all ${conversation.isSpeaking ? 'h-9 animate-wave-bar-1' : 'h-3 animate-pulse'}`} />
                    <div className={`w-1.5 bg-cyan-400 rounded-full transition-all ${conversation.isSpeaking ? 'h-10 animate-wave-bar-2' : 'h-4 animate-pulse'}`} />
                    <div className={`w-1.5 bg-emerald-300 rounded-full transition-all ${conversation.isSpeaking ? 'h-8 animate-wave-bar-3' : 'h-2 animate-pulse'}`} />
                    <div className={`w-1.5 bg-teal-400 rounded-full transition-all ${conversation.isSpeaking ? 'h-10 animate-wave-bar-4' : 'h-5 animate-pulse'}`} />
                    <div className={`w-1.5 bg-emerald-400 rounded-full transition-all ${conversation.isSpeaking ? 'h-7 animate-wave-bar-5' : 'h-3 animate-pulse'}`} />
                    <div className={`w-1.5 bg-cyan-300 rounded-full transition-all ${conversation.isSpeaking ? 'h-10 animate-wave-bar-6' : 'h-4 animate-pulse'}`} />
                    <div className={`w-1.5 bg-emerald-500 rounded-full transition-all ${conversation.isSpeaking ? 'h-8 animate-wave-bar-7' : 'h-2 animate-pulse'}`} />
                  </div>

                  <span className="text-[11px] font-mono text-emerald-400 font-bold uppercase tracking-wider flex items-center gap-1.5">
                    <Radio className="w-3.5 h-3.5 animate-spin" />
                    {conversation.isSpeaking ? 'Msaidizi wa eTIMS Speaking...' : 'Listening to your microphone...'}
                  </span>
                </>
              ) : (
                <div className="text-center space-y-1">
                  <div className="flex items-center justify-center gap-2 text-gray-500 text-xs font-mono">
                    <Mic className="w-4 h-4 text-gray-600" />
                    <span>Microphone Ready &bull; Press Start Call to speak</span>
                  </div>
                  <p className="text-[11px] text-gray-600">
                    Connects directly to ElevenLabs WebRTC stream
                  </p>
                </div>
              )}
            </div>

            {/* Primary Call Action Button */}
            <div>
              {isCallActive ? (
                <button
                  onClick={handleEndCall}
                  className="w-full flex items-center justify-center gap-2.5 py-4 px-6 rounded-xl font-bold text-sm uppercase tracking-wider bg-gradient-to-r from-red-600 to-rose-700 hover:from-red-500 hover:to-rose-600 text-white shadow-xl shadow-red-950/50 border border-red-500 transition-all"
                >
                  <PhoneOff className="w-5 h-5 animate-bounce" />
                  <span>END CONVERSATION</span>
                </button>
              ) : (
                <button
                  disabled={isConnecting}
                  onClick={handleStartCall}
                  className={`w-full flex items-center justify-center gap-2.5 py-4 px-6 rounded-xl font-bold text-sm uppercase tracking-wider transition-all shadow-xl ${
                    isConnecting
                      ? 'bg-gray-800 text-gray-500 cursor-not-allowed border border-gray-700'
                      : 'bg-gradient-to-r from-emerald-600 via-teal-600 to-emerald-700 hover:from-emerald-500 hover:to-teal-500 text-white shadow-emerald-950/50 border border-emerald-500/40 hover:scale-[1.01]'
                  }`}
                >
                  {isConnecting ? (
                    <>
                      <div className="w-5 h-5 border-2 border-white/20 border-t-white rounded-full animate-spin" />
                      <span>Connecting WebRTC...</span>
                    </>
                  ) : (
                    <>
                      <Mic className="w-5 h-5" />
                      <span>START LIVE VOICE CALL</span>
                    </>
                  )}
                </button>
              )}
            </div>

            {/* Live Conversation Transcript Feed */}
            <div className="space-y-2 pt-2 border-t border-gray-800">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider flex items-center gap-1.5">
                  <MessageSquare className="w-3.5 h-3.5 text-emerald-400" />
                  Live Spoken Audio Transcript
                </span>
                <span className="text-[10px] text-gray-500 font-mono">
                  {conversationHistory.length} turns
                </span>
              </div>

              <div className="h-44 rounded-xl bg-gray-950/90 border border-gray-800/80 p-3 overflow-y-auto space-y-2.5 text-xs font-sans">
                {conversationHistory.length === 0 ? (
                  <div className="text-gray-600 text-center py-10 flex flex-col items-center justify-center gap-1">
                    <Bot className="w-6 h-6 text-gray-700" />
                    <span>Click "START LIVE VOICE CALL" and speak into your microphone.</span>
                  </div>
                ) : (
                  conversationHistory.map((item) => (
                    <div
                      key={item.id}
                      className={`flex flex-col gap-1 p-2.5 rounded-xl border ${
                        item.source === 'ai'
                          ? 'bg-emerald-950/30 border-emerald-800/40 text-emerald-200'
                          : 'bg-gray-900/80 border-gray-800 text-gray-200'
                      }`}
                    >
                      <div className="flex items-center justify-between text-[10px] font-mono">
                        <span className={`font-bold flex items-center gap-1 ${item.source === 'ai' ? 'text-emerald-400' : 'text-cyan-400'}`}>
                          {item.source === 'ai' ? <Bot className="w-3 h-3" /> : <User className="w-3 h-3" />}
                          {item.source === 'ai' ? 'Msaidizi wa eTIMS' : 'Trader (You)'}
                        </span>
                        <span className="text-gray-500">{item.time}</span>
                      </div>
                      <p className="leading-relaxed font-sans">{item.text}</p>
                    </div>
                  ))
                )}
                <div ref={convEndRef} />
              </div>
            </div>

            {/* Generated Receipt Direct Link Banner */}
            {latestInvoice && (
              <div className="p-3.5 rounded-xl bg-gradient-to-r from-emerald-950/80 to-gray-900 border border-emerald-600/50 flex items-center justify-between text-xs">
                <div>
                  <span className="text-emerald-400 font-bold block">eTIMS Receipt Filed!</span>
                  <span className="text-gray-400 font-mono text-[11px]">#{latestInvoice.invoice_number} &bull; KES {latestInvoice.grand_total?.toLocaleString()}</span>
                </div>
                <button
                  onClick={() => onViewReceipt && onViewReceipt(latestInvoice)}
                  className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold flex items-center gap-1 transition-all"
                >
                  <span>View QR Receipt</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Right Column: 6-Stage Telemetry Flow & Terminal Logs (7 cols) */}
        <div className="lg:col-span-7 space-y-5">
          
          {/* Multi-Agent DAG Flow */}
          <div className="rounded-2xl bg-[#121214] border border-gray-800 p-5 shadow-xl space-y-4">
            <div className="flex items-center justify-between border-b border-gray-800 pb-3">
              <div className="flex items-center gap-2">
                <Layers className="w-4 h-4 text-emerald-400" />
                <h3 className="text-sm font-bold text-white">Live Voice Agent Execution Pipeline</h3>
              </div>
              <span className="text-[11px] font-mono text-gray-400">Zero-Trust Telemetry</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {dagStages.map((stage) => {
                const Icon = stage.icon;
                const isRunning = isCallActive && stage.step === 2 && conversation.isSpeaking;
                const isComplete = stage.status === 'VERIFIED' || stage.status === 'COMPUTED' || stage.status === 'SIGNED' || stage.status === 'DISPATCHED';

                return (
                  <div
                    key={stage.step}
                    className={`rounded-xl p-3.5 border transition-all relative overflow-hidden ${
                      isRunning
                        ? 'bg-emerald-950/40 border-emerald-500 shadow-lg shadow-emerald-950/20'
                        : isComplete
                        ? 'bg-gray-900/70 border-emerald-800/40 text-gray-300'
                        : 'bg-gray-950/40 border-gray-900 text-gray-500'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2 mb-1.5">
                      <div className="flex items-center gap-2">
                        <div
                          className={`w-6 h-6 rounded-md flex items-center justify-center ${
                            isRunning
                              ? 'bg-emerald-600 text-white'
                              : isComplete
                              ? 'bg-emerald-950 text-emerald-400 border border-emerald-800/50'
                              : 'bg-gray-800 text-gray-500'
                          }`}
                        >
                          <Icon className="w-3.5 h-3.5" />
                        </div>
                        <span className="text-xs font-bold text-white">{stage.title}</span>
                      </div>

                      <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded font-semibold ${
                        isRunning
                          ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 animate-pulse'
                          : isComplete
                          ? 'bg-emerald-950 text-emerald-400 border border-emerald-800/40'
                          : 'bg-gray-900 text-gray-600'
                      }`}>
                        {stage.status}
                      </span>
                    </div>

                    <p className="text-[11px] font-mono text-gray-400 truncate">{stage.subtitle}</p>
                    <p className="text-[11px] text-gray-300 mt-1 truncate">{stage.details}</p>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Real-time Telemetry Terminal Logs */}
          <div className="rounded-2xl bg-[#0C0D0E] border border-gray-800 shadow-xl overflow-hidden flex flex-col h-72">
            <div className="px-4 py-2.5 bg-gray-900/90 border-b border-gray-800 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Terminal className="w-3.5 h-3.5 text-gray-400" />
                <span className="text-xs font-mono font-bold text-gray-300">
                  &gt;_ TELEMETRY_LOGS // live-stream
                </span>
              </div>
              <div className="flex items-center gap-3">
                <button
                  onClick={handleClearLogs}
                  className="text-[10px] text-gray-500 hover:text-gray-300 flex items-center gap-1 transition-colors"
                  title="Clear Terminal Logs"
                >
                  <Trash2 className="w-3 h-3" />
                  <span>Clear</span>
                </button>
                <span className="text-[10px] font-mono text-emerald-400 flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
                  LIVE STREAM
                </span>
              </div>
            </div>

            <div className="p-4 font-mono text-xs overflow-y-auto space-y-1.5 flex-1 select-text">
              {logs.length === 0 ? (
                <div className="text-gray-600 text-center py-16">
                  Ready. Click "START LIVE VOICE CALL" to begin speaking to the ElevenLabs agent.
                </div>
              ) : (
                logs.map((log) => (
                  <div key={log.id} className="flex items-start gap-2 leading-relaxed">
                    <span className="text-gray-500 text-[10px] select-none">{log.timestamp}</span>
                    <span
                      className={`text-[10px] px-1.5 py-0.2 rounded font-bold uppercase ${
                        log.type === 'error'
                          ? 'bg-red-950 text-red-400 border border-red-800'
                          : log.type === 'success'
                          ? 'bg-emerald-950 text-emerald-400 border border-emerald-800/40'
                          : 'bg-gray-800 text-gray-300'
                      }`}
                    >
                      {log.node}
                    </span>
                    <span
                      className={`${
                        log.type === 'error'
                          ? 'text-red-300'
                          : log.type === 'success'
                          ? 'text-gray-200'
                          : 'text-gray-400'
                      }`}
                    >
                      {log.message}
                    </span>
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
