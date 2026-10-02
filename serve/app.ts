// The server: /api/simulacra plus the static SvelteKit build, with an SPA
// fallback to build/index.html for any other GET.
import { existsSync } from 'node:fs';
import path from 'node:path';
import express, { type Express } from 'express';
import { createSimulacraRouter, optionsFromEnv, type SimulacraOptions } from './simulacra';

export interface AppOptions {
  simulacra: SimulacraOptions;
  /** The static build folder (`pnpm build`); not served when it has no index.html. */
  build: string;
}

export const defaultAppOptions = (): AppOptions => ({
  simulacra: optionsFromEnv(),
  build: path.resolve(import.meta.dirname, '..', 'build')
});

export function createApp(opts: AppOptions = defaultAppOptions()): Express {
  const app = express();
  app.disable('x-powered-by');
  app.use('/api/simulacra', createSimulacraRouter(opts.simulacra));
  const index = path.join(opts.build, 'index.html');
  if (existsSync(index)) {
    app.use(express.static(opts.build));
    app.get('/{*path}', (_req, res) => res.sendFile(index));
  }
  return app;
}
