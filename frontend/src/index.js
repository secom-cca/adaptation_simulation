import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import FormulaPage from './FormulaPage'; // ← 追加
import reportWebVitals from './reportWebVitals';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'; // ← 追加

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <Router>
      <Routes>
        <Route path="/" element={<App />} />
        <Route path="/formula" element={<FormulaPage />} />
      </Routes>
    </Router>
  </React.StrictMode>
);

reportWebVitals();
