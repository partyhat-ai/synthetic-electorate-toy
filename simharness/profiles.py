"""Everything about one election that the pipeline needs and the data can't say:
who ran, how the brief blinds them, which letters are safe, what voters read,
and how the robot names the result.

1920 is the original: its values are the ones the harness was built with, so
its briefs stay byte-identical (and its cached answers keep matching).

1924 is the first carried-forward year (backbone.carry_forward): its
population is the 1920 census aged to November 1924, and its group structure
is the 1920 fit's, recalibrated exactly to the 1924 returns. See
DISCLOSURES C13–C16.
"""
from __future__ import annotations

import re

PROFILES = {
    1920: {
        'year': 1920,
        'base': None,
        'day_phrase': 'Tuesday, 2 November',
        'names': {'R': 'Harding', 'D': 'Cox', 'O': 'another candidate'},
        'full_names': {'R': 'Warren G. Harding', 'D': 'James M. Cox'},
        'descriptors': {
            'R': 'nominee of the party that has held a majority in Congress since the 1918 elections',
            'D': 'nominee of the party of the administration in office since 1913',
        },
        'compile_desc': {'R': 'the party that has held a majority in Congress since the 1918 elections',
                         'D': 'the party of the administration in office since 1913', 'president': 'Wilson'},
        'third': None,
        # No H(arding), C(ox), D(ebs), R(epublican), D(emocrat), S(ocialist),
        # F(armer-Labor), W(ilson), L(eague).
        'label_pool': ['K', 'M', 'N', 'P', 'T', 'V'],
        'others_line': 'Other candidates on some ballots, including a Socialist and a Farmer-Labor nominee (answer "other").',
        'plank_order': ['League of Nations', 'cost of living', 'labor', 'agriculture', 'women', 'immigration', 'Prohibition'],
        'names_re': r'\b(Harding|Cox|Coolidge|Roosevelt|Debs|Christensen|Republican|Democrat|G\.\s?O\.\s?P|Wilson)',
        'never_name': 'Harding, Cox, Coolidge, Franklin Roosevelt, Debs, Christensen or Wilson',
        'corpus': 'sources/corpus_1920.jsonl',
        'platforms': 'context/platforms_1920.json',
        'ev_label': '404–127',
        'slice_sources': {
            'men': '1920 census (Fourteenth Census, voting-age tables), men 21+ outside the eleven Southern states; turnout and choice from the backbone (1916→1920 natural experiment, calibrated to certified returns).',
            'women': '1920 census, women 21+ outside the South; turnout is each state\'s 1920 vote minus the men\'s predicted vote (1916 men\'s turnout × the change in states where women already voted).',
            'south-white': '1920 census, white adults in the eleven former Confederate states (includes a small number of American Indian and Asian adults); calibrated to certified returns.',
            'black-south': '1920 census, Black adults in the eleven former Confederate states; turnout from a Goodman regression of 1916 turnout on Black share across those states; the shortfall against white turnout is counted as exclusion.',
            'immigrants': '1920 census, foreign-born white adults who were aliens or had only declared their intent (first papers).',
        },
    },
    1924: {
        'year': 1924,
        'base': 1920,
        'day_phrase': 'Tuesday, 4 November',
        'names': {'R': 'Coolidge', 'D': 'Davis', 'O': 'La Follette'},
        'full_names': {'R': 'Calvin Coolidge', 'D': 'John W. Davis', 'O': 'Robert M. La Follette'},
        'descriptors': {
            'R': 'nominee of the party of the administration in office since 1921',
            'D': 'nominee of the party that held the presidency from 1913 to 1921',
            'O': 'independent candidate of the Progressive movement, endorsed by farm and labor organizations and the Socialist party',
        },
        'compile_desc': {'R': 'the party of the administration in office since 1921',
                         'D': 'the party that held the presidency from 1913 to 1921', 'president': 'Coolidge'},
        # La Follette is a labelled line on every 1924 ballot; he counts in O.
        'third': 'O',
        # No C(oolidge, Calvin), D(avis, Dawes, Democrat), L(a Follette), R(epublican),
        # P(rogressive), B(ryan), W(heeler), J(ohn W. Davis), H(arding), S(ocialist).
        'label_pool': ['K', 'M', 'N', 'T', 'V', 'X'],
        'others_line': 'Other candidates on some ballots, including a Prohibition and a Workers party nominee (answer "other").',
        'plank_order': ['corruption', 'monopoly', 'taxes', 'agriculture', 'labor', 'League of Nations', 'Prohibition'],
        'names_re': r'\b(Coolidge|Davis|La ?Follette|Dawes|Bryan|Wheeler|Harding|Wilson|Republican|Democrat|Progressive party|G\.\s?O\.\s?P)',
        'never_name': 'Coolidge, Davis, La Follette, Dawes, Bryan, Wheeler, Harding or Wilson',
        'corpus': None,  # no dated 1924 items yet (DISCLOSURES C15)
        'platforms': 'context/platforms_1924.json',
        'ev_label': '382–136–13',
        'slice_sources': {
            'men': '1920 census aged to November 1924 along each group\'s 1910→1920 trend; men 21+ outside the eleven Southern states; the 1920 backbone\'s group structure recalibrated exactly to the certified 1924 returns.',
            'women': '1920 census aged to 1924, women 21+ outside the South; the 1920 backbone\'s women-to-men turnout ratio carried forward, then calibrated to each state\'s 1924 vote (Corder–Wolbrecht 1924 held out as a check).',
            'south-white': '1920 census aged to 1924, white adults in the eleven former Confederate states; calibrated to certified 1924 returns.',
            'black-south': '1920 census aged to 1924, Black adults in the eleven former Confederate states; the 1920 exclusion estimate carried forward.',
            'immigrants': '1920 census aged to 1924, foreign-born white adults who were not citizens.',
        },
    },
}


def years() -> list[int]:
    return sorted(PROFILES)


def get(year: int) -> dict:
    if year not in PROFILES:
        raise SystemExit(f'No election profile for {year}. Simulated years: {years()}')
    return PROFILES[year]


def names_re(year: int):
    return re.compile(get(year)['names_re'], re.I)
