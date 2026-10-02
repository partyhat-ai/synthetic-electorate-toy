"""States, regions and 1920 electoral votes (and AK, HI, DC for 1960 on).

The electoral votes are checked at load time against the certified count in
the labels (NARA); see data.load_labels.
"""

STATE_NAME = {
    'AL': 'Alabama', 'AZ': 'Arizona', 'AR': 'Arkansas', 'CA': 'California', 'CO': 'Colorado',
    'CT': 'Connecticut', 'DE': 'Delaware', 'FL': 'Florida', 'GA': 'Georgia', 'ID': 'Idaho',
    'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa', 'KS': 'Kansas', 'KY': 'Kentucky',
    'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland', 'MA': 'Massachusetts', 'MI': 'Michigan',
    'MN': 'Minnesota', 'MS': 'Mississippi', 'MO': 'Missouri', 'MT': 'Montana', 'NE': 'Nebraska',
    'NV': 'Nevada', 'NH': 'New Hampshire', 'NJ': 'New Jersey', 'NM': 'New Mexico', 'NY': 'New York',
    'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio', 'OK': 'Oklahoma', 'OR': 'Oregon',
    'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina', 'SD': 'South Dakota',
    'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah', 'VT': 'Vermont', 'VA': 'Virginia',
    'WA': 'Washington', 'WV': 'West Virginia', 'WI': 'Wisconsin', 'WY': 'Wyoming', 'DC': 'District of Columbia',
    'AK': 'Alaska', 'HI': 'Hawaii',
}
CODE_OF = {v: k for k, v in STATE_NAME.items()}

# The eleven former Confederate states: where the 1890–1908 constitutions and
# laws (poll taxes, literacy and "understanding" tests, white primaries) kept
# most Black citizens from voting. Border states are separate.
SOUTH = ['VA', 'NC', 'SC', 'GA', 'FL', 'AL', 'MS', 'LA', 'TX', 'AR', 'TN']
BORDER = ['KY', 'MD', 'DE', 'MO', 'WV', 'OK', 'DC']
NORTHEAST = ['ME', 'NH', 'VT', 'MA', 'RI', 'CT', 'NY', 'NJ', 'PA']
MIDWEST = ['OH', 'IN', 'IL', 'MI', 'WI', 'MN', 'IA', 'ND', 'SD', 'NE', 'KS']
WEST = ['MT', 'ID', 'WY', 'CO', 'NM', 'AZ', 'UT', 'NV', 'WA', 'OR', 'CA', 'AK', 'HI']

REGIONS = {'northeast': NORTHEAST, 'midwest': MIDWEST, 'south': SOUTH, 'border': BORDER, 'west': WEST}
REGION_OF = {s: r for r, ss in REGIONS.items() for s in ss}
# The 48 states of 1920, listed explicitly so adding AK, HI and DC to REGIONS
# (for 1960 on) can't change it. DC had no electors until 1964.
STATES_1920 = ['AL', 'AR', 'AZ', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA', 'IA', 'ID', 'IL', 'IN', 'KS', 'KY', 'LA',
               'MA', 'MD', 'ME', 'MI', 'MN', 'MO', 'MS', 'MT', 'NC', 'ND', 'NE', 'NH', 'NJ', 'NM', 'NV', 'NY',
               'OH', 'OK', 'OR', 'PA', 'RI', 'SC', 'SD', 'TN', 'TX', 'UT', 'VA', 'VT', 'WA', 'WI', 'WV', 'WY']
ALL_STATES = sorted(STATE_NAME)  # 50 states + DC
# Every state and DC; which ones vote in a given year comes from the returns
# (data.states). 1789–1868 needs no extra codes: only states choose electors,
# and every state that ever did is one of today's 50 (VA before WV's 1863 split
# is VA; MA before ME's 1820 split is MA).

# Merge order for agent cohorts: a too-small cohort folds into the same sex
# and group in the nearest region.
NEAREST_REGION = {
    'northeast': ['midwest', 'border', 'west', 'south'],
    'midwest': ['northeast', 'west', 'border', 'south'],
    'west': ['midwest', 'northeast', 'border', 'south'],
    'border': ['south', 'midwest', 'northeast', 'west'],
    'south': ['border', 'midwest', 'northeast', 'west'],
}
