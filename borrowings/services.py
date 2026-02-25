from datetime import date


def calculate_overdue_days(*, expected: date, returned: date) -> int:
    if returned <= expected:
        return 0
    return (returned - expected).days
