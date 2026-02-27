"use client";

import React, { useEffect, useState } from "react";
import AlertTicker from "@/components/AlertTicker";
import FactoryFloorGrid from "@/components/FactoryFloorGrid";
import PageRankLeaderboard from "@/components/PageRankLeaderboard";
import CommunityClusters from "@/components/CommunityClusters";
import { ServerCog, RefreshCcw } from "lucide-react";

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
    // Initial fetch
    fetchData();

    // High frequency polling for industrial factory UI (every 3 seconds)
    const interval = setInterval(fetchData, 3000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="container">
      <div className="dashboard-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1><ServerCog size={24} /> Lambda Architecture: Predictive Maintenance</h1>
          <p>Unified Real-Time & Batch Analytics View | Cassandra Serving Layer</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: isLoading ? 'var(--text-tertiary)' : 'var(--signal-healthy)', fontSize: '0.85rem' }}>
          <RefreshCcw size={16} className={isLoading ? "spin" : ""} />
          {isLoading ? "Polling..." : "System Sync Active"}
        </div>
      </div>

      {/* Speed Layer UI */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', marginBottom: '1.5rem' }}>
        <AlertTicker alerts={alerts} />
        <FactoryFloorGrid states={states} />
      </div>

      {/* Batch / Graph Layer UI */}
      <div className="grid-2">
        <PageRankLeaderboard scores={pagerank} />
        <CommunityClusters communities={communities} />
      </div>

      <style dangerouslySetInnerHTML={{
        __html: `
        @keyframes spin { 100% { transform: rotate(360deg); } }
        .spin { animation: spin 2s linear infinite; }
      `}} />
    </div>
  );
}
