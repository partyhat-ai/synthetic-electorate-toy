"""Submit, wait for and download the NHGIS state-level population extract
behind every census year from 1870 to 1970 (and 1920 again, as a check on the
harness's own 1920 table).

    python3 scripts/harness/nhgis_extract.py submit     # prints the extract number
    python3 scripts/harness/nhgis_extract.py wait N     # polls, then downloads into the cache
    python3 scripts/harness/nhgis_extract.py status N

Key handling, cache layout and terms: nhgis_common.py (cite doi:10.18128/D050.V19.0 /
the NHGIS citation page).
"""
from nhgis_common import Extract, request

# Per census: adults 21+ (men only before 1920: women weren't tabulated by
# voting age) by race / nativity, citizenship of the foreign born, and the
# population by sex × race / nativity to estimate women 21+ where needed.
TABLES = {
    '1870_sPHX': ['NT1', 'NT45', 'NT46', 'NT47', 'NT48'],   # males 21+ by nativity, by race; male citizens 21+
    '1870_sRN': ['NT1', 'NT4'],                             # race by nativity
    '1880_sPHX': ['NT1', 'NT7'],                            # race/nativity by sex; males 21+ by race/nativity
    '1890_cPHAM': ['NT5', 'NT6', 'NT9', 'NT14'],            # nativity by sex, race/nativity by sex; males 21+ by race/nativity
    '1900_cPHAM': ['NT4', 'NT6', 'NT7', 'NT9', 'NT10', 'NT11', 'NT62'],  # + native males 21+ by race; FB males 21+ by citizenship
    '1910_cPHA': ['NT8', 'NT10', 'NT11', 'NT12', 'NT13', 'NT17'],         # males of voting age by race/nativity; FB white by citizenship
    '1920_cPHAM': ['NT12', 'NT13', 'NT15'],                 # check against harness_cache/population/adults_1920_by_state.csv
    '1930_cPAE': ['NT9', 'NT10', 'NT12'],                   # 21+ by race/nativity by sex; FB white 21+ by sex by citizenship
    '1930_cAge30': ['NT7', 'NT10'],
    '1940_cPHAE': ['NT8', 'NT9', 'NT10', 'NT12'],
    '1940_cAge': ['NT7', 'NT10'],                           # 21+ by race by sex; white 21+ by nativity by sex
    '1950_cPHA': ['NT8', 'NT9A', 'NT9B', 'NT48'],
    '1950_cAge': ['NT6', 'NT18'],                           # race by sex by age
    '1960_cAge1': ['NT5', 'NT11'],                          # sex by age; race by sex by age
    '1960_cPop': ['NT14'],
    '1970_Cnt1': ['NT18', 'NT19'],                          # sex by age; race by sex by age (non-white)
}

EXTRACT = Extract(request(TABLES, 'Simulacra harness: state adults 21+ by sex x race/nativity x citizenship, 1870-1970'),
                  'extract_request.json', '1870-1970 state tables', 'nhgis_extract.py')

if __name__ == '__main__':
    EXTRACT.cli()
