/**
 * File: frontend/vite.config.js
 * Description:
 *   Vite Bundler & Development Server Configuration.
 *   - Configures React plugin (@vitejs/plugin-react).
 *   - Sets up proxy to FastAPI backend running on port 8000 for seamless /api requests.
 */

import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
