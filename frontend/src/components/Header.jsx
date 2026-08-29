/**
 * File: frontend/src/components/Header.jsx
 * Description:
 *   Dashboard Top Navigation Header.
 *   - Displays JibuTax branding and Kenyan national color accents (#D32F2F, #2E7D32, #1B1B1B).
 *   - Shows live KRA sandbox connection status, OSCU hardware device signature,
 *     and compliance indicator badges.
 *   - Interactive tab navigation for stage demonstration modes.
 */

import React from 'react';
import {
  Mic,
  QrCode,
  Calculator,
  ShieldCheck,
  FileSpreadsheet,
  Activity,
  Zap,
  Radio,
  Sparkles,
} from 'lucide-react';

export default function Header({ activeTab, setActiveTab, stats = {} }) {
  const navItems = [
    {
      id: 'voice',
      label: 'Voice Telemetry',
      icon: Mic,
      badge: 'Live DAG',
      badgeColor: 'bg-kra-green text-white',
    },
    {
      id: 'receipt',
      label: 'Fiscal eTIMS Receipt',
      icon: QrCode,
      badge: 'QR Code',
      badgeColor: 'bg-amber-500/20 text-amber-400 border border-amber-500/30',
    },
    {
      id: 'calculator',
      label: 'Tax Math Engine',
      icon: Calculator,
      badge: 'Deterministic',
      badgeColor: 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30',
    },
    {
      id: 'pin',
      label: 'KRA PIN Checker',
      icon: ShieldCheck,
      badge: '<500ms SLA',
      badgeColor: 'bg-kra-red/20 text-red-400 border border-kra-red/30',
    },
    {
      id: 'ledger',
      label: 'Audit Ledger & Filings',
      icon: FileSpreadsheet,
      badge: '1.5% TOT & NIL',
      badgeColor: 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30',
    },
  ];

  return (
    <header className="sticky top-0 z-50 bg-[#0B0F17]/95 backdrop-blur-md border-b border-gray-800 shadow-2xl">
      {/* Kenyan Flag Ribbon Accent */}
      <div className="h-1.5 w-full flex">
        <div className="flex-1 bg-black" />
        <div className="w-4 bg-white" />
        <div className="flex-1 bg-kra-red" />
        <div className="w-4 bg-white" />
        <div className="flex-1 bg-kra-green" />
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between py-3.5 flex-wrap gap-4">
          
          {/* Logo & Brand Identity */}
          <div className="flex items-center gap-3.5">
            <div className="relative flex items-center justify-center w-11 h-11 rounded-xl bg-gradient-to-br from-kra-dark via-gray-900 to-black border border-kra-red/40 shadow-lg group">
              <div className="absolute inset-0 rounded-xl bg-kra-green/20 blur-sm group-hover:blur-md transition-all" />
              <Radio className="w-6 h-6 text-kra-red relative z-10 animate-pulse" />
              <span className="absolute -top-1 -right-1 flex h-3 w-3">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-kra-green opacity-75" />
                <span className="relative inline-flex rounded-full h-3 w-3 bg-kra-green" />
              </span>
            </div>

            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-extrabold tracking-tight text-white flex items-center gap-1.5">
                  <span className="text-white">Jibu</span>
                  <span className="text-kra-red">Tax</span>
                  <span className="text-xs px-2 py-0.5 rounded bg-kra-red/20 text-kra-red font-mono border border-kra-red/30">
                    eTIMS v1.0
                  </span>
                </h1>
              </div>
              <p className="text-xs text-gray-400 font-medium flex items-center gap-1">
                <Sparkles className="w-3 h-3 text-kra-green inline" />
                <span>Voice-First eTIMS Orchestrator</span>
                <span className="text-gray-600">•</span>
                <span className="text-emerald-400 font-mono">Turn 30s Speech $\to$ KRA Receipt</span>
              </p>
            </div>
          </div>

          {/* Live Status Telemetry Badges */}
          <div className="flex items-center gap-2.5 flex-wrap">
            {/* KRA Sandbox Status */}
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-gray-900/80 border border-gray-800 shadow-inner">
              <div className="w-2 h-2 rounded-full bg-kra-green animate-ping" />
              <div className="text-xs">
                <span className="text-gray-400">KRA Sandbox: </span>
                <span className="text-emerald-400 font-semibold font-mono">ONLINE</span>
              </div>
            </div>

            {/* OSCU Hardware Device */}
            <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-gray-900/80 border border-gray-800 shadow-inner">
              <Zap className="w-3.5 h-3.5 text-amber-400" />
              <div className="text-xs font-mono">
                <span className="text-gray-400">OSCU: </span>
                <span className="text-amber-300">OSCU-KE-NBO-0042</span>
              </div>
            </div>

            {/* SLA Benchmark */}
            <div className="hidden lg:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-gray-900/80 border border-gray-800 shadow-inner">
              <Activity className="w-3.5 h-3.5 text-cyan-400" />
              <div className="text-xs">
                <span className="text-gray-400">Response SLA: </span>
                <span className="text-cyan-300 font-mono font-semibold">&lt; 500ms</span>
              </div>
            </div>

            {/* Autonomous TOT & NIL Return Badge */}
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gradient-to-r from-kra-green/20 to-emerald-900/30 border border-kra-green/40 shadow-sm">
              <ShieldCheck className="w-4 h-4 text-kra-green" />
              <div className="text-xs font-medium text-emerald-300">
                <span>Auto-Filing: </span>
                <span className="font-mono font-bold text-white">18th Active</span>
              </div>
            </div>
          </div>
        </div>

        {/* Navigation Tabs Bar */}
        <div className="flex items-center gap-1 overflow-x-auto py-2 border-t border-gray-800/80 no-scrollbar">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold whitespace-nowrap transition-all duration-200 ${
                  isActive
                    ? 'bg-gradient-to-r from-kra-dark to-gray-900 text-white border border-kra-red/60 shadow-lg shadow-kra-red/10'
                    : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800/50 border border-transparent'
                }`}
              >
                <Icon
                  className={`w-4 h-4 ${
                    isActive ? 'text-kra-red' : 'text-gray-400 group-hover:text-gray-200'
                  }`}
                />
                <span>{item.label}</span>
                {item.badge && (
                  <span
                    className={`text-[10px] px-1.5 py-0.5 rounded-full font-mono font-medium ${
                      item.badgeColor
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>
    </header>
  );
}
