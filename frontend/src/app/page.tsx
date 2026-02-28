"use client";

import React, { useEffect, useState } from "react";
import AlertTicker from "@/components/AlertTicker";
import FactoryFloorGrid from "@/components/FactoryFloorGrid";
import PageRankLeaderboard from "@/components/PageRankLeaderboard";
import CommunityClusters from "@/components/CommunityClusters";
import RealTimeSensorChart from "@/components/RealTimeSensorChart";
import NetworkMetrics from "@/components/NetworkMetrics";
import { ServerCog, RefreshCcw } from "lucide-react";
import { cn } from "@/lib/utils";
import { useSSE } from "@/lib/useSSE";

export default function Dashboard() {
  const [states, setStates] = useState<any[]>([]);
  const [pagerank, setPagerank] = useState<any[]>([]);
  const [communities, setCommunities] = useState<any[]>([]);

  // Hook into the Server-Sent Events stream for ~<200ms latency updates from Cassandra Server
  const { data: realtimeAlerts, latency: sseLatency, isConnected: sseConnected } = useSSE("/api/stream", 50);

  const fetchBatchData = async () => {
    try {
      // The speed layer/alerts are populated instantly via SSE now. 
      // We still poll the longer-running batch graph analytics.
      const [statesRes, prRes, commRes] = await Promise.all([
        fetch("/api/states"),
        fetch("/api/pagerank"),
        fetch("/api/communities")
      ]);

      const statesData = statesRes.ok ? await statesRes.json() : [];
      const prData = prRes.ok ? await prRes.json() : [];
      const commData = commRes.ok ? await commRes.json() : [];

      setStates(statesData);
      setPagerank(prData);
      setCommunities(commData);
    } catch (e) {
      console.error("Failed to poll Cassandra batch API:", e);
    }
  };

  useEffect(() => {
    fetchBatchData();
    // Re-poll the slow-moving ML graph nodes every 5 seconds since it's a batch job
    const interval = setInterval(fetchBatchData, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <main className="max-w-[1440px] mx-auto p-4 md:p-8 min-h-screen">
      <header className="mb-8 pb-4 border-b border-border-subtle flex flex-col md:flex-row md:justify-between md:items-center gap-4">
        <div>
          <h1 className="text-xl md:text-2xl font-bold flex items-center gap-3 uppercase tracking-wide">
            <ServerCog className="text-content-secondary" size={28} />
            Lambda Architecture Dashboard
          </h1>
          <p className="text-content-secondary text-sm font-mono mt-2 flex items-center gap-2">
            Unified Real-Time
            <span className="px-1.5 py-0.5 bg-surface-raised border border-border-subtle rounded-md text-xs font-bold text-signal-healthy">SSE</span>
            & Batch Analytics
            <span className="px-1.5 py-0.5 bg-surface-raised border border-border-subtle rounded-md text-xs font-bold text-content-primary">POLL</span>
          </p>
        </div>
        <div className={cn(
          "flex items-center gap-2 text-sm font-medium px-3 py-1.5 rounded-full border",
          !sseConnected
            ? "text-signal-critical border-signal-critical bg-signal-critical-bg"
            : "text-signal-healthy border-signal-healthy bg-signal-healthy-bg"
        )}>
          <RefreshCcw size={16} className={sseConnected ? "animate-spin-slow" : ""} />
          {sseConnected ? "SSE Active" : "Reconnecting..."}
        </div>
      </header>

      {/* Speed Layer (Streaming WebSockets/SSE) */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        <NetworkMetrics latency={sseLatency} isConnected={sseConnected} />
        <RealTimeSensorChart data={realtimeAlerts} isConnected={sseConnected} />
      </div>

      <div className="flex flex-col gap-6 mb-6">
        <AlertTicker alerts={realtimeAlerts} />
        <FactoryFloorGrid states={states} />
      </div>

      {/* Batch Layer (HDFS -> PageRank Graph ML) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-12 pt-8 border-t border-border-subtle">
        <PageRankLeaderboard scores={pagerank} />
        <CommunityClusters communities={communities} />
      </div>
    </main>
  );
}
