// The page's state, reactive: the year on show with its groups and what-ifs
// the server sent (sim), the chosen what-ifs, the dragged dots (edits) and
// the rerun on show (result); the view (kept in the URL with the year); and
// the run in hand. The pure parts are state.ts.
import { SvelteMap } from 'svelte/reactivity';
import { type Edits, type SimulacraApi, SimError, type SliceEdit } from './api';
import { ELECTION_YEARS } from './geo';
import type { RunResult, RunStatus, Voter } from './schemas';
import { addEdit, electionFor, isDirty, type Server, type ShownRun, type Sim, toggled, urlForYear, type View } from './state';

/** The run on show while it works. `id` is null until the server has started it. */
export interface ActiveRun {
  readonly id: string | null;
  readonly year: number;
  /** States counted so far, of `total`. */
  readonly done: number;
  readonly total: number;
  /** The typed words, trimmed. */
  readonly text: string;
  /** The chosen what-ifs' labels. */
  readonly labels: readonly string[];
}

export interface PageStateOptions {
  readonly api: SimulacraApi;
  readonly year: number;
  /** Puts a URL in the address bar without navigating. */
  readonly replaceUrl?: (url: string) => void;
  /** The page's address now. */
  readonly href?: () => string;
  readonly sleep?: (ms: number) => Promise<void>;
}

/** Poll a run this often, ms. */
const POLL_MS = 300;
const wait = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms));
const messageOf = (err: unknown, fallback: string) => (err instanceof Error && err.message) || fallback;

export class PageState {
  readonly api: SimulacraApi;
  year = $state(1789);
  view = $state<View>('history');
  server = $state<Server>('connecting');
  /** Why the year's groups didn't load. */
  simFailed = $state<string | null>(null);
  simLoading = $state(false);
  /** The year's groups and what-ifs. */
  sim = $state<Sim | null>(null);
  chosen = $state<readonly string[]>([]);
  /** Dots dragged by hand: each group's change in its fractions, summed over drags. */
  edits = $state<Edits | undefined>(undefined);
  /** The rerun on show. */
  result = $state<ShownRun | null>(null);
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
  readonly whatIfs = $derived(this.sim?.whatIfs ?? []);
  readonly selected = $derived(this.chosen);
  /** The rerun on show: the year's result in the Rerun view. */
  readonly rerun = $derived(this.view === 'whatif' ? this.result : null);
  readonly showing = $derived<'history' | 'whatif'>(this.rerun ? 'whatif' : 'history');
  readonly light = $derived(this.view !== 'whatif');
  readonly running = $derived(!!this.run && this.run.year === this.year);
  readonly canRun = $derived(this.server === 'online' && !!this.sim && this.whatIfs.length > 0 && !this.running);
  readonly canEdit = $derived(this.server === 'online' && !!this.sim && !this.running && !this.election.unopposed);
  readonly dirty = $derived(isDirty(this.result, this.selected, this.typed, this.edits));
  readonly voterKey = $derived(this.openSlice ? `${this.year}|${this.openSlice}|${this.rerun?.runId ?? ''}` : null);
  readonly voter = $derived(this.voterKey ? (this.voters.get(this.voterKey) ?? null) : null);

  readonly #replaceUrl: ((url: string) => void) | undefined;
  readonly #href: () => string;
  readonly #sleep: (ms: number) => Promise<void>;
  /** Bumped by each start and stop: a run whose token is stale is dropped. */
  #token = 0;

  constructor(o: PageStateOptions) {
    this.api = o.api;
    this.year = o.year;
    this.#replaceUrl = o.replaceUrl;
    this.#href = o.href ?? (() => location.href);
    this.#sleep = o.sleep ?? wait;
  }

