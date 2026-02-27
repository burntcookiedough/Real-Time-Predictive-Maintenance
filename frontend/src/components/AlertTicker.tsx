"use client";
import React from "react";

export default function AlertTicker({ alerts }: { alerts: any[] }) {
    if (!alerts || alerts.length === 0) {
        return (
            <div className="card">
                <div className="card-header">Recent Critical Anomalies (Speed Layer)</div>
                <p style={{ color: "var(--text-tertiary)", fontSize: "0.85rem" }}>
                    No critical alerts detected in the data stream.
                </p>
            </div>
        );
    }

    return (
        <div className="card" style={{ borderLeft: "4px solid var(--signal-critical)" }}>
            <div className="card-header">
                Recent Critical Anomalies (Speed Layer)
                <span className="badge badge-critical" style={{ animation: "pulse 1.5s infinite" }}>
                    {alerts.length} Active
                </span>
            </div>
            <table className="data-table">
                <thead>
                    <tr>
                        <th>Time</th>
                        <th>Machine ID</th>
                        <th>Vitals (RPM / Temp)</th>
                        <th>Wear</th>
                    </tr>
                </thead>
                <tbody>
                    {alerts.map((alert, idx) => (
                        <tr key={`${alert.machineId}-${idx}`}>
                            <td style={{ color: "var(--text-secondary)" }}>
                                {new Date(alert.alertTime).toLocaleTimeString()}
                            </td>
                            <td style={{ fontWeight: 600 }}>{alert.machineId}</td>
                            <td>
                                {alert.rotationalSpeed.toFixed(0)} RPM / {alert.airTemp.toFixed(1)}K
                            </td>
                            <td style={{ color: alert.toolWear > 200 ? "var(--signal-warning)" : "inherit" }}>
                                {alert.toolWear} min
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
            <style dangerouslySetInnerHTML={{
                __html: `
        @keyframes pulse {
          0% { opacity: 1; }
          50% { opacity: 0.5; }
          100% { opacity: 1; }
        }
      `}} />
        </div>
    );
}
