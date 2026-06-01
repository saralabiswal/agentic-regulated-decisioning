// Author: Sarala Biswal
import React from 'react';

const layers = ['Intake', 'Stream', 'Orchestrator', 'Agents', 'MCP', 'Workbench', 'Data', 'Registry', 'Observability', 'Governance'];

/**
 * Standalone architecture page stub retained for route-level development.
 */
export default function Architecture() {
  return (
    <section className="page">
      <h1>Architecture</h1>
      <div className="metric-grid">
        {layers.map((layer, index) => <div className="metric" key={layer}><span>L{index}</span><strong>{layer}</strong></div>)}
      </div>
      <div className="panel">No platform code contains domain-specific logic. Domain behavior enters through DomainAdapter.</div>
    </section>
  );
}
