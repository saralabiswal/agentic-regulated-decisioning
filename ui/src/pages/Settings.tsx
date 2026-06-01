// Author: Sarala Biswal
import React from 'react';

/**
 * Standalone settings page stub retained for route-level development.
 */
export default function Settings() {
  return (
    <section className="page">
      <h1>Settings</h1>
      <div className="panel">
        <label>LLM provider </label>
        <select><option>mock</option><option>ollama</option><option>openai</option><option>anthropic</option></select>
      </div>
      <div className="panel">
        <label><input type="checkbox" defaultChecked /> Insurance</label>
        <label><input type="checkbox" defaultChecked /> Lending</label>
        <label><input type="checkbox" defaultChecked /> Healthcare</label>
        <label><input type="checkbox" defaultChecked /> Wealth</label>
      </div>
    </section>
  );
}
