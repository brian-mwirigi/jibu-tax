/**
 * File: frontend/src/App.jsx
 * Description:
 *   Root Application Layout & Telemetry Dashboard Container (Role 6).
 *   - Orchestrates main dashboard views:
 *       1. Voice Agent Simulator & Multi-Agent DAG Visualizer (VoiceSimulator.jsx)
 *       2. Official eTIMS Fiscal Invoice Viewer & Scannable QR (InvoiceViewer.jsx)
 *       3. Interactive Deterministic Tax Calculator (TaxCalculator.jsx)
 *       4. Real-time KRA PIN Verification Portal (PinChecker.jsx)
 *       5. Historical Invoice Audit Ledger & Month-End TOT / NIL (InvoiceList.jsx)
 *   - Kenyan color palette accents (#D32F2F, #2E7D32, #1B1B1B) & Dark Obsidian aesthetic.
 */

import React, { useState } from 'react';
import Header from './components/Header';
import VoiceSimulator from './components/VoiceSimulator';
import InvoiceViewer from './components/InvoiceViewer';
import TaxCalculator from './components/TaxCalculator';
import PinChecker from './components/PinChecker';
import InvoiceList from './components/InvoiceList';

export default function App() {
  const [activeTab, setActiveTab] = useState('voice');
  const [currentInvoice, setCurrentInvoice] = useState(null);

  const handleInvoiceGenerated = (result) => {
    if (result?.tax_breakdown) {
      const invNumber = `INV-2026-0042`;
      const controlCode = `KRA-9F4A-32BC-7E11`;
      const inv = {
        invoice_number: invNumber,
        buyer_name: result.sale?.buyer_name || 'SAFARI HOTEL & RESORT LTD',
        buyer_pin: result.sale?.buyer_pin || 'P051234567M',
        trader_name: result.trader_name || 'MARY WANJIKU MAMA MBOGA',
        trader_pin: result.trader_pin || 'A012345678W',
        grand_total: result.tax_breakdown.grand_total,
        net_total: result.tax_breakdown.net_amount,
        vat_total: result.tax_breakdown.vat_amount,
        oscu_control_code: controlCode,
        oscu_device_id: 'OSCU-KE-NBO-0042',
        qr_payload: `https://sbx.kra.go.ke/verify?cu=OSCU-KE-NBO-0042&inv=${invNumber}&tot=${result.tax_breakdown.grand_total.toFixed(2)}&sig=9F4A32BC7E11`,
        sms_status: 'SENT',
        whatsapp_status: 'DELIVERED',
        issued_at: new Date().toISOString(),
        items: [
          {
            item_name: result.sale?.item_description || 'Mahindi (Bags)',
            quantity: result.sale?.quantity || 50,
            unit_price: result.sale?.unit_price || 800,
            tax_rate: result.tax_breakdown.tax_rate,
            tax_category: result.tax_breakdown.tax_category,
            tax_schedule: result.tax_breakdown.tax_schedule,
            total_amount: result.tax_breakdown.grand_total,
            tax_amount: result.tax_breakdown.vat_amount,
            hs_code: result.tax_breakdown.hs_code || '1005.90.00',
          },
        ],
      };
      setCurrentInvoice(inv);
    }
  };

  const handleInvoiceCreated = (invoice) => {
    setCurrentInvoice(invoice);
    setActiveTab('receipt');
  };

  const handleSelectInvoiceFromList = (invoice) => {
    setCurrentInvoice(invoice);
    setActiveTab('receipt');
  };

  return (
    <div className="min-h-screen bg-[#0B0F17] text-gray-100 flex flex-col font-sans selection:bg-kra-red selection:text-white">
      {/* Top Header with Brand & Live Status Indicators */}
      <Header activeTab={activeTab} setActiveTab={setActiveTab} />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
        {activeTab === 'voice' && (
          <VoiceSimulator
            onInvoiceGenerated={handleInvoiceGenerated}
            onViewReceipt={() => setActiveTab('receipt')}
          />
        )}

        {activeTab === 'receipt' && (
          <InvoiceViewer invoice={currentInvoice} />
        )}

        {activeTab === 'calculator' && (
          <TaxCalculator onInvoiceCreated={handleInvoiceCreated} />
        )}

        {activeTab === 'pin' && (
          <PinChecker />
        )}

        {activeTab === 'ledger' && (
          <InvoiceList onSelectInvoice={handleSelectInvoiceFromList} />
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-800/80 bg-[#090C10] py-4 text-xs font-mono text-gray-500 text-center">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-kra-green" />
            <span className="text-gray-400">JibuTax eTIMS Telemetry Suite</span>
            <span>•</span>
            <span>Role 6 Frontend</span>
          </div>
          <div>
            Built with ❤️ for Kenyan Informal Micro-Enterprises • Finance Act 2023 Compliant
          </div>
        </div>
      </footer>
    </div>
  );
}
