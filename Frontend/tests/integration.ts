import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { createServer, type Server } from 'node:http';
import { fileURLToPath } from 'node:url';
import { createGateway } from '../server/gateway.ts';
import { evaluarCompra, registrarResultado, obtenerDecisionesRecientes, obtenerMetricas, evaluarPoliticas } from '../src/services/api.ts';

async function listen(server: Server) {
  await new Promise<void>(resolve => server.listen(0, '127.0.0.1', resolve));
  const address = server.address();
  if (!address || typeof address === 'string') throw new Error('No port');
  return address.port;
}
test('actual browser API client → gateway → FastAPI inference, feedback, metrics and evaluation', { timeout: 60000 }, async t => {
  const reservation = createServer();
  const port = await listen(reservation);
  await new Promise<void>(resolve => reservation.close(() => resolve()));
  const backendUrl = 'http://127.0.0.1:' + port;
  const child = spawn(process.env.PYTHON || 'python', ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', String(port)], {
    cwd: fileURLToPath(new URL('../../backend/', import.meta.url)),
    env: { ...process.env, DEMO_MODE: 'true', BACKEND_API_KEY: 'integration-test-only', MONGO_URI: '', MONGODB_URI: '', NESSIE_API_KEY: '' },
    windowsHide: true, stdio: 'ignore',
  });
  t.after(async () => {
    if (child.exitCode === null && !child.killed) { const exited = once(child, 'exit'); child.kill(); await exited; }
  });
  let started = false;
  child.on('error', () => { /* Startup assertion below provides the failure. */ });
  for (let i = 0; i < 150; i++) {
    try { if ((await fetch(backendUrl + '/ready')).ok) { started = true; break; } } catch { /* Wait for model warmup. */ }
    await new Promise(resolve => setTimeout(resolve, 200));
  }
  assert.ok(started, 'Backend must start; install backend dependencies first');
  const handler = createGateway({ backendUrl, apiKey: 'integration-test-only' });
  const server = createServer((req, res) => { handler(req, res).then(handled => { if (!handled) { res.writeHead(404); res.end(); } }); });
  const gatewayUrl = 'http://127.0.0.1:' + await listen(server);
  const realFetch = globalThis.fetch;
  globalThis.fetch = (input, init) => realFetch(typeof input === 'string' && input.startsWith('/api/') ? gatewayUrl + input : input, init);
  t.after(async () => { globalThis.fetch = realFetch; server.closeAllConnections(); await new Promise<void>(resolve => server.close(() => resolve())); });
  const attempt = { customer_id: 'demo-customer', account_id: 'demo-account', merchant: 'Demo shop', amount: 50 };
  const decision = await evaluarCompra(attempt);
  assert.ok(decision.id);
  assert.equal(decision.context_source, 'local');
  assert.equal(decision.persistence_source, 'memory');
  assert.equal(decision.safety_override, true);
  assert.equal(decision.decision, 'verify');
  assert.equal(typeof decision.verify_completion_probability, 'number');
  assert.equal((await registrarResultado(decision.id, 'abandoned')).outcome, 'abandoned');
  const second = await evaluarCompra(attempt);
  assert.equal((await registrarResultado(second.id, 'completed')).outcome, 'completed');
  assert.equal((await registrarResultado(second.id, 'completed')).outcome, 'completed');
  await assert.rejects(registrarResultado(second.id, 'abandoned'), /409/);
  const recent = await obtenerDecisionesRecientes();
  assert.equal(recent.length, 2);
  assert.equal(recent.find(row => row.id === decision.id)?.merchant, 'Demo shop');
  const metrics = await obtenerMetricas();
  assert.equal(metrics.completed, 1);
  assert.equal(metrics.abandoned, 1);
  assert.equal(metrics.pending, 0);
  const policies = await evaluarPoliticas(100, 2027);
  assert.equal(policies.length, 5);
  assert.equal(policies.find(p => p.policy === 'causal')?.safety_violations, 0);
  await assert.rejects(evaluarCompra({ ...attempt, account_id: '' }), /422/);
});
