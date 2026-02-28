"use client";

import { useEffect, useState, useRef } from "react";

interface SSEPayload {
    serverTime: number;
    data: any[];
}

export function useSSE(endpoint: string, maxBufferSize: number = 50) {
    const [data, setData] = useState<any[]>([]);
    const [latency, setLatency] = useState<number>(0);
    const [isConnected, setIsConnected] = useState<boolean>(false);
    const eventSourceRef = useRef<EventSource | null>(null);
    const backoffRef = useRef<number>(1000); // 1s initial backoff

    useEffect(() => {
        let isMounted = true;

        const connect = () => {
            // Clean up any existing connection
            if (eventSourceRef.current) {
                eventSourceRef.current.close();
            }

            console.log(`[SSE] Connecting to ${endpoint}...`);
            const eventSource = new EventSource(endpoint);
            eventSourceRef.current = eventSource;

            eventSource.onopen = () => {
                if (isMounted) {
                    setIsConnected(true);
                    backoffRef.current = 1000; // Reset backoff on success
                    console.log(`[SSE] Connected!`);
                }
            };

            eventSource.onmessage = (event) => {
                if (!isMounted) return;

                try {
                    const payload: SSEPayload = JSON.parse(event.data);
                    const clientTime = Date.now();

                    // Calculate one-way latency (Server processing time -> Client rendering time)
                    const currentLatency = clientTime - payload.serverTime;
                    setLatency(currentLatency);

                    // Update buffer with new array, keeping the timeline within 'maxBufferSize'
                    // Next.js API stream sends the latest 15 alerts, so we append the new batch to our historical buffer
                    // For simplicity in the chart, we'll just track the most recent 'tick' as the current state
                    setData(payload.data);
                } catch (e) {
                    console.error("[SSE] Failed to parse event:", e);
                }
            };

            eventSource.onerror = (err) => {
                console.error("[SSE] Connection error/drop, attempting reconnect...", err);
                if (isMounted) {
                    setIsConnected(false);
                    eventSource.close();

                    // Exponential backoff reconnect
                    const nextBackoff = Math.min(backoffRef.current * 2, 30000);
                    backoffRef.current = nextBackoff;
                    setTimeout(connect, nextBackoff);
                }
            };
        };

        connect();

        return () => {
            isMounted = false;
            if (eventSourceRef.current) {
                eventSourceRef.current.close();
            }
        };
    }, [endpoint, maxBufferSize]);

    return { data, latency, isConnected };
}
