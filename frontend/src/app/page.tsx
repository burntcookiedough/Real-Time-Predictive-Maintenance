"use client";

import React, { useEffect, useState } from "react";
import AlertTicker from "@/components/AlertTicker";
import FactoryFloorGrid from "@/components/FactoryFloorGrid";
import PageRankLeaderboard from "@/components/PageRankLeaderboard";
import CommunityClusters from "@/components/CommunityClusters";
import { ServerCog, RefreshCcw } from "lucide-react";
import { cn } from "@/lib/utils";

export default function Dashboard() {
  const [alerts, setAlerts] = useState<any[]>([]);
  const [states, setStates] = useState<any[]>([]);
  const [pagerank, setPagerank] = useState<any[]>([]);
  const [communities, setCommunities] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const fetchData = async () => {
    try {
      const [alertsRes, statesRes, prRes, commRes] = await Promise.all([
        fetch("/api/alerts"),
        fetch("/api/states"),
        fetch("/api/pagerank"),
        fetch("/api/communities")
      ]);

      const alertsData = alertsRes.ok ? await alertsRes.json() : [];
      const statesData = statesRes.ok ? await statesRes.json() : [];
      const prData = prRes.ok ? await prRes.json() : [];
      const commData = commRes.ok ? await commRes.json() : [];

      setAlerts(alertsData);
      setStates(statesData);
      setPagerank(prData);
      setCommunities(commData);
    } catch (e) {
      console.error("Failed to poll Cassandra API:", e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 3000);
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
          <p className="text-content-secondary text-sm font-mono mt-2">
            Unified Real-Time & Batch Analytics View | Cassandra Serving Layer
          </p>
        </div>
        <div className={cn(
          "flex items-center gap-2 text-sm font-medium px-3 py-1.5 rounded-full border",
          isLoading
            ? "text-content-tertiary border-border-subtle bg-surface"
            : "text-signal-healthy border-signal-healthy bg-signal-healthy-bg"
        )}>
          <RefreshCcw size={16} className={isLoading ? "animate-spin-slow" : ""} />
          {isLoading ? "Polling..." : "System Sync Active"}
        </div>
      </header>

      <div className="flex flex-col gap-6 mb-6">
        <AlertTicker alerts={alerts} />
        <FactoryFloorGrid states={states} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <PageRankLeaderboard scores={pagerank} />
        <CommunityClusters communities={communities} />
      </div>
    </main>
  );
}
