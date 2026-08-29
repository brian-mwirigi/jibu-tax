/**
 * File: frontend/src/services/api.js
 * Description:
 *   Frontend API Client for JibuTax FastAPI Backend.
 *   - Direct integration with backend endpoints (no dummy stubs or mock data).
 *   - Connects to:
 *       * /api/v1/agent/invoke (LangGraph Multi-Agent Voice Turn)
 *       * /api/v1/agent/state/{caller_phone} (Checkpoint state inspection)
 *       * /api/v1/kra/verify-pin (KRA Registry PIN Checker)
 *       * /api/v1/invoices (Create & List eTIMS Invoices)
 *       * /api/v1/invoices/preview (Deterministic VAT calculation)
 *       * /api/v1/invoices/verify/{control_code} (OSCU Verification)
 *       * /api/v1/invoices/{invoice_number}/whatsapp (WhatsApp Resend)
 *       * /api/v1/taxpayers/identity & enroll (Phone-to-PIN Identity)
 *       * /api/v1/ledger (PostgreSQL Immutable Ledger)
 *       * /api/v1/filings & filings/month-end (Turnover Tax & NIL Filing Engine)
 */

const rawApiBase = (import.meta.env.VITE_API_URL || '').trim();
const API_BASE = rawApiBase.replace(/\/+$/, '');

async function handleResponse(res) {
  if (!res.ok) {
    let errorDetail = 'API request failed';
    try {
      const errJson = await res.json();
      errorDetail = errJson.detail || errJson.message || JSON.stringify(errJson);
    } catch {
      errorDetail = `HTTP Error ${res.status}: ${res.statusText}`;
    }
    throw new Error(typeof errorDetail === 'string' ? errorDetail : JSON.stringify(errorDetail));
  }
  return await res.json();
}

