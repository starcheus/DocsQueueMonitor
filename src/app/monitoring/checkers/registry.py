"""Factory for per-location availability checkers."""

from __future__ import annotations

from app.config import Settings
from app.database.models import Location
from app.domain.enums import CheckerType
from app.monitoring.checkers.api import ApiAvailabilityChecker
from app.monitoring.checkers.browser import BrowserAvailabilityChecker
from app.monitoring.checkers.disabled import DisabledAvailabilityChecker
from app.monitoring.checkers.html import HtmlAvailabilityChecker


class CheckerRegistry:
    def __init__(
        self,
        *,
        settings: Settings,
        browser: BrowserAvailabilityChecker | None = None,
        html: HtmlAvailabilityChecker | None = None,
    ) -> None:
        self._browser = browser
        self._html = html
        self._api = ApiAvailabilityChecker()
        self._disabled = DisabledAvailabilityChecker()
        self._settings = settings

    def get(self, location: Location) -> object:
        if not location.is_active:
            return self._disabled
        checker_type = CheckerType(location.checker_type)
        if checker_type == CheckerType.BROWSER:
            if self._browser is None:
                return self._disabled
            return self._browser
        if checker_type == CheckerType.HTML:
            if self._html is None:
                return self._disabled
            return self._html
        if checker_type == CheckerType.API:
            return self._api
        return self._disabled
