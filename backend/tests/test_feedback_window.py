from datetime import date

from app.feedback_window import WindowState, closes_on, window_state

CLASS_DAY = date(2026, 3, 2)


def test_window_closes_seven_days_after_the_class():
    assert closes_on(CLASS_DAY) == date(2026, 3, 9)


def test_window_is_upcoming_before_the_class_day():
    assert window_state(CLASS_DAY, on=date(2026, 3, 1)) is WindowState.UPCOMING


def test_window_opens_on_the_class_day():
    assert window_state(CLASS_DAY, on=CLASS_DAY) is WindowState.OPEN


def test_window_is_still_open_on_the_last_day():
    assert window_state(CLASS_DAY, on=date(2026, 3, 9)) is WindowState.OPEN


def test_window_is_closed_the_day_after_the_deadline():
    assert window_state(CLASS_DAY, on=date(2026, 3, 10)) is WindowState.CLOSED
