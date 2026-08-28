const { db } = require('./_db');

// Anonymous on purpose, and terse on purpose: reachability only, never data.
// `auth` tells the frontend which sign-in flow this deployment expects.
module.exports = async (req, res) => {
  if (!process.env.DATABASE_URL) {
    return res.status(503).json({ ok: false, storage: 'unconfigured', auth: 'passcode' });
  }
  if (!process.env.APP_PASSCODE) {
    return res.status(503).json({ ok: false, storage: 'reachable', auth: 'unconfigured' });
  }
  try {
    const { sql, ready } = db();
    await ready;
    await sql`SELECT 1`;
    return res.status(200).json({ ok: true, storage: 'reachable', auth: 'passcode' });
  } catch (err) {
    return res.status(503).json({ ok: false, storage: 'unreachable', auth: 'passcode' });
  }
};
