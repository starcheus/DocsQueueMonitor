"""Extra parser cases for post-service-select availability."""

from __future__ import annotations

from app.domain.enums import CheckOutcome
from app.monitoring.parsers.pasport_html import parse_pasport_queue_html


def test_service_form_without_dates_is_not_available() -> None:
    html = """
    <html><body>
      <h1>Електронна черга</h1>
      <form name="services" id="services">
        <label>Оберіть послугу</label>
        <select name="service" id="service">
          <option value="">- Обрати -</option>
          <option value="4">Закордонний паспорт та (або) ID-картка</option>
        </select>
        <select name="date" id="date">
          <option value="">- Обрати -</option>
        </select>
      </form>
    </body></html>
    """
    outcome, reason = parse_pasport_queue_html(html)
    assert outcome != CheckOutcome.AVAILABLE
    assert outcome in {CheckOutcome.UNKNOWN, CheckOutcome.POSSIBLY_AVAILABLE}
    assert "service_form" in reason or "markers" in reason


def test_post_select_no_slots_message() -> None:
    html = """
    <html><body>
      <div role="alert">
        Вибачте, на даний момент всі місця зайняті!
        Вільні слоти з'являються у довільний час, кілька разів протягом доби.
      </div>
      <form name="services"><select name="service" id="service"></select></form>
    </body></html>
    """
    outcome, reason = parse_pasport_queue_html(html)
    assert outcome == CheckOutcome.NO_SLOTS
    assert "marker" in reason
