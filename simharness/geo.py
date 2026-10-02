"""States and regions."""

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
    'WA': 'Washington', 'WV': 'West Virginia', 'WI': 'Wisconsin', 'WY': 'Wyoming',
}
CODE_OF = {v: k for k, v in STATE_NAME.items()}

# The eleven former Confederate states: where the 1890–1908 constitutions and
# laws (poll taxes, literacy and "understanding" tests, white primaries) kept
# most Black citizens from voting. Border states are separate.
SOUTH = ['VA', 'NC', 'SC', 'GA', 'FL', 'AL', 'MS', 'LA', 'TX', 'AR', 'TN']
BORDER = ['KY', 'MD', 'DE', 'MO', 'WV', 'OK']
NORTHEAST = ['ME', 'NH', 'VT', 'MA', 'RI', 'CT', 'NY', 'NJ', 'PA']
MIDWEST = ['OH', 'IN', 'IL', 'MI', 'WI', 'MN', 'IA', 'ND', 'SD', 'NE', 'KS']
WEST = ['MT', 'ID', 'WY', 'CO', 'NM', 'AZ', 'UT', 'NV', 'WA', 'OR', 'CA']

REGIONS = {'northeast': NORTHEAST, 'midwest': MIDWEST, 'south': SOUTH, 'border': BORDER, 'west': WEST}
REGION_OF = {s: r for r, ss in REGIONS.items() for s in ss}
# The 48 states of 1920. DC had no electors until 1964.
STATES_1920 = sorted(STATE_NAME)

# Merge order for agent cohorts: a too-small cohort folds into the same sex
# and group in the nearest region.
NEAREST_REGION = {
    'northeast': ['midwest', 'border', 'west', 'south'],
    'midwest': ['northeast', 'west', 'border', 'south'],
    'west': ['midwest', 'northeast', 'border', 'south'],
    'border': ['south', 'midwest', 'northeast', 'west'],
    'south': ['border', 'midwest', 'northeast', 'west'],
}
