/**
 * File: frontend/src/components/TaxCalculator.jsx
 * Description:
 *   Deterministic Tax Calculation Playground.
 *   - Allows informal traders, accountants, and judges to test commodity classifications.
 *   - Demonstrates zero-AI deterministic calculation for:
 *       * 16% standard rated items (cement, hardware, services).
 *       * First Schedule exempt agricultural items (maize, potatoes, cabbages).
 *       * Second Schedule zero-rated items (fertilizer, certified seeds).
 *       * 8% Fuel & Energy tax schedule.
 *   - Discrepancy detector & generated bilingual voice summaries (Swahili & English).
 */

import React, { useState, useEffect } from 'react';
import {
  Calculator,
  Plus,
  Trash2,
  CheckCircle2,
  AlertTriangle,
  ShieldCheck,
  Sparkles,
  ArrowRight,
  FileCheck,
  RefreshCw,
  Info,
} from 'lucide-react';
import { api } from '../services/api';

const COMMODITY_PRESETS = [
  { name: 'Mahindi (Maize Bags)', qty: 50, price: 800, rate: 0.0, category: 'EXEMPT', schedule: 'First Schedule (Produce)' },
  { name: 'Saruji (Cement Bags)', qty: 20, price: 750, rate: 0.16, category: 'STANDARD_16', schedule: 'Standard Rated (16% VAT)' },
  { name: 'Fertilizer DAP (Bags)', qty: 10, price: 3000, rate: 0.0, category: 'ZERO_RATED', schedule: 'Second Schedule (Agro-Inputs)' },
  { name: 'Fresh Cabbage (kg)', qty: 100, price: 50, rate: 0.0, category: 'EXEMPT', schedule: 'First Schedule (Fresh Veg)' },
  { name: 'Diesel Fuel (Litres)', qty: 50, price: 180, rate: 0.08, category: 'FUEL_8', schedule: 'VAT Act Fuel Energy Rate (8%)' },
];

