#!/usr/bin/env python3
"""build_corpus.py — dated Chronicling America corpus for one election year.

Builds C/sources/corpus_<year>.jsonl in the 1920 corpus format (see
C/sources/PROVENANCE-sources.md): page-level items from the loc.gov
Chronicling America collection, each with a ~120-word excerpt cut
programmatically from the fetched OCR, dated from 1 September of the election
year through the day before election day (no item after the cutoff).

Usage:
  python scripts/harness/build_corpus.py 1896 [1932 ...] --cache-dir DIR [--out-dir DIR]
  python scripts/harness/build_corpus.py --provenance 1896 1932 --cache-dir DIR  # markdown

Politeness: single-threaded; >=3.2 s between www.loc.gov searches, >=1.1 s
between tile.loc.gov OCR fetches; exponential backoff (honouring Retry-After)
on 429/5xx/Cloudflare errors; every HTTP response is cached on disk so reruns
make no new requests. Descriptive User-Agent.

Selection is fully automatic (no LLM): per topic, one national search plus the
best-covered state in each census region (from the national query's
location_state facet), plus a second national query. The top hits are fetched,
the densest topic-keyword window of the OCR is excerpted, scored for OCR
readability, ad/patent-medicine noise, prediction talk and candidate mentions,
and items are then picked round-robin across regions with per-paper caps and
near-duplicate (shingle Jaccard) rejection.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import http.client
import json
import math
import os
import re
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

UA = ("SimulacraHarness-corpus-builder/1.0 (historical election research; "
      "single-threaded, cached, backs off on 429)")
SEARCH = "https://www.loc.gov/collections/chronicling-america/"
DEFAULT_CACHE = os.environ.get("CORPUS_BUILD_CACHE") or os.path.join(
    tempfile.gettempdir(), "simharness_corpus_build_cache")
DEFAULT_OUT = os.path.expanduser(
    "~/research_notes/historical_election_sim_data/harness_cache/sources")

# ---------------------------------------------------------------- geography
REGION = {}
for _r, _ss in {
    "Northeast": ["maine", "new hampshire", "vermont", "massachusetts", "rhode island",
                  "connecticut", "new york", "new jersey", "pennsylvania"],
    "Midwest": ["ohio", "indiana", "illinois", "michigan", "wisconsin", "minnesota", "iowa",
                "missouri", "north dakota", "south dakota", "nebraska", "kansas", "dakota"],
    "South": ["delaware", "maryland", "district of columbia", "virginia", "west virginia",
              "north carolina", "south carolina", "georgia", "florida", "kentucky",
              "tennessee", "alabama", "mississippi", "arkansas", "louisiana", "oklahoma",
              "texas", "indian territory"],
    "West": ["montana", "idaho", "wyoming", "colorado", "new mexico", "arizona", "utah",
             "nevada", "washington", "oregon", "california", "alaska", "hawaii"],
}.items():
    for _s in _ss:
        REGION[_s] = _r
REGIONS = ["Northeast", "Midwest", "South", "West"]

# ------------------------------------------------------------- year configs
# topics: (label, human description, [search queries], [extra window keywords])
# names: candidate / running-mate / incumbent / party words (case-sensitive).
Y: dict[int, dict] = {}


def year(y, election, names, topics, cutoff=None):
    e = dt.date.fromisoformat(election)
    Y[y] = dict(election=e, cutoff=dt.date.fromisoformat(cutoff) if cutoff else e - dt.timedelta(days=1),
                names=names, topics=topics)


GENERIC_PARTY = ["Republican", "Republicans", "Democrat", "Democrats", "Democratic", "Democracy"]

year(1840, "1840-10-30", ["Harrison", "Tyler", "Van Buren", "Johnson", "Birney", "Whig", "Whigs",
                          "Loco Foco", "Locofoco", "Locofocos", "Tippecanoe", "Liberty party"] + GENERIC_PARTY, [
    ("hard_times", "Hard times after the Panic of 1837", ["hard times", "times money scarce"], ["distress", "wages", "credit", "failures"]),
    ("sub_treasury", "Independent Treasury (sub-treasury)", ["sub treasury", "independent treasury"], ["specie", "treasury"]),
    ("banks_currency", "Banks, specie payments and paper money", ["specie payments banks", "bank notes currency"], ["suspension", "specie", "currency"]),
    ("national_bank", "A national bank", ["national bank"], ["bank", "charter"]),
    ("standing_army", "Militia plan / standing army", ["standing army", "militia"], ["poinsett", "army"]),
    ("abolition", "Abolition and slavery", ["abolition", "abolitionists slavery"], ["slaves", "slavery"]),
    ("tariff", "Tariff and home industry", ["tariff", "protection home industry"], ["duties", "manufactures"]),
    ("public_lands", "Public lands and pre-emption", ["public lands", "pre-emption"], ["lands", "settlers"]),
], cutoff="1840-10-29")
year(1844, "1844-11-01", ["Polk", "Dallas", "Clay", "Frelinghuysen", "Birney", "Tyler", "Whig", "Whigs",
                          "Loco Foco", "Locofoco", "Locofocos", "Liberty party"] + GENERIC_PARTY, [
    ("texas_annexation", "Annexation of Texas", ["annexation texas"], ["annex", "texas", "mexico"]),
    ("tariff_1842", "The tariff of 1842", ["tariff of 1842", "tariff protection"], ["duties", "manufactures"]),
    ("oregon", "The Oregon question", ["oregon territory", "oregon"], ["british", "boundary"]),
    ("national_bank", "A national bank", ["national bank"], ["bank", "currency"]),
    ("slavery_abolition", "Slavery and abolition", ["abolition slavery", "abolitionists"], ["slaves", "slavery"]),
    ("nativism", "Native Americanism and naturalization", ["native american", "naturalization foreigners"], ["catholic", "riots", "foreigners"]),
    ("distribution_lands", "Distribution of public land revenue", ["distribution public lands"], ["lands", "states"]),
    ("hard_money", "Currency and banks", ["currency banks specie"], ["specie", "paper"]),
], cutoff="1844-10-31")
year(1848, "1848-11-07", ["Taylor", "Fillmore", "Cass", "Butler", "Van Buren", "Adams", "Polk", "Whig", "Whigs",
                          "Free Soil", "Free Soilers", "Barnburner", "Barnburners", "Loco Foco", "Locofoco",
                          "Locofocos"] + GENERIC_PARTY, [
    ("wilmot_proviso", "Slavery in the new territories (Wilmot Proviso)", ["wilmot proviso", "slavery territories"], ["slavery", "territory", "proviso"]),
    ("mexican_war", "The Mexican War and its costs", ["mexican war", "war debt mexico"], ["war", "mexico", "soldiers"]),
    ("tariff", "The tariff of 1846", ["tariff of 1846", "tariff"], ["duties", "manufactures"]),
    ("california_gold", "California and the gold discovery", ["california gold"], ["gold", "mines"]),
    ("internal_improvements", "Rivers, harbors and internal improvements", ["rivers and harbors", "internal improvements"], ["harbor", "river"]),
    ("immigration_ireland", "Irish famine and immigration", ["ireland famine", "emigrants"], ["irish", "emigrants"]),
    ("public_lands", "Public lands and homesteads", ["public lands settlers"], ["lands", "settlers"]),
    ("europe_revolutions", "Revolutions in Europe", ["revolution france", "revolution europe"], ["republic", "france"]),
])
year(1852, "1852-11-02", ["Pierce", "King", "Scott", "Graham", "Hale", "Julian", "Fillmore", "Whig", "Whigs",
                          "Free Soil", "Free Soilers", "Free Democracy"] + GENERIC_PARTY, [
    ("fugitive_slave_law", "The Fugitive Slave Law", ["fugitive slave law", "fugitive slave"], ["slave", "fugitive"]),
    ("compromise_1850", "Finality of the Compromise of 1850", ["compromise measures", "compromise finality"], ["compromise", "agitation"]),
    ("tariff", "The tariff", ["tariff", "protection iron"], ["duties", "iron"]),
    ("foreigners", "Immigration and naturalization", ["foreigners naturalization", "adopted citizens"], ["foreign", "germans", "irish"]),
    ("temperance", "Temperance and the Maine Law", ["maine law", "liquor law temperance"], ["liquor", "temperance"]),
    ("internal_improvements", "Rivers, harbors and railroads", ["rivers and harbors", "railroad"], ["harbor", "railroad"]),
    ("homestead", "Homestead / free land", ["homestead bill", "public lands"], ["lands", "homestead"]),
    ("cuba", "Cuba and filibusters", ["cuba"], ["spain", "filibuster"]),
])
year(1856, "1856-11-04", ["Buchanan", "Breckinridge", "Fremont", "Frémont", "Dayton", "Fillmore", "Donelson",
                          "Pierce", "Know Nothing", "Know Nothings", "American party", "Black Republican",
                          "Whig", "Whigs"] + GENERIC_PARTY, [
    ("kansas", "Violence and slavery in Kansas", ["kansas border ruffians", "kansas"], ["lawrence", "free state", "ruffians"]),
    ("slavery_extension", "Extension of slavery into the territories", ["slavery extension territories", "nebraska bill"], ["slavery", "territories"]),
    ("sumner_assault", "The assault on Sumner", ["sumner brooks assault"], ["senate", "assault"]),
    ("disunion", "Threats of disunion", ["disunion", "dissolution of the union"], ["union", "south"]),
    ("foreigners_catholics", "Foreigners and Catholics (nativism)", ["foreigners naturalization", "catholics"], ["foreign", "catholic"]),
    ("temperance", "Temperance / Maine Law", ["maine law", "liquor law"], ["liquor", "temperance"]),
    ("pacific_railroad", "A Pacific railroad", ["pacific railroad"], ["railroad", "pacific"]),
    ("cuba_ostend", "Cuba and the Ostend Manifesto", ["cuba ostend", "cuba"], ["spain", "cuba"]),
])
year(1860, "1860-11-06", ["Lincoln", "Hamlin", "Douglas", "Johnson", "Breckinridge", "Lane", "Bell", "Everett",
                          "Buchanan", "Constitutional Union", "Black Republican", "Wide Awake", "Wide Awakes",
                          "Fusion"] + GENERIC_PARTY, [
    ("slavery_territories", "Slavery in the territories", ["slavery territories", "slave code territories"], ["slavery", "territories"]),
    ("secession", "Secession and disunion", ["secession", "disunion"], ["union", "dissolution"]),
    ("homestead", "The homestead bill", ["homestead bill", "free homes"], ["lands", "settlers"]),
    ("tariff", "Protective tariff", ["protective tariff", "tariff"], ["duties", "iron"]),
    ("john_brown", "John Brown and slave insurrection fears", ["john brown", "insurrection"], ["harper", "insurrection"]),
    ("pacific_railroad", "A Pacific railroad", ["pacific railroad"], ["railroad", "pacific"]),
    ("slave_trade", "Reopening the slave trade", ["african slave trade"], ["slave", "trade"]),
    ("hard_times", "Crops, money and business", ["crops prices money market"], ["crop", "prices"]),
])
year(1864, "1864-11-08", ["Lincoln", "Johnson", "McClellan", "Pendleton", "Fremont", "Frémont", "Union party",
                          "Copperhead", "Copperheads"] + GENERIC_PARTY, [
    ("war_peace", "Peace negotiations vs. continuing the war", ["peace negotiations", "armistice"], ["peace", "war"]),
    ("draft", "The draft and substitutes", ["draft conscription", "drafted substitutes"], ["draft", "quota"]),
    ("emancipation", "Emancipation and abolition", ["emancipation", "abolition slavery"], ["slaves", "freedom"]),
    ("soldiers_vote", "Soldiers voting in the field", ["soldiers vote"], ["soldiers", "field"]),
    ("prices_currency", "Prices, gold and greenbacks", ["gold premium", "high prices"], ["greenbacks", "currency"]),
    ("arbitrary_arrests", "Arbitrary arrests and civil liberties", ["arbitrary arrests", "habeas corpus"], ["arrest", "military"]),
    ("war_news", "The military campaigns (Atlanta, Shenandoah)", ["atlanta sherman", "sheridan valley"], ["army", "rebels"]),
    ("taxes_debt", "War taxes and the debt", ["taxes war debt", "internal revenue"], ["tax", "debt"]),
])
year(1868, "1868-11-03", ["Grant", "Colfax", "Seymour", "Blair", "Johnson"] + GENERIC_PARTY, [
    ("reconstruction", "Reconstruction of the South", ["reconstruction acts", "reconstruction"], ["military", "southern"]),
    ("negro_suffrage", "Black suffrage", ["negro suffrage", "colored voters"], ["negro", "suffrage", "colored"]),
    ("bonds_greenbacks", "Paying the bonds in greenbacks", ["bonds greenbacks", "five-twenty bonds"], ["bonds", "greenbacks", "currency"]),
    ("taxes", "Taxes and the public debt", ["taxation public debt", "internal revenue tax"], ["tax", "debt"]),
    ("ku_klux", "Ku Klux violence", ["ku klux", "outrages"], ["klan", "murdered"]),
    ("impeachment", "The impeachment of the president", ["impeachment"], ["senate", "acquittal"]),
    ("indian_war", "Indian wars on the plains", ["indian war", "indians"], ["indians", "frontier"]),
    ("tariff", "Tariff and protection", ["tariff", "protection"], ["duties", "wool"]),
])
year(1872, "1872-11-05", ["Grant", "Wilson", "Greeley", "Brown", "O'Conor", "Liberal Republican",
                          "Liberal Republicans", "Liberals"] + GENERIC_PARTY, [
    ("amnesty", "Amnesty for former Confederates", ["amnesty"], ["disabilities", "southern"]),
    ("ku_klux", "Ku Klux prosecutions and violence", ["ku klux"], ["klan", "outrages"]),
    ("civil_service_reform", "Civil service reform", ["civil service reform"], ["office", "reform"]),
    ("credit_mobilier", "Corruption: Credit Mobilier", ["credit mobilier"], ["congress", "stock"]),
    ("tammany", "The Tammany Ring", ["tammany ring", "tweed"], ["ring", "frauds"]),
    ("tariff_free_trade", "Tariff vs. free trade", ["free trade", "tariff"], ["duties", "protection"]),
    ("currency", "Specie payments and currency", ["specie payments", "greenbacks"], ["currency", "gold"]),
    ("eight_hour", "Labor and the eight-hour day", ["eight hour", "workingmen"], ["labor", "hours"]),
])
year(1876, "1876-11-07", ["Hayes", "Wheeler", "Tilden", "Hendricks", "Cooper", "Grant", "Greenback party",
                          "Greenbackers"] + GENERIC_PARTY, [
    ("southern_violence", "Southern elections, rifle clubs and violence", ["rifle clubs", "hamburg massacre"], ["negroes", "colored"]),
    ("reconstruction", "Carpet-bag rule and Reconstruction", ["carpet bag", "carpet-baggers"], ["southern", "state government"]),
    ("hard_times", "Hard times and unemployment", ["hard times", "out of employment"], ["work", "wages"]),
    ("currency", "Resumption and greenbacks", ["resumption act", "greenbacks"], ["specie", "currency"]),
    ("corruption", "Corruption and reform (Whisky Ring, Belknap)", ["whisky ring", "belknap"], ["fraud", "reform"]),
    ("indian_war", "The Sioux war", ["sioux war", "custer"], ["indians", "sioux"]),
    ("schools_sectarian", "Public schools and sectarian funds", ["public schools sectarian"], ["schools", "catholic"]),
    ("tariff", "Tariff", ["tariff"], ["duties", "protection"]),
])
year(1880, "1880-11-02", ["Garfield", "Arthur", "Hancock", "English", "Weaver", "Hayes", "Greenback party",
                          "Greenbackers", "Morey"] + GENERIC_PARTY, [
    ("tariff", "Tariff for revenue vs. protection", ["tariff for revenue", "protective tariff"], ["duties", "protection"]),
    ("solid_south", "The Solid South and southern elections", ["solid south"], ["southern", "bourbon"]),
    ("chinese", "Chinese immigration", ["chinese immigration", "chinese"], ["chinese", "coolie"]),
    ("currency", "Greenbacks and resumption", ["greenbacks resumption", "national banks"], ["currency", "specie"]),
    ("civil_service", "Civil service reform", ["civil service reform"], ["office", "reform"]),
    ("exodus", "The Black exodus from the South", ["negro exodus", "exodusters"], ["colored", "kansas"]),
    ("state_rights", "State rights and federal elections", ["state rights", "federal elections"], ["states", "constitution"]),
    ("labor", "Workingmen and wages", ["workingmen wages"], ["labor", "wages"]),
])
year(1884, "1884-11-04", ["Cleveland", "Hendricks", "Blaine", "Logan", "Butler", "St. John", "Arthur",
                          "Mugwump", "Mugwumps", "Greenback party", "Prohibition party"] + GENERIC_PARTY, [
    ("tariff", "Tariff and protection", ["tariff", "protection american industry"], ["duties", "wool"]),
    ("civil_service", "Civil service reform", ["civil service reform"], ["office", "spoils"]),
    ("labor", "Labor and contract labor", ["contract labor", "workingmen wages"], ["labor", "wages"]),
    ("chinese", "Chinese immigration", ["chinese immigration"], ["chinese", "coolies"]),
    ("prohibition", "Prohibition", ["prohibition"], ["liquor", "temperance"]),
    ("monopolies", "Railroads and monopolies", ["monopolies", "railroad monopoly"], ["corporations", "rates"]),
    ("solid_south", "The Solid South and the colored vote", ["solid south", "colored voters"], ["southern", "negro"]),
    ("silver", "Silver coinage", ["silver coinage", "silver dollar"], ["silver", "currency"]),
])
year(1888, "1888-11-06", ["Harrison", "Morton", "Cleveland", "Thurman", "Fisk", "Prohibition party",
                          "Union Labor"] + GENERIC_PARTY, [
    ("tariff_reform", "Tariff reform / the Mills bill", ["tariff reform", "mills bill"], ["duties", "protection"]),
    ("surplus", "The Treasury surplus", ["treasury surplus"], ["surplus", "taxation"]),
    ("wool_protection", "Wool, wages and protection", ["wool tariff", "free wool"], ["wool", "wages"]),
    ("pensions", "Soldiers' pensions", ["pension veto", "soldiers pensions"], ["pension", "veterans"]),
    ("trusts", "Trusts", ["trusts"], ["trust", "monopoly"]),
    ("chinese", "Chinese exclusion", ["chinese exclusion"], ["chinese", "coolies"]),
    ("prohibition", "Prohibition", ["prohibition"], ["liquor", "saloon"]),
    ("civil_service", "Civil service reform", ["civil service reform"], ["office", "reform"]),
])
year(1892, "1892-11-08", ["Cleveland", "Stevenson", "Harrison", "Reid", "Weaver", "Field", "Bidwell",
                          "Populist", "Populists", "People's party", "Peoples party", "Prohibition party"]
     + GENERIC_PARTY, [
    ("tariff", "The McKinley tariff", ["mckinley tariff", "tariff reform"], ["duties", "protection"]),
    ("force_bill", "The Force Bill / federal elections", ["force bill"], ["federal", "elections"]),
    ("silver", "Free silver", ["free silver", "silver coinage"], ["silver", "currency"]),
    ("homestead_strike", "The Homestead strike and labor", ["homestead strike", "pinkertons"], ["strikers", "labor"]),
    ("farmers_alliance", "Farmers' Alliance and the sub-treasury", ["farmers alliance", "sub-treasury"], ["farmers", "alliance"]),
    ("pensions", "Pensions", ["pensions"], ["pension", "soldiers"]),
    ("prohibition", "Prohibition", ["prohibition"], ["liquor", "saloon"]),
    ("railroads_monopolies", "Railroads and monopolies", ["railroad monopolies", "trusts"], ["rates", "corporations"]),
])
year(1896, "1896-11-03", ["McKinley", "Hobart", "Bryan", "Sewall", "Watson", "Palmer", "Buckner", "Cleveland",
                          "Populist", "Populists", "People's party", "Peoples party", "Popocrat", "Popocrats"]
     + GENERIC_PARTY, [
    ("free_silver", "Free silver at 16 to 1", ["free coinage silver", "free silver"], ["silver", "coinage", "16 to 1"]),
    ("gold_standard", "The gold standard / sound money", ["gold standard", "sound money"], ["gold", "money"]),
    ("tariff", "Protective tariff", ["protective tariff", "protection"], ["duties", "tariff"]),
    ("farm_prices", "Farm prices and mortgages", ["price of wheat", "farmers mortgages"], ["wheat", "cotton", "prices"]),
    ("trusts_railroads", "Trusts and railroads", ["trusts monopolies", "railroad rates"], ["corporations", "trust"]),
    ("labor_injunctions", "Labor and government by injunction", ["government by injunction", "workingmen wages"], ["labor", "injunction"]),
    ("income_tax", "The income tax and the Supreme Court", ["income tax"], ["income", "court"]),
    ("bonds_reserve", "Bond issues and the gold reserve", ["bond issue gold reserve", "bonds"], ["bonds", "reserve"]),
])
year(1900, "1900-11-06", ["McKinley", "Roosevelt", "Bryan", "Stevenson", "Debs", "Woolley", "Populist",
                          "Populists"] + GENERIC_PARTY, [
    ("imperialism", "Imperialism and the Philippines", ["imperialism", "philippines"], ["filipinos", "colonies"]),
    ("trusts", "Trusts", ["trusts"], ["trust", "monopoly"]),
    ("free_silver", "Free silver", ["free silver"], ["silver", "coinage"]),
    ("prosperity", "Prosperity and wages (full dinner pail)", ["full dinner pail", "prosperity wages"], ["wages", "work"]),
    ("coal_strike", "The anthracite coal strike", ["anthracite strike", "coal miners strike"], ["miners", "strike"]),
    ("china", "China and the Boxer crisis", ["china boxers", "pekin"], ["china", "troops"]),
    ("boers", "The Boer War", ["boers"], ["boer", "england"]),
    ("disfranchisement", "Black disfranchisement in the South", ["disfranchise negro", "suffrage amendment"], ["negro", "suffrage"]),
])
year(1904, "1904-11-08", ["Roosevelt", "Fairbanks", "Parker", "Davis", "Debs", "Swallow", "Watson",
                          "Populist", "Populists"] + GENERIC_PARTY, [
    ("trusts", "Trusts and corporations", ["trusts", "beef trust"], ["trust", "corporations"]),
    ("tariff", "Tariff revision", ["tariff revision", "tariff"], ["duties", "protection"]),
    ("philippines", "The Philippines", ["philippines"], ["filipinos", "islands"]),
    ("panama_canal", "The Panama Canal", ["panama canal"], ["canal", "isthmus"]),
    ("labor_strikes", "Strikes and labor (Colorado, packinghouse)", ["strike miners", "packing house strike"], ["strike", "union"]),
    ("race_suffrage", "Race and the suffrage in the South", ["negro question", "disfranchisement"], ["negro", "suffrage"]),
    ("pensions", "Pensions (Order No. 78)", ["pension order"], ["pension", "veterans"]),
    ("cost_of_living", "Prices and wages", ["cost of living", "prices wages"], ["prices", "wages"]),
])
year(1908, "1908-11-03", ["Taft", "Sherman", "Bryan", "Kern", "Debs", "Chafin", "Roosevelt", "Hisgen",
                          "Independence party"] + GENERIC_PARTY, [
    ("trusts", "Trusts and corporations", ["trusts", "standard oil"], ["trust", "corporations"]),
    ("tariff_revision", "Tariff revision", ["tariff revision"], ["duties", "schedules"]),
    ("bank_guaranty", "Bank deposit guaranty after the 1907 panic", ["guaranty of bank deposits", "guarantee deposits"], ["deposits", "banks"]),
    ("labor_injunctions", "Labor and injunctions", ["injunction labor", "injunctions"], ["labor", "courts"]),
    ("railroad_rates", "Railroad rates and regulation", ["railroad rates"], ["rates", "commission"]),
    ("prohibition", "Local and county option", ["local option", "county option"], ["saloon", "liquor"]),
    ("campaign_contributions", "Publicity of campaign contributions", ["campaign contributions publicity"], ["contributions", "funds"]),
    ("conservation", "Conservation of forests and water", ["conservation natural resources", "forests irrigation"], ["forests", "water"]),
])
year(1912, "1912-11-05", ["Wilson", "Marshall", "Taft", "Sherman", "Butler", "Roosevelt", "Johnson", "Debs",
                          "Seidel", "Chafin", "Progressive party", "Progressives", "Bull Moose",
                          "Bull Moosers"] + GENERIC_PARTY, [
    ("trusts", "Trusts and monopoly", ["trusts", "anti-trust"], ["trust", "monopoly"]),
    ("tariff_cost_of_living", "Tariff and the high cost of living", ["high cost of living", "tariff revision"], ["prices", "duties"]),
    ("direct_democracy", "Initiative, referendum and recall", ["initiative referendum recall"], ["recall", "referendum"]),
    ("woman_suffrage", "Votes for women", ["woman suffrage", "votes for women"], ["suffrage", "women"]),
    ("labor", "Child labor, wages and hours", ["child labor", "minimum wage"], ["labor", "wages"]),
    ("income_tax", "The income tax amendment", ["income tax amendment"], ["income", "amendment"]),
    ("currency_banking", "Currency reform and the money trust", ["currency reform", "money trust"], ["banks", "currency"]),
    ("prohibition", "Saloons and local option", ["local option saloon", "prohibition"], ["saloon", "liquor"]),
])
year(1916, "1916-11-07", ["Wilson", "Marshall", "Hughes", "Fairbanks", "Benson", "Hanly", "Roosevelt",
                          "Progressive party", "Progressives", "Bull Moose"] + GENERIC_PARTY, [
    ("preparedness", "Military preparedness", ["preparedness army navy"], ["preparedness", "navy"]),
    ("european_war", "The European war and neutrality", ["neutrality", "submarine"], ["war", "neutral"]),
    ("mexico", "Mexico and the border", ["mexican border", "villa"], ["mexico", "border", "guardsmen"]),
    ("eight_hour_law", "The eight-hour railroad law", ["eight hour law", "adamson"], ["railroad", "brotherhoods"]),
    ("hyphenates", "German-Americans and the hyphen", ["hyphenated", "german american"], ["hyphen", "german"]),
    ("woman_suffrage", "Woman suffrage", ["woman suffrage"], ["suffrage", "women"]),
    ("tariff", "Tariff", ["tariff"], ["duties", "protection"]),
    ("prohibition", "Prohibition amendments", ["prohibition amendment", "dry"], ["saloon", "liquor"]),
])
year(1928, "1928-11-06", ["Hoover", "Curtis", "Smith", "Robinson", "Thomas", "Coolidge", "Raskob",
                          "Tammany"] + GENERIC_PARTY, [
    ("prohibition", "Prohibition and enforcement", ["prohibition enforcement", "wet dry"], ["liquor", "eighteenth"]),
    ("religion", "Religion in the campaign", ["catholic religious issue", "religious intolerance"], ["catholic", "protestant"]),
    ("farm_relief", "Farm relief (McNary-Haugen)", ["farm relief", "mcnary-haugen"], ["farmers", "surplus"]),
    ("prosperity", "Prosperity and business", ["prosperity", "business conditions"], ["prosperity", "employment"]),
    ("tariff", "Tariff", ["tariff"], ["duties", "protection"]),
    ("water_power", "Water power and Muscle Shoals", ["muscle shoals", "water power"], ["power", "utilities"]),
    ("immigration", "Immigration restriction", ["immigration restriction", "national origins"], ["immigration", "quota"]),
    ("women_voters", "Women voters", ["women voters"], ["women", "register"]),
])
year(1932, "1932-11-08", ["Roosevelt", "Garner", "Hoover", "Curtis", "Thomas", "Foster", "Coolidge",
                          "Raskob"] + GENERIC_PARTY, [
    ("unemployment_relief", "Unemployment and relief", ["unemployment relief", "jobless"], ["unemployed", "relief"]),
    ("farm_crisis", "Farm prices and foreclosures", ["farm holiday", "farm mortgage foreclosure"], ["farmers", "prices"]),
    ("prohibition_repeal", "Repeal of prohibition", ["prohibition repeal", "repeal eighteenth amendment"], ["repeal", "liquor"]),
    ("banks", "Bank failures and hoarding", ["bank failure depositors", "hoarding"], ["bank", "deposits"]),
    ("veterans_bonus", "The veterans' bonus and the Bonus Army", ["bonus army", "veterans bonus"], ["bonus", "veterans"]),
    ("tariff", "Tariff", ["tariff"], ["duties", "smoot"]),
    ("rfc_public_works", "Federal loans and public works (RFC)", ["reconstruction finance corporation", "public works"], ["loans", "works"]),
    ("taxes_economy", "Taxes and government economy", ["sales tax", "taxes economy"], ["tax", "budget"]),
])
year(1936, "1936-11-03", ["Roosevelt", "Garner", "Landon", "Knox", "Lemke", "Thomas", "Browder", "Hoover",
                          "Union party", "New Deal", "New Dealers"] + GENERIC_PARTY, [
    ("social_security", "Social security and old-age pensions", ["social security", "old age pension"], ["pension", "security"]),
    ("townsend_plan", "The Townsend plan", ["townsend plan"], ["townsend", "pension"]),
    ("relief_wpa", "Relief and the WPA", ["works progress administration", "relief"], ["relief", "wpa"]),
    ("drought_farm", "Drought and farm programs", ["drought", "agricultural adjustment"], ["farmers", "drought"]),
    ("labor_organizing", "Labor organizing (CIO)", ["labor union organize", "cio"], ["union", "labor"]),
    ("spending_debt", "Spending and the national debt", ["national debt", "government spending"], ["debt", "spending"]),
    ("trade_agreements", "Reciprocal trade agreements", ["reciprocal trade agreements"], ["trade", "tariff"]),
    ("supreme_court", "The Supreme Court and the NRA/AAA", ["supreme court decision", "nra"], ["court", "constitution"]),
])
year(1940, "1940-11-05", ["Roosevelt", "Wallace", "Willkie", "McNary", "Thomas", "Browder", "Garner",
                          "New Deal", "New Dealers"] + GENERIC_PARTY, [
    ("aid_to_britain", "Aid to Britain / destroyers deal", ["aid to britain", "destroyers"], ["britain", "aid"]),
    ("draft", "The peacetime draft", ["selective service registration", "conscription"], ["draft", "registration"]),
    ("third_term", "The third-term tradition", ["third term"], ["tradition", "term"]),
    ("defense_jobs", "Defense spending and jobs", ["national defense contracts", "unemployment"], ["defense", "jobs"]),
    ("keep_out_of_war", "Keeping out of the war", ["keep out of war", "isolation"], ["war", "peace"]),
    ("farm_prices", "Farm prices", ["farm prices"], ["farmers", "prices"]),
    ("labor", "Labor, wages and hours", ["wages hours", "labor union"], ["labor", "wages"]),
    ("relief_wpa", "Relief and the WPA", ["wpa relief"], ["relief", "wpa"]),
])
year(1944, "1944-11-07", ["Roosevelt", "Truman", "Dewey", "Bricker", "Thomas", "Wallace",
                          "New Deal", "New Dealers"] + GENERIC_PARTY, [
    ("soldier_vote", "Servicemen voting", ["soldier vote", "absentee ballots servicemen"], ["ballots", "servicemen"]),
    ("postwar_jobs", "Postwar jobs and reconversion", ["postwar jobs", "reconversion"], ["jobs", "postwar"]),
    ("world_organization", "A postwar world organization", ["dumbarton oaks", "world organization peace"], ["peace", "nations"]),
    ("rationing_prices", "Rationing and price control", ["rationing", "price control opa"], ["ration", "prices"]),
    ("labor_pac", "Labor and the CIO-PAC", ["political action committee", "labor union"], ["labor", "union"]),
    ("taxes", "Taxes", ["taxes"], ["tax", "income"]),
    ("veterans", "Veterans' benefits (GI Bill)", ["veterans benefits", "gi bill"], ["veterans", "benefits"]),
    ("farm_prices", "Farm prices", ["farm prices"], ["farmers", "prices"]),
])
year(1948, "1948-11-02", ["Truman", "Barkley", "Dewey", "Warren", "Thurmond", "Wright", "Wallace", "Taylor",
                          "Dixiecrat", "Dixiecrats", "States' Rights", "States Rights", "Progressive party",
                          "Progressives"] + GENERIC_PARTY, [
    ("inflation", "High prices and inflation", ["high prices inflation", "cost of living"], ["prices", "inflation"]),
    ("housing", "The housing shortage", ["housing shortage"], ["housing", "homes"]),
    ("taft_hartley", "Taft-Hartley and labor", ["taft-hartley"], ["labor", "union"]),
    ("civil_rights", "Civil rights and the poll tax", ["civil rights", "poll tax"], ["negro", "rights"]),
    ("berlin_cold_war", "Berlin and the Soviet Union", ["berlin airlift", "russia"], ["soviet", "berlin"]),
    ("communism_home", "Communists at home", ["un-american activities", "communists"], ["communist", "spy"]),
    ("farm_price_supports", "Farm price supports", ["price supports", "farm prices"], ["farmers", "supports"]),
    ("draft", "The peacetime draft", ["draft registration", "selective service"], ["draft", "registration"]),
])
year(1952, "1952-11-04", ["Eisenhower", "Ike", "Nixon", "Stevenson", "Sparkman", "Truman", "Hallinan",
                          "Taft", "Kefauver"] + GENERIC_PARTY, [
    ("korea", "The Korean War", ["korea war", "korea truce"], ["korea", "troops"]),
    ("communism", "Communists in government", ["communists in government", "communism"], ["communist", "loyalty"]),
    ("corruption", "Corruption in government", ["corruption", "mink coat"], ["corruption", "scandal"]),
    ("inflation_controls", "Prices, inflation and controls", ["price controls", "inflation"], ["prices", "controls"]),
    ("taxes", "Taxes", ["taxes"], ["tax", "income"]),
    ("tidelands_oil", "Tidelands oil", ["tidelands oil"], ["tidelands", "oil"]),
    ("civil_rights", "Civil rights and FEPC", ["fepc", "civil rights"], ["rights", "negro"]),
    ("farm_prices", "Farm price supports", ["farm price supports", "farm prices"], ["farmers", "prices"]),
])
year(1956, "1956-11-06", ["Eisenhower", "Ike", "Nixon", "Stevenson", "Kefauver", "Truman"] + GENERIC_PARTY, [
    ("suez_hungary", "Suez and Hungary", ["suez", "hungary"], ["egypt", "soviet"]),
    ("h_bomb_tests", "H-bomb tests and the draft", ["h-bomb tests", "hydrogen bomb tests"], ["bomb", "tests"]),
    ("school_desegregation", "School desegregation", ["desegregation", "integration schools"], ["segregation", "schools"]),
    ("farm_soil_bank", "Farm prices and the soil bank", ["soil bank", "farm prices"], ["farmers", "prices"]),
    ("highways", "The highway program", ["highway program", "interstate highway"], ["highway", "roads"]),
    ("labor", "Labor and wages", ["labor union wages"], ["union", "wages"]),
    ("taxes", "Taxes and the budget", ["taxes balanced budget"], ["tax", "budget"]),
    ("cost_of_living", "Cost of living", ["cost of living"], ["prices", "living"]),
])
year(1960, "1960-11-08", ["Kennedy", "Johnson", "Nixon", "Lodge", "Eisenhower", "Ike", "Jack",
                          "Kennedy-Johnson", "Nixon-Lodge"] + GENERIC_PARTY, [
    ("cuba_castro", "Castro and Cuba", ["castro cuba"], ["castro", "cuba"]),
    ("khrushchev_cold_war", "Khrushchev and the cold war", ["khrushchev", "soviet"], ["soviet", "khrushchev"]),
    ("defense_missiles", "Missiles and national defense", ["missile gap", "missiles defense"], ["missile", "defense"]),
    ("civil_rights", "Civil rights and sit-ins", ["sit-in", "civil rights"], ["negro", "rights"]),
    ("religion", "Religion and the presidency", ["catholic president", "religious issue"], ["catholic", "religion"]),
    ("economy_jobs", "Recession and unemployment", ["unemployment recession"], ["jobs", "unemployment"]),
    ("farm_surplus", "Farm surplus and prices", ["farm surplus", "farm prices"], ["farmers", "surplus"]),
    ("medical_care_aged", "Medical care for the aged", ["medical care aged", "social security medical"], ["aged", "medical"]),
])

# --------------------------------------------------------------------- http
_last = {}
INTERVAL = {"www.loc.gov": 3.2, "tile.loc.gov": 1.5}
LOG: list = []


def _sleep_for(host):
    gap = INTERVAL.get(host, 1.5)
    t = _last.get(host, 0)
    now = time.time()
    if now - t < gap:
        time.sleep(gap - (now - t))
    _last[host] = time.time()


def fetch_json(url, cache_dir):
    key = hashlib.sha1(url.encode()).hexdigest()
    p = os.path.join(cache_dir, "http", key[:2], key + ".json")
    if os.path.exists(p):
        with open(p) as f:
            rec = json.load(f)
        return rec["body"], rec["ts"]
    host = urllib.parse.urlparse(url).netloc
    delay = 15
    for attempt in range(8):
        _sleep_for(host)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read().decode("utf-8", "replace")
            body = json.loads(raw)
            ts = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w") as f:
                json.dump({"url": url, "ts": ts, "body": body}, f)
            return body, ts
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504, 520, 521, 522, 524, 525):
                ra = e.headers.get("Retry-After") if e.headers else None
                wait = max(delay, int(ra) if ra and ra.isdigit() else 0)
                print(f"  [http {e.code}] backoff {wait}s {url[:100]}", file=sys.stderr)
                time.sleep(wait)
                delay = min(delay * 2, 300)
                continue
            if e.code == 404:
                return None, None
            print(f"  [http {e.code}] giving up {url[:100]}", file=sys.stderr)
            return None, None
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError, http.client.HTTPException) as e:
            print(f"  [err {type(e).__name__}] backoff {delay}s {url[:100]}", file=sys.stderr)
            time.sleep(delay)
            delay = min(delay * 2, 300)
    return None, None


def search(q, y, state, cache_dir, c=20, facets=False):
    cfg = Y[y]
    params = [("q", q), ("dates", f"{y}-09-01/{cfg['cutoff'].isoformat()}"), ("fo", "json"), ("c", str(c)),
              ("at", "results,pagination" + (",facets" if facets else ""))]
    if state:
        params.append(("fa", f"location_state:{state}"))
    url = SEARCH + "?" + urllib.parse.urlencode(params)
    body, ts = fetch_json(url, cache_dir)
    total = None
    res, fac = [], {}
    if body:
        total = (body.get("pagination") or {}).get("of")
        res = body.get("results") or []
        for f in body.get("facets") or []:
            if f.get("field") == "location_state" or "location_state" in str(f.get("type", "")):
                for it in f.get("filters", []):
                    fac[it.get("title", "").lower()] = it.get("count", 0)
    LOG.append(dict(ts=ts, q=q, state=state or "—", total=total, returned=len(res)))
    return res, fac


def ocr_url_for(r):
    w = r.get("word_coordinates_url") or ""
    qs = urllib.parse.parse_qs(urllib.parse.urlparse(w).query)
    seg = (qs.get("segment") or [None])[0]
    if not seg:
        return None
    return ("https://tile.loc.gov/text-services/word-coordinates-service?segment="
            + urllib.parse.quote(seg, safe="") + "&format=alto_xml&full_text=1")


def fetch_ocr(url, cache_dir):
    body, ts = fetch_json(url, cache_dir)
    if not body or not isinstance(body, dict):
        return None, ts
    for v in body.values():
        if isinstance(v, dict) and "full_text" in v:
            return v["full_text"], ts
    return None, ts


# ------------------------------------------------------------------- text
_DICT = None


def words_dict():
    global _DICT
    if _DICT is None:
        s = set()
        for p in ("/usr/share/dict/words", "/usr/share/dict/web2"):
            if os.path.exists(p):
                with open(p, errors="ignore") as f:
                    s.update(w.strip().lower() for w in f)
        s.update("a i the of and to in is was for on that by with as at from are be this which it "
                 "he his they their has have had not but or an its were been will would who all".split())
        _DICT = s
    return _DICT


def in_dict(w):
    d = words_dict()
    if w in d:
        return True
    for suf in ("'s", "s", "es", "ed", "d", "ing", "ly", "ies", "ers", "er", "ment", "ments"):
        if w.endswith(suf) and len(w) - len(suf) >= 2:
            b = w[: -len(suf)]
            if b in d or (suf == "ies" and b + "y" in d) or (suf in ("ed", "ing") and b + "e" in d):
                return True
    return False


def normalize_ocr(t):
    t = t.replace("^^", "").replace("^", " ").replace("\n", " ")
    t = re.sub(r"(\w)- (\w)", r"\1\2", t)  # remaining line-break hyphens
    return re.sub(r"\s+", " ", t).strip()


STRAY = re.compile(r"^[\|■•»«\*\^_~`ijI!l1;:,\.'\"]{1,2}$")


def clean_tokens(toks):
    """Light cleaning: drop stray margin chars silently; collapse runs of garbage
    tokens to [OCR illegible]. Returns (tokens, changed_with_brackets)."""
    out, changed = [], False
    for w in toks:
        if STRAY.match(w) and w.lower() not in ("i", "a"):
            continue
        letters = sum(ch.isalpha() for ch in w)
        bad = len(w) >= 3 and letters / len(w) < 0.5 and not re.match(r"^[\$\d,\.%-]+$", w)
        if bad:
            if not out or out[-1] != "[OCR illegible]":
                out.append("[OCR illegible]")
                changed = True
            continue
        out.append(w)
    return out, changed


def quality(toks):
    al = [re.sub(r"[^a-z']", "", w.lower()).strip("'") for w in toks]
    al = [w for w in al if len(w) >= 2]
    if not al:
        return 0.0
    return sum(in_dict(w) for w in al) / len(al)


AD_RX = re.compile(r"\b(pills?|sarsaparilla|druggists?|cures?d?|liniment|bitters|remedy|per bottle|"
                   r"for sale|bargains?|ladies'? (?:hats|suits)|catarrh|rheumatism|kidney|dyspepsia|"
                   r"sale price|special sale)\b", re.I)
PRED_RX = re.compile(r"\b(electoral votes?|will carry|carry the state|majority of \d|plurality|"
                     r"straw vote|poll shows|betting odds|even money)\b", re.I)


def kw_list(topic):
    """Search and extra keywords, cut to 7 letters so they match as word prefixes."""
    _, _, queries, extra = topic
    stop = {"the", "of", "and", "to", "in", "for", "by", "a", "on", "with", "out", "is"}
    kws = {w[:7] for q in queries for w in re.split(r"[\s\-]+", q.lower()) if w and w not in stop and len(w) > 2}
    kws.update(w.lower()[:7] for w in extra)
    return sorted(kws)


def best_window(toks, kws, W=125):
    lows = [re.sub(r"[^a-z0-9]", "", w.lower()) for w in toks]
    hit = [1 if any(l.startswith(k.replace(" ", "")) for k in kws) and l else 0 for l in lows]
    if len(toks) <= W:
        return 0, len(toks), sum(hit)
    pref = [0]
    for h in hit:
        pref.append(pref[-1] + h)
    best, bs = -1, 0
    for s in range(0, len(toks) - W + 1):
        v = pref[s + W] - pref[s]
        if v > best:
            best, bs = v, s
    # centre the window on the hits a little: shift start back to a sentence start
    s = bs
    for j in range(bs, max(bs - 25, -1), -1):
        if j > 0 and re.search(r"[\.\?!]['\"]?$", toks[j - 1]) and toks[j][:1].isupper():
            s = j
            break
    e = min(len(toks), s + 120)
    for j in range(e, min(len(toks), s + 160)):
        if re.search(r"[\.\?!]['\"]?$", toks[j - 1]):
            e = j
            break
    else:
        for j in range(e, max(s + 90, e - 30), -1):
            if re.search(r"[\.\?!]['\"]?$", toks[j - 1]):
                e = j
                break
    return s, e, pref[e] - pref[s]


def cand_regex(y):
    names = Y[y]["names"]
    pat = r"\b(" + "|".join(re.escape(n) for n in sorted(names, key=len, reverse=True)) + r")\b"
    rx_names = re.compile(pat)
    rx_gen = re.compile(r"\b(ticket|nominee|nominees|presidential candidate)\b", re.I)
    return lambda t: bool(rx_names.search(t) or rx_gen.search(t))


def lean_of(paper, y):
    p = paper.lower()
    if "springfield republican" in p:
        return "ind"
    if re.search(r"\b(labor|socialist|appeal to reason|worker|toiler|union record)\b", p):
        return "ind"
    if y >= 1856 and re.search(r"\brepublican\b", p) and "democrat" not in p:
        return "R"
    if re.search(r"\bdemocrat", p) and "republican" not in p:
        return "D"
    return "unknown"


def shingles(text, n=5):
    w = re.findall(r"[a-z]+", text.lower())
    return {" ".join(w[i:i + n]) for i in range(max(0, len(w) - n + 1))}


# ------------------------------------------------------------------- build
def first(v):
    if isinstance(v, list):
        return v[0] if v else None
    return v


def select(cands, topics, target):
    """Up to `target` items: per topic, round-robin across the least-covered regions (candidate
    mentions only once half the topic's quota is filled), then the leftovers by score; at most
    4 items per paper and no near-duplicates (shingle overlap > 0.3)."""
    per_topic = math.ceil(target / len(topics))
    chosen, paper_n = [], {}
    reg_n = {r: 0 for r in REGIONS + ["unknown"]}

    def ok(c):
        if paper_n.get(c["lccn"], 0) >= 4:
            return False
        for o in chosen:
            if o["lccn"] == c["lccn"] and o["date"] == c["date"] and o["page"] == c["page"]:
                return False
            a, b = c["_sh"], o["_sh"]
            if a and b and len(a & b) / max(1, min(len(a), len(b))) > 0.3:
                return False
        return True

    leftovers = []
    for topic in topics:
        pool = sorted([c for c in cands if c["topic"] == topic[0]], key=lambda c: -c["_score"])
        got = 0
        while got < per_topic and pool:
            regs = sorted(REGIONS, key=lambda r: reg_n[r])
            pick = None
            for reg in regs:
                for c in pool:
                    if c["region"] == reg and ok(c) and not (c["mentions_candidates"] and got < per_topic // 2):
                        pick = c
                        break
                if pick:
                    break
            if not pick:
                for c in pool:
                    if ok(c):
                        pick = c
                        break
            if not pick:
                break
            pool.remove(pick)
            chosen.append(pick)
            paper_n[pick["lccn"]] = paper_n.get(pick["lccn"], 0) + 1
            reg_n[pick["region"]] = reg_n.get(pick["region"], 0) + 1
            got += 1
        leftovers += pool
    for c in sorted(leftovers, key=lambda c: -c["_score"]):
        if len(chosen) >= target:
            break
        if ok(c):
            chosen.append(c)
            paper_n[c["lccn"]] = paper_n.get(c["lccn"], 0) + 1
    return chosen


def build_year(y, cache_dir, out_dir, target=88, verbose=True):
    cfg = Y[y]
    LOG.clear()
    start, cutoff = dt.date(y, 9, 1), cfg["cutoff"]
    is_cand = cand_regex(y)
    topics = cfg["topics"]
    seen_pages = set()
    cands = []
    rejected = {"date": 0, "no_ocr": 0, "low_quality": 0, "few_hits": 0, "territory": 0}
    used_states = {r: {} for r in REGIONS}

    def consider(r, ti, q):
        rid = r.get("id") or ""
        if rid in seen_pages:
            return
        seen_pages.add(rid)
        d = r.get("date")
        try:
            dd = dt.date.fromisoformat(d)
        except (TypeError, ValueError):  # missing or malformed date
            rejected["date"] += 1
            return
        if not (start <= dd <= cutoff):
            rejected["date"] += 1
            return
        state = (first(r.get("location_state")) or "").lower()
        if state in ("hawaii", "alaska") and y < 1960:
            rejected["territory"] += 1
            return
        ou = ocr_url_for(r)
        if not ou:
            rejected["no_ocr"] += 1
            return
        txt, ts = fetch_ocr(ou, cache_dir)
        if not txt:
            rejected["no_ocr"] += 1
            return
        toks = normalize_ocr(txt).split(" ")
        kws = kw_list(topics[ti])
        s, e, hits = best_window(toks, kws)
        raw = toks[s:e]
        qual = quality(raw)
        if qual < 0.70:
            rejected["low_quality"] += 1
            return
        if hits < 3:
            rejected["few_hits"] += 1
            return
        ctoks, changed = clean_tokens(raw)
        excerpt = " ".join(ctoks).strip()
        nwords = len(excerpt.split())
        if nwords < 60:
            rejected["few_hits"] += 1
            return
        mc = is_cand(excerpt)
        ads = len(AD_RX.findall(excerpt))
        preds = len(PRED_RX.findall(excerpt))
        score = hits / max(1, nwords) * 40 + (qual - 0.7) * 20 - 4 * mc - 2.5 * ads - 2 * preds
        m = re.search(r"[?&]sp=(\d+)", rid)
        sp = m.group(1) if m else "1"
        lccn = first(r.get("number_lccn")) or ""
        paper = first(r.get("partof_title")) or (r.get("title") or "")
        url = re.sub(r"&q=.*$", "", r.get("url") or rid).replace("http://", "https://")
        cands.append(dict(
            id=f"ca-{lccn}-{d}-{sp}", year=y, date=d, paper=paper,
            city=(first(r.get("location_city")) or "").title(), state=state.title(),
            region=REGION.get(state, "unknown"), lccn=lccn, page=int(sp),
            url=url, ocr_url=ou, topic=topics[ti][0], topic_code=f"T{ti + 1}",
            topic_label=topics[ti][1], query=q, excerpt=excerpt, excerpt_words=nwords,
            excerpt_is_verbatim=not changed, mentions_candidates=mc, leans=lean_of(paper, y),
            ocr_quality=round(qual, 3), retrieved_at=ts, _score=score, _sh=shingles(excerpt)))

    for ti, topic in enumerate(topics):
        label, desc, queries, extra = topic
        if verbose:
            print(f"[{y}] T{ti + 1} {label}", file=sys.stderr)
        # loc.gov searches take ~30 s each server-side, so: national searches with
        # larger pages first, then a state-facet search only for regions that
        # are still short of candidates for this topic.
        res, fac = search(queries[0], y, None, cache_dir, c=40, facets=True)
        for r in res[:10]:
            consider(r, ti, queries[0])
        for q in queries[1:]:
            rs, _ = search(q, y, None, cache_dir, c=30)
            for r in rs[:8]:
                consider(r, ti, q)
        for reg in REGIONS:
            have = sum(1 for c in cands if c["topic"] == label and c["region"] == reg)
            if have >= 2:
                continue
            opts = [(c, s) for s, c in fac.items() if REGION.get(s) == reg and c > 0
                    and not (s in ("hawaii", "alaska") and y < 1960)]
            if not opts:
                continue
            opts.sort(key=lambda cs: (used_states[reg].get(cs[1], 0), -cs[0]))
            st = opts[0][1]
            used_states[reg][st] = used_states[reg].get(st, 0) + 1
            rs, _ = search(queries[0], y, st, cache_dir, c=15)
            for r in rs[:6]:
                consider(r, ti, queries[0])

    chosen = select(cands, topics, target)
    chosen.sort(key=lambda c: (c["topic_code"], c["date"], c["id"]))
    assert all(c["date"] <= cutoff.isoformat() for c in chosen)
    os.makedirs(out_dir, exist_ok=True)
    outp = os.path.join(out_dir, f"corpus_{y}.jsonl")
    with open(outp, "w") as f:
        for c in chosen:
            f.write(json.dumps({k: v for k, v in c.items() if not k.startswith("_")}, ensure_ascii=False) + "\n")
    meta = dict(year=y, election=cfg["election"].isoformat(), cutoff=cutoff.isoformat(),
                n_items=len(chosen), n_candidates=len(cands), n_queries=len(LOG),
                pages_seen=len(seen_pages), rejected=rejected,
                topics=[dict(code=f"T{i + 1}", label=t[0], desc=t[1], queries=t[2],
                             n=sum(c["topic"] == t[0] for c in chosen),
                             regions={r: sum(c["topic"] == t[0] and c["region"] == r for c in chosen)
                                      for r in REGIONS}) for i, t in enumerate(topics)],
                mentions_candidates=sum(c["mentions_candidates"] for c in chosen),
                verbatim=sum(c["excerpt_is_verbatim"] for c in chosen),
                leans={k: sum(c["leans"] == k for c in chosen) for k in ("R", "D", "ind", "unknown")},
                states=sorted({c["state"] for c in chosen}),
                date_range=[min((c["date"] for c in chosen), default=None),
                            max((c["date"] for c in chosen), default=None)],
                queries=list(LOG))
    with open(os.path.join(cache_dir, f"meta_{y}.json"), "w") as f:
        json.dump(meta, f, indent=1, default=str)
    print(f"[{y}] wrote {len(chosen)} items ({len(cands)} candidates, {len(LOG)} queries) -> {outp}",
          file=sys.stderr)
    return meta


def provenance_md(years, cache_dir):
    out = []
    for y in years:
        p = os.path.join(cache_dir, f"meta_{y}.json")
        if not os.path.exists(p):
            continue
        with open(p) as f:
            m = json.load(f)
        ts = [q["ts"] for q in m["queries"] if q.get("ts")]
        out.append(f"\n### corpus_{y}.jsonl\n")
        out.append(f"- Election {m['election']}; cutoff {m['cutoff']}; search filter "
                   f"`dates={y}-09-01/{m['cutoff']}`. Item dates {m['date_range'][0]} to {m['date_range'][1]}.")
        out.append(f"- **{m['n_items']} items** from {m['n_candidates']} scored candidates "
                   f"({m['pages_seen']} distinct pages returned); {m['n_queries']} searches"
                   + (f", retrieved {min(ts)} to {max(ts)} UTC" if ts else "") + ".")
        out.append(f"- Rejected before scoring: {m['rejected']}.")
        out.append(f"- `mentions_candidates=true`: {m['mentions_candidates']}; verbatim: {m['verbatim']}; "
                   f"leans: {m['leans']}; states ({len(m['states'])}): {', '.join(m['states'])}.")
        out.append("\n| Code | topic | Items | NE | MW | S | W | Queries |\n|---|---|---|---|---|---|---|---|")
        for t in m["topics"]:
            r = t["regions"]
            out.append(f"| {t['code']} | `{t['label']}` — {t['desc']} | {t['n']} | {r['Northeast']} | "
                       f"{r['Midwest']} | {r['South']} | {r['West']} | {'; '.join('`'+q+'`' for q in t['queries'])} |")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("years", nargs="+", type=int)
    ap.add_argument("--cache-dir", default=DEFAULT_CACHE)
    ap.add_argument("--out-dir", default=DEFAULT_OUT)
    ap.add_argument("--target", type=int, default=88)
    ap.add_argument("--provenance", action="store_true")
    a = ap.parse_args()
    os.makedirs(a.cache_dir, exist_ok=True)
    if a.provenance:
        print(provenance_md(a.years, a.cache_dir))
        return
    for y in a.years:
        if y not in Y:
            print(f"no config for {y}", file=sys.stderr)
            continue
        try:
            build_year(y, a.cache_dir, a.out_dir, target=a.target)
        except Exception as e:  # keep going across years
            print(f"[{y}] FAILED: {type(e).__name__}: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
