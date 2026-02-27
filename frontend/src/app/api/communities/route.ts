import { NextResponse } from 'next/server';
import { cassandraClient } from '@/lib/cassandra';

export async function GET() {
    try {
        const query = 'SELECT community_id, machine_id FROM pdm.failure_communities';
        const result = await cassandraClient.execute(query);

        // Group machines by community_id to send structured data to frontend
        const communitiesMap: Record<string, string[]> = {};

        result.rows.forEach(row => {
            const commId = row.community_id;
            if (!communitiesMap[commId]) {
                communitiesMap[commId] = [];
            }
            communitiesMap[commId].push(row.machine_id);
        });

        const formattedCommunities = Object.keys(communitiesMap).map(id => ({
            communityId: id,
            machines: communitiesMap[id]
        }));

        return NextResponse.json(formattedCommunities);
    } catch (error: any) {
        console.error('Error fetching communities:', error);
        return NextResponse.json({ error: 'Failed to fetch communities', details: error.message }, { status: 500 });
    }
}
