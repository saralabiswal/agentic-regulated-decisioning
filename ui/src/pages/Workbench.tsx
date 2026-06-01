// Author: Sarala Biswal
import React from 'react';

const rows = [
  ['case-101', 'insurance', 'US_CA', 'ACCEPT_WITH_CONDITIONS', '0.84', 'High value override'],
  ['case-204', 'wealth', 'US_FL', 'ESCALATE', '0.66', 'Risk profile mismatch'],
];

/**
 * Standalone workbench page stub retained for route-level development.
 */
export default function Workbench() {
  return (
    <section className="page">
      <h1>Workbench</h1>
      <table className="table">
        <thead><tr><th>Case</th><th>Domain</th><th>Jurisdiction</th><th>Recommendation</th><th>Confidence</th><th>Reason</th></tr></thead>
        <tbody>
          {rows.map((row) => <tr key={row[0]}>{row.map((cell) => <td key={cell}>{cell}</td>)}</tr>)}
        </tbody>
      </table>
    </section>
  );
}
