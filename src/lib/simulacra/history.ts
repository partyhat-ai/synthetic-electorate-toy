// Every presidential election from 1789 to 2024 as it happened: who ran, who
// won, the electoral and popular vote, and which party carried each state.
// This is the page's starting point, the truth every rerun is measured
// against, so it ships with the page rather than coming from the simulation
// server, and the page can show who won before anything else answers.
//
// Sources: results and notes, the standard record (the National Archives'
// Electoral College tables, each election's Wikipedia article); each state's
// winner, Wikipedia's "List of United States presidential election results by
// state"; electoral votes by state, the House apportionments plus two (D.C.
// three). Portraits: Wikimedia Commons, the lead image of each candidate's
// Wikipedia article.
import { STATES } from './geo';
import type { Family } from './palette';

const PORTRAITS = 'https://upload.wikimedia.org/wikipedia/commons/thumb/';

// Party codes (the by-state table's) → label and the palette family
// (palette.ts candidateHues) that sets the colour.
const PARTIES = {
  GW: ['No party', null],
  F: ['Federalist', 'federalist'],
  DR: ['Democratic-Republican', 'democratic-republican'],
  DR2: ['Democratic-Republican', 'democratic-republican'],
  Adams: ['Democratic-Republican', 'democratic-republican'],
  Jackson: ['Democratic-Republican', 'democratic-republican'],
  Crawford: ['Democratic-Republican', 'democratic-republican'],
  Clay: ['Democratic-Republican', 'democratic-republican'],
  D: ['Democratic', 'democratic'],
  NR: ['National Republican', 'national-republican'],
  W: ['Whig', 'whig'], W2: ['Whig', 'whig'], W3: ['Whig', 'whig'], W4: ['Whig', 'whig'],
  N: ['Nullifier', null],
  AM: ['Anti-Masonic', null],
  FS: ['Free Soil', null],
  KN: ['American', null],
  R: ['Republican', 'republican'],
  SD: ['Southern Democratic', 'democratic'],
  ND: ['Northern Democratic', 'democratic'],
  CU: ['Constitutional Union', null],
  LR: ['Liberal Republican', 'democratic'],
  PO: ['Populist', null],
  BM: ['Progressive', null],
  PR: ['Progressive', null],
  S: ['Socialist', null],
  SR: ['States’ Rights', null],
  PG: ['Progressive', null],
  I: ['Unpledged electors', null],
  AI: ['American Independent', null],
  IA: ['Independent', null],
  IP: ['Independent', null],
  RF: ['Reform', null],
  SP: ['Split', null],
} as const satisfies Record<string, readonly [string, Family | null]>;
type PartyCode = keyof typeof PARTIES;
const PARTY_BY_CODE: ReadonlyMap<string, readonly [string, Family | null]> = new Map(Object.entries(PARTIES));

