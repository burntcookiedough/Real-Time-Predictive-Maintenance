"use client";

import React from "react";
import { Gauge, ArrowUpDown, CloudUpload, RefreshCcw, Activity, Database } from "lucide-react";
import { cn } from "@/lib/utils";

interface ControllerData {
  controllerId: string;
  latencyThreshold: number;
  cloudSampleRate: number;
  retrainInterval: number;
  edgeAnomalyRate: number;
  cloudBacklog: number;
  avgRtt: number;
  lastUpdated: string | null;
  active: boolean;
}

interface ControllerStatusProps {
  data: ControllerData | null;
}

function MetricCard({
  icon: Icon,
  label,
  value,
  unit,
  color,
}: {
  icon: any;
  label: string;
  value: string | number;
  unit?: string;
  color: string;
}) {
  return (
    <div className="flex items-center gap-2.5 min-w-[140px]">
      <div className={cn("p-1.5 rounded", color)}>
        <Icon size={13} />
      </div>
      <div>
        <p className="text-[0.6rem] uppercase tracking-wider text-content-secondary font-medium">
          {label}
        </p>
        <p className="text-sm font-bold font-mono">
          {value}
          {unit && (
            <span className="text-[0.6rem] text-content-secondary ml-0.5">
              {unit}
            </span>
          )}
        </p>
      </div>
    </div>
  );
}

export default function ControllerStatus({ data }: ControllerStatusProps) {
  const isActive = data?.active ?? false;

  return (
    <div className="card p-3">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Gauge size={14} className="text-content-secondary" />
          <h3 className="text-xs font-bold uppercase tracking-wider">
            Adaptive Controller
          </h3>
        </div>
        <span
          className={cn(
            "text-[0.55rem] font-bold px-2 py-0.5 rounded-full border",
            isActive
              ? "text-signal-healthy border-signal-healthy bg-signal-healthy-bg"
              : "text-content-secondary border-border-subtle"
          )}
        >
          {isActive ? "ACTIVE" : "WAITING"}
        </span>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        <MetricCard
          icon={ArrowUpDown}
          label="Latency Threshold"
          value={data ? Math.round(data.latencyThreshold) : "—"}
          unit="ms"
          color="bg-blue-500/10 text-blue-400"
        />
        <MetricCard
          icon={CloudUpload}
          label="Cloud Sample Rate"
          value={data ? `${(data.cloudSampleRate * 100).toFixed(0)}%` : "—"}
          color="bg-purple-500/10 text-purple-400"
        />
        <MetricCard
          icon={RefreshCcw}
          label="Retrain Interval"
          value={data ? data.retrainInterval : "—"}
          unit="rec"
          color="bg-amber-500/10 text-amber-400"
        />
        <MetricCard
          icon={Activity}
          label="Anomaly Rate"
          value={
            data ? `${(data.edgeAnomalyRate * 100).toFixed(1)}%` : "—"
          }
          color="bg-red-500/10 text-red-400"
        />
        <MetricCard
          icon={Database}
          label="Cloud Backlog"
          value={data ? data.cloudBacklog : "—"}
          unit="msg"
          color="bg-cyan-500/10 text-cyan-400"
        />
        <MetricCard
          icon={ArrowUpDown}
          label="Avg RTT"
          value={data ? Math.round(data.avgRtt) : "—"}
          unit="ms"
          color="bg-green-500/10 text-green-400"
        />
      </div>

      {/* Last Updated */}
      {data?.lastUpdated && (
        <p className="text-[0.55rem] text-content-secondary mt-2 text-right font-mono">
          Updated: {new Date(data.lastUpdated).toLocaleTimeString()}
        </p>
      )}
    </div>
  );
}
