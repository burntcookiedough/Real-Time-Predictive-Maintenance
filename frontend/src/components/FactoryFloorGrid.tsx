"use client";
import React from "react";
import { Server } from "lucide-react";

export default function FactoryFloorGrid({ states }: { states: any[] }) {
    if (!states || states.length === 0) {
        return (
            <div className="card">
                <div className="card-header">Factory Floor Status</div>
                <p style={{ color: "var(--text-tertiary)" }}>Awaiting sensor spin-up...</p>
            </div>
        );
    }

    return (
        <div className="card">
            <div className="card-header">
                Factory Floor Status (Current State)
                <span style={{ fontSize: "0.8rem", color: "var(--text-tertiary)", textTransform: "none" }}>
                    Live Cassandra View
                </span>
            </div>

            <div style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fill, minmax(130px, 1fr))",
                gap: "1rem"
            }}>
                {states.map((machine) => {
                    const isCritical = machine.status === "CRITICAL";
                    return (
                        <div
                            key={machine.machineId}
                            style={{
                                backgroundColor: isCritical ? "var(--signal-critical-bg)" : "var(--bg-surface-raised)",
                                border: `1px solid ${isCritical ? "var(--signal-critical)" : "var(--border-subtle)"}`,
                                borderRadius: "6px",
                                padding: "1rem",
                                display: "flex",
                                flexDirection: "column",
                                alignItems: "center",
                                gap: "0.5rem"
                            }}
                        >
                            <Server size={24} color={isCritical ? "var(--signal-critical)" : "var(--signal-healthy)"} />
                            <div style={{ textAlign: "center" }}>
                                <div style={{ fontWeight: 600, fontSize: "0.9rem" }}>{machine.machineId}</div>
                                <div style={{
                                    fontSize: "0.75rem",
                                    color: isCritical ? "var(--signal-critical)" : "var(--text-secondary)",
                                    marginTop: "0.25rem"
                                }}>
                                    {machine.status}
                                </div>
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
