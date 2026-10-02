"""Submit, wait for and download the NHGIS state-level extract behind the
1790–1860 censuses (early-republic population: sex × race × free/enslaved ×
age bands, plus nativity for 1850 and 1860).

    python3 scripts/harness/nhgis_extract_republic.py submit     # prints the extract number
    python3 scripts/harness/nhgis_extract_republic.py wait N     # polls, then downloads into the cache
    python3 scripts/harness/nhgis_extract_republic.py status N

Key handling, cache layout and terms: nhgis_common.py.
"""
from nhgis_common import Extract, request

TABLES = {
    '1790_cPop': ['NT1', 'NT4', 'NT5', 'NT6'],          # white males 16+/<16, white females; race/slave status
    '1800_cPop': ['NT1', 'NT5', 'NT6', 'NT9'],          # free white by sex × age; nonwhite by slave status
    '1810_cPop': ['NT1', 'NT5', 'NT6', 'NT9'],
    '1820_cPop': ['NT1', 'NT4A', 'NT4B', 'NT5', 'NT7', 'NT8', 'NT10'],  # + colored by slave status × sex × age; aliens
    '1830_cPop': ['NT1', 'NT4', 'NT5', 'NT9', 'NT12'],  # + foreigners not naturalized
    '1840_cPopX': ['NT1', 'NT4', 'NT5', 'NT25'],
    '1850_cPAX': ['NT1', 'NT4', 'NT5', 'NT40'],         # race/slave × sex × age; nativity
    '1850_sPAX': ['NT1', 'NT5', 'NT7'],                 # native / foreign / unknown birthplace × race × sex
    '1860_cPAX': ['NT1', 'NT4', 'NT5', 'NT7'],          # race/slave × age × sex; nativity × race × sex
}

EXTRACT = Extract(request(TABLES, 'Simulacra harness (agent G): state population by sex x race x free/slave x age, 1790-1860'),
                  'extract_request_republic_{n}.json', '1790–1860 state tables', 'nhgis_extract_republic.py')

if __name__ == '__main__':
    EXTRACT.cli()