export const api = {
  /**
   * Health Check Probe
   */
  async getHealth() {
    const res = await fetch(`${API_BASE}/health`);
    return await handleResponse(res);
  },

  /**
   * Verify KRA PIN against government registry / eCitizen
   * POST /api/v1/kra/verify-pin
   */
  async verifyKraPin(pin) {
    const cleanPin = (pin || '').trim().toUpperCase();
    const res = await fetch(`${API_BASE}/api/v1/kra/verify-pin`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pin: cleanPin }),
    });
    return await handleResponse(res);
  },

  /**
   * Phone-to-PIN Identity Lookup
   * GET /api/v1/taxpayers/identity
   */
  async getTaxpayerIdentity(phone, language = 'sw') {
    const res = await fetch(
      `${API_BASE}/api/v1/taxpayers/identity?phone=${encodeURIComponent(phone)}&language=${encodeURIComponent(language)}`
    );
    return await handleResponse(res);
  },

  /**
   * Enroll Taxpayer Phone to PIN
   * POST /api/v1/taxpayers/enroll
   */
  async enrollTaxpayer({ phone, pin, language = 'sw', legal_name = null }) {
    const res = await fetch(`${API_BASE}/api/v1/taxpayers/enroll`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phone, pin, language, legal_name }),
    });
    return await handleResponse(res);
  },

  /**
   * Invoke Voice Agent Turn (LangGraph DAG)
   * POST /api/v1/agent/invoke
   */
  async invokeAgentTurn({ caller_phone, transcript, language = 'sw' }) {
    const res = await fetch(`${API_BASE}/api/v1/agent/invoke`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ caller_phone, transcript, language }),
    });
    return await handleResponse(res);
  },

  /**
   * Get LangGraph Checkpoint State
   * GET /api/v1/agent/state/{caller_phone}
   */
  async getAgentCheckpointState(callerPhone) {
    const res = await fetch(`${API_BASE}/api/v1/agent/state/${encodeURIComponent(callerPhone)}`);
    return await handleResponse(res);
  },

  /**
   * Fetch Live Telemetry Log Stream
   * GET /api/v1/stats/telemetry
   */
  async getTelemetryStream(limit = 50) {
    const res = await fetch(`${API_BASE}/api/v1/stats/telemetry?limit=${limit}`);
    return await handleResponse(res);
  },

  /**
   * Synthesize Spoken Audio with ElevenLabs
   * POST /api/v1/agent/speak
   */
  async synthesizeSpeech(text) {
    const res = await fetch(`${API_BASE}/api/v1/agent/speak`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    });
    if (!res.ok) {
      throw new Error(`TTS failed with status ${res.status}`);
    }
    const blob = await res.blob();
    return URL.createObjectURL(blob);
  },

  /**
   * Deterministic Tax Math Preview
   * POST /api/v1/invoices/preview
   */
  async previewTax(items, claimedTotal = null, traderPin = 'A012345678W') {
    const formattedItems = items.map((i) => ({
      description: i.description || i.item_name || i.name || '',
      item_name: i.item_name || i.description || i.name || '',
      quantity: parseFloat(i.quantity) || 1,
      unit_price: parseFloat(i.unit_price) || 0,
      tax_rate: i.tax_rate !== undefined ? parseFloat(i.tax_rate) : undefined,
    }));

    const res = await fetch(`${API_BASE}/api/v1/invoices/preview`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        trader_pin: traderPin,
        items: formattedItems,
        claimed_grand_total: claimedTotal !== null && claimedTotal !== '' ? parseFloat(claimedTotal) : null,
      }),
    });
    return await handleResponse(res);
  },

  /**
   * Create eTIMS Fiscal Invoice
   * POST /api/v1/invoices
   */
  async createInvoice(payload) {
    const res = await fetch(`${API_BASE}/api/v1/invoices`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return await handleResponse(res);
  },

  /**
   * Fetch All Issued eTIMS Invoices
   * GET /api/v1/invoices
   */
  async getInvoices() {
    const res = await fetch(`${API_BASE}/api/v1/invoices`);
    return await handleResponse(res);
  },

  /**
   * Fetch Specific Invoice by Number
   * GET /api/v1/invoices/{invoice_number}
   */
  async getInvoiceByNumber(number) {
    const res = await fetch(`${API_BASE}/api/v1/invoices/${encodeURIComponent(number)}`);
    return await handleResponse(res);
  },

  /**
   * Verify Invoice by OSCU Control Code
   * GET /api/v1/invoices/verify/{control_code}
   */
  async verifyInvoiceByControlCode(code) {
    const res = await fetch(`${API_BASE}/api/v1/invoices/verify/${encodeURIComponent(code)}`);
    return await handleResponse(res);
  },

  /**
   * Trigger WhatsApp Resend
   * POST /api/v1/invoices/{invoice_number}/whatsapp
   */
  async resendWhatsApp(invoiceNumber) {
    const res = await fetch(`${API_BASE}/api/v1/invoices/${encodeURIComponent(invoiceNumber)}/whatsapp`, {
      method: 'POST',
    });
    return await handleResponse(res);
  },

  /**
   * List Ledger Entries
   * GET /api/v1/ledger
   */
  async listLedgerEntries() {
    const res = await fetch(`${API_BASE}/api/v1/ledger`);
    return await handleResponse(res);
  },

  /**
   * List Month-End Filings
   * GET /api/v1/filings
   */
  async listFilings(year = null, month = null) {
    const params = new URLSearchParams();
    if (year) params.append('year', year);
    if (month) params.append('month', month);
    const queryString = params.toString() ? `?${params.toString()}` : '';

    const res = await fetch(`${API_BASE}/api/v1/filings${queryString}`);
    return await handleResponse(res);
  },

  /**
   * Run Month-End Automation Trigger
   * POST /api/v1/filings/month-end
   */
  async runMonthEnd(asOf = null) {
    const res = await fetch(`${API_BASE}/api/v1/filings/month-end`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ as_of: asOf }),
    });
    return await handleResponse(res);
  },
};