export default function TaxCalculator({ onInvoiceCreated }) {
  const [items, setItems] = useState([
    { id: '1', item_name: 'Mahindi (Bags)', quantity: 50, unit_price: 800, tax_rate: 0.0 },
    { id: '2', item_name: 'Saruji (Bags)', quantity: 10, unit_price: 750, tax_rate: 0.16 },
  ]);
  const [claimedTotal, setClaimedTotal] = useState('');
  const [calculation, setCalculation] = useState(null);
  const [buyerName, setBuyerName] = useState('SAFARI HOTEL & RESORT LTD');
  const [buyerPin, setBuyerPin] = useState('P051234567M');

  const runCalculation = async () => {
    const claimed = claimedTotal ? parseFloat(claimedTotal) : null;
    const res = await api.previewTax(items, claimed);
    setCalculation(res);
  };

  useEffect(() => {
    runCalculation();
  }, [items, claimedTotal]);

  const addItem = () => {
    setItems((prev) => [
      ...prev,
      {
        id: Math.random().toString(36).substring(7),
        item_name: 'New Commodity',
        quantity: 1,
        unit_price: 100,
        tax_rate: 0.16,
      },
    ]);
  };

  const removeItem = (id) => {
    if (items.length <= 1) return;
    setItems((prev) => prev.filter((item) => item.id !== id));
  };

  const updateItem = (id, field, value) => {
    setItems((prev) =>
      prev.map((item) => {
        if (item.id === id) {
          const updated = { ...item, [field]: value };
          if (field === 'item_name') {
            const lower = value.toLowerCase();
            if (lower.includes('mahindi') || lower.includes('maize') || lower.includes('cabbage') || lower.includes('mboga')) {
              updated.tax_rate = 0.0;
            } else if (lower.includes('fertilizer') || lower.includes('seed')) {
              updated.tax_rate = 0.0;
            } else if (lower.includes('fuel') || lower.includes('diesel')) {
              updated.tax_rate = 0.08;
            } else {
              updated.tax_rate = 0.16;
            }
          }
          return updated;
        }
        return item;
      })
    );
  };

  const handleApplyPreset = (preset) => {
    setItems((prev) => [
      ...prev,
      {
        id: Math.random().toString(36).substring(7),
        item_name: preset.name,
        quantity: preset.qty,
        unit_price: preset.price,
        tax_rate: preset.rate,
      },
    ]);
  };

  const handleCreateInvoice = async () => {
    const payload = {
      buyer_name: buyerName,
      buyer_pin: buyerPin,
      trader_name: 'MARY WANJIKU MAMA MBOGA',
      trader_pin: 'A012345678W',
      items: items.map((i) => ({
        item_name: i.item_name,
        quantity: parseFloat(i.quantity),
        unit_price: parseFloat(i.unit_price),
        tax_rate: parseFloat(i.tax_rate),
      })),
      claimed_grand_total: claimedTotal ? parseFloat(claimedTotal) : null,
    };

    const invoice = await api.createInvoice(payload);
    if (onInvoiceCreated) {
      onInvoiceCreated(invoice);
    }
  };

  return (
    <div className="space-y-6">
      
      {/* Top Banner */}
      <div className="rounded-2xl bg-gradient-to-r from-kra-dark via-[#151922] to-gray-900 border border-gray-800 p-5 shadow-2xl">
        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-semibold bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                100% DETERMINISTIC PYTHON ENGINE
              </span>
              <span className="text-xs text-gray-400">•</span>
              <span className="text-xs text-emerald-400 font-mono">Zero AI Arithmetic Hallucination</span>
            </div>
            <h2 className="text-2xl font-black tracking-tight text-white flex items-center gap-2">
              <span>Deterministic VAT Act Tax Playground</span>
            </h2>
            <p className="text-xs sm:text-sm text-gray-300 mt-1 max-w-2xl">
              Under Kenyan Law, LLMs are strictly forbidden from performing tax calculations.
              Test audited VAT classifications: Standard Rate (16%), First Schedule Produce (0% Exempt), Second Schedule (0% Zero-Rated), and Fuel (8%).
            </p>
          </div>

          {/* Quick Preset Selector */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs text-gray-400 font-semibold hidden sm:inline">Add Preset:</span>
            {COMMODITY_PRESETS.map((p, idx) => (
              <button
                key={idx}
                onClick={() => handleApplyPreset(p)}
                className="text-xs px-2.5 py-1.5 rounded-lg bg-gray-900 border border-gray-800 text-gray-300 hover:bg-gray-800 hover:text-white transition-all"
              >
                + {p.name.split(' ')[0]}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Main Grid: Left = Line Items Builder, Right = Calculations & Scripts */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left Column: Line Items Table & Discrepancy Input (7 cols) */}
        <div className="lg:col-span-7 space-y-4">
          <div className="rounded-2xl bg-[#121214] border border-gray-800 p-5 shadow-xl space-y-4">
            <div className="flex items-center justify-between border-b border-gray-800 pb-3">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-kra-dark border border-gray-700 flex items-center justify-center text-cyan-400">
                  <Calculator className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white">Invoice Line Items Builder</h3>
                  <p className="text-[11px] text-gray-400">Dynamic Schedule &amp; Commodity Classifier</p>
                </div>
              </div>

              <button
                onClick={addItem}
                className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-kra-dark hover:bg-gray-800 border border-gray-700 text-xs font-semibold text-white transition-colors"
              >
                <Plus className="w-3.5 h-3.5 text-kra-green" />
                <span>Add Item</span>
              </button>
            </div>

            {/* Line Items Table */}
            <div className="space-y-3">
              {items.map((item, index) => {
                const lineNet = item.quantity * item.unit_price;
                const lineVat = item.tax_rate > 0 ? lineNet * item.tax_rate : 0;
                return (
                  <div
                    key={item.id}
                    className="p-3.5 rounded-xl bg-gray-900/90 border border-gray-800 hover:border-gray-700 space-y-3 transition-all"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs font-mono font-bold text-gray-500">#{index + 1}</span>
                      <input
                        type="text"
                        value={item.item_name}
                        onChange={(e) => updateItem(item.id, 'item_name', e.target.value)}
                        className="flex-1 px-3 py-1.5 rounded-lg bg-black/60 border border-gray-800 text-xs text-white font-semibold focus:outline-none focus:border-cyan-500"
                        placeholder="Commodity description..."
                      />
                      <button
                        onClick={() => removeItem(item.id)}
                        disabled={items.length <= 1}
                        className="p-1.5 text-gray-500 hover:text-red-400 disabled:opacity-30 transition-colors"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>

                    <div className="grid grid-cols-3 gap-3 text-xs">
                      <div>
                        <label className="text-[10px] text-gray-400 uppercase font-semibold block mb-1">
                          Quantity
                        </label>
                        <input
                          type="number"
                          min="1"
                          value={item.quantity}
                          onChange={(e) => updateItem(item.id, 'quantity', Math.max(1, parseFloat(e.target.value) || 1))}
                          className="w-full px-2.5 py-1.5 rounded-lg bg-black/60 border border-gray-800 text-xs font-mono text-white focus:outline-none focus:border-cyan-500"
                        />
                      </div>

                      <div>
                        <label className="text-[10px] text-gray-400 uppercase font-semibold block mb-1">
                          Unit Price (KES)
                        </label>
                        <input
                          type="number"
                          min="0"
                          value={item.unit_price}
                          onChange={(e) => updateItem(item.id, 'unit_price', Math.max(0, parseFloat(e.target.value) || 0))}
                          className="w-full px-2.5 py-1.5 rounded-lg bg-black/60 border border-gray-800 text-xs font-mono text-white focus:outline-none focus:border-cyan-500"
                        />
                      </div>

                      <div>
                        <label className="text-[10px] text-gray-400 uppercase font-semibold block mb-1">
                          Tax Rate / Schedule
                        </label>
                        <select
                          value={item.tax_rate}
                          onChange={(e) => updateItem(item.id, 'tax_rate', parseFloat(e.target.value))}
                          className="w-full px-2 py-1.5 rounded-lg bg-black/60 border border-gray-800 text-xs font-semibold text-white focus:outline-none focus:border-cyan-500"
                        >
                          <option value={0.0}>0% Exempt (1st Sched)</option>
                          <option value={0.0}>0% Zero-Rated (2nd Sched)</option>
                          <option value={0.16}>16% Standard VAT</option>
                          <option value={0.08}>8% Fuel Energy</option>
                        </select>
                      </div>
                    </div>

                    <div className="flex items-center justify-between text-[11px] font-mono pt-1 text-gray-400 border-t border-gray-800/60">
                      <span>Net: KES {lineNet.toLocaleString()}</span>
                      <span className="text-emerald-400">VAT: KES {lineVat.toLocaleString()}</span>
                      <span className="font-bold text-white">Line Total: KES {(lineNet + lineVat).toLocaleString()}</span>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Claimed Grand Total Discrepancy Checker */}
            <div className="p-3.5 rounded-xl bg-gray-900 border border-gray-800 space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-xs font-bold text-white flex items-center gap-1.5">
                  <Info className="w-3.5 h-3.5 text-amber-400" />
                  <span>Trader Spoken Claim Total (Discrepancy Test)</span>
                </label>
                <span className="text-[10px] text-gray-500 font-mono">Optional</span>
              </div>
              <input
                type="number"
                value={claimedTotal}
                onChange={(e) => setClaimedTotal(e.target.value)}
                placeholder="e.g. Enter 42000 to test arithmetic mismatch detector..."
                className="w-full px-3 py-2 rounded-lg bg-black/60 border border-gray-800 text-xs font-mono text-white focus:outline-none focus:border-amber-400"
              />

              {calculation?.discrepancy_detected && (
                <div className="p-2.5 rounded-lg bg-red-950/40 border border-red-500/40 text-xs text-red-300 flex items-start gap-2 animate-fadeIn">
                  <AlertTriangle className="w-4 h-4 text-kra-red flex-shrink-0 mt-0.5" />
                  <div>
                    <strong>Discrepancy Detected: </strong>
                    Trader claimed KES {parseFloat(claimedTotal).toLocaleString()}, but exact statutory calculation is KES {calculation.grand_total.toLocaleString()} (Difference: KES {Math.abs(calculation.discrepancy_amount).toLocaleString()}). JibuTax auto-corrects before filing.
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right Column: Computed Financial Summary & Voice Script (5 cols) */}
        <div className="lg:col-span-5 space-y-4">
          
          {/* Computation Summary Card */}
          <div className="rounded-2xl bg-[#121214] border border-gray-800 p-5 shadow-xl space-y-4">
            <div className="flex items-center justify-between border-b border-gray-800 pb-3">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-kra-green" />
                <h3 className="text-sm font-bold text-white">Statutory Tax Summary</h3>
              </div>
              <span className="text-[10px] font-mono text-emerald-400 bg-kra-green/10 px-2 py-0.5 rounded border border-kra-green/30">
                AUDITED
              </span>
            </div>

            <div className="space-y-2.5 text-xs font-mono">
              <div className="flex justify-between text-gray-400">
                <span>First Schedule Exempt (0%):</span>
                <span className="text-white">KES {calculation?.exempt_total?.toLocaleString() || 0}</span>
              </div>

              <div className="flex justify-between text-gray-400">
                <span>Second Schedule Zero-Rated (0%):</span>
                <span className="text-white">KES {calculation?.zero_rated_total?.toLocaleString() || 0}</span>
              </div>

              <div className="flex justify-between text-gray-400">
                <span>Standard Rated Taxable Net (16%):</span>
                <span className="text-white">KES {calculation?.standard_16_net?.toLocaleString() || 0}</span>
              </div>

              <div className="flex justify-between text-gray-400 border-t border-gray-800 pt-2">
                <span>Total Statutory VAT Amount:</span>
                <span className="text-emerald-400 font-bold">KES {calculation?.vat_total?.toLocaleString() || 0}</span>
              </div>

              <div className="flex justify-between text-base font-black text-white pt-2 border-t-2 border-dashed border-gray-700">
                <span className="text-kra-red font-sans">FINAL GRAND TOTAL:</span>
                <span className="text-lg font-mono text-white">
                  KES {calculation?.grand_total?.toLocaleString() || 0}
                </span>
              </div>
            </div>

            {/* Generate eTIMS Invoice Button */}
            <button
              onClick={handleCreateInvoice}
              className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl bg-gradient-to-r from-kra-red to-rose-700 hover:from-red-600 hover:to-rose-800 text-white font-bold text-xs uppercase tracking-wider shadow-lg shadow-kra-red/20 border border-kra-red transition-all"
            >
              <FileCheck className="w-4 h-4" />
              <span>Issue Official eTIMS Receipt</span>
            </button>
          </div>

          {/* Generated Bilingual Voice Script */}
          <div className="rounded-2xl bg-gradient-to-br from-kra-dark to-[#121214] border border-gray-800 p-5 shadow-xl space-y-3">
            <div className="flex items-center gap-2 text-xs font-bold text-white">
              <Sparkles className="w-4 h-4 text-amber-400" />
              <span>Generated Spoken Voice Summary</span>
            </div>

            <div className="space-y-2 text-xs">
              <div className="p-3 rounded-xl bg-gray-900/90 border border-gray-800 text-emerald-300 font-sans leading-relaxed">
                <strong className="text-gray-400 text-[10px] uppercase font-mono block mb-1">Kiswahili:</strong>
                "Jumla ya mauzo ni KES {calculation?.grand_total?.toLocaleString() || 0}. Ushuru wa VAT ni KES {calculation?.vat_total?.toLocaleString() || 0}. Risiti ya KRA imethibitishwa."
              </div>

              <div className="p-3 rounded-xl bg-gray-900/90 border border-gray-800 text-cyan-300 font-sans leading-relaxed">
                <strong className="text-gray-400 text-[10px] uppercase font-mono block mb-1">English:</strong>
                "Sale grand total is KES {calculation?.grand_total?.toLocaleString() || 0} including KES {calculation?.vat_total?.toLocaleString() || 0} VAT. Official KRA eTIMS invoice confirmed."
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
