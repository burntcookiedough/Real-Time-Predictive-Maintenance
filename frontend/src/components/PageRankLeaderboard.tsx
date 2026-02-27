"use client";
import React from "react";
import { Activity } from "lucide-react";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export default function PageRankLeaderboard({ scores }: { scores: any[] }) {
    if (!scores || scores.length === 0) {
        return (
            <Card>
                <CardHeader>Batch Analytics: Bottleneck Nodes (PageRank)</CardHeader>
                <CardContent>
                    <p className="text-content-tertiary">No graph analytics computed yet.</p>
                </CardContent>
            </Card>
        );
    }

    return (
        <Card>
            <CardHeader>
                Bottleneck Nodes (PageRank)
                <Activity size={18} className="text-content-secondary" />
            </CardHeader>
            <div className="w-full">
                <table className="w-full text-sm text-left border-collapse font-mono">
                    <thead>
                        <tr className="border-b border-border-subtle text-content-tertiary uppercase tracking-wider text-xs">
                            <th className="px-6 py-3 font-semibold">Rank</th>
                            <th className="px-6 py-3 font-semibold">Machine ID</th>
                            <th className="px-6 py-3 font-semibold">Centrality Score</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-border-subtle/50">
                        {scores.slice(0, 10).map((score, index) => (
                            <tr key={score.machineId} className="hover:bg-surface-raised/50 transition-colors">
                                <td className={cn("px-6 py-3", index < 3 ? "text-signal-warning font-bold" : "text-content-tertiary")}>
                                    #{index + 1}
                                </td>
                                <td className="px-6 py-3 font-semibold">{score.machineId}</td>
                                <td className="px-6 py-3 text-content-secondary">
                                    {parseFloat(score.pagerank).toFixed(6)}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </Card>
    );
}