// [full name, surname, portrait path under PORTRAITS].
const PEOPLE = {
  washington: ["George Washington", "Washington", "b/b6/Gilbert_Stuart_Williamstown_Portrait_of_George_Washington.jpg/330px-Gilbert_Stuart_Williamstown_Portrait_of_George_Washington.jpg"],
  adams: ["John Adams", "Adams", "7/75/John_Adams_Portrait.jpg/330px-John_Adams_Portrait.jpg"],
  jefferson: ["Thomas Jefferson", "Jefferson", "0/07/Official_Presidential_portrait_of_Thomas_Jefferson_%28by_Rembrandt_Peale%2C_1800%29.jpg/330px-Official_Presidential_portrait_of_Thomas_Jefferson_%28by_Rembrandt_Peale%2C_1800%29.jpg"],
  pinckney: ["Charles Cotesworth Pinckney", "Pinckney", "4/45/James_Earl_-_General_Charles_Cotesworth_Pinckney_-_Google_Art_Project.jpg/330px-James_Earl_-_General_Charles_Cotesworth_Pinckney_-_Google_Art_Project.jpg"],
  madison: ["James Madison", "Madison", "1/1d/James_Madison.jpg/330px-James_Madison.jpg"],
  clinton: ["DeWitt Clinton", "Clinton", "6/63/DeWitt_Clinton_by_Rembrandt_Peale.jpg/330px-DeWitt_Clinton_by_Rembrandt_Peale.jpg"],
  monroe: ["James Monroe", "Monroe", "5/5e/James_Monroe_White_House_portrait_1819_%28cropped%29%282%29.jpg/330px-James_Monroe_White_House_portrait_1819_%28cropped%29%282%29.jpg"],
  king: ["Rufus King", "King", "5/59/Gilbert_Stuart_-_Portrait_of_Rufus_King_%281819-1820%29_-_Google_Art_Project.jpg/330px-Gilbert_Stuart_-_Portrait_of_Rufus_King_%281819-1820%29_-_Google_Art_Project.jpg"],
  adams2: ["John Quincy Adams", "Adams", "3/3a/JQA_Photo_Crop_%28cropped%29.jpg/330px-JQA_Photo_Crop_%28cropped%29.jpg"],
  jackson: ["Andrew Jackson", "Jackson", "2/2a/Andrew_jackson_head_%28cropped%29.jpg/330px-Andrew_jackson_head_%28cropped%29.jpg"],
  clay: ["Henry Clay", "Clay", "6/67/Clay_1848.jpg/330px-Clay_1848.jpg"],
  vanburen: ["Martin Van Buren", "Van Buren", "7/72/Martin_Van_Buren_by_Mathew_Brady_c1855-58-%284%29.jpg/330px-Martin_Van_Buren_by_Mathew_Brady_c1855-58-%284%29.jpg"],
  harrison: ["William Henry Harrison", "Harrison", "2/2c/William_Henry_Harrison_crop.jpg/330px-William_Henry_Harrison_crop.jpg"],
  polk: ["James K. Polk", "Polk", "f/f3/James_K._Polk_restored_%283x4_cropped%29.jpg/330px-James_K._Polk_restored_%283x4_cropped%29.jpg"],
  taylor: ["Zachary Taylor", "Taylor", "3/35/Zachary_Taylor_restored_and_cropped_%283.5x4.5_cropped%29_%282%29.jpg/330px-Zachary_Taylor_restored_and_cropped_%283.5x4.5_cropped%29_%282%29.jpg"],
  cass: ["Lewis Cass", "Cass", "a/ae/Lewis_Cass_circa_1855.jpg/330px-Lewis_Cass_circa_1855.jpg"],
  pierce: ["Franklin Pierce", "Pierce", "7/74/Mathew_Brady_-_Franklin_Pierce_-_alternate_crop_%28cropped%29%282%29.jpg/330px-Mathew_Brady_-_Franklin_Pierce_-_alternate_crop_%28cropped%29%282%29.jpg"],
  scott: ["Winfield Scott", "Scott", "5/5f/Winfield_Scott_by_Fredricks%2C_1862_crop.jpg/330px-Winfield_Scott_by_Fredricks%2C_1862_crop.jpg"],
  buchanan: ["James Buchanan", "Buchanan", "2/21/James_Buchanan_%28cropped%29.jpg/330px-James_Buchanan_%28cropped%29.jpg"],
  frmont: ["John C. Frémont", "Frémont", "b/b3/John_Charles_Fremont_Oval.png/330px-John_Charles_Fremont_Oval.png"],
  lincoln: ["Abraham Lincoln", "Lincoln", "a/ab/Abraham_Lincoln_O-77_matte_collodion_print.jpg/330px-Abraham_Lincoln_O-77_matte_collodion_print.jpg"],
  breckinridge: ["John C. Breckinridge", "Breckinridge", "6/65/John_C._Breckinridge_1860_portrait_%283x4_cropped%29.jpg/330px-John_C._Breckinridge_1860_portrait_%283x4_cropped%29.jpg"],
  mcclellan: ["George B. McClellan", "McClellan", "8/86/George_B_McClellan_-_retouched%2C_cropped.jpg/330px-George_B_McClellan_-_retouched%2C_cropped.jpg"],
  grant: ["Ulysses S. Grant", "Grant", "9/98/Ulysses_S._Grant_1870-1880_%28cropped%29.jpg/330px-Ulysses_S._Grant_1870-1880_%28cropped%29.jpg"],
  seymour: ["Horatio Seymour", "Seymour", "6/6e/Horatio_Seymour_%28cropped%2C_retouched%29.jpg/330px-Horatio_Seymour_%28cropped%2C_retouched%29.jpg"],
  greeley: ["Horace Greeley", "Greeley", "1/11/Horace_Greeley_restored.jpg/330px-Horace_Greeley_restored.jpg"],
  hayes: ["Rutherford B. Hayes", "Hayes", "5/50/President_Rutherford_Hayes_1870_-_1880_Restored.jpg/330px-President_Rutherford_Hayes_1870_-_1880_Restored.jpg"],
  tilden: ["Samuel J. Tilden", "Tilden", "e/e8/Samuel_Tilden._Portrait_of_the_American_politician%2C_who_served_as_the_25th_Governor_of_New_York%2C_Samuel_Jones_Tilden_%281814-1886%29%2C_by_Jos%C3%A9_Mar%C3%ADa_Mora%2C_c._1870.jpg/330px-thumbnail.jpg"],
  garfield: ["James A. Garfield", "Garfield", "1/1f/James_Abram_Garfield%2C_photo_portrait_seated.jpg/330px-James_Abram_Garfield%2C_photo_portrait_seated.jpg"],
  hancock: ["Winfield Scott Hancock", "Hancock", "5/5b/Gen._Winfield_S._Hancock_-_NARA_-_529369_%28cropped%2C_retouched%29.jpg/330px-Gen._Winfield_S._Hancock_-_NARA_-_529369_%28cropped%2C_retouched%29.jpg"],
  cleveland: ["Grover Cleveland", "Cleveland", "3/36/StephenGroverCleveland.jpg/330px-StephenGroverCleveland.jpg"],
  blaine: ["James G. Blaine", "Blaine", "f/fb/James_G._Blaine_-_Brady-Handy.jpg/330px-James_G._Blaine_-_Brady-Handy.jpg"],
  harrison2: ["Benjamin Harrison", "Harrison", "4/49/Pach_Brothers_-_Benjamin_Harrison_%28cropped%29_%28cropped%29.jpg/330px-Pach_Brothers_-_Benjamin_Harrison_%28cropped%29_%28cropped%29.jpg"],
  mckinley: ["William McKinley", "McKinley", "3/30/McKinley_%28cropped%29.jpg/330px-McKinley_%28cropped%29.jpg"],
  bryan: ["William Jennings Bryan", "Bryan", "2/20/Portrait_of_Secretary_William_Jennings_Bryan_of_Nebraska%2C_1913.jpeg/330px-Portrait_of_Secretary_William_Jennings_Bryan_of_Nebraska%2C_1913.jpeg"],
  roosevelt: ["Theodore Roosevelt", "Roosevelt", "6/69/Theodore_Roosevelt_by_the_Pach_Bros_%284x5_cropped%29_%282%29.jpg/330px-Theodore_Roosevelt_by_the_Pach_Bros_%284x5_cropped%29_%282%29.jpg"],
  parker: ["Alton B. Parker", "Parker", "b/b4/Alton_Brooks_Parker_Portrait_%283x4_cropped%29.jpg/330px-Alton_Brooks_Parker_Portrait_%283x4_cropped%29.jpg"],
  taft: ["William Howard Taft", "Taft", "1/11/William_Howard_Taft_by_Pach_Brothers_%283x4_ropped%29_%28cropped%29.jpg/330px-William_Howard_Taft_by_Pach_Brothers_%283x4_ropped%29_%28cropped%29.jpg"],
  wilson: ["Woodrow Wilson", "Wilson", "9/96/President_Woodrow_Wilson_Harris_%26_Ewing_%283x4_cropped_b%29.jpg/330px-President_Woodrow_Wilson_Harris_%26_Ewing_%283x4_cropped_b%29.jpg"],
  hughes: ["Charles Evans Hughes", "Hughes", "e/ee/Charles_Evans_Hughes_cph.3b15401.jpg/330px-Charles_Evans_Hughes_cph.3b15401.jpg"],
  harding: ["Warren G. Harding", "Harding", "4/4e/Warren_G._Harding_1920s_portrait_%283x4_cropped%29.jpg/330px-Warren_G._Harding_1920s_portrait_%283x4_cropped%29.jpg"],
  cox: ["James M. Cox", "Cox", "5/57/James_M._Cox_Portrait_%283x4_cropped_b%29.jpg/330px-James_M._Cox_Portrait_%283x4_cropped_b%29.jpg"],
  coolidge: ["Calvin Coolidge", "Coolidge", "4/4c/President_Calvin_Coolidge%2C_1924_portrait_photograph_%283x4_cropped_2%29.jpeg/330px-President_Calvin_Coolidge%2C_1924_portrait_photograph_%283x4_cropped_2%29.jpeg"],
  davis: ["John W. Davis", "Davis", "c/c5/DAVIS%2C_JOHN_W._HONORABLE_LCCN2016862563_%28cropped%29.jpg/330px-DAVIS%2C_JOHN_W._HONORABLE_LCCN2016862563_%28cropped%29.jpg"],
  hoover: ["Herbert Hoover", "Hoover", "5/57/President_Hoover_portrait.jpg/330px-President_Hoover_portrait.jpg"],
  smith: ["Al Smith", "Smith", "1/1f/SMITH%2C_ALFRED._HONORABLE_LCCN2016862532_Trim.jpg/330px-SMITH%2C_ALFRED._HONORABLE_LCCN2016862532_Trim.jpg"],
  roosevelt2: ["Franklin D. Roosevelt", "Roosevelt", "f/fd/FDR-1944-Campaign-Portrait_%283x4_retouched%2C_cropped%29.jpg/330px-FDR-1944-Campaign-Portrait_%283x4_retouched%2C_cropped%29.jpg"],
  landon: ["Alf Landon", "Landon", "3/37/Unsuccessful_1936.jpg/330px-Unsuccessful_1936.jpg"],
  willkie: ["Wendell Willkie", "Willkie", "b/b5/Portrait_of_Wendell_Lewis_Willkie_Sitting_by_Wall_%28cropped%29.jpg/330px-Portrait_of_Wendell_Lewis_Willkie_Sitting_by_Wall_%28cropped%29.jpg"],
  dewey: ["Thomas E. Dewey", "Dewey", "5/52/Thomas_Dewey_in_1944.jpg/330px-Thomas_Dewey_in_1944.jpg"],
  truman: ["Harry S. Truman", "Truman", "0/0b/TRUMAN_58-766-06_%28cropped%29.jpg/330px-TRUMAN_58-766-06_%28cropped%29.jpg"],
  eisenhower: ["Dwight D. Eisenhower", "Eisenhower", "0/02/Dwight_D._Eisenhower%2C_official_photo_portrait%2C_May_29%2C_1959_%28cropped%29%283%29.jpg/330px-Dwight_D._Eisenhower%2C_official_photo_portrait%2C_May_29%2C_1959_%28cropped%29%283%29.jpg"],
  stevenson: ["Adlai Stevenson", "Stevenson", "c/ce/Portrait_of_Ambassador_Adlai_E._Stevenson_II_%28cropped%29.jpg/330px-Portrait_of_Ambassador_Adlai_E._Stevenson_II_%28cropped%29.jpg"],
  kennedy: ["John F. Kennedy", "Kennedy", "c/c3/John_F._Kennedy%2C_White_House_color_photo_portrait.jpg/330px-John_F._Kennedy%2C_White_House_color_photo_portrait.jpg"],
  nixon: ["Richard Nixon", "Nixon", "2/2c/Richard_Nixon_presidential_portrait_%281%29.jpg/330px-Richard_Nixon_presidential_portrait_%281%29.jpg"],
  johnson: ["Lyndon B. Johnson", "Johnson", "5/54/Lyndon_B._Johnson%2C_photo_portrait%2C_color_%283x4_cropped%29%282%29.jpg/330px-Lyndon_B._Johnson%2C_photo_portrait%2C_color_%283x4_cropped%29%282%29.jpg"],
  goldwater: ["Barry Goldwater", "Goldwater", "1/19/Senator_Goldwater_1960.jpg/330px-Senator_Goldwater_1960.jpg"],
  humphrey: ["Hubert Humphrey", "Humphrey", "2/23/Hubert_Humphrey_vice_presidential_portrait.jpg/330px-Hubert_Humphrey_vice_presidential_portrait.jpg"],
  mcgovern: ["George McGovern", "McGovern", "6/6f/George_McGovern_%28D-SD%29.jpg/330px-George_McGovern_%28D-SD%29.jpg"],
  carter: ["Jimmy Carter", "Carter", "6/6a/Jimmy_Carter_Official_Portrait2_%283x4_cropped%29.jpg/330px-Jimmy_Carter_Official_Portrait2_%283x4_cropped%29.jpg"],
  ford: ["Gerald Ford", "Ford", "3/36/Gerald_Ford_presidential_portrait_%28cropped%29.jpg/330px-Gerald_Ford_presidential_portrait_%28cropped%29.jpg"],
  reagan: ["Ronald Reagan", "Reagan", "1/16/Official_Portrait_of_President_Reagan_1981.jpg/330px-Official_Portrait_of_President_Reagan_1981.jpg"],
  mondale: ["Walter Mondale", "Mondale", "4/41/Walter_Mondale_1977_vice_presidential_portrait.jpg/330px-Walter_Mondale_1977_vice_presidential_portrait.jpg"],
  bush: ["George H. W. Bush", "Bush", "d/dc/George_H._W._Bush_presidential_portrait_%28cropped%29_%282%29.jpg/330px-George_H._W._Bush_presidential_portrait_%28cropped%29_%282%29.jpg"],
  dukakis: ["Michael Dukakis", "Dukakis", "0/0c/Michael_Dukakis_%283x4_cropped%29.jpg/330px-Michael_Dukakis_%283x4_cropped%29.jpg"],
  clinton2: ["Bill Clinton", "Clinton", "d/d3/Bill_Clinton.jpg/330px-Bill_Clinton.jpg"],
  dole: ["Bob Dole", "Dole", "a/a9/Ks_1996_dole.jpg/330px-Ks_1996_dole.jpg"],
  bush2: ["George W. Bush", "Bush", "d/d4/George-W-Bush.jpeg/330px-George-W-Bush.jpeg"],
  gore: ["Al Gore", "Gore", "c/c5/Al_Gore%2C_Vice_President_of_the_United_States%2C_official_portrait_1994.jpg/330px-Al_Gore%2C_Vice_President_of_the_United_States%2C_official_portrait_1994.jpg"],
  kerry: ["John Kerry", "Kerry", "7/73/John_Kerry_portrait_of_Climate_Envoy_%28cropped%29.jpg/330px-John_Kerry_portrait_of_Climate_Envoy_%28cropped%29.jpg"],
  obama: ["Barack Obama", "Obama", "8/8d/President_Barack_Obama.jpg/330px-President_Barack_Obama.jpg"],
  mccain: ["John McCain", "McCain", "7/74/John_McCain_official_portrait_2009_%283x4_cropped%29.jpg/330px-John_McCain_official_portrait_2009_%283x4_cropped%29.jpg"],
  romney: ["Mitt Romney", "Romney", "7/7f/Mitt_Romney_official_US_Senate_portrait.jpg/330px-Mitt_Romney_official_US_Senate_portrait.jpg"],
  trump: ["Donald Trump", "Trump", "1/16/Official_Presidential_Portrait_of_President_Donald_J._Trump_%282025%29.jpg/330px-Official_Presidential_Portrait_of_President_Donald_J._Trump_%282025%29.jpg"],
  clinton3: ["Hillary Clinton", "Clinton", "e/ec/Former_United_States_Secretary_of_State_Hillary_Rodham_Clinton_at_the_U.S._Department_of_State_on_September_26%2C_2023_in_Washington%2C_D.C._14_%28cropped%29.jpg/330px-Former_United_States_Secretary_of_State_Hillary_Rodham_Clinton_at_the_U.S._Department_of_State_on_September_26%2C_2023_in_Washington%2C_D.C._14_%28cropped%29.jpg"],
  biden: ["Joe Biden", "Biden", "6/68/Joe_Biden_presidential_portrait.jpg/330px-Joe_Biden_presidential_portrait.jpg"],
  harris: ["Kamala Harris", "Harris", "4/41/Kamala_Harris_Vice_Presidential_Portrait.jpg/330px-Kamala_Harris_Vice_Presidential_Portrait.jpg"],
} as const satisfies Record<string, readonly [string, string, string]>;
type PersonId = keyof typeof PEOPLE;

