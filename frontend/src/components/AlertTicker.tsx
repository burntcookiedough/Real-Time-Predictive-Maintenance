"use client";
import React from "react";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { AlertTriangle } from "lucide-react";

export default function AlertTicker({ alerts }: { alerts: any[] }) {
    if (!alerts || alerts.length === 0) {
        return (
            <Card>
                <CardHeader>Recent Critical Anomalies (Speed Layer)</CardHeader>
                <CardContent>
                    <p className="text-content-tertiary text-sm">
                        No critical alerts detected in the data stream.
                    </p>
                </CardContent>
            </Card>
        );
    }

    return (
        <Card className="border-l-4 border-l-signal-critical">
            <CardHeader>
                <div className="flex items-center gap-2">
                    <AlertTriangle className="text-signal-critical h-5 w-5" />
                    Recent Critical Anomalies
                </div>
                <Badge variant="critical">
                    {alerts.length} Active
                </Badge>
            </CardHeader>
            <CardContent>
                <div className="space-y-3">
                    {alerts.map((alert, idx) => (
                        <Alert key={`${alert.machineId}-${idx}`} variant="destructive" className="py-3">
                            <AlertTriangle className="h-4 w-4" />
                            <AlertTitle className="text-sm font-semibold">{alert.machineId}</AlertTitle>
                            <AlertDescription className="flex justify-between items-center text-xs mt-1">
                                <span>{new Date(alert.alertTime).toLocaleTimeString()}</span>
                                <span>{(alert.rotationalSpeed ?? 0).toFixed(0)} RPM / {(alert.airTemp ?? 0).toFixed(1)}K</span>
                                <span className={alert.toolWear > 200 ? "text-signal-warning font-bold" : ""}>
                                    Wear: {alert.toolWear ?? 'N/A'} min
                                </span>
                            </AlertDescription>
                        </Alert>
                    ))}
                </div>
            </CardContent>
        </Card>
    );
}
