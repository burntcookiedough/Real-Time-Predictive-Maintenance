"use client";

import React, { useMemo } from "react";
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend,
    Filler
} from "chart.js";
import { Line } from "react-chartjs-2";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { Activity } from "lucide-react";
import { Badge } from "@/components/ui/badge";

ChartJS.register(
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend,
    Filler
);

interface RealTimeSensorChartProps {
    data: any[]; // Expecting the latest 15 alerts polled from SSE
    isConnected: boolean;
}

export default function RealTimeSensorChart({ data, isConnected }: RealTimeSensorChartProps) {
    // Chart.js requires chronological data; SSE array might be reversed (newest first). Let's prep it.
    const chartData = useMemo(() => {
        if (!data || data.length === 0) return null;

        // Sort chronological: oldest to newest for left-to-right scrolling feel
        const chronological = [...data].sort(
            (a, b) => new Date(a.alertTime).getTime() - new Date(b.alertTime).getTime()
        );

        const labels = chronological.map(d => new Date(d.alertTime).toLocaleTimeString());

        // Identify critical anomaly points dynamically to color them RED in the line chart
        const pointColors = chronological.map(d =>
            d.toolWear > 200 ? "#ff5252" : "#50fa7b"
        );

        return {
            labels,
            datasets: [
                {
                    label: "Rotational Speed (RPM)",
                    data: chronological.map(d => d.rotationalSpeed),
                    borderColor: "#e6edf3", // Content Primary
                    backgroundColor: pointColors,
                    pointBackgroundColor: pointColors,
                    pointBorderColor: pointColors,
                    pointRadius: chronological.map(d => d.toolWear > 200 ? 5 : 2), // Pulse size for anomalies
                    borderWidth: 2,
                    tension: 0.4, // Smooth Spline curve
                }
            ]
        };
    }, [data]);

    const chartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        animation: {
            duration: 0 // Disable broad animations to make SSE scrolling snappier
        },
        scales: {
            y: {
                beginAtZero: false,
                title: {
                    display: true,
                    text: "RPM",
                    color: "#8b949e",
                    font: { size: 10, weight: "bold" as const }
                },
                grid: {
                    color: "#30363d", // Border Subtle
                },
                ticks: {
                    callback: (value: any) => `${value}`,
                    color: "#8b949e",
                    font: { size: 9 }
                }
            },
            x: {
                grid: {
                    display: false,
                },
                ticks: {
                    color: "#8b949e",
                    font: { size: 9 },
                    maxTicksLimit: 8
                }
            }
        },
        plugins: {
            legend: {
                display: false
            },
            tooltip: {
                callbacks: {
                    label: (ctx: any) => `${ctx.parsed.y.toFixed(0)} RPM`
                }
            }
        }
    };

    return (
        <Card className="col-span-1 lg:col-span-2">
            <CardHeader>
                <div className="flex items-center gap-2">
                    <Activity className="text-signal-warning h-5 w-5" />
                    Real-Time Telemetry (Speed Layer)
                </div>
                <Badge variant={isConnected ? "healthy" : "critical"}>
                    {isConnected ? "Live Stream Active" : "Stream Offline"}
                </Badge>
            </CardHeader>
            <CardContent>
                {chartData ? (
                    <div className="h-[250px] w-full">
                        <Line data={chartData} options={chartOptions} />
                    </div>
                ) : (
                    <div className="h-[250px] w-full flex items-center justify-center border-2 border-dashed border-border-subtle rounded-md">
                        <p className="text-content-tertiary">Waiting for data stream...</p>
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
