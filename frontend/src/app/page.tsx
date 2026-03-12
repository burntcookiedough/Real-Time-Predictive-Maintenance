"use client";

import React, { useEffect, useState } from "react";
import AlertTicker from "@/components/AlertTicker";
import FactoryFloorGrid from "@/components/FactoryFloorGrid";
import PageRankLeaderboard from "@/components/PageRankLeaderboard";
import CommunityClusters from "@/components/CommunityClusters";
import RealTimeSensorChart from "@/components/RealTimeSensorChart";
import NetworkMetrics from "@/components/NetworkMetrics";
import ControllerStatus from "@/components/ControllerStatus";
import { ServerCog, RefreshCcw, Box } from "lucide-react";
import { cn } from "@/lib/utils";
import { useSSE } from "@/lib/useSSE";
import Link from "next/link";

export default function Dashboard() {
  const [states, setStates] = useState<any[]>([]);
  const [pagerank, setPagerank] = useState<any[]>([]);
  const [communities, setCommunities] = useState<any[]>([]);
  const [controllerData, setControllerData] = useState<any>(null);

  // Hook into the Server-Sent Events stream for ~<200ms latency updates from Cassandra Server
  const { data: realtimeAlerts, latency: sseLatency, isConnected: sseConnected } = useSSE("/api/stream", 50);

  const fetchBatchData = async () => {
    try {
      const [statesRes, prRes, commRes, ctrlRes] = await Promise.all([
        fetch("/api/states"),
        fetch("/api/pagerank"),
        fetch("/api/communities"),
        fetch("/api/controller")
      ]);

      const statesData = statesRes.ok ? await statesRes.json() : [];
      const prData = prRes.ok ? await prRes.json() : [];
      const commData = commRes.ok ? await commRes.json() : [];
      const ctrlData = ctrlRes.ok ? await ctrlRes.json() : null;

      setStates(statesData);
      setPagerank(prData);
      setCommunities(commData);
      setControllerData(ctrlData);
    } catch (e) {
      console.error("Failed to poll Cassandra batch API:", e);
    }
  };

  useEffect(() => {
    fetchBatchData();
    const interval = setInterval(fetchBatchData, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <main className="max-w-[1440px] mx-auto p-4 md:p-6 min-h-screen">
      {/* ── Header ──────────────────────────────────────────── */}
      <header className="mb-6 pb-3 border-b border-border-subtle flex flex-col md:flex-row md:justify-between md:items-center gap-3">
        <div>
          <h1 className="text-lg md:text-xl font-bold flex items-center gap-2 uppercase tracking-wide">
            <ServerCog className="text-content-secondary" size={22} />
            Predictive Maintenance Dashboard
          </h1>
          <p className="text-content-secondary text-xs font-mono mt-1 flex items-center gap-2">
            Real-Time
            <span className="px-1.5 py-0.5 bg-surface-raised border border-border-subtle rounded text-[0.6rem] font-bold text-signal-healthy">SSE</span>
            + Batch
            <span className="px-1.5 py-0.5 bg-surface-raised border border-border-subtle rounded text-[0.6rem] font-bold text-content-primary">POLL</span>
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link href="/factory" className="flex items-center gap-1.5 text-xs font-medium px-3 py-1 rounded-full border border-border-subtle text-content-secondary hover:text-content-primary hover:border-content-secondary transition-colors">
            <Box size={12} />
            3D View
          </Link>
          <div className={cn(
            "flex items-center gap-2 text-xs font-medium px-3 py-1 rounded-full border",
            !sseConnected
              ? "text-signal-critical border-signal-critical bg-signal-critical-bg"
              : "text-signal-healthy border-signal-healthy bg-signal-healthy-bg"
          )}>
            <RefreshCcw size={12} className={sseConnected ? "animate-spin-slow" : ""} />
            {sseConnected ? "SSE Active" : "Reconnecting..."}
          </div>
        </div>
      </header>

      {/* ── Adaptive Controller Status ────────────────────────── */}
      <div className="mb-4">
        <ControllerStatus data={controllerData} />
      </div>

      {/* ── Speed Layer: Stream Health + Real-Time Chart (side-by-side) ── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
        <NetworkMetrics latency={sseLatency} isConnected={sseConnected} />
        <RealTimeSensorChart data={realtimeAlerts} isConnected={sseConnected} />
      </div>

      {/* ── Speed Layer: Alerts + Machine Monitor (stacked, compact) ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
        <AlertTicker alerts={realtimeAlerts} />
        <FactoryFloorGrid states={states} />
      </div>

      {/* ── Batch Layer: PageRank + Fault Cascades (side-by-side) ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 pt-4 border-t border-border-subtle">
        <PageRankLeaderboard scores={pagerank} />
        <CommunityClusters communities={communities} />
      </div>
    </main>
  );
}