// winner / runner-up: [person, party, electoral votes, popular vote %]
type Ran = readonly [id: PersonId, party: PartyCode, ev: number, popular: number | null];
// others: [name, surname, party, electoral votes, popular vote %]
type Other = readonly [name: string, short: string, party: PartyCode, ev: number, popular: number | null];
// [year, electoral votes, needed to win, winner, runner-up, others, note,
//  each state's winning party (geo.ts STATES order; - = no vote), each state's electoral votes]
type Row = readonly [
  year: number,
  total: number,
  majority: number,
  winner: Ran,
  runnerUp: Ran | null,
  others: readonly Other[],
  note: string,
  parties: string,
  evs: string,
];
const RESULTS: readonly Row[] = [
  [1789, 69, 35, ['washington', "GW", 69, null], null, [], "Unopposed. Every elector voted for him; John Adams came second and became vice president.",
    "- - - - GW - - - - - - - - GW - - - - - - - GW GW GW - - - - - - - - GW GW GW - - - - - - GW - - - - - GW - - -",
    "0 0 0 0 5 0 0 0 0 0 0 0 0 10 0 0 0 0 0 0 0 10 6 7 0 0 0 0 0 0 0 0 12 8 3 0 0 0 0 0 0 7 0 0 0 0 0 5 0 0 0"],
  [1792, 132, 67, ['washington', "GW", 132, null], null, [], "Unopposed again. John Adams came second and stayed vice president.",
    "- - - GW GW - - - - - - - GW GW - - - - - - - GW GW GW GW - - - - - GW - GW GW GW - - - - - GW GW - - - - - GW - - -",
    "0 0 0 4 6 0 0 0 0 0 0 0 12 16 0 0 0 0 0 0 0 15 7 9 4 0 0 0 0 0 4 0 21 10 3 0 0 0 0 0 12 8 0 0 0 0 0 4 0 0 0"],
  [1796, 138, 70, ['adams', "F", 71, null], ['jefferson', "DR", 68, null], [], "Jefferson came second and, under the rules then, became Adams’s vice president.",
    "- - - F F - - - - - - - F F - - - - - - - DR F F F - - - - - DR - DR F F - - - - DR DR DR - - - - - DR - - -",
    "0 0 0 4 6 0 0 0 0 0 0 0 12 16 0 0 0 0 0 0 0 15 7 9 4 0 0 0 0 0 4 0 21 10 3 0 0 0 0 3 12 8 0 0 0 0 0 4 0 0 0"],
  [1800, 138, 70, ['jefferson', "DR", 73, null], ['adams', "F", 65, null], [], "Jefferson tied his own running mate, Aaron Burr, at 73. The House chose Jefferson on its 36th ballot.",
    "- - - F F - - - - - - - DR F - - - - - - - DR F F F - - - - - DR - DR SP F - - - - DR DR DR - - - - - DR - - -",
    "0 0 0 4 6 0 0 0 0 0 0 0 12 16 0 0 0 0 0 0 0 15 7 9 4 0 0 0 0 0 4 0 21 10 3 0 0 0 0 3 12 8 0 0 0 0 0 4 0 0 0"],
  [1804, 176, 89, ['jefferson', "DR", 162, null], ['pinckney', "F", 14, null], [], "",
    "- - - DR DR - - - - - - - DR DR - - - - - - DR DR DR F DR - - - - - DR - DR DR F - - - - DR DR DR - - - - - DR - - -",
    "0 0 0 6 7 0 0 0 0 0 0 0 19 19 0 0 0 0 0 0 3 20 8 9 4 0 0 0 0 0 8 0 24 11 3 0 0 0 0 5 14 10 0 0 0 0 0 6 0 0 0"],
  [1808, 175, 88, ['madison', "DR", 122, null], ['pinckney', "F", 47, null], [["George Clinton", "Clinton", "DR2", 6, null]], "",
    "- - - DR F - - - - - - - DR F - - - - - - DR DR DR F F - - - - - DR - DR DR F - - - - DR DR DR - - - - - DR - - -",
    "0 0 0 6 7 0 0 0 0 0 0 0 19 19 0 0 0 0 0 0 3 20 8 9 4 0 0 0 0 0 8 0 24 11 3 0 0 0 0 5 14 10 0 0 0 0 0 6 0 0 0"],
  [1812, 217, 109, ['madison', "DR", 128, null], ['clinton', "F", 89, null], [], "Clinton, a Democratic-Republican, ran with the Federalists against the war with Britain.",
    "- - - DR F - - - - - - - F F - - - - - - DR DR F F F - - - - - DR - DR DR F - - - - DR DR DR - - DR - - DR - - -",
    "0 0 0 8 8 0 0 0 0 0 0 0 29 22 0 0 0 0 0 0 8 25 8 9 4 0 0 0 0 0 12 0 25 11 4 0 0 0 0 8 15 11 0 0 3 0 0 8 0 0 0"],
  [1816, 217, 109, ['monroe', "DR", 183, null], ['king', "F", 34, null], [], "The Federalists’ last presidential campaign.",
    "- - - DR DR - - - - - - - DR F - - - - - DR DR DR DR F DR - - - - - DR - DR DR F - - - - DR DR DR - - DR - - DR - - -",
    "0 0 0 8 8 0 0 0 0 0 0 0 29 22 0 0 0 0 0 3 8 25 8 9 4 0 0 0 0 0 12 0 25 11 4 0 0 0 0 8 15 11 0 0 3 0 0 8 0 0 0"],
  [1820, 232, 117, ['monroe', "DR", 231, null], null, [], "Unopposed. One elector voted for John Quincy Adams instead.",
    "- DR - DR DR - - - - - DR - DR DR - - - - - DR DR DR DR DR DR - - - - DR DR - DR DR DR - - - - DR DR DR - - DR DR DR DR - - -",
    "0 3 0 8 8 0 0 0 0 0 3 0 29 22 0 0 0 0 0 3 8 25 8 9 4 0 0 0 0 3 12 0 25 11 4 0 0 0 0 8 15 11 0 0 3 3 3 8 0 0 0"],
  [1824, 261, 131, ['adams2', "Adams", 84, 30.9], ['jackson', "Jackson", 99, 41.4], [["William H. Crawford", "Crawford", "Crawford", 41, 11.2], ["Henry Clay", "Clay", "Clay", 37, 13.0]], "Jackson led but no one had a majority. The House chose Adams.",
    "- Adams - Adams Adams - - - - - Jackson - Adams Adams - - - - - Jackson Clay Jackson Jackson Adams Adams - - - - Jackson Clay - Crawford Jackson Crawford - - - - Jackson Jackson Jackson - - Jackson Jackson Jackson Crawford - - -",
    "0 9 0 7 8 0 0 0 0 0 3 0 36 15 0 0 0 0 0 5 16 28 8 8 4 0 0 0 0 3 14 0 24 11 3 0 0 0 0 11 15 11 0 0 5 3 5 9 0 0 0"],
  [1828, 261, 131, ['jackson', "D", 178, 56.0], ['adams2', "NR", 83, 43.6], [], "",
    "- NR - NR NR - - - - - D - D NR - - - - - D D D NR NR NR - - - - D D - D NR NR - - - - D D D - - D D D D - - -",
    "0 9 0 7 8 0 0 0 0 0 3 0 36 15 0 0 0 0 0 5 16 28 8 8 4 0 0 0 0 3 14 0 24 11 3 0 0 0 0 11 15 11 0 0 5 3 5 9 0 0 0"],
  [1832, 286, 144, ['jackson', "D", 219, 54.2], ['clay', "NR", 49, 37.4], [["John Floyd", "Floyd", "N", 11, null], ["William Wirt", "Wirt", "AM", 7, 7.8]], "",
    "- D - AM D - - - - - D - D NR - - - - - D D D D NR NR - - - - D NR - D NR NR - - - - D D N - - D D D D - - -",
    "0 10 0 7 7 0 0 0 0 0 5 0 42 14 0 0 0 0 0 9 21 30 8 8 4 0 0 0 0 4 15 0 23 10 3 0 0 0 0 15 15 11 0 0 5 4 7 11 0 0 0"],
  [1836, 294, 148, ['vanburen', "D", 170, 50.8], ['harrison', "W", 73, 36.6], [["Hugh Lawson White", "White", "W2", 26, 9.7], ["Daniel Webster", "Webster", "W3", 14, 2.7], ["Willie P. Mangum", "Mangum", "W4", 11, null]], "The Whigs ran four regional candidates, hoping to force the race into the House.",
    "- D - W D - - - - - D D D W - - - - - W W D W D D - - - - D W - D W W - - - D W D W - - D D D W - - -",
    "0 10 0 7 7 0 0 0 0 0 5 3 42 14 0 0 0 0 0 9 21 30 8 8 4 0 0 0 0 4 15 0 23 10 3 0 0 0 3 15 15 11 0 0 5 4 7 11 0 0 0"],
  [1840, 294, 148, ['harrison', "W", 234, 52.9], ['vanburen', "D", 60, 46.8], [], "",
    "- W - W D - - - - - D W W W - - - - - W W W W W W - - - - D W - D W W - - - D W W D - - W W D W - - -",
    "0 10 0 7 7 0 0 0 0 0 5 3 42 14 0 0 0 0 0 9 21 30 8 8 4 0 0 0 0 4 15 0 23 10 3 0 0 0 3 15 15 11 0 0 5 4 7 11 0 0 0"],
  [1844, 275, 138, ['polk', "D", 170, 49.5], ['clay', "W", 105, 48.1], [], "New York, and the election, turned on about 5,000 votes.",
    "- D - W D - - - - - D D D W - - - - - D W D W W W - - - - D W - D W W - - - D W W D - - D D D D - - -",
    "0 9 0 6 6 0 0 0 0 0 9 5 36 12 0 0 0 0 0 12 23 26 7 6 4 0 0 0 0 7 12 0 17 8 3 0 0 0 3 13 11 9 0 0 6 6 9 10 0 0 0"],
  [1848, 290, 146, ['taylor', "W", 163, 47.3], ['cass', "D", 127, 42.5], [["Martin Van Buren", "Van Buren", "FS", 0, 10.1]], "",
    "- D D W D - - - - - D D W W - - - - D D D W W W W - - - - D W - D W W - - - D W W D - - W D D W - D W",
    "0 9 4 6 6 0 0 0 0 0 9 5 36 12 0 0 0 0 4 12 23 26 7 6 4 0 0 0 0 7 12 0 17 8 3 0 0 0 3 13 11 9 0 0 6 6 9 10 0 4 3"],
  [1852, 296, 149, ['pierce', "D", 254, 50.8], ['scott', "W", 42, 43.9], [], "The Whigs’ last presidential campaign.",
    "- D D W D - - - - - D D D W - - - - D D D D D D D D - - - D W - D D D - - - D W D D - - D D D D - D D",
    "0 8 5 5 5 0 0 0 0 0 11 6 35 13 0 0 0 0 4 13 23 27 7 6 4 4 0 0 0 9 12 0 15 8 3 0 0 0 4 12 10 8 0 0 6 7 9 10 0 4 3"],
  [1856, 296, 149, ['buchanan', "D", 174, 45.3], ['frmont', "R", 114, 33.1], [["Millard Fillmore", "Fillmore", "KN", 8, 21.5]], "The new Republican Party’s first campaign.",
    "- R R R R - - - - - D R R R - - - - R D R D D R R D - - - D D - D KN D - - - D D D D - - D D D D - D D",
    "0 8 5 5 5 0 0 0 0 0 11 6 35 13 0 0 0 0 4 13 23 27 7 6 4 4 0 0 0 9 12 0 15 8 3 0 0 0 4 12 10 8 0 0 6 7 9 10 0 4 3"],
  [1860, 303, 152, ['lincoln', "R", 180, 39.8], ['breckinridge', "SD", 72, 18.1], [["John Bell", "Bell", "CU", 39, 12.6], ["Stephen A. Douglas", "Douglas", "ND", 12, 29.5]], "The Democrats split in two. Lincoln won without a single Southern electoral vote.",
    "- R R R R - - - - R R R R R R - - - R R R R R R R R - - - ND CU - CU SD SD - - - SD CU SD SD - - SD SD SD SD - SD SD",
    "0 8 5 5 5 0 0 0 0 4 11 6 35 13 3 0 0 0 4 13 23 27 7 6 4 4 0 0 0 9 12 0 15 8 3 0 0 0 4 12 10 8 0 0 6 7 9 10 0 4 3"],
  [1864, 233, 117, ['lincoln', "R", 212, 55.0], ['mcclellan', "D", 21, 45.0], [], "Held during the Civil War. The eleven Confederate states cast no votes.",
    "- R R R R - - - - R R R R R R R - - R R R R D R R R - - - R D R - R D - - R - - - - - - - - - - - - -",
    "0 7 8 5 5 0 0 0 0 4 16 8 33 12 3 3 0 0 8 13 21 26 7 6 4 5 0 0 0 11 11 5 0 7 3 0 0 3 0 0 0 0 0 0 0 0 0 0 0 0 0"],
  [1868, 294, 148, ['grant', "R", 214, 52.7], ['seymour', "D", 80, 47.3], [], "The first election with Black men voting across the South.",
    "- R R R R - - - - R R R D R D R - - R R R R D R R R - - R R D R - D D - - R R R R R - - D - R D - - R",
    "0 7 8 5 5 0 0 0 0 4 16 8 33 12 3 3 0 0 8 13 21 26 7 6 4 5 0 0 3 11 11 5 0 7 3 0 0 3 5 10 9 6 0 0 7 0 8 9 0 0 3"],
  [1872, 366, 184, ['grant', "R", 286, 55.6], ['greeley', "LR", 66, 43.8], [], "Greeley died three weeks after Election Day; his 66 electors voted for others.",
    "- R R R R - - - - R R R R R R R - - R R R R R R R R - - R LR LR R R LR R - - R R LR R R - - R R R LR - LR R",
    "0 7 10 5 5 0 0 0 0 5 21 11 35 13 3 3 0 0 11 15 22 29 9 6 4 6 0 0 3 15 12 5 11 8 3 0 0 5 6 12 10 7 0 0 8 8 10 11 0 8 4"],
  [1876, 369, 185, ['hayes', "R", 185, 47.9], ['tilden', "D", 184, 51.0], [], "Tilden won the popular vote. A commission gave all 20 disputed electoral votes to Hayes.",
    "- R R R R - - - - R R R D R R R - - R D R R D D R R - R R D D D D D D - - R D D D R - - R D D D - D R",
    "0 7 10 5 5 0 0 0 0 5 21 11 35 13 3 3 0 0 11 15 22 29 9 6 4 6 0 3 3 15 12 5 11 8 3 0 0 5 6 12 10 7 0 0 8 8 10 11 0 8 4"],
  [1880, 369, 185, ['garfield', "R", 214, 48.3], ['hancock', "D", 155, 48.2], [], "Decided by about 2,000 popular votes out of 9 million.",
    "- R R R R - - - - R R R R R R D - - R R R R D R R D - R R D D D D D D - - R D D D D - - D D D D - D D",
    "0 7 10 5 5 0 0 0 0 5 21 11 35 13 3 3 0 0 11 15 22 29 9 6 4 6 0 3 3 15 12 5 11 8 3 0 0 5 6 12 10 7 0 0 8 8 10 11 0 8 4"],
  [1884, 401, 201, ['cleveland', "D", 219, 48.9], ['blaine', "R", 182, 48.3], [], "New York went to Cleveland by 1,047 votes.",
    "- R R R R - - - - R R R D R R R - - R D R R D D R R - R R D D D D D D - - R D D D D - - D D D D - D D",
    "0 6 11 4 4 0 0 0 0 7 22 13 36 14 3 3 0 0 13 15 23 30 9 6 4 8 0 3 5 16 13 6 12 8 3 0 0 9 7 12 11 9 0 0 8 9 10 12 0 13 4"],
  [1888, 401, 201, ['harrison2', "R", 233, 47.8], ['cleveland', "D", 168, 48.6], [], "Cleveland won the popular vote.",
    "- R R R R - - - - R R R R R R R - - R R R R D D R R - R R D D D D D D - - R D D D D - - D D D D - D D",
    "0 6 11 4 4 0 0 0 0 7 22 13 36 14 3 3 0 0 13 15 23 30 9 6 4 8 0 3 5 16 13 6 12 8 3 0 0 9 7 12 11 9 0 0 8 9 10 12 0 13 4"],
  [1892, 444, 223, ['cleveland', "D", 277, 46.0], ['harrison2', "R", 145, 43.0], [["James B. Weaver", "Weaver", "PO", 22, 8.5]], "",
    "- R D R R R PO R SP R D R D R R PO R R R D R R D D R D - PO R D D D D D D - - PO D D D D - - D D D D - D D",
    "0 6 12 4 4 4 3 3 3 9 24 14 36 15 4 3 3 4 13 15 23 32 10 6 4 9 0 4 8 17 13 6 12 8 3 0 0 10 8 12 11 9 0 0 8 9 11 13 0 15 4"],
  [1896, 447, 224, ['mckinley', "R", 271, 51.0], ['bryan', "D", 176, 46.7], [], "Gold against silver, city against farm, three years into a depression.",
    "- R R R R D D D R R R R R R R D D D R R R R R R R R D D D D R R D R R - - D D D D D - - D D D D - D D",
    "0 6 12 4 4 4 3 3 3 9 24 14 36 15 4 3 3 4 13 15 23 32 10 6 4 9 3 4 8 17 13 6 12 8 3 0 0 10 8 12 11 9 0 0 8 9 11 13 0 15 4"],
  [1900, 447, 224, ['mckinley', "R", 292, 51.6], ['bryan', "D", 155, 45.5], [], "",
    "- R R R R R D D R R R R R R R D R R R R R R R R R R R D R D D R D R R - - R D D D D - - D D D D - D D",
    "0 6 12 4 4 4 3 3 3 9 24 14 36 15 4 3 3 4 13 15 23 32 10 6 4 9 3 4 8 17 13 6 12 8 3 0 0 10 8 12 11 9 0 0 8 9 11 13 0 15 4"],
  [1904, 476, 239, ['roosevelt', "R", 336, 56.4], ['parker', "D", 140, 37.6], [], "",
    "- R R R R R R R R R R R R R R R R R R R R R R R R R R R R R D R D D R - - R D D D D - - D D D D - D D",
    "0 6 13 4 4 5 3 3 4 11 27 14 39 16 4 3 3 4 13 15 23 34 12 7 4 10 3 5 8 18 13 7 12 8 3 0 0 10 9 12 12 9 0 0 9 10 11 13 0 18 5"],
  [1908, 483, 242, ['taft', "R", 321, 51.6], ['bryan', "D", 162, 43.0], [], "",
    "- R R R R R R R R R R R R R R D R R R R R R R R R R R D D R D R D D R - - R D D D D - D D D D D - D D",
    "0 6 13 4 4 5 3 3 4 11 27 14 39 16 4 3 3 4 13 15 23 34 12 7 4 10 3 5 8 18 13 7 12 8 3 0 0 10 9 12 12 9 0 7 9 10 11 13 0 18 5"],
  [1912, 531, 266, ['wilson', "D", 435, 41.8], ['roosevelt', "BM", 88, 27.4], [["William Howard Taft", "Taft", "R", 8, 23.2], ["Eugene V. Debs", "Debs", "S", 0, 6.0]], "Roosevelt split the Republicans, and Wilson won with 42% of the vote.",
    "- D D R D BM D D D BM D BM D D D D D BM D D D BM D D D BM R D D D D D D D D D D D D D D D - D D D D D - D D",
    "0 6 13 4 4 7 4 4 5 12 29 15 45 18 5 3 3 5 13 15 24 38 14 7 5 13 4 6 8 18 13 8 12 8 3 3 3 10 9 12 12 9 0 10 10 10 12 14 0 20 6"],
  [1916, 531, 266, ['wilson', "D", 277, 49.2], ['hughes', "R", 254, 46.1], [], "California, and the election, went to Wilson by 3,773 votes.",
    "- R R R D D D D D R R R R R R D D R R R D R R R R D D D D D D R D D R D D D D D D D - D D D D D - D D",
    "0 6 13 4 4 7 4 4 5 12 29 15 45 18 5 3 3 5 13 15 24 38 14 7 5 13 4 6 8 18 13 8 12 8 3 3 3 10 9 12 12 9 0 10 10 10 12 14 0 20 6"],
  [1920, 531, 266, ['harding', "R", 404, 60.3], ['cox', "D", 127, 34.1], [], "The first election after the 19th Amendment.",
    "- R R R R R R R R R R R R R R R R R R R R R R R R R R R R R D R D R R R R R D R D D - R D D D D - D D",
    "0 6 13 4 4 7 4 4 5 12 29 15 45 18 5 3 3 5 13 15 24 38 14 7 5 13 4 6 8 18 13 8 12 8 3 3 3 10 9 12 12 9 0 10 10 10 12 14 0 20 6"],
  [1924, 531, 266, ['coolidge', "R", 382, 54.0], ['davis', "D", 136, 28.8], [["Robert M. La Follette", "La Follette", "PR", 13, 16.6]], "",
    "- R PR R R R R R R R R R R R R R R R R R R R R R R R R R R R R R D R R R R R D D D D - D D D D D - D D",
    "0 6 13 4 4 7 4 4 5 12 29 15 45 18 5 3 3 5 13 15 24 38 14 7 5 13 4 6 8 18 13 8 12 8 3 3 3 10 9 12 12 9 0 10 10 10 12 14 0 20 6"],
  [1928, 531, 266, ['hoover', "R", 444, 58.2], ['smith', "D", 87, 40.8], [], "Smith, the first Catholic nominee, cracked the Solid South the wrong way.",
    "- R R R R R R R R R R R R D R R R R R R R R R R D R R R R R R R R R R R R R D R R D - R D D D D - R R",
    "0 6 13 4 4 7 4 4 5 12 29 15 45 18 5 3 3 5 13 15 24 38 14 7 5 13 4 6 8 18 13 8 12 8 3 3 3 10 9 12 12 9 0 10 10 10 12 14 0 20 6"],
  [1932, 531, 266, ['roosevelt2', "D", 472, 57.4], ['hoover', "R", 59, 39.7], [], "Three years into the Great Depression.",
    "- R D R R D D D D D D D D D D D D D D D D R D R D D D D D D D D D D R D D D D D D D - D D D D D - D D",
    "0 5 12 3 4 8 4 4 4 11 29 19 47 17 5 3 3 4 11 14 26 36 16 8 4 22 4 6 7 15 11 8 11 8 3 3 3 9 9 11 13 8 0 11 10 9 11 12 0 23 7"],
  [1936, 531, 266, ['roosevelt2', "D", 523, 60.8], ['landon', "R", 8, 36.5], [], "Landon carried Maine and Vermont.",
    "- R D R D D D D D D D D D D D D D D D D D D D D D D D D D D D D D D D D D D D D D D - D D D D D - D D",
    "0 5 12 3 4 8 4 4 4 11 29 19 47 17 5 3 3 4 11 14 26 36 16 8 4 22 4 6 7 15 11 8 11 8 3 3 3 9 9 11 13 8 0 11 10 9 11 12 0 23 7"],
  [1940, 531, 266, ['roosevelt2', "D", 449, 54.7], ['willkie', "R", 82, 44.8], [], "A third term, with war in Europe.",
    "- R D R D D D D R D D R D D D D D R R R D D D D D D D R R D D D D D D D D R D D D D - D D D D D - D D",
    "0 5 12 3 4 8 4 4 4 11 29 19 47 17 5 3 3 4 11 14 26 36 16 8 4 22 4 6 7 15 11 8 11 8 3 3 3 9 9 11 13 8 0 11 10 9 11 12 0 23 7"],
  [1944, 531, 266, ['roosevelt2', "D", 432, 53.4], ['dewey', "R", 99, 45.9], [], "",
    "- R R R D D D D R D D D D D D D R R R R R D D D D D D R R D D D D D D D D R D D D D - D D D D D - D D",
    "0 5 12 3 4 8 4 4 4 11 28 19 47 16 6 3 3 4 10 13 25 35 16 8 4 25 4 6 6 15 11 8 11 8 3 4 4 8 9 12 14 8 0 10 10 9 11 12 0 23 8"],
  [1948, 531, 266, ['truman', "D", 303, 49.6], ['dewey', "R", 189, 45.1], [["Strom Thurmond", "Thurmond", "SR", 39, 2.4], ["Henry A. Wallace", "Wallace", "PG", 0, 2.4]], "Every major poll had Dewey winning.",
    "- R D R R D D D R D D R R D R D D R D R D R R R D D D D R D D D D R R D D R D D D SR - D SR SR SR D - D D",
    "0 5 12 3 4 8 4 4 4 11 28 19 47 16 6 3 3 4 10 13 25 35 16 8 4 25 4 6 6 15 11 8 11 8 3 4 4 8 9 12 14 8 0 10 10 9 11 12 0 23 8"],
  [1952, 531, 266, ['eisenhower', "R", 442, 55.2], ['stevenson', "D", 89, 44.3], [], "",
    "- R R R R R R R R R R R R R R R R R R R R R R R R R R R R R D D R R R R R R D R D D - R D D D D - R R",
    "0 5 12 3 4 9 4 4 4 11 27 20 45 16 6 3 3 4 10 13 25 32 16 8 4 32 4 6 6 13 10 8 12 9 3 4 4 8 8 11 14 8 0 8 10 8 11 12 0 24 10"],
  [1956, 531, 266, ['eisenhower', "R", 457, 57.4], ['stevenson', "D", 73, 42.0], [], "",
    "- R R R R R R R R R R R R R R R R R R R R R R R R R R R R D R R R R R R R R D R D D - R R D D D - R R",
    "0 5 12 3 4 9 4 4 4 11 27 20 45 16 6 3 3 4 10 13 25 32 16 8 4 32 4 6 6 13 10 8 12 9 3 4 4 8 8 11 14 8 0 8 10 8 11 12 0 24 10"],
  [1960, 537, 269, ['kennedy', "D", 303, 49.7], ['nixon', "R", 219, 49.5], [["Harry F. Byrd", "Byrd", "I", 15, null]], "Kennedy won the popular vote by about 112,000 out of 69 million.",
    "R R R R R R R R R D D D D D R D R R R R R D D D D R R R R D R D R D D R D R D R D D - R D I I D D D R",
    "3 5 12 3 4 9 4 4 4 11 27 20 45 16 6 3 3 4 10 13 25 32 16 8 4 32 4 6 6 13 10 8 12 9 3 4 4 8 8 11 14 8 0 8 10 8 11 12 3 24 10"],
  [1964, 538, 270, ['johnson', "D", 486, 61.1], ['goldwater', "R", 52, 38.5], [], "",
    "D D D D D D D D D D D D D D D D D D D D D D D D D D D D D D D D D D D R D D D D D R D D R R R R D D D",
    "3 4 12 3 4 9 4 4 4 10 26 21 43 14 6 3 3 4 9 13 26 29 17 8 4 40 4 6 5 12 9 7 12 10 3 5 4 7 6 11 13 8 3 8 10 7 10 12 4 25 14"],
  [1968, 538, 270, ['nixon', "R", 301, 43.4], ['humphrey', "D", 191, 42.7], [["George Wallace", "Wallace", "AI", 46, 13.5]], "Wallace carried five Southern states.",
    "R D R R R D R R R D R D D D R R R R R R R D R D D R R R R R R D R D R R R R AI R R R D R AI AI AI AI D D R",
    "3 4 12 3 4 9 4 4 4 10 26 21 43 14 6 3 3 4 9 13 26 29 17 8 4 40 4 6 5 12 9 7 12 10 3 5 4 7 6 11 13 8 3 8 10 7 10 12 4 25 14"],
  [1972, 538, 270, ['nixon', "R", 520, 60.7], ['mcgovern', "D", 17, 37.5], [], "The first election with 18-year-olds voting everywhere.",
    "R R R R R R R R R R R R R D R R R R R R R R R R R R R R R R R R R R R R R R R R R R D R R R R R R R R",
    "3 4 11 3 4 9 4 4 3 10 26 21 41 14 6 3 3 4 8 13 25 27 17 8 4 45 4 7 5 12 9 6 12 10 3 6 4 7 6 10 13 8 3 8 10 7 9 12 4 26 17"],
  [1976, 538, 270, ['carter', "D", 297, 50.1], ['ford', "R", 240, 48.0], [], "",
    "R R D R R R R R R D R R D D R R R R R R D D R R D R R R R D D D R D D R R R D D D D D R D D D D D D D",
    "3 4 11 3 4 9 4 4 3 10 26 21 41 14 6 3 3 4 8 13 25 27 17 8 4 45 4 7 5 12 9 6 12 10 3 6 4 7 6 10 13 8 3 8 10 7 9 12 4 26 17"],
  [1980, 538, 270, ['reagan', "R", 489, 50.7], ['carter', "D", 49, 41.0], [["John B. Anderson", "Anderson", "IA", 0, 6.6]], "",
    "R R R R R R R R R D R R R R R R R R R R R R R R D R R R R R R D R D R R R R R R R R D R R R R D D R R",
    "3 4 11 3 4 9 4 4 3 10 26 21 41 14 6 3 3 4 8 13 25 27 17 8 4 45 4 7 5 12 9 6 12 10 3 6 4 7 6 10 13 8 3 8 10 7 9 12 4 26 17"],
  [1984, 538, 270, ['reagan', "R", 525, 58.8], ['mondale', "D", 13, 40.6], [], "Mondale carried Minnesota and D.C.",
    "R R R R R R R R R D R R R R R R R R R R R R R R R R R R R R R R R R R R R R R R R R D R R R R R R R R",
    "3 4 11 3 4 10 4 4 3 10 24 20 36 13 7 4 3 3 8 12 23 25 16 8 4 47 5 8 5 11 9 6 12 10 3 7 5 7 6 11 13 8 3 8 10 7 9 12 4 29 21"],
  [1988, 538, 270, ['bush', "R", 426, 53.4], ['dukakis', "D", 111, 45.6], [], "",
    "R R D R R D R R R D R R D D D R R R D R R R R R D R R R R R R D R R R R R R R R R R D R R R R R D R R",
    "3 4 11 3 4 10 4 4 3 10 24 20 36 13 7 4 3 3 8 12 23 25 16 8 4 47 5 8 5 11 9 6 12 10 3 7 5 7 6 11 13 8 3 8 10 7 9 12 4 29 21"],
  [1992, 538, 270, ['clinton2', "D", 370, 43.0], ['bush', "R", 168, 37.4], [["Ross Perot", "Perot", "IP", 0, 18.9]], "",
    "R D D D D D R D R D D D D D D D R R D R D D D D D D R D R D D D R D D R D R D D R R D R D R R D D R R",
    "3 4 11 3 4 11 4 3 3 10 22 18 33 12 7 4 3 3 7 12 21 23 15 8 4 54 5 8 5 11 8 5 13 10 3 8 5 6 6 11 14 8 3 8 9 7 9 13 4 32 25"],
  [1996, 538, 270, ['clinton2', "D", 379, 49.2], ['dole', "R", 159, 40.7], [["Ross Perot", "Perot", "RF", 0, 8.4]], "",
    "R D D D D D R R R D D D D D D D R R D R D D D D D D R R R D D D R D D D D R D D R R D R D R R R D R D",
    "3 4 11 3 4 11 4 3 3 10 22 18 33 12 7 4 3 3 7 12 21 23 15 8 4 54 5 8 5 11 8 5 13 10 3 8 5 6 6 11 14 8 3 8 9 7 9 13 4 32 25"],
  [2000, 538, 270, ['bush2', "R", 271, 47.9], ['gore', "D", 266, 48.4], [], "Gore won the popular vote. Florida was decided by 537 votes.",
    "R D D D R D R R R D D D D D D R R R D R R D D D D D R R R R R R R D D R D R R R R R D R R R R R D R R",
    "3 4 11 3 4 11 4 3 3 10 22 18 33 12 7 4 3 3 7 12 21 23 15 8 4 54 5 8 5 11 8 5 13 10 3 8 5 6 6 11 14 8 3 8 9 7 9 13 4 32 25"],
  [2004, 538, 270, ['bush2', "R", 286, 50.7], ['kerry', "D", 251, 48.3], [], "",
    "R D D D D D R R R D D D D D D R R R R R R D D D D D R R R R R R R D D R R R R R R R D R R R R R D R R",
    "3 4 10 3 4 11 4 3 3 10 21 17 31 12 7 5 3 3 7 11 20 21 15 7 4 55 5 9 5 11 8 5 13 10 3 10 5 6 6 11 15 8 3 7 9 6 9 15 4 34 27"],
  [2008, 538, 270, ['obama', "D", 365, 52.9], ['mccain', "R", 173, 45.7], [], "",
    "R D D D D D R R R D D D D D D D R R D D D D D D D D R D R R R R D D D R D R R R D R D R R R R R D R D",
    "3 4 10 3 4 11 4 3 3 10 21 17 31 12 7 5 3 3 7 11 20 21 15 7 4 55 5 9 5 11 8 5 13 10 3 10 5 6 6 11 15 8 3 7 9 6 9 15 4 34 27"],
  [2012, 538, 270, ['obama', "D", 332, 51.1], ['romney', "R", 206, 47.2], [], "",
    "R D D D D D R R R D D D D D D D R R D R D D D D D D R D R R R R D D D R D R R R R R D R R R R R D R D",
    "3 4 10 3 4 12 4 3 3 10 20 16 29 11 7 6 3 3 6 11 18 20 14 7 4 55 6 9 5 10 8 5 13 10 3 11 5 6 6 11 15 9 3 7 8 6 9 16 4 38 29"],
  [2016, 538, 270, ['trump', "R", 304, 46.1], ['clinton3', "D", 227, 48.2], [], "Clinton won the popular vote. Seven electors broke ranks.",
    "R D R D D D R R R D D R D D D D R R R R R R D D D D R D R R R R D D D R D R R R R R D R R R R R D R R",
    "3 4 10 3 4 12 4 3 3 10 20 16 29 11 7 6 3 3 6 11 18 20 14 7 4 55 6 9 5 10 8 5 13 10 3 11 5 6 6 11 15 9 3 7 8 6 9 16 4 38 29"],
  [2020, 538, 270, ['biden', "D", 306, 51.3], ['trump', "R", 232, 46.8], [], "",
    "R D D D D D R R R D D D D D D D R R R R R D D D D D R D R R R R D D D D D R R R R R D R R R R D D R R",
    "3 4 10 3 4 12 4 3 3 10 20 16 29 11 7 6 3 3 6 11 18 20 14 7 4 55 6 9 5 10 8 5 13 10 3 11 5 6 6 11 15 9 3 7 8 6 9 16 4 38 29"],
  [2024, 538, 270, ['trump', "R", 312, 49.8], ['harris', "D", 226, 48.3], [], "",
    "R D R D D D R R R D D R D D D R R R R R R R D D D D R D R R R R D D D R D R R R R R D R R R R R D R R",
    "3 4 10 3 4 12 4 4 3 10 19 15 28 11 8 6 3 3 6 11 17 19 14 7 4 54 6 10 5 10 8 4 13 10 3 11 5 6 6 11 16 9 3 7 8 6 9 16 4 40 30"],
];

