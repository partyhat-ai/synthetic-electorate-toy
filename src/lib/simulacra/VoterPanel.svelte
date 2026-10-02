<script lang="ts">
  // A few of the people in the electorate for one year: who they are, and
  // whether they could vote, voted, stayed home or were turned away — the
  // dot cloud's dots, one at a time.
  interface Person {
    readonly name: string;
    readonly line: string;
    readonly status: 'voted' | 'home' | 'away' | 'barred';
    readonly why: string;
  }
  let { year, people }: { year: number; people: readonly Person[] } = $props();

  const STATUS: Readonly<Record<Person['status'], string>> = {
    voted: 'Voted',
    home: 'Stayed home',
    away: 'Turned away',
    barred: 'Couldn’t vote',
  };
</script>

<section class="voters" aria-label="Voters in {year}">
  <h3>Meet the voters of {year}</h3>
  <ul>
    {#each people as p (p.name)}
      <li>
        <p class="who"><b>{p.name}</b> {p.line}</p>
        <p class="what"><span class="status {p.status}">{STATUS[p.status]}</span> {p.why}</p>
      </li>
    {/each}
  </ul>
</section>

<style>
  h3 { margin: 0 0 10px; font-size: 14px; }
  ul { display: flex; flex-direction: column; gap: 10px; margin: 0; padding: 0; list-style: none; }
  li { padding: 10px 12px; border-radius: 10px; background: #fff; box-shadow: 0 0 0 0.5px rgba(0, 0, 0, 0.12); }
  p { margin: 0; font-size: 13px; line-height: 1.45; }
  .who { color: rgba(0, 0, 0, 0.6); }
  .who b { color: #000; }
  .what { margin-top: 4px; }
  .status { display: inline-block; margin-right: 6px; padding: 0 7px; border-radius: 999px; font-size: 11px; font-weight: 600; }
  .status.voted { background: #2a78d6; color: #fff; }
  .status.home { box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.4); }
  .status.away { background: #eb6834; color: #fff; }
  .status.barred { background: rgba(0, 0, 0, 0.12); }
</style>
