/**
 * File: frontend/src/main.jsx
 * Description:
 *   React Application Mount Point.
 *   - Mounts App component to DOM root element.
 *   - Imports global Tailwind CSS styles.
 */

import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.jsx';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
