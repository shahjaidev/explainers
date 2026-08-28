// Stub the Table SDK with an in-memory table, then drive the real handler.
const Module = require('module');
const store = new Map();
const fakeClient = {
  createTable: async () => {},
  async *listEntities({queryOptions}) {
    const user = queryOptions.filter.match(/'(.*)'/)[1];
    for (const [k, v] of [...store.entries()].sort())
      if (v.partitionKey === user) yield v;
  },
  upsertEntity: async e => { store.set(e.partitionKey+'|'+e.rowKey, e); },
  deleteEntity: async (p, r) => {
    if (!store.has(p+'|'+r)) { const e = new Error('nope'); e.statusCode = 404; throw e; }
    store.delete(p+'|'+r);
  }
};
const orig = Module.prototype.require;
Module.prototype.require = function (id) {
  if (id === '@azure/data-tables') return { TableClient: { fromConnectionString: () => fakeClient } };
  if (id === '@azure/functions') return { app: { http: (n, o) => { global.__h = o.handler; } } };
  return orig.apply(this, arguments);
};
process.env.STORAGE_CONNECTION_STRING = 'fake';
require('../src/functions/workouts.js');
const h = global.__h;
const ctx = { log: () => {} };

const principal = u => Buffer.from(JSON.stringify({userId:u,userDetails:u})).toString('base64');
const req = (method, opts={}) => ({
  method,
  params: opts.params || {},
  headers: { get: k => k === 'x-ms-client-principal' ? (opts.user ? principal(opts.user) : null) : null },
  json: async () => opts.body
});
const assert = require('assert');

(async () => {
  // anonymous is rejected
  assert.equal((await h(req('GET'), ctx)).status, 401);

  // save two sessions for jai
  const s1 = {id: 1700000000000, date:'Mon', entries:{'Lat Pulldown':{weight:'115',r1:'6'}}};
  const s2 = {id: 1700086400000, date:'Tue', entries:{'Vert Row':{weight:'120',r1:'7'}}};
  assert.equal((await h(req('POST',{user:'jai',body:s1}), ctx)).status, 201);
  await h(req('POST',{user:'jai',body:s2}), ctx);

  // newest first
  let got = (await h(req('GET',{user:'jai'}), ctx)).jsonBody;
  assert.deepEqual(got.map(s=>s.id), [s2.id, s1.id], 'newest-first order');

  // another user sees nothing
  assert.deepEqual((await h(req('GET',{user:'other'}), ctx)).jsonBody, []);

  // bad body rejected
  assert.equal((await h(req('POST',{user:'jai',body:{}}), ctx)).status, 400);

  // delete, incl. idempotent re-delete
  assert.equal((await h(req('DELETE',{user:'jai',params:{id:String(s1.id)}}), ctx)).status, 204);
  assert.equal((await h(req('DELETE',{user:'jai',params:{id:String(s1.id)}}), ctx)).status, 204);
  assert.equal((await h(req('GET',{user:'jai'}), ctx)).jsonBody.length, 1);

  // other user cannot delete jai's row
  await h(req('DELETE',{user:'other',params:{id:String(s2.id)}}), ctx);
  assert.equal((await h(req('GET',{user:'jai'}), ctx)).jsonBody.length, 1, 'cross-user delete blocked');

  console.log('all API tests passed');
})().catch(e => { console.error('FAIL:', e.message); process.exit(1); });
