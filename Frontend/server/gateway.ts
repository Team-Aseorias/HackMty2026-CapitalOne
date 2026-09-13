import type { IncomingMessage, ServerResponse } from 'node:http';
import { createHash, timingSafeEqual } from 'node:crypto';

export interface GatewayConfig { backendUrl: string; apiKey?: string; username?: string; password?: string; requireLogin?: boolean }
export function createGateway(config: GatewayConfig) {
  const target = new URL(config.backendUrl);
  if (!['http:', 'https:'].includes(target.protocol) || target.username || target.password || target.search || target.hash) throw new Error('BACKEND_URL inválida');
  if (config.requireLogin && (!config.username || !config.password || !config.apiKey)) throw new Error('Configura DEMO_ACCESS_USER, DEMO_ACCESS_PASSWORD y BACKEND_API_KEY');
  const expected = 'Basic ' + Buffer.from((config.username ?? '') + ':' + (config.password ?? '')).toString('base64');
  const digest = (value: string) => createHash('sha256').update(value).digest();
  return async function gateway(req: IncomingMessage, res: ServerResponse): Promise<boolean> {
    const send = (status: number, detail: string) => { res.writeHead(status, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' }); res.end(JSON.stringify({ detail })); };
    // Guard the whole demo, including the global account history.
    if ((config.requireLogin || config.password) && !timingSafeEqual(digest(req.headers.authorization ?? ''), digest(expected))) {
      res.setHeader('WWW-Authenticate', 'Basic realm="ANCLA demo", charset="UTF-8"');
      send(401, 'Acceso restringido a la demo'); return true;
    }
    const url = new URL(req.url ?? '/', 'http://local');
    if (!url.pathname.startsWith('/api/')) return false;
    const path = url.pathname.slice(4);
    const allowed = req.method === 'GET'
      ? /^\/(dashboard\/metrics|demo-profiles|decisions\/recent|decisions\/[a-zA-Z0-9_-]+)$/.test(path)
      : req.method === 'POST' && /^\/(purchase-attempts|demo-profiles\/[a-zA-Z0-9_-]+\/purchase-attempts|evaluations\/run|decisions\/[a-zA-Z0-9_-]+\/(complete|abandon))$/.test(path);
    if (!allowed) { send(404, 'Ruta no disponible'); return true; }
    if (req.method === 'POST') {
      const origin = req.headers.origin;
      let wrongOrigin: boolean;
      try { wrongOrigin = !!origin && new URL(origin).host !== req.headers.host; } catch { wrongOrigin = true; }
      if (wrongOrigin || req.headers['sec-fetch-site'] === 'cross-site' || !req.headers['content-type']?.startsWith('application/json')) {
        send(403, 'Origen o tipo de contenido no permitido'); return true;
      }
    }
    try {
      const chunks: Buffer[] = []; let size = 0;
      for await (const chunk of req) {
        size += chunk.length;
        if (size > 16384) { send(413, 'Solicitud demasiado grande'); return true; }
        chunks.push(Buffer.from(chunk));
      }
      const response = await fetch(target.origin + target.pathname.replace(/\/$/, '') + path + url.search, {
        method: req.method,
        headers: { 'Content-Type': 'application/json', ...(config.apiKey ? { 'X-API-Key': config.apiKey } : {}) },
        body: req.method === 'POST' && size ? Buffer.concat(chunks) : undefined,
        redirect: 'error', signal: AbortSignal.timeout(120000),
      });
      const body = await response.text();
      if (!response.headers.get('content-type')?.includes('application/json')) { send(502, 'El backend no devolvió JSON'); return true; }
      res.writeHead(response.status, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' }); res.end(body);
    } catch {
      send(502, 'No se pudo confirmar la respuesta del backend. Consulta el historial antes de repetir una operación.');
    }
    return true;
  };
}
