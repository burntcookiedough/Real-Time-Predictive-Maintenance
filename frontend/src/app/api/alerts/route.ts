import { NextResponse } from 'next/server';
import { cassandraClient } from '@/lib/cassandra';

export async function GET() {
    try {
        // Fetch the top 15 most recent alerts
        const query = 'SELECT machine_id, alert_time, air_temp, process_temp, rotational_speed, tool_wear, torque FROM pdm.realtime_alerts LIMIT 15';
        const result = await cassandraClient.execute(query);

        // Sort by alert_time descending manually if Cassandra didn't (though clustering handles it)
        const alerts = result.rows.map(row => ({
            machineId: row.machine_id,
            alertTime: row.alert_time,
            airTemp: row.air_temp,
            processTemp: row.process_temp,
            rotationalSpeed: row.rotational_speed,
            toolWear: row.tool_wear,
            torque: row.torque
        })).sort((a, b) => new Date(b.alertTime).getTime() - new Date(a.alertTime).getTime());

        return NextResponse.json(alerts);
    } catch (error: any) {
        console.error('Error fetching alerts:', error);
        return NextResponse.json({ error: 'Failed to fetch alerts', details: error.message }, { status: 500 });
    }
}
