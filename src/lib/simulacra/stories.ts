// The sample's ten written elections: for each, the groups of voters worth
// looking at, one person from each, and the what-ifs that matter most. The
// people are invented; what they talk about happened. Their numbers are
// rough, and are only there so the sample model (sample.ts) has something to
// rerun. A real run gets all of it from the simulation server.
//
// slice: sampleTypes.ts SliceSpec. voter: [name, who, history, then, quote];
//   history / then: 'A' | 'B' | 'O' | 'home' | 'barred' — then is the
//   person's choice once a what-if reaches their group.
// whatIfs: [key, label, kind, detail, slices, apply(ctx)] — kind 'franchise'
//   (who can vote), 'population' (who lives where) or 'issue' (what people
//   cared about). ctx is sample.ts's (enfranchise, swing, swingAll, drop,
//   unite, move, apportion, …).
// states: a few states' real vote shares [A, B] (the rest are modelled), so
//   the close calls these stories turn on are close.
import type { Story } from './sampleTypes';

export const STORIES: Readonly<Record<number, Story>> = {
  1800: {
    slices: [
      { key: 'south-farmers', label: 'Southern farmers', share: 0.12, barred: 0.35, turnout: 0.4, lean: [0.8, 0.2, 0], where: 'south',
        voter: ['Josiah Hale', '38, farmer, Orange County, North Carolina', 'A', 'A', 'The Federalists taxed my whiskey and marched an army west to collect it. Mr. Jefferson says he’ll repeal the tax, and I believe him.'] },
      { key: 'new-england', label: 'New Englanders', share: 0.1, barred: 0.3, turnout: 0.45, lean: [0.22, 0.78, 0], where: 'new-england',
        voter: ['Ebenezer Cabot', '46, shipping merchant, Salem, Massachusetts', 'B', 'B', 'French privateers took two of my ships. Mr. Adams built the navy that stopped them, and kept us out of a war we couldn’t afford.'] },
      { key: 'no-property', label: 'Men without property', share: 0.1, barred: 0.7, turnout: 0.5, lean: [0.65, 0.35, 0], where: 'all',
        voter: ['Patrick Doyle', '27, dockworker, New York City', 'barred', 'A', 'New York lets a man vote for the Assembly only if he pays forty shillings a year in rent. I pay less. The Assembly picks our electors, so I don’t count twice over.'] },
      { key: 'enslaved', label: 'Enslaved people', share: 0.16, barred: 1, turnout: 0.6, lean: [0, 0, 0], leanIf: [0.3, 0.7, 0], where: 'black',
        voter: ['Hannah', '30, enslaved cook, Albemarle County, Virginia', 'barred', 'B', 'The Constitution counts me as three-fifths of a person, so Virginia gets more electors for owning me. I get no say at all.'] },
      { key: 'women', label: 'Women', share: 0.47, barred: 0.995, turnout: 0.4, lean: [0.45, 0.55, 0], mirror: true, tilt: -0.03, where: 'all',
        voter: ['Mary Watson', '34, widow and property owner, Burlington, New Jersey', 'B', 'B', 'I own my house and pay my taxes, so New Jersey lets me vote, and I voted Federalist. My sister across the river in Pennsylvania can’t vote at all.'] },
    ],
    whatIfs: [
      ['three-fifths', 'No Three-Fifths Bonus', 'franchise', 'Slave states lose the electors they got for counting enslaved people as three-fifths of a person.', ['enslaved'],
        (c) => c.apportion()],
      ['no-property', 'No Property Test', 'franchise', 'Every free man can vote, whether or not he owns land or pays enough rent.', ['no-property'],
        (c) => c.enfranchise('no-property', { barred: 0 })],
      ['women', 'Women Vote, as in New Jersey', 'franchise', 'Women everywhere can vote on the terms New Jersey gave its property-owning women.', ['women'],
        (c) => c.enfranchise('women', { barred: 0.6, turnout: 0.35 })],
      ['sedition', 'No Sedition Act', 'issue', 'Adams never signs the 1798 law that jailed newspaper editors for criticizing the government.', ['new-england'],
        (c) => c.swingAll(2, 'B', 'middle', 'Adams gains 2 points in the middle states, where the Sedition Act cost him most.')],
    ],
    states: { NY: [0.51, 0.49], PA: [0.53, 0.47] },
  },

  1860: {
    slices: [
      { key: 'north-farmers', label: 'Northern farmers', share: 0.14, barred: 0.02, turnout: 0.85, lean: [0.62, 0.03, 0.35], where: 'north',
        voter: ['Silas Morton', '44, wheat farmer, Knox County, Illinois', 'A', 'A', 'Free soil, free labor, free men. I won’t see Kansas carved into plantations worked by people who can never leave.'] },
      { key: 'immigrants', label: 'Irish and German immigrants', share: 0.05, barred: 0.35, turnout: 0.75, lean: [0.3, 0.05, 0.65], where: 'immigrant',
        voter: ['Michael Brennan', '31, canal laborer, Buffalo, New York', 'O', 'O', 'Douglas says let each territory decide for itself. The Republicans would start a war over it, and it’s men like me who’d be sent to fight.'] },
      { key: 'south-white', label: 'White Southern men', share: 0.1, barred: 0.02, turnout: 0.7, lean: [0, 0.45, 0.55], where: 'south',
        voter: ['John Coffey', '39, farmer, Madison County, Alabama', 'B', 'B', 'Breckinridge will protect our property in the territories. If Lincoln wins, Alabama won’t stay in the Union to be ruled by him.'] },
      { key: 'enslaved', label: 'Enslaved people', share: 0.13, barred: 1, turnout: 0.7, lean: [0, 0, 0], leanIf: [0.9, 0.02, 0.08], where: 'black',
        voter: ['Moses', '26, enslaved field hand, Dougherty County, Georgia', 'barred', 'A', 'Nobody asks us anything. But we hear them at the big house: if Lincoln wins, everything changes.'] },
      { key: 'women', label: 'Women', share: 0.48, barred: 1, turnout: 0.5, lean: [0, 0, 0], mirror: true, tilt: 0.04, where: 'all',
        voter: ['Lydia Grant', '36, schoolteacher and abolitionist, Worcester, Massachusetts', 'barred', 'A', 'I have sent petitions against slavery to Congress for ten years. I may sign a petition. I may not sign a ballot.'] },
    ],
    whatIfs: [
      ['unite', 'The Democrats Don’t Split', 'issue', 'Douglas and Breckinridge stand down for one Democrat, and most of Bell’s voters join him.', ['south-white', 'immigrants'],
        (c) => c.unite(0.9, 'Breckinridge, Douglas and Bell’s voters line up behind one candidate.')],
      ['emancipation', 'Emancipation and the Vote', 'franchise', 'Slavery ends before the election, and freed men vote like other men in their states.', ['enslaved'],
        (c) => c.enfranchise('enslaved', { barred: 0.5 })],
      ['women', 'Women Vote', 'franchise', 'Every woman can vote on the same terms as the men of her state.', ['women'],
        (c) => c.enfranchise('women', { barred: 0.14 })],
      ['three-fifths', 'No Three-Fifths Bonus', 'franchise', 'Slave states lose the electors they got for counting enslaved people as three-fifths of a person.', ['enslaved'],
        (c) => c.apportion()],
    ],
    // Lincoln's real share in the free states (the rest went mostly to Douglas),
    // and the three the united Democrats could take.
    states: {
      ME: [0.64, 0.02], NH: [0.57, 0.01], VT: [0.76, 0.01], MA: [0.63, 0.04], RI: [0.61, 0.0], CT: [0.54, 0.04],
      NY: [0.54, 0.0], PA: [0.56, 0.0], OH: [0.52, 0.03], IN: [0.51, 0.05], IL: [0.51, 0.01], MI: [0.57, 0.01],
      WI: [0.56, 0.01], IA: [0.55, 0.01], MN: [0.63, 0.02], NJ: [0.52, 0.0], CA: [0.32, 0.28], OR: [0.36, 0.34],
      // Lincoln was on no ballot in ten slave states.
      VA: [0.01, 0.445], NC: [0, 0.505], SC: [0, 0.9], GA: [0, 0.487], FL: [0, 0.597], AL: [0, 0.54], MS: [0, 0.59],
      LA: [0, 0.446], TX: [0, 0.755], AR: [0, 0.535], TN: [0, 0.449], KY: [0.009, 0.363], MD: [0.025, 0.455],
      MO: [0.103, 0.189], DE: [0.237, 0.459],
    },
  },

  1876: {
    slices: [
      { key: 'freedmen', label: 'Black men in the South', share: 0.045, barred: 0.55, turnout: 0.85, lean: [0.9, 0.1, 0],
        where: 'black-south',
        states: { MS: 4, SC: 3, LA: 3, AL: 2.5, GA: 2, FL: 1.5, NC: 1.2, VA: 1, TX: 0.6, AR: 0.6, TN: 0.6 },
        voter: ['Isaiah Freeman', '33, sharecropper, Edgefield County, South Carolina', 'A', 'A', 'The Red Shirts rode past my door the night before, forty men with rifles. I voted anyway, at the courthouse, with Union soldiers at the door.'] },
      { key: 'south-white', label: 'White Southern men', share: 0.11, barred: 0.02, turnout: 0.8, lean: [0.15, 0.85, 0], where: 'south',
        voter: ['Wade Pickens', '41, cotton farmer, Abbeville County, South Carolina', 'B', 'B', 'Eight years of carpetbag government and taxes. Tilden will get the soldiers out and give us our state back.'] },
      { key: 'north-workers', label: 'Northern workers', share: 0.12, barred: 0.05, turnout: 0.85, lean: [0.46, 0.54, 0], where: 'industrial',
        voter: ['Thomas Quinn', '35, iron molder, Troy, New York', 'B', 'A', 'Three years of the panic and I’ve had work for eight months of it. The party in power owns the hard times. Tilden, this time.'] },
      { key: 'north-farmers', label: 'Northern farmers', share: 0.13, barred: 0.02, turnout: 0.88, lean: [0.56, 0.44, 0], where: 'north',
        voter: ['Amos Whitcomb', '52, dairy farmer, Delaware County, Ohio', 'A', 'A', 'I fought for the Union. I vote the way I shot.'] },
      { key: 'women', label: 'Women', share: 0.48, barred: 1, turnout: 0.5, lean: [0, 0, 0], mirror: true, tilt: 0.02, where: 'all',
        voter: ['Susan Kellogg', '40, milliner, Rochester, New York', 'barred', 'A', 'Miss Anthony was arrested for voting in this city four years ago. They fined her a hundred dollars. She never paid it.'] },
    ],
    whatIfs: [
      ['fifteenth', 'Enforce the 15th Amendment', 'franchise', 'Black Southerners vote without the rifle clubs, the ballot-box stuffing and the threats.', ['freedmen'],
        (c) => c.enfranchise('freedmen', { barred: 0.05 })],
      ['panic', 'No Panic of 1873', 'issue', 'The railroad bubble doesn’t burst, and the depression that followed never comes.', ['north-workers'],
        (c) => c.swing('north-workers', 6, 'A')],
      ['women', 'Women Vote', 'franchise', 'Every woman can vote on the same terms as the men of her state.', ['women'],
        (c) => c.enfranchise('women', { barred: 0.1 })],
      ['everyone', 'Everyone Votes', 'franchise', 'Every adult can vote, and turns out.', ['freedmen', 'women'],
        (c) => c.everyone()],
    ],
    states: {
      SC: [0.503, 0.497], FL: [0.5, 0.499], LA: [0.517, 0.483], OR: [0.505, 0.475], NY: [0.482, 0.514], IN: [0.487, 0.493],
      CT: [0.485, 0.504], NJ: [0.47, 0.524], CA: [0.507, 0.491], NV: [0.527, 0.473], PA: [0.502, 0.482], OH: [0.502, 0.492],
      WI: [0.504, 0.482], IL: [0.506, 0.466], NH: [0.515, 0.48], NC: [0.465, 0.535], MS: [0.318, 0.682],
      VA: [0.404, 0.596], AL: [0.402, 0.598], GA: [0.279, 0.721],
    },
  },

  1896: {
    slices: [
      { key: 'plains-farmers', label: 'Plains and Western farmers', share: 0.07, barred: 0.02, turnout: 0.85, lean: [0.4, 0.6, 0], where: 'plains',
        voter: ['Emil Lindqvist', '44, wheat farmer, Reno County, Kansas', 'B', 'B', 'Wheat is fifty cents a bushel. I signed my mortgage when it was a dollar. Bryan wants money cheap enough to pay it back with.'] },
      { key: 'north-workers', label: 'Northern factory workers', share: 0.12, barred: 0.12, turnout: 0.82, lean: [0.57, 0.43, 0], where: 'industrial',
        voter: ['Anton Kowalski', '29, steelworker, Pittsburgh, Pennsylvania', 'A', 'B', 'The foreman says if Bryan wins, the mill won’t open Monday. Maybe it’s a bluff. I can’t afford to find out.'] },
      { key: 'south-white', label: 'White Southern men', share: 0.1, barred: 0.08, turnout: 0.6, lean: [0.3, 0.7, 0], where: 'south',
        voter: ['Robert Dunn', '47, cotton farmer, Hill County, Texas', 'B', 'B', 'Cotton is six cents and the railroads take half of it. Bryan and the Populists are the only ones who say so out loud.'] },
      { key: 'black-south', label: 'Black men in the South', share: 0.04, barred: 0.6, turnout: 0.6, lean: [0.88, 0.12, 0], where: 'black-south',
        voter: ['Isaiah Freeman', '53, tenant farmer, Edgefield County, South Carolina', 'barred', 'A', 'The new constitution says I must read any section the registrar picks and explain it to his satisfaction. He picks. I haven’t voted since.'] },
      { key: 'women', label: 'Women', share: 0.48, barred: 0.985, turnout: 0.5, lean: [0.5, 0.5, 0], mirror: true, tilt: 0.02, where: 'all',
        voter: ['Mary Hollis', '38, schoolteacher, Topeka, Kansas', 'barred', 'B', 'Kansas lets me vote for the school board and the mayor, and nothing else. I have read more about silver than my husband has.'] },
    ],
    whatIfs: [
      ['panic', 'No Panic of 1893', 'issue', 'The 1893 crash never happens, so a Democrat isn’t in the White House for three years of depression.', ['north-workers'],
        (c) => c.swing('north-workers', 4, 'B')],
      ['money', 'Equal Campaign Money', 'issue', 'Bryan spends as much as McKinley did, about ten times what he really had.', ['north-workers', 'plains-farmers'],
        (c) => c.swingAll(1.5, 'B', 'north', 'Bryan gains 1.5 points across the North.')],
      ['fifteenth', 'Enforce the 15th Amendment', 'franchise', 'Black Southerners vote as freely as white Southerners: no literacy tests, poll taxes or terror.', ['black-south'],
        (c) => c.enfranchise('black-south', { barred: 0.05 })],
      ['women', 'Women Vote Everywhere', 'franchise', 'Every woman can vote on the same terms as the men of her state, not only in the four Western states that allowed it.', ['women'],
        (c) => c.enfranchise('women', { barred: 0.12 })],
    ],
    states: {
      KY: [0.4868, 0.4865], CA: [0.4913, 0.4849], OR: [0.5007, 0.4798], IN: [0.5082, 0.4796], OH: [0.5186, 0.4708],
      WV: [0.5271, 0.4648], MD: [0.5425, 0.4165], DE: [0.5271, 0.4403], SD: [0.4948, 0.4965], KS: [0.4746, 0.5149],
      NE: [0.4602, 0.5153], WY: [0.4743, 0.5134], NC: [0.4665, 0.5265], VA: [0.4585, 0.5265], TN: [0.4618, 0.5213],
      MO: [0.4524, 0.5465], IL: [0.5572, 0.4262], MI: [0.5385, 0.4376], MN: [0.5662, 0.4096], IA: [0.5577, 0.4292],
      WA: [0.4165, 0.5584],
    },
  },

  1912: {
    slices: [
      { key: 'progressives', label: 'Progressive Republicans', share: 0.08, barred: 0.05, turnout: 0.7, lean: [0.1, 0.8, 0.1], where: 'north',
        voter: ['Walter Pierce', '36, lawyer, Minneapolis, Minnesota', 'B', 'B', 'Taft handed the party to the railroads and the trusts. Roosevelt bolted, and I bolted with him.'] },
      { key: 'regulars', label: 'Loyal Republicans', share: 0.07, barred: 0.05, turnout: 0.75, lean: [0.1, 0.2, 0.7], where: 'north',
        voter: ['Horace Beale', '58, banker, Hartford, Connecticut', 'O', 'B', 'Roosevelt had his two terms. A man who wants a third will want a crown. The party nominated Taft, and I vote for the party.'] },
      { key: 'south-white', label: 'White Southern men', share: 0.1, barred: 0.15, turnout: 0.45, lean: [0.85, 0.1, 0.05], where: 'south',
        voter: ['James Pruitt', '44, tobacco farmer, Pitt County, North Carolina', 'A', 'A', 'Wilson was born in Virginia. My daddy voted Democratic, and I will till the day I die.'] },
      { key: 'socialists', label: 'Socialist workers', share: 0.03, barred: 0.2, turnout: 0.7, lean: [0.15, 0.15, 0.7], where: 'industrial',
        voter: ['Karl Weber', '32, machinist, Milwaukee, Wisconsin', 'O', 'A', 'Milwaukee already elected a Socialist mayor. Debs is the only man on the ballot who ever worked on a railroad.'] },
      { key: 'women', label: 'Women', share: 0.48, barred: 0.92, turnout: 0.5, lean: [0.38, 0.34, 0.28], mirror: true, tilt: -0.03, where: 'all',
        voter: ['Alice Moore', '29, stenographer, Los Angeles, California', 'B', 'B', 'California gave us the vote last year. Roosevelt’s party is the only one that says every woman should have it.'] },
    ],
    whatIfs: [
      ['taft-out', 'Taft Steps Aside', 'issue', 'Taft withdraws for Roosevelt, and three in four of his voters follow.', ['regulars'],
        (c) => c.drop(0.8, { B: 0.75, A: 0.1 }, 'Three in four Taft voters go to Roosevelt.')],
      ['women', 'Women Vote Everywhere', 'franchise', 'Every woman can vote, not only in the six Western states that allowed it.', ['women'],
        (c) => c.enfranchise('women', { barred: 0.1 })],
      ['debs-out', 'Debs Doesn’t Run', 'issue', 'The Socialists sit out, and half of Debs’s voters go to Wilson.', ['socialists'],
        (c) => c.drop(0.2, { A: 0.5, B: 0.3 }, 'Half of Debs’s voters go to Wilson.')],
      ['fifteenth', 'Enforce the 15th Amendment', 'franchise', 'Black Southerners vote as freely as white Southerners.', ['south-white'],
        (c) => c.enfranchiseBlackSouth({ lean: [0.35, 0.1, 0.55] })],
    ],
    states: { CA: [0.4178, 0.418], MI: [0.274, 0.389], MN: [0.318, 0.377], PA: [0.325, 0.365], WA: [0.269, 0.352], SD: [0.422, 0.506], UT: [0.326, 0.215], VT: [0.244, 0.352] },
  },

  1948: {
    slices: [
      { key: 'union', label: 'Union households', share: 0.12, barred: 0.03, turnout: 0.6, lean: [0.66, 0.3, 0.04], where: 'industrial',
        voter: ['Frank Novak', '41, autoworker, Flint, Michigan', 'A', 'A', 'Congress passed Taft-Hartley over Truman’s veto. He stood with us. The polls can say whatever they like.'] },
      { key: 'farm', label: 'Farm families', share: 0.1, barred: 0.02, turnout: 0.55, lean: [0.53, 0.45, 0.02], where: 'midwest',
        voter: ['Dale Harmon', '50, corn farmer, Story County, Iowa', 'A', 'A', 'Corn fell by a third this fall and the Republican Congress cut the money for the bins to store it. I’m sticking with Harry.'] },
      { key: 'south-white', label: 'White Southerners', share: 0.11, barred: 0.25, turnout: 0.3, lean: [0.52, 0.2, 0.28], where: 'south',
        voter: ['Earl Cobb', '46, mill hand, Spartanburg, South Carolina', 'O', 'O', 'Truman wants federal laws against lynching and the poll tax. The Dixiecrats say that’s the end of the South as we know it.'] },
      { key: 'black-south', label: 'Black Southerners', share: 0.045, barred: 0.88, turnout: 0.6, lean: [0.75, 0.22, 0.03], where: 'black-south',
        voter: ['Ruth Jenkins', '34, schoolteacher, Sunflower County, Mississippi', 'barred', 'A', 'The registrar asked me how many bubbles are in a bar of soap. I teach algebra. I did not get registered.'] },
      { key: 'black-north', label: 'Black Northerners', share: 0.03, barred: 0.05, turnout: 0.6, lean: [0.77, 0.2, 0.03], where: 'black-north',
        voter: ['Leon Carter', '29, packinghouse worker, Chicago, Illinois', 'A', 'A', 'My folks came up from Mississippi in ’41 so we could vote. Truman desegregated the Army this summer. That’s my vote.'] },
    ],
    whatIfs: [
      ['migration', 'No Great Migration', 'population', 'The six million Black Southerners who moved north after 1910 stay in the South, where almost none can vote.', ['black-north', 'black-south'],
        (c) => c.move('black-north', 0.7, 'black-south')],
      ['thurmond-out', 'The Dixiecrats Stay', 'issue', 'Thurmond and the States’ Rights Democrats don’t walk out of the party.', ['south-white'],
        (c) => c.drop(0.95, { A: 0.85, B: 0.05 }, 'Thurmond’s voters go back to Truman.', 'south')],
      ['wallace-out', 'Wallace Doesn’t Run', 'issue', 'Henry Wallace stays out, and three in four of his voters go to Truman.', ['union'],
        (c) => c.drop(0.9, { A: 0.75, B: 0.05 }, 'Three in four Wallace voters go to Truman.', 'north')],
      ['fifteenth', 'Enforce the 15th Amendment', 'franchise', 'Black Southerners vote as freely as white Southerners.', ['black-south'],
        (c) => c.enfranchise('black-south', { barred: 0.05 })],
    ],
    states: {
      OH: [0.4948, 0.4924], CA: [0.4786, 0.4713], IL: [0.5007, 0.4922], NY: [0.4501, 0.46], MI: [0.4723, 0.4923],
      MD: [0.4801, 0.4841], IN: [0.4858, 0.4958], CT: [0.4791, 0.4955], PA: [0.4675, 0.5052], NJ: [0.4557, 0.5054],
      SC: [0.2414, 0.0378], AL: [0.0, 0.1909], MS: [0.1002, 0.0262], LA: [0.3272, 0.1745],
    },
  },

  1960: {
    slices: [
      { key: 'catholic', label: 'Catholic voters', share: 0.22, barred: 0.02, turnout: 0.75, lean: [0.78, 0.22, 0], where: 'industrial',
        voter: ['Margaret Doyle', '44, nurse, Worcester, Massachusetts', 'A', 'A', 'Al Smith lost because he was Catholic, and my mother cried. Kennedy told those Houston ministers exactly where he stands.'] },
      { key: 'south-white', label: 'White Southerners', share: 0.13, barred: 0.1, turnout: 0.4, lean: [0.5, 0.45, 0.05], where: 'south',
        voter: ['Carl Pritchett', '52, feed-store owner, Tupelo, Mississippi', 'O', 'O', 'Neither party will leave segregation alone. I’m voting for the unpledged electors so Mississippi can bargain.'] },
      { key: 'black-south', label: 'Black Southerners', share: 0.05, barred: 0.7, turnout: 0.6, lean: [0.68, 0.32, 0], where: 'black-south',
        voter: ['Samuel Hayes', '38, minister, Albany, Georgia', 'barred', 'A', 'Dr. King was in Reidsville prison last month and Kennedy called Mrs. King. Nixon said nothing. The word went round every church in Georgia.'] },
      { key: 'black-north', label: 'Black Northerners', share: 0.045, barred: 0.05, turnout: 0.6, lean: [0.72, 0.28, 0], where: 'black-north',
        voter: ['Doris Wallace', '31, postal clerk, Detroit, Michigan', 'A', 'A', 'My parents voted for the party of Lincoln until Roosevelt. After that call to Mrs. King, my father says he’s done with Nixon.'] },
      { key: 'youth', label: '18- to 20-year-olds', share: 0.075, barred: 0.96, turnout: 0.45, lean: [0.52, 0.48, 0], leanIf: [0.52, 0.48, 0], where: 'all',
        voter: ['Gary Olsen', '19, Army private, Fort Hood, Texas', 'barred', 'A', 'Old enough to be drafted, not old enough to vote. Georgia lets its eighteen-year-olds vote. Texas doesn’t.'] },
    ],
    whatIfs: [
      ['debate', 'No Televised Debates', 'issue', 'Nixon and Kennedy never meet on television, and Nixon’s edge in experience holds.', ['catholic'],
        (c) => c.swingAll(0.6, 'B', null, 'Nixon gains 0.6 points everywhere.')],
      ['migration', 'No Great Migration', 'population', 'The Black Southerners who moved north after 1910 stay in the South, where most can’t vote.', ['black-north', 'black-south'],
        (c) => c.move('black-north', 0.7, 'black-south')],
      ['fifteenth', 'Enforce the 15th Amendment', 'franchise', 'Black Southerners vote as freely as white Southerners, five years before the Voting Rights Act.', ['black-south'],
        (c) => c.enfranchise('black-south', { barred: 0.05 })],
      ['age18', 'Vote at 18', 'franchise', 'Eighteen-year-olds vote everywhere, eleven years before the 26th Amendment.', ['youth'],
        (c) => c.enfranchise('youth', { barred: 0 })],
    ],
    states: {
      IL: [0.4998, 0.4980], TX: [0.5052, 0.4852], NJ: [0.4996, 0.4916], MO: [0.5026, 0.4974], MN: [0.5067, 0.4916],
      MI: [0.5085, 0.4884], PA: [0.5106, 0.4874], HI: [0.5003, 0.4997], NV: [0.5116, 0.4884], NM: [0.5039, 0.4941],
      DE: [0.5078, 0.4921], SC: [0.5124, 0.4876], CA: [0.4955, 0.5010], AK: [0.4094, 0.5090], WA: [0.4855, 0.5068],
      FL: [0.4849, 0.5151], VA: [0.4697, 0.5204], TN: [0.4577, 0.5292], KY: [0.4641, 0.5359],
    },
  },

  1968: {
    slices: [
      { key: 'south-white', label: 'White Southerners', share: 0.13, barred: 0.02, turnout: 0.55, lean: [0.35, 0.15, 0.5], where: 'south',
        voter: ['Wayne Tate', '45, pipefitter, Birmingham, Alabama', 'O', 'A', 'Wallace says what the rest of them only think. Neither party will stand up to the federal judges.'] },
      { key: 'union', label: 'Union households', share: 0.12, barred: 0.02, turnout: 0.65, lean: [0.29, 0.56, 0.15], where: 'industrial',
        voter: ['Joe Kowalczyk', '48, steelworker, Gary, Indiana', 'B', 'B', 'Half the guys on my shift like Wallace. The union hall says a vote for Wallace is a vote for Nixon, and Nixon never did a thing for a working man.'] },
      { key: 'black', label: 'Black voters', share: 0.095, barred: 0.2, turnout: 0.58, lean: [0.07, 0.92, 0.01], where: 'black',
        voter: ['Ella Brooks', '52, seamstress, Selma, Alabama', 'B', 'B', 'I registered in 1965, after the march. This is my first vote for president, and I have waited fifty-two years for it.'] },
      { key: 'youth', label: '18- to 20-year-olds', share: 0.08, barred: 0.95, turnout: 0.5, lean: [0.38, 0.47, 0.15], leanIf: [0.38, 0.47, 0.15], where: 'all',
        voter: ['Danny Ruiz', '19, draftee, Oakland, California', 'barred', 'B', 'I ship out to Vietnam in January. I can’t vote on who sends me there.'] },
      { key: 'suburbs', label: 'Suburban voters', share: 0.15, barred: 0.02, turnout: 0.7, lean: [0.52, 0.38, 0.1], where: 'north',
        voter: ['Patricia Hale', '39, homemaker, Orange County, California', 'A', 'A', 'Riots on the news every night, and the Democrats had their own in Chicago. Nixon says he has a plan to end the war. I want some order.'] },
    ],
    whatIfs: [
      ['wallace-out', 'Wallace Stays Out', 'issue', 'George Wallace doesn’t run, and his voters choose between Nixon and Humphrey.', ['south-white', 'union'],
        (c) => c.drop(1, { A: 0.6, B: 0.3 }, 'Wallace’s voters split 2 to 1 for Nixon.')],
      ['peace', 'Peace Talks Move in October', 'issue', 'The Paris talks break through before Election Day instead of stalling.', ['suburbs', 'youth'],
        (c) => c.swingAll(1.5, 'B', null, 'Humphrey gains 1.5 points everywhere.')],
      ['age18', 'Vote at 18', 'franchise', 'Eighteen-year-olds vote everywhere, three years before the 26th Amendment.', ['youth'],
        (c) => c.enfranchise('youth', { barred: 0 })],
      ['everyone', 'Everyone Votes', 'franchise', 'Every adult can vote, and turns out.', ['black', 'youth'],
        (c) => c.everyone()],
    ],
    states: {
      MO: [0.4487, 0.4368], NJ: [0.4610, 0.4399], OH: [0.4523, 0.4296], IL: [0.4708, 0.4404], CA: [0.4782, 0.4474],
      TX: [0.3987, 0.4125], MD: [0.4194, 0.4359], WA: [0.4512, 0.4723], PA: [0.4402, 0.4760], WI: [0.4776, 0.4427],
      NC: [0.3951, 0.2911], TN: [0.3785, 0.2813], SC: [0.3809, 0.2961], AR: [0.3063, 0.3033], GA: [0.3040, 0.2698],
      AL: [0.1399, 0.1872], MS: [0.1352, 0.2302], LA: [0.2357, 0.2803],
    },
  },

  2000: {
    slices: [
      { key: 'felony', label: 'People with felony records', share: 0.022, barred: 0.75, turnout: 0.3, lean: [0.31, 0.69, 0], leanIf: [0.31, 0.69, 0], where: 'felony',
        voter: ['Marcus Webb', '41, roofer, Tallahassee, Florida', 'barred', 'B', 'I served my time for a drug charge in 1983. I pay taxes and coach Little League. Florida says I can never vote again unless the governor pardons me.'] },
      { key: 'young', label: 'Voters under 30', share: 0.2, barred: 0.03, turnout: 0.4, lean: [0.46, 0.48, 0.06], where: 'all',
        voter: ['Jenna Park', '22, graduate student, Madison, Wisconsin', 'O', 'B', 'Gore and Bush take the same corporate money. I’m voting Nader so the Greens get five percent and federal funding next time.'] },
      { key: 'seniors', label: 'Seniors', share: 0.16, barred: 0.01, turnout: 0.68, lean: [0.47, 0.5, 0.03], where: 'all',
        voter: ['Sylvia Katz', '76, retired bookkeeper, Palm Beach County, Florida', 'O', 'B', 'I meant to vote for Gore. The holes ran down the middle of the ballot, and I think I punched Buchanan. I’ve voted Democratic since Truman.'] },
      { key: 'latino', label: 'Latino voters', share: 0.09, barred: 0.4, turnout: 0.45, lean: [0.35, 0.62, 0.03], where: 'latino',
        voter: ['Luis Ortega', '48, restaurant owner, Miami, Florida', 'A', 'A', 'After what the Clinton people did with Elián in April, nobody on this street is voting for Gore.'] },
      { key: 'rural', label: 'Rural voters', share: 0.2, barred: 0.02, turnout: 0.55, lean: [0.59, 0.38, 0.03], where: 'all',
        voter: ['Roy Hatfield', '55, coal miner, Logan County, West Virginia', 'A', 'A', 'My family has voted Democratic since the union came in. But Gore wants to shut the mines and take our guns. I’m voting Bush.'] },
    ],
    whatIfs: [
      ['felons', 'Felony Records Don’t Bar Voting', 'franchise', 'Everyone who has served a sentence can vote, as in Maine and Vermont.', ['felony'],
        (c) => c.enfranchise('felony', { barred: 0 })],
      ['nader-out', 'Nader Stays Out', 'issue', 'Ralph Nader doesn’t run, and his voters choose between Gore and Bush or stay home.', ['young'],
        (c) => c.drop(0.9, { B: 0.45, A: 0.25 }, 'Nader’s voters go to Gore by almost 2 to 1.')],
      ['ballot', 'Palm Beach Gets a Clear Ballot', 'franchise', 'Palm Beach County’s butterfly ballot is redesigned, and about 2,000 voters get the candidate they meant.', ['seniors'],
        (c) => c.shift({ FL: 0.0007 }, 'B', 'About 2,000 Palm Beach votes go to the candidate their voters meant.')],
      ['everyone', 'Everyone Votes', 'franchise', 'Every adult citizen votes.', ['felony', 'young'],
        (c) => c.everyone()],
    ],
    states: {
      FL: [0.4885, 0.4884], NM: [0.4785, 0.4791], WI: [0.4780, 0.4783], IA: [0.4822, 0.4854], OR: [0.4652, 0.4696],
      NH: [0.4807, 0.4680], MN: [0.4550, 0.4791], MO: [0.5042, 0.4708], OH: [0.4997, 0.4644], NV: [0.4955, 0.4593],
      TN: [0.5115, 0.4728], PA: [0.4643, 0.5061], MI: [0.4615, 0.5128], WA: [0.4471, 0.5016], AR: [0.5131, 0.4586],
      WV: [0.5192, 0.4559], AZ: [0.5102, 0.4473],
    },
  },

  2016: {
    slices: [
      { key: 'white-nodegree', label: 'White voters without a degree', share: 0.4, barred: 0.02, turnout: 0.58, lean: [0.64, 0.29, 0.07], where: 'all',
        voter: ['Dale Kowalski', '54, laid-off machinist, Macomb County, Michigan', 'A', 'A', 'The plant moved to Mexico in 2009. I voted for Obama twice. Trump is the only one who talks about the plants.'] },
      { key: 'black', label: 'Black voters', share: 0.12, barred: 0.08, turnout: 0.6, lean: [0.08, 0.89, 0.03], where: 'black',
        voter: ['Denise Harper', '45, home health aide, Milwaukee, Wisconsin', 'home', 'B', 'I voted for Obama both times. This year the lines were long, I had a double shift, and I didn’t feel it for either of them.'] },
      { key: 'latino', label: 'Latino voters', share: 0.12, barred: 0.4, turnout: 0.48, lean: [0.28, 0.66, 0.06], where: 'latino',
        voter: ['Rosa Delgado', '37, nurse, Phoenix, Arizona', 'B', 'B', 'He called Mexicans rapists the day he announced. My father was a legal resident for forty years. I voted early, for Clinton.'] },
      { key: 'young', label: 'Voters under 30', share: 0.21, barred: 0.04, turnout: 0.46, lean: [0.37, 0.55, 0.08], where: 'all',
        voter: ['Tyler Brooks', '24, barista, Philadelphia, Pennsylvania', 'O', 'O', 'I was all in for Bernie. I couldn’t make myself vote for Clinton, so I wrote him in.'] },
      { key: 'felony', label: 'People with felony records', share: 0.025, barred: 0.7, turnout: 0.3, lean: [0.3, 0.7, 0], leanIf: [0.3, 0.7, 0], where: 'felony',
        voter: ['Andre Simmons', '38, warehouse worker, Jacksonville, Florida', 'barred', 'B', 'I finished my sentence in 2008. Florida still won’t let me vote. One in five Black men here is in the same spot.'] },
    ],
    whatIfs: [
      ['comey', 'No Comey Letter', 'issue', 'The FBI director doesn’t reopen the email inquiry eleven days before the election.', ['white-nodegree'],
        (c) => c.swingAll(1, 'B', null, 'Clinton gains a point with voters who decided late.')],
      ['felons', 'Felony Records Don’t Bar Voting', 'franchise', 'Everyone who has served a sentence can vote, as in Maine and Vermont.', ['felony'],
        (c) => c.enfranchise('felony', { barred: 0 })],
      ['turnout', 'Black Turnout Matches 2012', 'issue', 'Black voters turn out at the rate they did for Obama’s reelection.', ['black'],
        (c) => c.turnout('black', 0.67)],
      ['everyone', 'Everyone Votes', 'franchise', 'Every adult citizen votes.', ['black', 'young', 'felony'],
        (c) => c.everyone()],
    ],
    states: {
      MI: [0.4750, 0.4727], WI: [0.4722, 0.4645], PA: [0.4818, 0.4746], FL: [0.4902, 0.4782], NH: [0.4661, 0.4698],
      MN: [0.4492, 0.4644], NV: [0.4550, 0.4792], AZ: [0.4867, 0.4513], NC: [0.4983, 0.4617], ME: [0.4487, 0.4783],
      GA: [0.5077, 0.4564], VA: [0.4443, 0.4973], CO: [0.4325, 0.4816], OH: [0.5169, 0.4356], IA: [0.5115, 0.4174],
    },
  },
};
