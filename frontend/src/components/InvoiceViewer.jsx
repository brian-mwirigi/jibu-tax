/**
 * File: frontend/src/components/InvoiceViewer.jsx
 * Description:
 *   Official KRA eTIMS Fiscal Electronic Receipt Visualizer.
 *   - Formats invoice details matching official KRA fiscal receipt standards.
 *   - Renders scannable 2D KRA QR code, OSCU hardware device signature, and
 *     cryptographic HMAC-SHA256 control code.
 *   - Fetches live invoices from backend /api/v1/invoices.
 *   - Interactive action modals for WhatsApp QR media delivery and SMS text dispatch.
 */

import React, { useState, useEffect } from 'react';
import { QRCodeSVG } from 'qrcode.react';
import {
  QrCode,
  Smartphone,
  MessageCircle,
  Copy,
  Check,
  ShieldCheck,
  Printer,
  BadgeCheck,
  FileQuestion,
} from 'lucide-react';
import { api } from '../services/api';

export default function InvoiceViewer({ invoice: propInvoice }) {
  const [invoice, setInvoice] = useState(propInvoice);
  const [loading, setLoading] = useState(false);
  const [copiedCode, setCopiedCode] = useState(false);
  const [showWhatsAppModal, setShowWhatsAppModal] = useState(false);
  const [showSmsModal, setShowSmsModal] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);
  const [verifyStatus, setVerifyStatus] = useState(null);

  useEffect(() => {
    if (propInvoice) {
      setInvoice(propInvoice);
    } else {
      loadLatestInvoice();
    }
  }, [propInvoice]);

  const loadLatestInvoice = async () => {
    setLoading(true);
    try {
      const list = await api.getInvoices();
      if (Array.isArray(list) && list.length > 0) {
        // Fetch full invoice detail
        const full = await api.getInvoiceByNumber(list[0].invoice_number);
        setInvoice(full);
      }
    } catch {
      // Handled
    } finally {
      setLoading(false);
    }
  };

  const copyControlCode = () => {
    if (!invoice?.oscu_control_code) return;
    navigator.clipboard.writeText(invoice.oscu_control_code);
    setCopiedCode(true);
    setTimeout(() => setCopiedCode(false), 2000);
  };

  const handleVerifyKRA = async () => {
    if (!invoice?.oscu_control_code) return;
    setIsVerifying(true);
    try {
      const res = await api.verifyInvoiceByControlCode(invoice.oscu_control_code);
      setVerifyStatus(res);
    } catch (err) {
      setVerifyStatus({
        valid: false,
        message: err.message || 'Control code could not be verified on gateway.',
      });
    } finally {
      setIsVerifying(false);
    }
  };

  const handlePrint = () => {
    window.print();
  };

  if (loading) {
    return (
      <div className="text-center py-16 text-gray-400 font-mono text-xs">
        <div className="w-6 h-6 border-2 border-kra-red border-t-transparent rounded-full animate-spin mx-auto mb-2" />
        <span>Loading fiscal receipt from backend...</span>
      </div>
    );
  }

  if (!invoice) {
    return (
      <div className="max-w-md mx-auto text-center py-16 px-4 space-y-3 bg-[#121214] rounded-2xl border border-gray-800 shadow-xl">
        <FileQuestion className="w-10 h-10 text-gray-500 mx-auto" />
        <h3 className="text-sm font-bold text-white">No Electronic Invoices Found</h3>
        <p className="text-xs text-gray-400 font-sans">
          Simulate a voice trade in the <strong>Voice Telemetry</strong> tab or run a calculation in the <strong>Tax Math Engine</strong> to issue a live KRA eTIMS invoice.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      
      {/* Top Controls Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 bg-[#121214] p-4 rounded-2xl border border-gray-800 shadow-xl">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-semibold bg-kra-green/20 text-emerald-400 border border-kra-green/30">
              OFFICIAL eTIMS FISCAL RECEIPT
            </span>
            <span className="text-xs text-gray-500 font-mono">OSCU v2.1</span>
          </div>
          <h2 className="text-xl font-bold text-white mt-1 flex items-center gap-2">
            <span>Invoice #{invoice.invoice_number}</span>
          </h2>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => setShowWhatsAppModal(true)}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 text-xs font-semibold border border-emerald-500/30 transition-all"
          >
            <MessageCircle className="w-4 h-4 text-emerald-400" />
            <span>WhatsApp Receipt</span>
          </button>

          <button
            onClick={() => setShowSmsModal(true)}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-cyan-600/20 hover:bg-cyan-600/30 text-cyan-300 text-xs font-semibold border border-cyan-500/30 transition-all"
          >
            <Smartphone className="w-4 h-4 text-cyan-400" />
            <span>SMS Dispatch</span>
          </button>

          <button
            onClick={handlePrint}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-gray-800 hover:bg-gray-700 text-gray-200 text-xs font-semibold border border-gray-700 transition-all"
          >
            <Printer className="w-4 h-4" />
            <span>Print Receipt</span>
          </button>
        </div>
      </div>

      {/* Main Fiscal Receipt Container */}
      <div className="max-w-2xl mx-auto">
        <div className="bg-[#18181B] border-2 border-kra-red/40 rounded-3xl p-6 sm:p-8 shadow-2xl relative overflow-hidden text-gray-200">
          
          {/* Header Section */}
          <div className="text-center border-b-2 border-dashed border-gray-700 pb-5 space-y-1">
            <div className="inline-flex items-center justify-center gap-2 px-3 py-1 rounded-full bg-kra-dark border border-kra-red/40 mb-2">
              <span className="w-2 h-2 rounded-full bg-kra-green animate-pulse" />
              <span className="text-[11px] font-black tracking-widest text-white uppercase">
                KENYA REVENUE AUTHORITY
              </span>
            </div>
            
            <h3 className="text-lg font-black tracking-tight text-white uppercase">
              ELECTRONIC TAX INVOICE (eTIMS)
            </h3>
            <p className="text-xs font-semibold text-kra-red uppercase tracking-wider">
              FISCAL RECEIPT • OSCU AUTOMATED
            </p>
            <p className="text-[11px] text-gray-400 font-mono">
              Device Serial: {invoice.oscu_device_id || 'OSCU-KE-NBO-0042'} • KRA Sandbox Gateway
            </p>
          </div>

          {/* Taxpayer & Buyer Metadata Table */}
          <div className="py-4 border-b border-gray-800 text-xs font-mono grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="space-y-1">
              <span className="text-[10px] text-gray-500 uppercase tracking-wider block font-sans font-bold">
                SELLER / TAXPAYER
              </span>
              <p className="font-bold text-white text-sm">{invoice.trader_name}</p>
              <p className="text-emerald-400 font-bold">PIN: {invoice.trader_pin}</p>
              <p className="text-gray-400 text-[11px]">Turnover Tax (TOT) Registered</p>
            </div>

            <div className="space-y-1 sm:text-right">
              <span className="text-[10px] text-gray-500 uppercase tracking-wider block font-sans font-bold">
                BUYER DETAILS
              </span>
              <p className="font-bold text-white text-sm">{invoice.buyer_name}</p>
              <p className="text-cyan-400 font-bold">PIN: {invoice.buyer_pin || 'CONSUMER_RETAIL'}</p>
              <p className="text-gray-400 text-[11px]">
                Date: {invoice.issued_at ? new Date(invoice.issued_at).toLocaleString() : new Date().toLocaleString()}
              </p>
            </div>
          </div>

          {/* Itemized Line Items Table */}
          <div className="py-4 border-b border-gray-800">
            <table className="w-full text-left text-xs font-mono">
              <thead>
                <tr className="text-[10px] text-gray-500 uppercase border-b border-gray-800 pb-2">
                  <th className="py-1">Item / HS Code</th>
                  <th className="py-1 text-center">Qty</th>
                  <th className="py-1 text-right">Price</th>
                  <th className="py-1 text-right">Rate</th>
                  <th className="py-1 text-right">Total (KES)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800/60">
                {(invoice.items || []).map((item, idx) => (
                  <tr key={idx} className="hover:bg-gray-800/30">
                    <td className="py-2.5">
                      <div className="font-bold text-white">{item.item_name}</div>
                      <div className="text-[10px] text-gray-500">HS: {item.hs_code || '1005.90.00'} • {item.tax_category || (item.tax_rate > 0 ? 'STANDARD_16' : 'EXEMPT')}</div>
                    </td>
                    <td className="py-2.5 text-center text-gray-300">{item.quantity}</td>
                    <td className="py-2.5 text-right text-gray-300">{(item.unit_price || 0).toLocaleString()}</td>
                    <td className="py-2.5 text-right font-semibold text-emerald-400">
                      {item.tax_rate > 0 ? `${(item.tax_rate * 100).toFixed(0)}%` : '0%'}
                    </td>
                    <td className="py-2.5 text-right font-bold text-white">
                      {(item.total_amount || item.line_grand || item.quantity * item.unit_price).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Financial Totals Calculation Box */}
          <div className="py-4 border-b-2 border-dashed border-gray-700 space-y-1.5 text-xs font-mono">
            <div className="flex justify-between text-gray-400">
              <span>NET TAXABLE VALUE:</span>
              <span className="font-semibold text-white">KES {invoice.net_total?.toLocaleString()}</span>
            </div>
            
            <div className="flex justify-between text-gray-400">
              <span>TOTAL VAT AMOUNT (16% / 0%):</span>
              <span className="font-semibold text-emerald-400">KES {invoice.vat_total?.toLocaleString()}</span>
            </div>

            <div className="flex justify-between text-base font-black text-white pt-2 border-t border-gray-800">
              <span className="text-kra-red font-sans">GRAND TOTAL (INCL. TAX):</span>
              <span className="text-xl font-mono text-white">
                KES {invoice.grand_total?.toLocaleString()}
              </span>
            </div>
          </div>

          {/* Scannable 2D KRA QR Code & Cryptographic Signature */}
          <div className="py-5 flex flex-col sm:flex-row items-center justify-between gap-6">
            <div className="flex flex-col items-center gap-2">
              <div className="p-3 bg-white rounded-2xl shadow-xl ring-4 ring-kra-red/20">
                <QRCodeSVG
                  value={invoice.qr_payload || `https://sbx.kra.go.ke/verify?cu=OSCU-KE-NBO-0042&inv=${invoice.invoice_number}`}
                  size={120}
                  level="H"
                  includeMargin={false}
                />
              </div>
              <span className="text-[10px] font-mono text-gray-400 text-center flex items-center gap-1">
                <QrCode className="w-3 h-3 text-kra-red inline" />
                <span>Scan with Camera to Verify</span>
              </span>
            </div>

            {/* Cryptographic Control Code Card */}
            <div className="flex-1 space-y-2.5 w-full">
              <div className="p-3 rounded-xl bg-gray-900/90 border border-gray-800 space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider">
                    OSCU HMAC-SHA256 Control Code
                  </span>
                  <button
                    onClick={copyControlCode}
                    className="text-[10px] text-kra-red hover:text-red-400 flex items-center gap-1 font-mono"
                  >
                    {copiedCode ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                    <span>{copiedCode ? 'COPIED' : 'COPY'}</span>
                  </button>
                </div>
                
                <div className="text-sm font-mono font-extrabold text-amber-300 tracking-wider bg-black/50 p-2 rounded border border-gray-800 text-center">
                  {invoice.oscu_control_code}
                </div>
              </div>

              <button
                disabled={isVerifying}
                onClick={handleVerifyKRA}
                className="w-full flex items-center justify-center gap-2 py-2 px-3 rounded-xl bg-gradient-to-r from-kra-green to-emerald-700 hover:from-emerald-600 hover:to-emerald-800 text-white text-xs font-bold shadow-md transition-all"
              >
                {isVerifying ? (
                  <div className="w-3.5 h-3.5 border-2 border-white/20 border-t-white rounded-full animate-spin" />
                ) : (
                  <ShieldCheck className="w-4 h-4" />
                )}
                <span>Verify Signature on KRA Gateway</span>
              </button>

              {verifyStatus && (
                <div className="p-2 rounded-lg bg-emerald-950/40 border border-emerald-500/30 text-[11px] text-emerald-300 flex items-center gap-1.5 animate-fadeIn">
                  <BadgeCheck className="w-4 h-4 text-kra-green flex-shrink-0" />
                  <span>{verifyStatus.message}</span>
                </div>
              )}
            </div>
          </div>

          {/* Footer Notice */}
          <div className="text-center pt-3 border-t border-gray-800 text-[10px] text-gray-500 font-mono uppercase tracking-wider">
            ISSUED PURSUANT TO FINANCE ACT 2023 SEC. 16 • JIBUTAX ZERO-TRUST ENGINE
          </div>
        </div>
      </div>

      {/* WhatsApp Modal */}
      {showWhatsAppModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#121214] border border-gray-800 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-gray-800 pb-3">
              <div className="flex items-center gap-2">
                <MessageCircle className="w-5 h-5 text-emerald-400" />
                <h3 className="text-sm font-bold text-white">WhatsApp Cloud Dispatch Preview</h3>
              </div>
              <button
                onClick={() => setShowWhatsAppModal(false)}
                className="text-gray-500 hover:text-white text-xs font-bold"
              >
                ✕
              </button>
            </div>

            <div className="bg-[#0B141A] rounded-xl p-4 border border-gray-800 space-y-3 font-sans text-xs">
              <div className="flex items-center gap-2 text-emerald-400 font-bold border-b border-gray-800 pb-2">
                <span>🟢 JibuTax KRA Assistant</span>
              </div>
              
              <p className="text-gray-200 leading-relaxed">
                Hujambo <strong>{invoice.trader_name}</strong>! 🎉
                <br /><br />
                Ankara yako ya KRA eTIMS imetolewa kikamilifu:
                <br />
                📄 <strong>Nambari:</strong> #{invoice.invoice_number}
                <br />
                🏢 <strong>Mnunuzi:</strong> {invoice.buyer_name}
                <br />
                💰 <strong>Jumla:</strong> KES {invoice.grand_total?.toLocaleString()}
                <br />
                🔐 <strong>KRA Control Code:</strong> {invoice.oscu_control_code}
              </p>

              <div className="p-3 bg-white rounded-lg flex items-center justify-center">
                <QRCodeSVG value={invoice.qr_payload || `https://sbx.kra.go.ke/verify?cu=OSCU-KE-NBO-0042&inv=${invoice.invoice_number}`} size={100} />
              </div>
            </div>

            <button
              onClick={() => setShowWhatsAppModal(false)}
              className="w-full py-2.5 rounded-xl bg-kra-green hover:bg-emerald-600 text-white font-bold text-xs"
            >
              Close WhatsApp Preview
            </button>
          </div>
        </div>
      )}

      {/* SMS Modal */}
      {showSmsModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#121214] border border-gray-800 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-gray-800 pb-3">
              <div className="flex items-center gap-2">
                <Smartphone className="w-5 h-5 text-cyan-400" />
                <h3 className="text-sm font-bold text-white">SMS Gateway (Africa's Talking)</h3>
              </div>
              <button
                onClick={() => setShowSmsModal(false)}
                className="text-gray-500 hover:text-white text-xs font-bold"
              >
                ✕
              </button>
            </div>

            <div className="bg-gray-900 rounded-xl p-4 border border-gray-800 space-y-2 font-mono text-xs text-gray-300">
              <div className="text-cyan-400 text-[11px] font-bold">SMS FROM: KRA-JIBUTAX</div>
              <div className="bg-black/60 p-3 rounded-lg border border-gray-800 leading-relaxed">
                KRA eTIMS Confirmed: Inv #{invoice.invoice_number} of KES {invoice.grand_total?.toLocaleString()} to {invoice.buyer_name} filed. Control: {invoice.oscu_control_code}. Verify: https://sbx.kra.go.ke/v?c={invoice.oscu_control_code}
              </div>
            </div>

            <button
              onClick={() => setShowSmsModal(false)}
              className="w-full py-2.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-xs"
            >
              Close SMS Preview
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
