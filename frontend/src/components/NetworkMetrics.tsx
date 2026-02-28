"use client";

import React from "react";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { Activity, Zap } from "lucide-react";
import { cn } from "@/lib/utils";

interface NetworkMetricsProps {
    latency: number; // Ms
    isConnected: boolean;
}

export default function NetworkMetrics({ latency, isConnected }: NetworkMetricsProps) {
    // Thresholds based on Goal (Target <200ms)
    const isOptimal = latency < 200;
    const isModerate = latency >= 200 && latency < 500;

    const getLatencyColor = () => {
        if (!isConnected) return "border-signal-critical text-signal-critical";
        if (isOptimal) return "border-signal-healthy text-signal-healthy";
        if (isModerate) return "border-signal-warning text-signal-warning";
        return "border-signal-critical text-signal-critical";
    };

    return (
        <Card className="col-span-1 border-l-4 border-l-signal-healthy">
            <CardHeader>
                <div className="flex items-center gap-2">
                    <Zap className="text-signal-healthy h-5 w-5" />
                    Stream Health
                </div>
            </CardHeader>
            <CardContent className="flex flex-col gap-6">

                {/* Latency Gauge / Readout */}
                <div className="flex items-center justify-between">
                    <div>
                        <p className="text-sm font-semibold uppercase tracking-wide text-content-secondary">SSE Delta Latency</p>
                        <p className="text-xs text-content-tertiary mt-1">E2E Server Processing Time</p>
                    </div>
                    <div className={cn(
                        "flex items-center justify-center h-16 w-16 rounded-full border-4 font-mono font-bold font-lg",
                        getLatencyColor()
                    )}>
                        {isConnected ? `${latency}ms` : "---"}
                    </div>
                </div>

                {/* Network Efficiency Readout */}
                <div className="p-4 bg-surface-raised rounded-md border border-border-subtle">
                    <div className="flex justify-between items-center">
                        <span className="text-sm font-medium">Bandwidth Strategy</span>
                        <span className="text-xs text-signal-healthy">Efficient</span>
                    </div>
                    <p className="text-xs text-content-tertiary mt-2">
                        utilizing Server-Sent Events (SSE) instead of 3-sec generic HTTP polling yields an active persistent TCP connection, eliminating standard HTTP handshaking overhead on every delta.
                    </p>
                </div>

            </CardContent>
        </Card>
    );
}
