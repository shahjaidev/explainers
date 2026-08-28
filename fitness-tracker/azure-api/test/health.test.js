// Drives the health handler through its three outcomes with a stubbed SDK.
const Module = require('module');
let mode = 'ok';
const fakeClient = {
  createTable: async () => { if (mode === 'down') { const e = new Error('auth'); e.statusCode = 403; throw e; } },
  listEntities: () => ({ byPage: () => ({ next: async () => ({ value: [] }) }) })
};
const orig = Module.prototype.require;
Module.prototype.require = function (id) {
  if (id === '@azure/data-tables') return { TableClient: { fromConnectionString: () => fakeClient } };
  if (id === '@azure/functions') return { app: { http: (n, o) => { global.__h = o.handler; } } };
  return orig.apply(this, arguments);
};
require('../src/functions/health.js');
const h = global.__h, ctx = { log: () => {} }, assert = require('assert');

(async () => {
  delete process.env.STORAGE_CONNECTION_STRING;
  let r = await h({}, ctx);
  assert.equal(r.status, 503); assert.equal(r.jsonBody.storage, 'unconfigured');

  process.env.STORAGE_CONNECTION_STRING = 'fake';
  mode = 'ok';
  r = await h({}, ctx);
  assert.equal(r.status, undefined); assert.equal(r.jsonBody.ok, true);

  mode = 'down';
  r = await h({}, ctx);
  assert.equal(r.status, 503); assert.equal(r.jsonBody.storage, 'unreachable'); assert.equal(r.jsonBody.code, 403);

  console.log('all health tests passed');
})().catch(e => { console.error('FAIL:', e.message); process.exit(1); });
