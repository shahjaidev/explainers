const { app } = require('@azure/functions');
const { TableClient } = require('@azure/data-tables');

// Deliberately anonymous and deliberately terse: it reports whether the API can
// reach its table, and nothing about the account, the data, or the environment.
app.http('health', {
  methods: ['GET'],
  authLevel: 'anonymous',
  route: 'health',
  handler: async (request, context) => {
    const conn = process.env.STORAGE_CONNECTION_STRING;
    if (!conn) {
      return { status: 503, jsonBody: { ok: false, storage: 'unconfigured' } };
    }
    try {
      const client = TableClient.fromConnectionString(conn, 'workouts');
      await client.createTable().catch(err => { if (err.statusCode !== 409) throw err; });
      // A bounded read proves credentials work, not just that the URL parses.
      const page = await client.listEntities({ queryOptions: { filter: "PartitionKey eq '__health__'" } })
        .byPage({ maxPageSize: 1 }).next();
      return { jsonBody: { ok: true, storage: 'reachable', rows: page.value ? page.value.length : 0 } };
    } catch (err) {
      context.log(`health check failed: ${err.message}`);
      return { status: 503, jsonBody: { ok: false, storage: 'unreachable', code: err.statusCode || null } };
    }
  }
});
