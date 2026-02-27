"use client";
import React from "react";
import { Network } from "lucide-react";

export default function CommunityClusters({ communities }: { communities: any[] }) {
    if (!communities || communities.length === 0) {
        return (
            <div className="card">
                <div className="card-header">Batch Analytics: Fault Cascade Clusters (Connected Components)</div>
                <p style={{ color: "var(--text-tertiary)" }}>No graph analytics computed yet.</p>
            </div>
        );
    }

    return (
        <div className="card">
            <div className="card-header">
                Batch Analytics: Fault Cascade Clusters (Connected Components)
                <Network size={18} color="var(--text-secondary)" />
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                {communities.slice(0, 5).map((cluster: any, idx: number) => (
                    <div key={idx} style={{
                        padding: "1rem",
                        backgroundColor: "var(--bg-base)",
                        border: "1px solid var(--border-subtle)",
                        borderRadius: "4px"
                    }}>
                        <div style={{ fontSize: "0.85rem", color: "var(--text-tertiary)", marginBottom: "0.5rem", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                            Cluster / Community {cluster.communityId}
                        </div>
                        <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
                            {cluster.machines.map((machineId: string) => (
                                <span key={machineId} className="badge badge-healthy" style={{ color: "var(--text-primary)", backgroundColor: "var(--bg-surface-raised)", border: "1px solid var(--border-accent)" }}>
                                    {machineId}
                                </span>
                            ))}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
