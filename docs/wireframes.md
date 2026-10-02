# Wireframes: three ways in

Three concepts for the page, sketched before any of them is built. ASCII
only, so nobody would fall for the pixels. Each answers the same question —
what would the country have done with one thing changed? — from a different
door.

## (a) Time map

The whole timeline on one map. Scrub through 60 elections; each state is a
tile filled with the model's call and ringed with what actually happened,
so a miss is a tile that disagrees with itself.

```
 SIMULACRA AMERICANA                        [Map] [Accuracy]   [ search ] [⚗]
 ┌────────────────────────────────────────────────────┐ ┌───────────────────┐
 │  AK                                       ME       │ │ Ohio, 1896        │
 │               WI          VT NH                    │ │                   │
 │  WA ID MT ND MN IL MI    NY MA                     │ │ actual   McKinley │
 │  OR NV WY SD IA IN OH PA NJ CT RI                  │ │ model    McKinley │
 │  CA UT CO NE MO KY WV VA MD DE                     │ │ margin   +x.x     │
 │     AZ NM KS AR TN NC SC DC                        │ │                   │
 │           OK LA MS AL GA                           │ │ missed n of 26    │
 │  HI       TX          FL        ▣ fill = call      │ │                   │
 │                                 □ ring = actual    │ └───────────────────┘
 │                                 ✕ = miss           │
 └────────────────────────────────────────────────────┘
 ▶  1789 ──┼──┼──┼──┼──┼──●──┼──┼──┼──┼──┼──┼──┼── 2024        1896
            15th   Miss. Plan     19th       VRA  26th
```

Risk: it reads as a forecast scoreboard. The interesting part (who could
vote) is invisible.

## (b) Meet five, call it

One election, five voters. Read who they are and what they read that year,
guess how each voted, then see what the simulation says they did.

```
 1896 · "gold" vs "silver"                                  [ another year ]
 ┌──────────────┬──────────────┬──────────────┬──────────────┬─────────────┐
 │ ○ Silas      │ ○ Nora       │ ○ Henry      │ ○ Ida        │ ○ Jacob     │
 │ wheat farmer │ laundress    │ dockworker   │ stenographer │ sharecropper│
 │ Kansas, 44   │ Chicago, 41  │ New Orleans  │ Minneapolis  │ Mississippi │
 │              │              │              │              │             │
 │ reads: the   │ reads: the   │ reads: —     │ reads: the   │ reads: —    │
 │ Farmers'     │ Tribune      │              │ Journal      │             │
 │ Alliance     │              │              │              │             │
 │              │              │              │              │             │
 │ [Bryan]      │ can't vote   │ turned away  │ can't vote   │ turned away │
 │ [McKinley]   │              │              │              │             │
 └──────────────┴──────────────┴──────────────┴──────────────┴─────────────┘
                     you called n of 2 · the model called n of 2
```

Risk: five people is an anecdote, and three of these five never vote. That
is the point, but the game doesn't survive it.

## (c) The electorate

Everyone, as dots. Who voted sits in the middle; around them, who stayed
home, who was turned away at the polls, and out at the edge, who couldn't
vote at all. Change the year and watch the middle grow.

```
 1920   ├──────────────────────────────────●──────────────────────┤
                                      19th Amendment: sex can no longer bar voting

          · · · · · ·                      voted ........ xx.xM  ●
        · · ○ ○ ○ ○ · ·                    stayed home .. xx.xM  ○
      · ○ ○ ● ● ● ● ○ ○ ·                  turned away ..  x.xM  ◆
      · ○ ● ● ● ● ● ● ○ ·                  couldn't vote  x.xM  ·
      · ○ ● ● ● ● ● ● ○ ◆
        · ○ ○ ● ● ○ ○ ◆               [██████████|██████████|█|███]
          · · ◆ ◆ ◆ ·                    voted     home      away barred

 Meet the voters of 1920
   Ruth Robinson, 36, farm wife, upstate NY ........ voted (first time)
   Albert Mayes, 50, farmer, Alabama ............... turned away (poll tax)
```

Risk: no election in it. Who won, and whether it would change, is a second
screen.

## What we'll prototype

(a) and (c), behind `?proto=a` and `?proto=c`, time-boxed and sharing no
code. (b) needs the simulated voters to exist first.
