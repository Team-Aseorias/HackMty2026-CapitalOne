import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { resolve, extname, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createGateway } from './gateway.ts';

const root = fileURLToPath(new URL('../dist/', import.meta.url));
const requireLogin = process.env.REQUIRE_DEMO_LOGIN === 'true'
  || process.env.NODE_ENV === 'production'
  || process.env.RENDER === 'true';
const gateway = createGateway({
  backendUrl: process.env.BACKEND_URL || 'http://127.0.0.1:8000',
  apiKey: process.env.BACKEND_API_KEY,
  username: process.env.DEMO_ACCESS_USER, password: process.env.DEMO_ACCESS_PASSWORD,
  requireLogin,
});
const types: Record<string, string> = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.png': 'image/png', '.svg': 'image/svg+xml', '.ico': 'image/x-icon' };
const server = createServer(async (req, res) => {
  try {
    if (await gateway(req, res)) return;
    if (req.method !== 'GET' && req.method !== 'HEAD') { res.writeHead(405); res.end(); return; }
    const path = decodeURIComponent(new URL(req.url ?? '/', 'http://local').pathname);
    const file = resolve(root, path === '/' ? 'index.html' : '.' + path);
    if (!file.startsWith(resolve(root) + sep)) { res.writeHead(403); res.end(); return; }
    const data = await readFile(file);
    res.writeHead(200, { 'Content-Type': types[extname(file)] || 'application/octet-stream', 'X-Content-Type-Options': 'nosniff', 'Cache-Control': extname(file) === '.html' ? 'no-store' : 'private, max-age=3600' });
    res.end(req.method === 'HEAD' ? undefined : data);
  } catch { if (!res.headersSent) res.writeHead(404); res.end(); }
});
server.listen(Number(process.env.PORT || 3000), '0.0.0.0', () => console.log('ANCLA frontend listo'));
