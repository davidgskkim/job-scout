import sys
sys.path.insert(0, '.')
from filters.tier1 import EXCLUDE_YOE_PATTERNS, EXCLUDE_TITLE_PATTERNS, AUTO_PASS_TITLE_PATTERNS, INCLUDE_TITLE_PATTERNS, _matches_any, is_relevant

print('='*60)
print('COMPREHENSIVE TIER 1 AUDIT - RANGE VARIANTS')
print('='*60)

all_good = True

# Testing is_relevant directly because I want to test the full logic including potential pre-processing
def run_test_logic(text):
    job = {'title': 'Software Engineer', 'description': text, 'location': 'Remote'}
    passed, reason, _ = is_relevant(job)
    return passed, reason

# ---- RANGE TESTS ----
should_pass = [
    ('1 to 3 years of experience', '1 to 3'),
    ('0 to 5 years of experience', '0 to 5'),
    ('1 through 10 years of experience', '1 through 10 (user qualifies due to min of 1)'),
    ('zero to four years of experience', 'written zero to four'),
    ('1-15 years of experience', '1-15 range'),
    ('0 - 2 years experience', 'spaced hyphen'),
]

should_reject = [
    ('3 to 5 years of experience', '3 to 5 (min is 3)'),
    ('2 to 4 years of experience', '2 to 4 (user said lower bound > 1 is reject)'),
    ('3 through 7 years', '3 through 7'),
]

print('\n--- COMPLEX RANGES (Should Pass) ---')
for text, label in should_pass:
    passed, reason = run_test_logic(text)
    status = 'PASS' if passed else '** FAIL **'
    if not passed:
        all_good = False
    print(f'  [{status}] "{text}" ({label})')

print('\n--- COMPLEX RANGES (Should Reject) ---')
for text, label in should_reject:
    passed, reason = run_test_logic(text)
    status = 'PASS' if not passed else '** FAIL **'
    if passed:
        all_good = False
    print(f'  [{status}] "{text}" ({label})')

if all_good:
    print('\nALL TESTS PASSED!')
else:
    print('\nSOME TESTS FAILED')
