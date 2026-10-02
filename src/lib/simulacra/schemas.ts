// The simulation server's answers, parsed once where they enter the page
// (api.ts). The schemas are the server's own (serve/contract.ts, one
// definition for both sides), so the page's types can't drift from what the
// server sends; every type the page uses for them derives from these.
export * from '../../../serve/contract';
