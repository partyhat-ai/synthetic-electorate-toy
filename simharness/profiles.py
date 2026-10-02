"""Everything about one election that the pipeline needs and the data can't say:
who ran, how the brief blinds them, which letters are safe, what voters read,
and how the robot names the result.

1920 is the original: its values are the ones the harness was built with, so
its briefs stay byte-identical (and its cached answers keep matching).
"""
from __future__ import annotations

import re

PROFILES = {
    1920: {
        'year': 1920,
        'day_phrase': 'Tuesday, 2 November',
        'names': {'R': 'Harding', 'D': 'Cox', 'O': 'another candidate'},
        'full_names': {'R': 'Warren G. Harding', 'D': 'James M. Cox'},
        'descriptors': {
            'R': 'nominee of the party that has held a majority in Congress since the 1918 elections',
            'D': 'nominee of the party of the administration in office since 1913',
        },
        'compile_desc': {'R': 'the party that has held a majority in Congress since the 1918 elections',
                         'D': 'the party of the administration in office since 1913', 'president': 'Wilson'},
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
}


def years() -> list[int]:
    return sorted(PROFILES)


def get(year: int) -> dict:
    if year not in PROFILES:
        raise SystemExit(f'No election profile for {year}. Simulated years: {years()}')
    return PROFILES[year]


def names_re(year: int):
    return re.compile(get(year)['names_re'], re.I)
