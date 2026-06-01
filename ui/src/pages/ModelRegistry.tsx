// Author: Sarala Biswal
import React from 'react';

const models = [
  ['insurance_risk_scorer', 'insurance', '1', 'Production'],
  ['lending_credit_scorer', 'lending', '1', 'Production'],
  ['healthcare_criteria_scorer', 'healthcare', '1', 'Production'],
  ['wealth_suitability_scorer', 'wealth', '1', 'Production'],
];

/**
 * Standalone model-registry page stub retained for route-level development.
 */
export default function ModelRegistry() {
  return (
    <section className="page">
      <h1>Model Registry</h1>
      <table className="table">
        <thead><tr><th>Model</th><th>Domain</th><th>Version</th><th>Stage</th></tr></thead>
        <tbody>{models.map((row) => <tr key={row[0]}>{row.map((cell) => <td key={cell}>{cell}</td>)}</tr>)}</tbody>
      </table>
    </section>
  );
}
