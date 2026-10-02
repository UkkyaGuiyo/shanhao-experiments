"""Pure release preconditions; deliberately does not contain credentials or push code."""
from datetime import date
import re

def validate_weeks(weeks):
    if not isinstance(weeks, list) or not weeks or any(not isinstance(week, str) for week in weeks):
        raise ValueError("nonempty week list required")
    if weeks != sorted(set(weeks)):
        raise ValueError("duplicate or out-of-order week")
    for week in weeks:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", week) or date.fromisoformat(week).weekday() != 5:
            raise ValueError("week must be a Saturday's JST date")

def publication_allowed(*, expected_sha, actual_sha, week, completed, stopped=False,
                        locked=False, tests_passed=False, reviewed=False):
    validate_weeks([week])
    if not re.fullmatch(r"[0-9a-f]{40}", expected_sha):
        return False
    return (expected_sha == actual_sha and week not in completed and not stopped
            and locked and tests_passed and reviewed)
