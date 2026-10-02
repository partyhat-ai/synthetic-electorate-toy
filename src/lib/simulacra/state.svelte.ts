// The page's state, reactive: per year, the groups and what-ifs the server
// sent (sims), the chosen what-ifs, the dragged dots (edits) and the rerun on
// show (results); the year and view (kept in the URL); and the run in hand.
// The pure parts are state.ts; reruns are runs.ts.
import { SvelteMap } from 'svelte/reactivity';
import type { Edits, SimulacraApi, SliceEdit } from './api';
import { ELECTION_YEARS } from './geo';
import { traceOf } from './narrator';
import { type ActiveRun, createRunner, type Finished, type Runner } from './runs';
import type { Voter } from './schemas';
import {
  addEdit,
  askOf,
  electionFor,
  isDirty,
  type Server,
  type ShownRun,
  type Sim,
  toggled,
  urlForYear,
  type View,
} from './state';

export interface PageStateOptions {
  readonly api: SimulacraApi;
  readonly year: number;
  /** Puts a URL in the address bar without navigating. */
  readonly replaceUrl?: (url: string) => void;
  /** The page's address now. */
  readonly href?: () => string;
  /** A rerun finished for the year on show: its steps start coming out. */
  readonly onFresh?: (steps: number) => void;
  readonly sleep?: (ms: number) => Promise<void>;
  readonly now?: () => number;
}

export class PageState {
  readonly api: SimulacraApi;
  year = $state(1789);
  view = $state<View>('history');
  server = $state<Server>('connecting');
  /** Why the year's groups didn't load. */
  simFailed = $state<string | null>(null);
  readonly sims = new SvelteMap<number, Sim>();
  readonly chosen = new SvelteMap<number, readonly string[]>();
  /** Dots dragged by hand, per year: each group's change in its fractions, summed over drags. */
  readonly edits = new SvelteMap<number, Edits>();
  readonly results = new SvelteMap<number, ShownRun>();
  /** Bumped by Reset, so the rows drop any drag in hand. */
  editEpoch = $state(0);
  typed = $state('');
  lastToggled = $state<string | null>(null);
  run = $state<ActiveRun | null>(null);
  runError = $state<string | null>(null);
  openSlice = $state<string | null>(null);
  readonly voters = new SvelteMap<string, Voter | null>();
  voterLoading = $state<string | null>(null);
  /** The URL is written once the router is ready. */
  urlReady = false;

  readonly election = $derived(electionFor(this.year));
  readonly sim = $derived(this.sims.get(this.year) ?? null);
  readonly whatIfs = $derived(this.sim?.whatIfs ?? []);
  readonly selected = $derived(this.chosen.get(this.year) ?? []);
  readonly result = $derived(this.results.get(this.year) ?? null);
  /** The rerun on show: the year's result in the Rerun view. */
  readonly rerun = $derived(this.view === 'whatif' ? this.result : null);
  readonly showing = $derived<'history' | 'whatif'>(this.rerun ? 'whatif' : 'history');
  readonly light = $derived(this.view !== 'whatif');
  readonly running = $derived(!!this.run && this.run.year === this.year);
  readonly canRun = $derived(this.server === 'online' && !!this.sim && this.whatIfs.length > 0 && !this.running);
  readonly canEdit = $derived(this.server === 'online' && !!this.sim && !this.running && !this.election.unopposed);
  readonly dirty = $derived(isDirty(this.result, this.selected, this.typed, this.edits.get(this.year)));
  readonly voterKey = $derived(this.openSlice ? `${this.year}|${this.openSlice}|${this.rerun?.runId ?? ''}` : null);
  readonly voter = $derived(this.voterKey ? (this.voters.get(this.voterKey) ?? null) : null);

  readonly #runner: Runner;
  readonly #replaceUrl: ((url: string) => void) | undefined;
  readonly #href: () => string;
  readonly #onFresh: ((steps: number) => void) | undefined;

