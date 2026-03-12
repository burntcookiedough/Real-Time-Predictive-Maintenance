import { NextResponse } from 'next/server';
import { cassandraClient } from '@/lib/cassandra';

export async function GET() {
    try {
        const query = `SELECT controller_id, latency_threshold, cloud_sample_rate,
                               retrain_interval, edge_anomaly_rate, cloud_backlog,
                               avg_rtt, last_updated
                        FROM pdm.controller_state
                        WHERE controller_id = 'edge_controller_v1'`;
        const result = await cassandraClient.execute(query);

        if (result.rows.length === 0) {
            return NextResponse.json({
                controllerId: 'edge_controller_v1',
                latencyThreshold: 200,
                cloudSampleRate: 0.2,
                retrainInterval: 500,
                edgeAnomalyRate: 0,
                cloudBacklog: 0,
                avgRtt: 0,
                lastUpdated: null,
                active: false
            });
        }

        const row = result.rows[0];
        return NextResponse.json({
            controllerId: row.controller_id,
            latencyThreshold: row.latency_threshold,
            cloudSampleRate: row.cloud_sample_rate,
            retrainInterval: row.retrain_interval,
            edgeAnomalyRate: row.edge_anomaly_rate,
            cloudBacklog: row.cloud_backlog,
            avgRtt: row.avg_rtt,
            lastUpdated: row.last_updated,
            active: true
        });
    } catch (error: any) {
        console.error('Error fetching controller state:', error);
        return NextResponse.json(
            { error: 'Failed to fetch controller state', details: error.message },
            { status: 500 }
        );
    }
}
