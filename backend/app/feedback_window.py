"""Ventana de feedback de una clase (D-022): del día de la clase al día +N, en APP_TIMEZONE."""

import enum
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.config import get_settings


class WindowState(enum.StrEnum):
    UPCOMING = "upcoming"  # la clase todavía no ocurrió
    OPEN = "open"  # se puede crear y editar feedback
    CLOSED = "closed"  # venció el plazo


def today() -> date:
    return datetime.now(ZoneInfo(get_settings().app_timezone)).date()


def closes_on(class_date: date) -> date:
    """Último día (inclusive) en que se puede crear o editar feedback."""
    return class_date + timedelta(days=get_settings().feedback_window_days)


def window_state(class_date: date, on: date | None = None) -> WindowState:
    current = on or today()
    if current < class_date:
        return WindowState.UPCOMING
    if current > closes_on(class_date):
        return WindowState.CLOSED
    return WindowState.OPEN
