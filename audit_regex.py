import sys
sys.path.insert(0, '.')
from filters.tier1 import EXCLUDE_YOE_PATTERNS, EXCLUDE_TITLE_PATTERNS, AUTO_PASS_TITLE_PATTERNS, INCLUDE_TITLE_PATTERNS, _matches_any

print('='*60)
print('TIER 1 REGEX AUDIT - CRITICAL EDGE CASES')
print('='*60)

all_good = True

# ---- YOE TESTS ----
should_reject = [
    ('3+ years of experience', 'explicit 3+'),
    ('5 years of professional software development experience', 'long phrase'),
    ('2+ years of experience', '2+ is too senior'),
    ('2-3 years of experience', 'range starting at 2 going up'),
    ('3-5 years experience', 'range 3-5'),
    ('minimum 3 years', 'explicit minimum'),
    ('at least 4 years of experience', 'at least'),
    ('requires 5 years', 'requires keyword'),
    ('3 years required', 'reversed phrasing'),
    ('over 2 years of experience', 'over 2'),
    ('more than 2 years', 'more than 2'),
    ('10+ years of experience', 'double digit'),
    ('three years of experience', 'written out'),
    ('five or more years', 'written out with or more'),
    ('2 to 5 years of experience', '2 to 5'),
    ('between 2 and 5 years', 'between 2 and 5'),
    ('8+ years of hands-on software engineering experience', 'long complex'),
    ('2+ yoe', '2+ YOE abbreviation'),
    ('5+ yrs of experience', 'yrs abbreviation'),
    ('two or more years', 'written two'),
    ('minimum 2+ years', 'minimum 2+'),
]

should_pass = [
    ('1-3 years of experience', '1-3 range, user qualifies'),
    ('0-2 years of experience', '0-2 range, user qualifies'),
    ('1 year of experience', '1 year'),
    ('2 years of experience', 'exactly 2 years, user qualifies'),
    ('1-2 years', '1-2 range'),
    ('up to 2 years of experience', 'up to 2'),
    ('No experience required', 'no experience'),
    ('', 'empty description'),
    ('looking for a motivated engineer', 'no YOE mentioned at all'),
    ('1+ years of experience', '1+ is fine'),
    ('Some relevant experience in software engineering', 'vague experience'),
]

print()
print('--- SHOULD BE REJECTED (high YOE) ---')
for text, label in should_reject:
    matched = _matches_any(text, EXCLUDE_YOE_PATTERNS)
    status = 'PASS' if matched else '** FAIL **'
    if not matched:
        all_good = False
    print(f'  [{status}] "{text}" ({label})')

print()
print('--- SHOULD BE ALLOWED (within YOE) ---')
for text, label in should_pass:
    matched = _matches_any(text, EXCLUDE_YOE_PATTERNS)
    status = 'PASS' if not matched else '** FAIL **'
    if matched:
        all_good = False
    print(f'  [{status}] "{text}" ({label})')

# ---- TITLE TESTS ----
print()
print('--- TITLE EXCLUSIONS ---')
title_reject = [
    'Software Engineer Intern',
    'Summer 2026 Software Developer Internship',
    'Software Engineer II',
    'Software Engineer III',
    'Senior Software Engineer',
    'Staff Software Developer',
    'Software Engineer, iOS',
    'DevOps Engineer',
    'Software Engineer Co-op',
]
for t in title_reject:
    inc = _matches_any(t, INCLUDE_TITLE_PATTERNS)
    exc = _matches_any(t, EXCLUDE_TITLE_PATTERNS)
    blocked = (not inc) or exc
    status = 'PASS' if blocked else '** FAIL **'
    if not blocked:
        all_good = False
    print(f'  [{status}] BLOCKED: "{t}"')

print()
print('--- TITLE AUTO-PASS ---')
title_auto = [
    'Junior Software Engineer',
    'Software Engineer I',
    'Software Engineer 1',
    'Entry Level Software Developer',
    'New Grad Software Engineer',
    'Associate Software Developer',
    'Graduate Software Engineer',
]
for t in title_auto:
    inc = _matches_any(t, INCLUDE_TITLE_PATTERNS)
    exc = _matches_any(t, EXCLUDE_TITLE_PATTERNS)
    auto = _matches_any(t, AUTO_PASS_TITLE_PATTERNS)
    ok = inc and (not exc) and auto
    status = 'PASS' if ok else '** FAIL **'
    if not ok:
        all_good = False
        print(f'  [{status}] AUTO-PASS: "{t}" (inc={inc}, exc={exc}, auto={auto})')
    else:
        print(f'  [{status}] AUTO-PASS: "{t}"')

print()
print('--- SHOULD PASS THROUGH (no auto-pass, no block) ---')
title_through = [
    'Software Engineer',
    'Full Stack Developer',
    'Backend Engineer',
    'Python Developer',
    'AI Engineer',
    'Software Engineer, Backend',
    'Founding Software Engineer',
]
for t in title_through:
    inc = _matches_any(t, INCLUDE_TITLE_PATTERNS)
    exc = _matches_any(t, EXCLUDE_TITLE_PATTERNS)
    ok = inc and (not exc)
    status = 'PASS' if ok else '** FAIL **'
    if not ok:
        all_good = False
        print(f'  [{status}] PASS-THROUGH: "{t}" (inc={inc}, exc={exc})')
    else:
        print(f'  [{status}] PASS-THROUGH: "{t}"')

print()
if all_good:
    print('ALL TESTS PASSED!')
else:
    print('SOME TESTS FAILED - SEE ABOVE')
