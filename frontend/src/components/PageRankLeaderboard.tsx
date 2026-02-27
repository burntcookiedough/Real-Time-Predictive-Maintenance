"use client";
import React from "react";
import { Activity } from "lucide-react";

export default function PageRankLeaderboard({ scores }: { scores: any[] }) {
    if (!scores || scores.length === 0) {
        return (
            <div className="card">
                <div className="card-header">Batch Analytics: Critical Bottleneck Nodes (PageRank)</div>
                <p style={{ color: "var(--text-tertiary)" }}>No graph analytics computed yet.</p>
            </div>
        );
    }

    return (
        <div className="card">
            <div className="card-header">
                Batch Analytics: Critical Bottleneck Nodes (PageRank)
                <Activity size={18} color="var(--text-secondary)" />
            </div>
            <table className="data-table">
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Machine ID</th>
                        <th>Centrality Score</th>
                    </tr>
                </thead>
                <tbody>
                    {scores.slice(0, 10).map((score, index) => (
                        <tr key={score.machineId}>
                            <td style={{ color: index < 3 ? "var(--signal-warning)" : "var(--text-tertiary)", fontWeight: index < 3 ? "bold" : "normal" }}>
                                #{index + 1}
                            </td>
                            <td style={{ fontWeight: 600 }}>{score.machineId}</td>
                            <td style={{ fontFamily: "var(--font-mono)", color: "var(--text-secondary)" }}>
                                {parseFloat(score.pagerank).toFixed(6)}
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
