import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createServer, type Server } from 'node:http';
import { createGateway } from '../server/gateway.ts';
import { cost, percent, outcomeLabel } from '../src/services/api.ts';

async function listen(server: Server) {
  await new Promise<void>(resolve => server.listen(0, '127.0.0.1', resolve));
  const address = server.address();
  if (!address || typeof address === 'string') throw new Error('No port');
  return 'http://127.0.0.1:' + address.port;
}
async function stop(server: Server) {
  server.closeAllConnections();
  await new Promise<void>((resolve, reject) => server.close(err => err ? reject(err) : resolve()));
}
test('gateway protects the demo, forwards only authorized routes and preserves feedback errors', async () => {
  const calls: { path?: string; key?: string; auth?: string; body: string }[] = [];
  const backend = createServer(async (req, res) => {
    let body = ''; for await (const chunk of req) body += chunk;
    calls.push({ path: req.url, key: req.headers['x-api-key'] as string, auth: req.headers.authorization, body });
    res.writeHead(req.url?.endsWith('/abandon') ? 409 : 200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify(req.url?.endsWith('/abandon') ? { detail: 'Decision already has a different reported outcome' } : { ok: true }));
  });
  const backendUrl = await listen(backend);
  const gateway = createGateway({ backendUrl, apiKey: 'server-secret', username: 'demo', password: 'test-pass', requireLogin: true });
  const frontend = createServer((req, res) => { gateway(req, res).then(handled => { if (!handled) { res.writeHead(200); res.end('app'); } }); });
  const base = await listen(frontend);
  const headers = { Authorization: 'Basic ' + Buffer.from('demo:test-pass').toString('base64'), 'Content-Type': 'application/json' };
  try {
    assert.equal((await fetch(base + '/api/decisions/recent')).status, 401);
    assert.equal((await fetch(base + '/')).status, 401);
    assert.equal(calls.length, 0);
    assert.equal((await fetch(base + '/api/decisions/recent?limit=25', { headers })).status, 200);
    assert.equal(calls[0].path, '/decisions/recent?limit=25');
    assert.equal(calls[0].key, 'server-secret');
    assert.equal(calls[0].auth, undefined);
    assert.equal((await fetch(base + '/api/demo-profiles', { headers })).status, 200);
    for (const path of ['/api/health', '/api/decisions/d1/verification', '/api/accounts', '/api/decisions/d1/complete/extra']) {
      assert.equal((await fetch(base + path, { headers })).status, 404);
    }
    assert.equal((await fetch(base + '/api/purchase-attempts', { method: 'POST', headers: { ...headers, Origin: 'https://other.example' }, body: '{}' })).status, 403);
    assert.equal((await fetch(base + '/api/purchase-attempts', { method: 'POST', headers, body: 'x'.repeat(20000) })).status, 413);
    const payload = { customer_id: 'c1', account_id: 'a1', merchant: 'Shop', amount: 20 };
    assert.equal((await fetch(base + '/api/purchase-attempts', { method: 'POST', headers: { ...headers, Origin: base }, body: JSON.stringify(payload) })).status, 200);
    assert.deepEqual(JSON.parse(calls.at(-1)!.body), payload);
    const profilePayload = { merchant: 'Shop', amount: 20 };
    assert.equal((await fetch(base + '/api/demo-profiles/estable/purchase-attempts', { method: 'POST', headers, body: JSON.stringify(profilePayload) })).status, 200);
    assert.deepEqual(JSON.parse(calls.at(-1)!.body), profilePayload);
    const conflict = await fetch(base + '/api/decisions/d1/abandon', { method: 'POST', headers });
    assert.equal(conflict.status, 409);
    assert.match(((await conflict.json()) as { detail: string }).detail, /different reported outcome/);
    assert.equal((await fetch(base + '/api/evaluations/run?rows=100&seed=2027', { method: 'POST', headers })).status, 200);
  } finally { await stop(frontend); await stop(backend); }
});
test('production requires credentials and missing estimates are never displayed as zero', () => {
  assert.throws(() => createGateway({ backendUrl: 'http://localhost:8000', requireLogin: true }), /Configura/);
  assert.equal(cost(null), 'No disponible');
  assert.equal(percent(null), 'No disponible');
  assert.equal(percent(0), '0.0%');
  assert.match(cost(-2), /-2/);
  assert.equal(outcomeLabel('abandoned'), 'Abandonada (reportada)');
});
