"use client";
import React from "react";
import { Network } from "lucide-react";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export default function CommunityClusters({ communities }: { communities: any[] }) {
    if (!communities || communities.length === 0) {
        return (
            <Card>
                <CardHeader>Batch Analytics: Fault Cascade Clusters</CardHeader>
                <CardContent>
                    <p className="text-content-tertiary">No graph analytics computed yet.</p>
                </CardContent>
            </Card>
        );
    }

    return (
        <Card>
            <CardHeader>
                Fault Cascade Clusters
                <Network size={18} className="text-content-secondary" />
            </CardHeader>
            <CardContent className="flex flex-col gap-4">
                {communities.slice(0, 5).map((cluster: any, idx: number) => (
                    <div key={idx} className="p-4 bg-base border border-border-subtle rounded-md">
                        <div className="text-xs text-content-tertiary mb-3 font-semibold uppercase tracking-wider">
                            Cluster {cluster.communityId}
                        </div>
                        <div className="flex flex-wrap gap-2">
                            {cluster.machines.map((machineId: string) => (
                                <Badge key={machineId} variant="default" className="font-mono text-[0.7rem] px-2">
                                    {machineId}
                                </Badge>
                            ))}
                        </div>
                    </div>
                ))}
            </CardContent>
        </Card>
    );
}
