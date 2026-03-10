"use client";
import React, { useState, useMemo } from "react";
import { Server, Thermometer, RotateCcw, Wrench, ChevronDown, ChevronUp } from "lucide-react";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export default function FactoryFloorGrid({ states }: { states: any[] }) {
    const [expanded, setExpanded] = useState(false);

    const { critical, healthy, summary } = useMemo(() => {
        if (!states || states.length === 0) return { critical: [], healthy: [], summary: null };
        const crit = states.filter(m => m.status === "CRITICAL");
        const hlth = states.filter(m => m.status !== "CRITICAL");

        // Compute aggregate stats
        const temps = states.map(m => parseFloat(m.airTemp) || 0);
        const torques = states.map(m => parseFloat(m.torque) || 0);
        const speeds = states.map(m => parseFloat(m.rotationalSpeed) || 0);
        const wears = states.map(m => parseFloat(m.toolWear) || 0);
        const avg = (arr: number[]) => arr.reduce((a, b) => a + b, 0) / arr.length;
        const max = (arr: number[]) => Math.max(...arr);
        const min = (arr: number[]) => Math.min(...arr);

        return {
            critical: crit,
            healthy: hlth,
            summary: {
                total: states.length,
                critCount: crit.length,
                healthyCount: hlth.length,
                avgTemp: avg(temps),
                maxTemp: max(temps),
                minTemp: min(temps),
                avgTorque: avg(torques),
                maxTorque: max(torques),
                avgSpeed: avg(speeds),
                maxWear: max(wears),
                avgWear: avg(wears),
            }
        };
    }, [states]);

    if (!states || states.length === 0) {
        return (
            <Card>
                <CardHeader>Machine Monitor</CardHeader>
                <CardContent>
                    <p className="text-content-tertiary">Awaiting sensor spin-up...</p>
                </CardContent>
            </Card>
        );
    }

    return (
        <Card>
            <CardHeader>
                <div className="flex items-center gap-2">
                    <Server size={18} className="text-content-secondary" />
                    Machine Monitor
                </div>
                <div className="flex items-center gap-3">
                    <Badge variant="healthy">{summary!.healthyCount} Healthy</Badge>
                    {summary!.critCount > 0 && (
                        <Badge variant="critical">{summary!.critCount} Critical</Badge>
                    )}
                    <span className="text-xs text-content-tertiary font-mono">{summary!.total} total</span>
                </div>
            </CardHeader>
            <CardContent className="space-y-4">
                {/* ── Fleet Summary Stats ─────────────────────────── */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    <StatCard
                        icon={<Thermometer size={14} />}
                        label="Avg Temperature"
                        value={`${summary!.avgTemp.toFixed(1)} K`}
                        sub={`Range: ${summary!.minTemp.toFixed(0)}–${summary!.maxTemp.toFixed(0)} K`}
                    />
                    <StatCard
                        icon={<RotateCcw size={14} />}
                        label="Avg Speed"
                        value={`${summary!.avgSpeed.toFixed(0)} RPM`}
                        sub="Rotational Speed"
                    />
                    <StatCard
                        icon={<Wrench size={14} />}
                        label="Avg Torque"
                        value={`${summary!.avgTorque.toFixed(1)} Nm`}
                        sub={`Peak: ${summary!.maxTorque.toFixed(1)} Nm`}
                    />
                    <StatCard
                        icon={<Wrench size={14} />}
                        label="Tool Wear"
                        value={`${summary!.avgWear.toFixed(0)} min`}
                        sub={`Max: ${summary!.maxWear.toFixed(0)} min`}
                        alert={summary!.maxWear > 200}
                    />
                </div>

                {/* ── Critical Machines (always shown) ────────────── */}
                {critical.length > 0 && (
                    <div className="border border-signal-critical/30 rounded-md overflow-hidden">
                        <div className="bg-signal-critical-bg px-4 py-2 text-xs font-semibold uppercase tracking-wider text-signal-critical flex items-center gap-2">
                            ⚠ Critical Machines
                        </div>
                        <div className="overflow-x-auto max-h-[250px] overflow-y-auto">
                            <MachineTable machines={critical} isCritical />
                        </div>
                    </div>
                )}

                {/* ── Healthy Machines (collapsible) ──────────────── */}
                <div className="border border-border-subtle rounded-md overflow-hidden">
                    <button
                        onClick={() => setExpanded(!expanded)}
                        className="w-full bg-surface-raised px-4 py-2 text-xs font-semibold uppercase tracking-wider text-content-secondary flex items-center justify-between hover:bg-surface-raised/80 transition-colors"
                    >
                        <span>Healthy Machines ({healthy.length})</span>
                        {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                    </button>
                    {expanded && (
                        <div className="overflow-x-auto max-h-[300px] overflow-y-auto">
                            <MachineTable machines={healthy} />
                        </div>
                    )}
                </div>
            </CardContent>
        </Card>
    );
}

function StatCard({ icon, label, value, sub, alert = false }: {
    icon: React.ReactNode; label: string; value: string; sub: string; alert?: boolean;
}) {
    return (
        <div className={cn(
            "p-3 rounded-md border",
            alert ? "bg-signal-warning/5 border-signal-warning/30" : "bg-surface-raised border-border-subtle"
        )}>
            <div className="flex items-center gap-1.5 text-content-tertiary text-[0.65rem] uppercase tracking-wider font-semibold mb-1">
                {icon} {label}
            </div>
            <div className={cn("text-lg font-bold font-mono", alert && "text-signal-warning")}>
                {value}
            </div>
            <div className="text-[0.65rem] text-content-tertiary mt-0.5">{sub}</div>
        </div>
    );
}

function MachineTable({ machines, isCritical = false }: { machines: any[]; isCritical?: boolean }) {
    return (
        <table className="w-full text-xs font-mono">
            <thead className="bg-base sticky top-0">
                <tr className="text-content-tertiary uppercase tracking-wider text-[0.6rem] border-b border-border-subtle">
                    <th className="px-3 py-2 text-left font-semibold">Machine ID</th>
                    <th className="px-3 py-2 text-left font-semibold">Status</th>
                    <th className="px-3 py-2 text-right font-semibold">Temp (K)</th>
                    <th className="px-3 py-2 text-right font-semibold">Speed (RPM)</th>
                    <th className="px-3 py-2 text-right font-semibold">Torque (Nm)</th>
                    <th className="px-3 py-2 text-right font-semibold">Wear (min)</th>
                </tr>
            </thead>
            <tbody className="divide-y divide-border-subtle/40">
                {machines.map(m => (
                    <tr key={m.machineId} className="hover:bg-surface-raised/50 transition-colors">
                        <td className="px-3 py-1.5 font-semibold">{m.machineId}</td>
                        <td className="px-3 py-1.5">
                            <span className={cn(
                                "text-[0.65rem] font-medium",
                                isCritical ? "text-signal-critical" : "text-signal-healthy"
                            )}>
                                {m.status}
                            </span>
                        </td>
                        <td className="px-3 py-1.5 text-right">{parseFloat(m.airTemp || 0).toFixed(1)}</td>
                        <td className="px-3 py-1.5 text-right">{parseFloat(m.rotationalSpeed || 0).toFixed(0)}</td>
                        <td className="px-3 py-1.5 text-right">{parseFloat(m.torque || 0).toFixed(1)}</td>
                        <td className={cn(
                            "px-3 py-1.5 text-right",
                            parseFloat(m.toolWear || 0) > 200 && "text-signal-warning font-bold"
                        )}>
                            {parseFloat(m.toolWear || 0).toFixed(0)}
                        </td>
                    </tr>
                ))}
            </tbody>
        </table>
    );
}
