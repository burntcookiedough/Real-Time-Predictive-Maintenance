import { cassandraClient } from "@/lib/cassandra";

export const dynamic = "force-dynamic";
export const maxDuration = 60; // Set max duration for Vercel/Next.js edge limits, prevents infinite timeouts if not on actual Edge

export async function GET(request: Request) {
    const encoder = new TextEncoder();
    const stream = new ReadableStream({
        async start(controller) {
            const client = cassandraClient;
            let isClosed = false;

            // Ensure we clean up if the client drops connection
            request.signal.addEventListener("abort", () => {
                isClosed = true;
            });

            // Simple polling loop simulating an event stream since Cassandra lacks native triggers
            // In a pure production env with high load, we'd pipe this from Redis pub/sub directly.
            while (!isClosed) {
                try {
                    const result = await client.execute(
                        "SELECT * FROM pdm.realtime_alerts LIMIT 15"
                    );

                    if (result.rows.length > 0) {
                        // Map snake_case Cassandra columns to camelCase to match component expectations
                        const normalized = result.rows.map(row => ({
                            machineId: row.machine_id,
                            alertTime: row.alert_time,
                            airTemp: row.air_temp,
                            processTemp: row.process_temp,
                            rotationalSpeed: row.rotational_speed,
                            torque: row.torque,
                            toolWear: row.tool_wear,
                            predictionScore: row.prediction_score,
                        }));
                        const payload = {
                            serverTime: Date.now(),
                            data: normalized
                        };
                        controller.enqueue(encoder.encode(`data: ${JSON.stringify(payload)}\n\n`));
                    }
                } catch (err) {
                    console.error("SSE Cassandra polling error:", err);
                }

                // Wait 1 second before querying Cassandra again to prevent overloading the DB
                await new Promise((resolve) => setTimeout(resolve, 1000));
            }

            try {
                controller.close();
            } catch (e) {
                // Ignore close errors if stream is already closed
            }
        },
    });

    return new Response(stream, {
        headers: {
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
        },
    });
}