  constructor(o: PageStateOptions) {
    this.api = o.api;
    this.year = o.year;
    this.#replaceUrl = o.replaceUrl;
    this.#href = o.href ?? (() => location.href);
    this.#onFresh = o.onFresh;
    this.#runner = createRunner({
      api: o.api,
      ...(o.sleep ? { sleep: o.sleep } : {}),
      ...(o.now ? { now: o.now } : {}),
      getRun: () => this.run,
      setRun: (r) => {
        this.run = r;
      },
      reloadSim: async (y) => {
        this.sims.delete(y);
        await this.loadSim(y);
      },
      whatIfsOf: (y) => this.sims.get(y)?.whatIfs ?? [],
      finished: (f) => this.#finish(f),
      failed: (message) => {
        this.runError = message;
      },
    });
  }

  /** What a rerun of year `y` would send. */
  askOf(y: number, keys: readonly string[], text: string): string {
    return askOf(keys, text, this.edits.get(y));
  }

  // ── Loading an election's groups and what-ifs ──
  async loadSim(y: number): Promise<void> {
    if (this.sims.has(y)) return;
    this.simFailed = null;
    const out = await this.api.election(y);
    switch (out.kind) {
      case 'ok':
        this.sims.set(y, { slices: out.value.slices, whatIfs: out.value.whatIfs });
        this.server = 'online';
        return;
      case 'unsupported':
        this.server = 'unsupported';
        break;
      case 'error':
        if (out.reason === 'offline' || out.reason === 'auth') this.server = out.reason;
        else if (this.server === 'connecting') this.server = 'offline';
        break;
      case 'indeterminate':
        if (this.server === 'connecting') this.server = 'offline';
        break;
      default:
        out satisfies never;
    }
    this.simFailed = out.message || 'Couldn’t load this election’s voters.';
  }

  retry(): void {
    this.server = 'connecting';
    this.sims.delete(this.year);
    void this.loadSim(this.year);
  }

  setYear(y: number): void {
    if (!ELECTION_YEARS.includes(y) || y === this.year) return;
    this.year = y;
    this.openSlice = null;
    this.typed = '';
    this.lastToggled = null;
    this.runError = null;
    this.view = this.results.has(y) ? 'whatif' : 'history';
    this.syncUrl();
  }

  step(d: number): void {
    const i = ELECTION_YEARS.indexOf(this.year);
    const y = ELECTION_YEARS[Math.max(0, Math.min(ELECTION_YEARS.length - 1, i + d))];
    if (y !== undefined) this.setYear(y);
  }

  syncUrl(): void {
    if (!this.urlReady || !this.#replaceUrl) return;
    const url = urlForYear(this.#href(), this.year);
    if (url) this.#replaceUrl(url);
  }

  // ── What-ifs and reruns ──
  toggle(key: string): void {
    const next = toggled(this.chosen.get(this.year) ?? [], key);
    this.chosen.set(this.year, next);
    this.lastToggled = next.includes(key) ? key : null;
    this.runError = null;
  }

  rerunNow(): void {
    if (!this.canRun) return;
    // Nothing changed since this year's last rerun: show it again rather than
    // running (and walking the robot) for the same answer.
    const r = this.results.get(this.year);
    if (r && !this.typed.trim() && this.askOf(this.year, this.chosen.get(this.year) ?? [], '') === r.ask) {
      this.view = 'whatif';
      this.lastToggled = null;
      return;
    }
    void this.startRerun();
  }

  /** A drag on a group's dots: added to the year's edits, then rerun at once. */
  editSlice(key: string, d: SliceEdit): void {
    if (!this.canEdit) return;
    this.edits.set(this.year, addEdit(this.edits.get(this.year), key, d));
    void this.startRerun();
  }

  startRerun(): Promise<void> {
    const y = this.year;
    const keys = [...(this.chosen.get(y) ?? [])];
    const labels = keys.flatMap((k) => this.whatIfs.find((w) => w.key === k)?.label ?? []);
    const text = this.typed.trim();
    this.runError = null;
    this.openSlice = null;
    const edits = this.edits.get(y) ?? {};
    return this.#runner.start({ year: y, keys, text, edits, total: this.election.states.length, labels });
  }

  stop(): void {
    this.#runner.stop();
  }

  #finish(f: Finished): void {
    const { year: y, id, result, keys, text, applied } = f;
    // ask: the page's state right after this run, so pressing Rerun again
    // with nothing changed just shows this.
    const trace = traceOf(result, text, keys, y);
    this.results.set(y, { ...result, runId: id, keys, text, trace, ask: this.askOf(y, applied, ''), ran: applied });
    if (y === this.year) this.#onFresh?.(trace.length);
    // What was applied, typed words included, shows as the chosen what-ifs.
    this.chosen.set(y, applied);
    this.run = null;
    if (y === this.year) {
      this.typed = '';
      this.lastToggled = null;
      this.view = 'whatif';
    }
  }

  reset(): void {
    this.chosen.set(this.year, []);
    this.results.delete(this.year);
    this.edits.delete(this.year);
    this.editEpoch += 1;
    this.typed = '';
    this.lastToggled = null;
    this.runError = null;
    this.view = 'history';
  }

  // ── One person from a group ──
  toggleSlice(key: string): void {
    this.openSlice = this.openSlice === key ? null : key;
    this.lastToggled = null;
  }

  /** Fetches the open group's person, once per year, group and rerun. */
  fetchVoter(): void {
    const key = this.voterKey;
    const slice = this.openSlice;
    if (!key || !slice || this.voters.has(key) || this.voterLoading === key) return;
    this.voterLoading = key;
    void this.api.voter(this.year, slice, this.rerun?.runId ?? null).then((out) => {
      this.voters.set(key, out.kind === 'ok' ? out.value : null);
      if (this.voterLoading === key) this.voterLoading = null;
    });
  }

  /** Stops the run on show (the page is going away). */
  dispose(): void {
    this.run = null;
  }
}
