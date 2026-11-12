"""Rules for daily issues dated 2026-11-13 onward.

Weekly issues, and anything before that date, are not limited here.
A daily issue uses 今日导读 and must contain 2 to 6 topic folders.
"""
from datetime import date

DAILY_TOPIC_MIN = 2
DAILY_TOPIC_MAX = 6
DAILY_RULE_FROM = date(2026, 11, 13)


def validate_topic_count(issue_name, daily, count):
    """Raise ValueError when a daily issue on or after the rule date is outside 2–6 topics."""
    if not daily:
        return
    try:
        year, month, day = (int(part) for part in str(issue_name).split('-'))
        issued = date(year, month, day)
    except (TypeError, ValueError) as error:
        raise ValueError(f'无法从 {issue_name} 读取日期') from error
    if issued >= DAILY_RULE_FROM and not (DAILY_TOPIC_MIN <= count <= DAILY_TOPIC_MAX):
        raise ValueError(
            f'{issue_name} 是每日课程，题材数必须在 {DAILY_TOPIC_MIN} 到 {DAILY_TOPIC_MAX} 之间，'
            f'现在是 {count} 个'
        )