/** One candidate: A the winner, B the runner-up, C, D, … everyone else. */
export interface Candidate {
  readonly key: string;
  /** PEOPLE's id, for the winner and runner-up; null for the others. */
  readonly id: PersonId | null;
  readonly name: string;
  readonly short: string;
  readonly party: string;
  readonly partyLabel: string;
  readonly family: Family | null;
  readonly ev: number;
  readonly popular: number | null;
  readonly portrait: string | null;
}

/** A state that cast electoral votes, and who carried it ('O': a split delegation). */
export interface ElectionState {
  readonly code: string;
  readonly ev: number;
  readonly party: string;
  readonly won: string;
}

export interface Election {
  readonly year: number;
  readonly total: number;
  readonly majority: number;
  readonly note: string;
  readonly candidates: readonly [Candidate, ...Candidate[]];
  readonly winner: 'A';
  readonly unopposed: boolean;
  readonly states: readonly ElectionState[];
}

// The geo.ts tile order the per-state strings above follow.
const ORDER = STATES.map((s) => s.code);

const party = (code: string): Pick<Candidate, 'party' | 'partyLabel' | 'family'> => {
  const [label, family] = PARTY_BY_CODE.get(code) ?? [code, null];
  return { party: code, partyLabel: label, family };
};

const person = ([id, code, ev, popular]: Ran, key: string): Candidate => {
  const [name, short, path] = PEOPLE[id];
  return { key, id, name, short, ...party(code), ev, popular, portrait: PORTRAITS + path };
};

