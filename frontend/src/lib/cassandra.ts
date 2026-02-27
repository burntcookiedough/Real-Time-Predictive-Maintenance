import { Client } from 'cassandra-driver';

// Singleton Cassandra Client pattern for Next.js to avoid connection leaks in dev
const globalForCassandra = global as unknown as { cassandraClient: Client };

export const cassandraClient =
  globalForCassandra.cassandraClient ||
  new Client({
    contactPoints: ['127.0.0.1'], // Adjust if Docker networking requires differently from host
    localDataCenter: 'datacenter1', // Default datacenter for basic cassandra image
    keyspace: 'pdm',
  });

if (process.env.NODE_ENV !== 'production') globalForCassandra.cassandraClient = cassandraClient;
