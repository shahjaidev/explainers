const { app } = require('@azure/functions');
const { TableClient } = require('@azure/data-tables');

const TABLE = 'workouts';
let clientPromise;

// One table, partitioned by user. Created on first use so deployment needs no setup step.
function table() {
  if (!clientPromise) {
    const conn = process.env.STORAGE_CONNECTION_STRING;
    if (!conn) throw new Error('STORAGE_CONNECTION_STRING app setting is not configured');
    const client = TableClient.fromConnectionString(conn, TABLE);
    clientPromise = client.createTable().catch(err => {
      if (err.statusCode !== 409) throw err;
    }).then(() => client);
  }
  return clientPromise;
}

// Static Web Apps puts the signed-in identity here; it cannot be forged by the browser.
function userId(request) {
  const header = request.headers.get('x-ms-client-principal');
  if (!header) return null;
  try {
    const principal = JSON.parse(Buffer.from(header, 'base64').toString('utf8'));
    return principal.userId || null;
  } catch {
    return null;
  }
}

// Row keys sort ascending, so store the inverted timestamp to get newest-first for free.
const rowKey = id => String(1e15 - Number(id)).padStart(16, '0');

app.http('workouts', {
  methods: ['GET', 'POST', 'DELETE'],
  authLevel: 'anonymous',
  route: 'workouts/{id?}',
  handler: async (request, context) => {
    const user = userId(request);
    if (!user) return { status: 401, jsonBody: { error: 'Sign in required' } };
    const client = await table();

    if (request.method === 'GET') {
      const sessions = [];
      const rows = client.listEntities({
        queryOptions: { filter: `PartitionKey eq '${user.replace(/'/g, "''")}'` }
      });
      for await (const row of rows) sessions.push(JSON.parse(row.data));
      return { jsonBody: sessions };
    }

    if (request.method === 'POST') {
      const session = await request.json();
      if (!session || !session.id || !session.entries) {
        return { status: 400, jsonBody: { error: 'Expected { id, date, entries }' } };
      }
      await client.upsertEntity({
        partitionKey: user,
        rowKey: rowKey(session.id),
        data: JSON.stringify(session)
      }, 'Replace');
      context.log(`saved session ${session.id}`);
      return { status: 201, jsonBody: session };
    }

    const id = request.params.id;
    if (!id) return { status: 400, jsonBody: { error: 'Session id required' } };
    try {
      await client.deleteEntity(user, rowKey(id));
    } catch (err) {
      if (err.statusCode !== 404) throw err;
    }
    return { status: 204 };
  }
});
