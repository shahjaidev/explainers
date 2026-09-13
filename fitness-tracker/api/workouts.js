const { db, authed, USER } = require('./_db');

module.exports = async (req, res) => {
  if (!authed(req)) return res.status(401).json({ error: 'Bad or missing passcode' });

  let sql, ready;
  try { ({ sql, ready } = db()); await ready; }
  catch (err) { return res.status(503).json({ error: 'Database unavailable' }); }

  if (req.method === 'GET') {
    const rows = await sql`SELECT data FROM workouts WHERE user_id = ${USER} ORDER BY id DESC`;
    return res.status(200).json(rows.map(r => r.data));
  }

  if (req.method === 'POST') {
    const session = typeof req.body === 'string' ? JSON.parse(req.body) : req.body;
    if (!session || !session.id || !session.entries) {
      return res.status(400).json({ error: 'Expected { id, date, entries }' });
    }
    await sql`INSERT INTO workouts (user_id, id, data)
              VALUES (${USER}, ${session.id}, ${JSON.stringify(session)})
              ON CONFLICT (user_id, id) DO UPDATE SET data = EXCLUDED.data`;
    return res.status(201).json(session);
  }

  if (req.method === 'DELETE') {
    const id = (req.query && req.query.id) || '';
    if (!id) return res.status(400).json({ error: 'Session id required' });
    await sql`DELETE FROM workouts WHERE user_id = ${USER} AND id = ${id}`;
    return res.status(204).end();
  }

  return res.status(405).json({ error: 'Method not allowed' });
};
