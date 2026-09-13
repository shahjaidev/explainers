// Neon Postgres, provisioned through the Vercel Marketplace integration, which
// injects DATABASE_URL for us. One table, one row per finished workout.
const { neon } = require('@neondatabase/serverless');
const crypto = require('crypto');

let ready;
function db() {
  if (!process.env.DATABASE_URL) throw new Error('DATABASE_URL is not configured');
  const sql = neon(process.env.DATABASE_URL);
  ready = ready || sql`CREATE TABLE IF NOT EXISTS workouts (
    user_id text NOT NULL,
    id      bigint NOT NULL,
    data    jsonb NOT NULL,
    PRIMARY KEY (user_id, id)
  )`;
  return { sql, ready };
}

// Single-user app: one shared passcode, compared in constant time so the
// comparison itself cannot be used to guess it a character at a time.
function authed(req) {
  const expected = process.env.APP_PASSCODE;
  if (!expected) return false;
  const given = req.headers['x-app-passcode'] || '';
  const a = crypto.createHash('sha256').update(String(given)).digest();
  const b = crypto.createHash('sha256').update(expected).digest();
  return crypto.timingSafeEqual(a, b);
}

const USER = 'me';

module.exports = { db, authed, USER };
