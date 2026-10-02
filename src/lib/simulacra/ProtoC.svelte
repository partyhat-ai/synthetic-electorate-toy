<script lang="ts">
  // Prototype C, the electorate: for any year, who could vote and did, who
  // stayed home, who was turned away and who couldn't vote at all — as a
  // cloud of dots, as one bar, and as a few of the people in it. The numbers
  // are rough sketches of the franchise's history, made up for the
  // prototype; they share nothing with prototype A.
  import DotCloud from './DotCloud.svelte';
  import { ELECTION_YEARS } from './geo';
  import StackBar from './StackBar.svelte';
  import VoterPanel from './VoterPanel.svelte';

  let year = $state(1920);

  // Adults, roughly: about 2% more each year.
  const adultsIn = (y: number) => 1.9e6 * Math.exp(0.0209 * (y - 1789));
  // The share of adults who could vote, with the franchise's steps in it.
  function couldVote(y: number): number {
    let s = y < 1828 ? 0.3 : 0.4;
    if (y >= 1870) s += 0.04;
    if (y >= 1890 && y < 1965) s -= 0.03;
    if (y >= 1920) s = s * 2 - 0.06;
    if (y >= 1968) s += 0.04;
    if (y >= 1972) s += 0.06;
    return Math.min(0.94, s);
  }
  // Turned away at the polls, out of all adults: the Jim Crow years stand out.
  const awayIn = (y: number) => (y >= 1890 && y < 1965 ? 0.05 : 0.004);
  // Turnout of those who could vote.
  const turnoutIn = (y: number) => (y < 1828 ? 0.25 : 0.55 + 0.25 * Math.sin((y - 1828) / 40));

  const electorate = $derived.by(() => {
    const could = couldVote(year);
    const away = Math.min(awayIn(year), could);
    const voted = (could - away) * turnoutIn(year);
    return { voted, home: could - away - voted, away, barred: 1 - could };
  });
  const parts = $derived([
    { key: 'voted', label: 'Voted', share: electorate.voted, color: '#2a78d6' },
    { key: 'home', label: 'Stayed home', share: electorate.home, color: '#9a9a9a' },
    { key: 'away', label: 'Turned away', share: electorate.away, color: '#eb6834' },
    { key: 'barred', label: 'Couldn’t vote', share: electorate.barred, color: '#cfcfcf' },
  ]);

  // A few people per era: [from, name, who, status, why].
  type Status = 'voted' | 'home' | 'away' | 'barred';
  const PEOPLE: readonly (readonly [number, string, string, Status, string])[] = [
    [1789, 'Josiah Hale', '38, farmer, North Carolina', 'voted', 'He owns his land, so he can vote for the legislature that picks the electors.'],
    [1789, 'Patrick Doyle', '27, dockworker, New York City', 'barred', 'He pays too little rent to meet the property test.'],
    [1789, 'Hannah', '30, enslaved cook, Virginia', 'barred', 'Enslaved people have no vote; Virginia gets extra electors for counting her.'],
    [1870, 'Jacob Wells', '30, sharecropper, Mississippi', 'voted', 'The 15th Amendment is new, and federal troops still guard the polls.'],
    [1890, 'Henry Toussaint', '48, dockworker, New Orleans', 'away', 'The polling place moved three times and nobody told him where.'],
    [1890, 'Ida Lindgren', '32, stenographer, Minneapolis', 'barred', 'Women can’t vote for president in Minnesota.'],
    [1920, 'Ruth Robinson', '36, farm wife, upstate New York', 'voted', 'The 19th Amendment passed in August; this is her first presidential vote.'],
    [1920, 'Albert Mayes', '50, farmer, Alabama', 'away', 'The poll tax adds up for every year he missed.'],
    [1972, 'Kevin Tran', '19, line cook, San Jose', 'home', 'The 26th Amendment lets him vote; he forgets to register.'],
    [2000, 'Marcus Webb', '41, roofer, Tallahassee', 'barred', 'He served his sentence years ago; Florida still bars him.'],
    [2000, 'Ana Morales', '34, dental hygienist, San Antonio', 'voted', 'Her parents took her to the polls every time.'],
  ];
  const people = $derived(
    PEOPLE.filter(([from]) => from <= year)
      .slice(-3)
      .map(([, name, line, status, why]) => ({ name, line, status, why })),
  );
</script>

<div class="proto-c">
  <label class="year">
    <span>{year}</span>
    <input
      type="range"
      min="0"
      max={ELECTION_YEARS.length - 1}
      value={ELECTION_YEARS.indexOf(year)}
      aria-label="Election"
      oninput={(e) => {
        const y = ELECTION_YEARS[Number(e.currentTarget.value)];
        if (y !== undefined) year = y;
      }}
    />
  </label>
  <DotCloud {year} {electorate} adults={adultsIn(year)} />
  <StackBar {parts} />
  <VoterPanel {year} {people} />
</div>

<style>
  .proto-c { display: flex; flex-direction: column; gap: 20px; }
  .year { display: flex; align-items: center; gap: 14px; }
  .year span { width: 3.5em; font-size: 28px; font-weight: 700; font-variant-numeric: tabular-nums; }
  .year input { flex: 1; accent-color: #111; }
</style>
