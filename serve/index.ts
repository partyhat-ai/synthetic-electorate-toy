// `pnpm serve`: the page and its API on PORT (default 8787).
import { createApp } from './app';

const port = Number(process.env.PORT || 8787);
createApp().listen(port, () => {
  console.log(`simulacra on http://localhost:${port} (bundles from ${process.env.SIMULACRA_BUNDLES || 'serve/bundles'})`);
});
