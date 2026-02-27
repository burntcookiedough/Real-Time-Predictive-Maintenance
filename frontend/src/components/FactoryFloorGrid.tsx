"use client";
import React from "react";
import { Server } from "lucide-react";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export default function FactoryFloorGrid({ states }: { states: any[] }) {
    if (!states || states.length === 0) {
        return (
            <Card>
                <CardHeader>Factory Floor Status</CardHeader>
                <CardContent>
                    <p className="text-content-tertiary">Awaiting sensor spin-up...</p>
                </CardContent>
            </Card>
        );
    }

    return (
        <Card>
            <CardHeader>
                Factory Floor Status
                <span className="text-xs text-content-tertiary normal-case font-normal">
                    Live Cassandra View
                </span>
            </CardHeader>

            <CardContent className="grid grid-cols-[repeat(auto-fill,minmax(130px,1fr))] gap-4">
                {states.map((machine) => {
                    const isCritical = machine.status === "CRITICAL";
                    return (
                        <div
                            key={machine.machineId}
                            className={cn(
                                "flex flex-col items-center gap-2 p-4 rounded-md border text-center transition-colors duration-200",
                                isCritical
                                    ? "bg-signal-critical-bg border-signal-critical"
                                    : "bg-surface-raised border-border-subtle"
                            )}
                        >
                            <Server
                                size={24}
                                className={isCritical ? "text-signal-critical" : "text-signal-healthy"}
                            />
                            <div>
                                <div className="font-semibold text-sm">{machine.machineId}</div>
                                <div className={cn(
                                    "text-xs mt-1 font-medium tracking-wide",
                                    isCritical ? "text-signal-critical" : "text-content-secondary"
                                )}>
                                    {machine.status}
                                </div>
                            </div>
                        </div>
                    );
                })}
            </CardContent>
        </Card>
    );
}
