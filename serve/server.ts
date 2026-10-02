// The production entry (the API container's CMD, bundled to dist/server.mjs).
// `pnpm serve` (index.ts) stays the local entry. This adds what a host behind
// a load balancer needs and the local server doesn't:
//   - GET /healthz: 200 "ok", no dependencies, registered before the app so a
//     broken bundle or router can't fail the ALB health check;
//   - trust proxy TRUST_PROXY_HOPS (default 2: the request comes through
//     Vercel's proxy, then the ALB), so req.ip is the visitor's address for
//     the per-IP rate limits. A request sent to the ALB directly can forge
//     X-Forwarded-For; the dollar caps hang on access keys, not IPs;
//   - SIGTERM: stop accepting, let in-flight requests finish, exit. A running
//     worker is killed with the container; its queue item stays un-done and is
//     retried by the next worker.
import express from 'express';
import { createApp } from './app';

const port = Number(process.env.PORT || 8080);
const app = express();
app.disable('x-powered-by');
app.set('trust proxy', Number(process.env.TRUST_PROXY_HOPS || 2));
app.get('/healthz', (_req, res) => {
  res.set('Cache-Control', 'no-store').type('text/plain').send('ok');
});
app.use(createApp());

const server = app.listen(port, () => {
  console.log(`simulacra api on :${port} (bundles from ${process.env.SIMULACRA_BUNDLES || 'serve/bundles'})`);
});

function shutdown(signal: string): void {
  console.log(`simulacra: ${signal}, closing`);
  server.close(() => process.exit(0));
  server.closeIdleConnections();
  // ECS's stopTimeout is 30s; leave room to exit on our own terms.
  setTimeout(() => process.exit(0), 20_000).unref();
}
process.on('SIGTERM', () => shutdown('SIGTERM'));
process.on('SIGINT', () => shutdown('SIGINT'));
