import { NextResponse } from 'next/server';
import { cassandraClient } from '@/lib/cassandra';

export async function GET() {
    try {
        const query = 'SELECT machine_id, pagerank, last_computed FROM pdm.pagerank_scores';
        const result = await cassandraClient.execute(query);

        const scores = result.rows.map(row => ({
            machineId: row.machine_id,
            pagerank: row.pagerank,
            lastComputed: row.last_computed
        })).sort((a, b) => b.pagerank - a.pagerank); // Sort highest pagerank first

        return NextResponse.json(scores);
    } catch (error: any) {
        console.error('Error fetching pagerank scores:', error);
        return NextResponse.json({ error: 'Failed to fetch pagerank', details: error.message }, { status: 500 });
    }
}
