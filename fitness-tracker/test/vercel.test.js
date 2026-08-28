// Drives the Vercel handlers against an in-memory stand-in for Neon.
const Module = require('module');
const assert = require('assert');
const path = require('path');

let rows = [];              // {user_id, id, data}
let failNext = false;
const sqlTag = async (strings, ...vals) => {
  if (failNext) throw new Error('connection refused');
  const q = strings.join('?');
  if (/CREATE TABLE/.test(q) || /SELECT 1/.test(q)) return [];
  if (/^\s*SELECT data/.test(q)) {
    return rows.filter(r => r.user_id === vals[0])
               .sort((a, b) => b.id - a.id).map(r => ({ data: r.data }));
  }
  if (/INSERT INTO/.test(q)) {
    const [user_id, id, data] = vals;
    rows = rows.filter(r => !(r.user_id === user_id && String(r.id) === String(id)));
    rows.push({ user_id, id: Number(id), data: JSON.parse(data) });
    return [];
  }
  if (/DELETE FROM/.test(q)) {
    const [user_id, id] = vals;
    rows = rows.filter(r => !(r.user_id === user_id && String(r.id) === String(id)));
    return [];
  }
  throw new Error('unexpected query: ' + q);
};

const orig = Module.prototype.require;
Module.prototype.require = function (id) {
  if (id === '@neondatabase/serverless') return { neon: () => sqlTag };
  return orig.apply(this, arguments);
};

process.env.DATABASE_URL = 'postgres://fake';
process.env.APP_PASSCODE = 'correct-horse';
const workouts = require(path.join(__dirname, '../api/workouts.js'));
const health = require(path.join(__dirname, '../api/health.js'));

const res = () => {
  const r = { code: 200, body: undefined };
  r.status = c => { r.code = c; return r; };
  r.json = b => { r.body = b; return r; };
  r.end = () => r;
  return r;
};
const req = (method, opts = {}) => ({
  method,
  headers: opts.pass ? { 'x-app-passcode': opts.pass } : {},
  query: opts.query || {},
  body: opts.body
});
const P = 'correct-horse';

(async () => {
  // no passcode, and a wrong one, are both rejected
  assert.equal((await workouts(req('GET'), res())).code, 401);
  assert.equal((await workouts(req('GET', {pass: 'wrong'}), res())).code, 401);
  // a wrong passcode of a different length must not throw (timingSafeEqual needs equal buffers)
  assert.equal((await workouts(req('GET', {pass: 'x'}), res())).code, 401);

  const s1 = {id: 1700000000000, date: 'Mon', entries: {'Lat Pulldown': {weight: '115'}}};
  const s2 = {id: 1700086400000, date: 'Tue', entries: {'Vert Row': {weight: '120'}}};
  assert.equal((await workouts(req('POST', {pass: P, body: s1}), res())).code, 201);
  await workouts(req('POST', {pass: P, body: s2}), res());

  // body arriving as a raw string still parses
  await workouts(req('POST', {pass: P, body: JSON.stringify(s1)}), res());

  let r = await workouts(req('GET', {pass: P}), res());
  assert.deepEqual(r.body.map(s => s.id), [s2.id, s1.id], 'newest-first');
  assert.equal(r.body.length, 2, 'upsert did not duplicate');

  assert.equal((await workouts(req('POST', {pass: P, body: {}}), res())).code, 400);
  assert.equal((await workouts(req('PUT', {pass: P}), res())).code, 405);
  assert.equal((await workouts(req('DELETE', {pass: P}), res())).code, 400);

  assert.equal((await workouts(req('DELETE', {pass: P, query: {id: String(s1.id)}}), res())).code, 204);
  assert.equal((await workouts(req('DELETE', {pass: P, query: {id: String(s1.id)}}), res())).code, 204);
  assert.equal((await workouts(req('GET', {pass: P}), res())).body.length, 1);

  // health: happy, db down, and both unconfigured paths
  assert.equal((await health(req('GET'), res())).body.ok, true);
  failNext = true;
  r = await health(req('GET'), res());
  assert.equal(r.code, 503); assert.equal(r.body.storage, 'unreachable');
  failNext = false;

  delete process.env.APP_PASSCODE;
  assert.equal((await health(req('GET'), res())).body.auth, 'unconfigured');
  delete process.env.DATABASE_URL;
  assert.equal((await health(req('GET'), res())).body.storage, 'unconfigured');

  console.log('all Vercel tests passed');
})().catch(e => { console.error('FAIL:', e.message); process.exit(1); });
