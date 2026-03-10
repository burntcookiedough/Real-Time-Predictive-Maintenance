"use client";
import React from "react";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";

export default function AlertTicker({ alerts }: { alerts: any[] }) {
    if (!alerts || alerts.length === 0) {
        return (
            <Card>
                <CardHeader>
                    <div className="flex items-center gap-2">
                        <AlertTriangle size={16} className="text-content-tertiary" />
                        Recent Anomalies
                    </div>
                </CardHeader>
                <CardContent>
                    <p className="text-content-tertiary text-sm">
                        No critical alerts detected in the data stream.
                    </p>
                </CardContent>
            </Card>
        );
    }

    // Show only the latest 5 alerts to keep UI compact
    const recent = alerts.slice(0, 5);

    return (
        <Card className="border-l-4 border-l-signal-critical">
            <CardHeader>
                <div className="flex items-center gap-2">
                    <AlertTriangle className="text-signal-critical h-4 w-4" />
                    Recent Anomalies
                </div>
                <Badge variant="critical">
                    {alerts.length} Active
                </Badge>
            </CardHeader>
            <CardContent>
                <div className="overflow-x-auto">
                    <table className="w-full text-xs font-mono">
                        <thead>
                            <tr className="text-content-tertiary uppercase tracking-wider text-[0.6rem] border-b border-border-subtle">
                                <th className="px-3 py-2 text-left font-semibold">Machine</th>
                                <th className="px-3 py-2 text-left font-semibold">Time</th>
                                <th className="px-3 py-2 text-right font-semibold">Speed (RPM)</th>
                                <th className="px-3 py-2 text-right font-semibold">Temp (K)</th>
                                <th className="px-3 py-2 text-right font-semibold">Torque (Nm)</th>
                                <th className="px-3 py-2 text-right font-semibold">Wear (min)</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-border-subtle/40">
                            {recent.map((alert, idx) => (
                                <tr key={`${alert.machineId}-${idx}`} className="hover:bg-surface-raised/50">
                                    <td className="px-3 py-1.5 font-semibold text-signal-critical">{alert.machineId}</td>
                                    <td className="px-3 py-1.5 text-content-tertiary">
                                        {new Date(alert.alertTime).toLocaleTimeString()}
                                    </td>
                                    <td className="px-3 py-1.5 text-right">
                                        {(alert.rotationalSpeed ?? 0).toFixed(0)}
                                    </td>
                                    <td className="px-3 py-1.5 text-right">
                                        {(alert.airTemp ?? 0).toFixed(1)}
                                    </td>
                                    <td className="px-3 py-1.5 text-right">
                                        {(alert.torque ?? 0).toFixed(1)}
                                    </td>
                                    <td className={cn(
                                        "px-3 py-1.5 text-right",
                                        (alert.toolWear ?? 0) > 200 && "text-signal-warning font-bold"
                                    )}>
                                        {alert.toolWear ?? 'N/A'}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </CardContent>
        </Card>
    );
}