  // ── Loading the year's groups and what-ifs ──
  async loadSim(y: number): Promise<void> {
    this.simFailed = null;
    this.simLoading = true;
    try {
      const value = await this.api.election(y);
      if (y !== this.year) return;
      this.sim = { slices: value.slices, whatIfs: value.whatIfs };
      this.server = 'online';
    } catch (err) {
      if (y !== this.year) return;
      const reason = err instanceof SimError ? err.reason : 'failed';
      if (reason === 'unsupported' || reason === 'offline' || reason === 'auth') this.server = reason;
      else if (this.server === 'connecting') this.server = 'offline';
      this.simFailed = messageOf(err, 'Couldn’t load this election’s voters.');
    } finally {
      this.simLoading = false;
    }
  }

  retry(): void {
    this.server = 'connecting';
    this.sim = null;
    void this.loadSim(this.year);
  }

  setYear(y: number): void {
    if (!ELECTION_YEARS.includes(y) || y === this.year) return;
    this.stop();
    this.year = y;
    // A new year starts fresh: its groups load, with nothing chosen or rerun.
    this.sim = null;
    this.chosen = [];
    this.edits = undefined;
    this.result = null;
    this.openSlice = null;
    this.typed = '';
    this.lastToggled = null;
    this.runError = null;
    this.view = 'history';
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
    this.chosen = toggled(this.chosen, key);
    this.lastToggled = this.chosen.includes(key) ? key : null;
    this.runError = null;
  }

  rerunNow(): void {
    if (!this.canRun) return;
    void this.startRerun();
  }

  /** A drag on a group's dots: added to the edits, then rerun at once. */
  editSlice(key: string, d: SliceEdit): void {
    if (!this.canEdit) return;
    this.edits = addEdit(this.edits, key, d);
    void this.startRerun();
  }

  async startRerun(): Promise<void> {
    this.stop();
    const token = this.#token;
    const y = this.year;
    const keys = [...this.chosen];
    const labels = keys.flatMap((k) => this.whatIfs.find((w) => w.key === k)?.label ?? []);
    const text = this.typed.trim();
    this.runError = null;
    this.openSlice = null;
    this.run = { id: null, year: y, done: 0, total: this.election.states.length, text, labels };
    let id: string;
    try {
      ({ id } = await this.api.startRun(y, { whatIfs: keys, text, edits: this.edits ?? {} }));
    } catch (err) {
      if (token !== this.#token) return;
      this.run = null;
      this.runError = messageOf(err, 'The rerun didn’t start.');
      return;
    }
    if (token !== this.#token || !this.run) return;
    this.run = { ...this.run, id };
    for (;;) {
      await this.#sleep(POLL_MS);
      if (token !== this.#token) return;
      let status: RunStatus;
      try {
        status = await this.api.run(id);
      } catch (err) {
        if (token !== this.#token) return;
        this.run = null;
        this.runError = messageOf(err, 'Lost track of the rerun.');
        return;
      }
      if (token !== this.#token || !this.run) return;
      switch (status.status) {
        case 'running':
          this.run = { ...this.run, done: status.done, total: status.total };
          break;
        case 'done':
          this.#finish(id, status.result, keys, text);
          return;
        case 'failed':
          this.run = null;
          this.runError = status.error || 'The rerun failed.';
          return;
        default:
          status satisfies never;
      }
    }
  }

  /** Stops the run on show, telling the server. */
  stop(): void {
    const r = this.run;
    this.#token += 1;
    this.run = null;
    if (r?.id) void this.api.stopRun(r.id).catch(() => undefined);
  }

  #finish(id: string, result: RunResult, keys: readonly string[], text: string): void {
    this.result = { ...result, runId: id, keys, text, ran: keys };
    this.run = null;
    this.typed = '';
    this.lastToggled = null;
    this.view = 'whatif';
  }

  reset(): void {
    this.chosen = [];
    this.result = null;
    this.edits = undefined;
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
    const got = (v: Voter | null) => {
      this.voters.set(key, v);
      if (this.voterLoading === key) this.voterLoading = null;
    };
    void this.api.voter(this.year, slice, this.rerun?.runId ?? null).then(got, () => got(null));
  }

  /** Stops the run on show (the page is going away). */
  dispose(): void {
    this.#token += 1;
    this.run = null;
  }
}
