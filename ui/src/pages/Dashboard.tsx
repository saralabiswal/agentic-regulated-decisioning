// Author: Sarala Biswal
import React from 'react';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, XAxis, YAxis } from 'recharts';

const volume = [
  { domain: 'Insurance', submissions: 18 },
  { domain: 'Lending', submissions: 11 },
  { domain: 'Healthcare', submissions: 9 },
  { domain: 'Wealth', submissions: 7 },
];

/**
 * Standalone dashboard page stub retained for route-level development.
 */
export default function Dashboard() {
  return (
    <section className="page">
      <h1>Dashboard</h1>
      <div className="metric-grid">
        <div className="metric"><span>Total today</span><strong>45</strong></div>
        <div className="metric"><span>Auto decision</span><strong>72%</strong></div>
        <div className="metric"><span>Escalation</span><strong>28%</strong></div>
        <div className="metric"><span>Avg latency</span><strong>842ms</strong></div>
      </div>
      <div className="panel" style={{ height: 280 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={volume}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="domain" />
            <YAxis />
            <Bar dataKey="submissions" fill="#2f6f73" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
