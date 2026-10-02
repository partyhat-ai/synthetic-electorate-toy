import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vitest/config';

// In development the page calls /api/simulacra on the local server (pnpm serve).
export default defineConfig({
  plugins: [sveltekit()],
  server: { proxy: { '/api': 'http://localhost:8787' } },
  test: { include: ['src/**/*.test.ts', 'serve/**/*.test.ts'] }
});
