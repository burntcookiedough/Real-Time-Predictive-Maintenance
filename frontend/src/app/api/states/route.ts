import { NextResponse } from 'next/server';
import { cassandraClient } from '@/lib/cassandra';

export async function GET() {
    try {
        // Fetch the current state of all machines
        const query = 'SELECT machine_id, last_update, status, air_temp, torque FROM pdm.machine_states';
        const result = await cassandraClient.execute(query);

        const states = result.rows.map(row => ({
            machineId: row.machine_id,
            lastUpdate: row.last_update,
            status: row.status,
            airTemp: row.air_temp,
            torque: row.torque
        }));

        return NextResponse.json(states);
    } catch (error: any) {
        console.error('Error fetching machine states:', error);
        return NextResponse.json({ error: 'Failed to fetch states', details: error.message }, { status: 500 });
    }
}
