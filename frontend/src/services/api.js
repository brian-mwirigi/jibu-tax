/**
 * File: frontend/src/services/api.js
 * Description:
 *   Frontend API Client for FastAPI Backend.
 *   - Provides client methods for:
 *       * verifyPin(pin): Validates KRA PIN via /api/v1/kra/verify-pin.
 *       * calculateTax(items): Runs deterministic tax calculation via /api/v1/tools/calculate-tax.
 *       * createInvoice(payload): Files official eTIMS invoice via /api/v1/invoices.
 *       * getInvoices(): Fetches list of submitted electronic invoices.
 *       * getStats(): Fetches live compliance and filing metrics.
 */

const API_BASE = import.meta.env.VITE_API_URL || '';

export const api = {
  // Methods for backend communication are defined here
};