const cache = new Map<number, Election>();

/**
 * One election as it happened, or null for a year with none.
 * candidates: the winner (key A), the runner-up (B, absent when unopposed),
 * then anyone else who won electoral votes or a real share of the vote
 * (C, D, …). states: each state that cast electoral votes, with the
 * candidate key that carried it ('O' for a split delegation).
 */
export function electionOf(year: number): Election | null {
  const hit = cache.get(year);
  if (hit) return hit;
  const row = RESULTS.find((r) => r[0] === year);
  if (!row) return null;
  const [y, total, majority, a, b, others, note, codes, evs] = row;
  const candidates: [Candidate, ...Candidate[]] = [person(a, 'A')];
  if (b) candidates.push(person(b, 'B'));
  others.forEach(([name, short, code, ev, popular], i) => {
    candidates.push({ key: String.fromCharCode(67 + i), id: null, name, short, ...party(code), ev, popular, portrait: null });
  });
  const byParty = new Map<string, string>();
  for (const c of candidates) if (!byParty.has(c.party)) byParty.set(c.party, c.key);
  const code = codes.split(' ');
  const ev = evs.split(' ').map(Number);
  const states = ORDER.map((s, i) => {
    const p = code[i] ?? '-';
    return { code: s, ev: ev[i] ?? 0, party: p, won: byParty.get(p) ?? 'O' };
  }).filter((s) => s.party !== '-');
  const e: Election = { year: y, total, majority, note, candidates, winner: 'A', unopposed: !b, states };
  cache.set(year, e);
  return e;
}

/** The years with a rich story: where a random start lands. */
export const FEATURED: readonly number[] = [1800, 1860, 1876, 1896, 1912, 1948, 1960, 1968, 2000, 2016];
