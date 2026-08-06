"""HTML parser tests using fixtures."""

from __future__ import annotations

from pathlib import Path

from app.domain.enums import CheckOutcome
from app.monitoring.parsers.pasport_html import hash_normalized_html, parse_pasport_queue_html


def test_parse_no_slots(fixtures_dir: Path) -> None:
    html = (fixtures_dir / "no_slots.html").read_text(encoding="utf-8")
    outcome, reason = parse_pasport_queue_html(html)
    assert outcome == CheckOutcome.NO_SLOTS
    assert "marker" in reason


def test_parse_available(fixtures_dir: Path) -> None:
    html = (fixtures_dir / "available.html").read_text(encoding="utf-8")
    outcome, reason = parse_pasport_queue_html(html)
    assert outcome == CheckOutcome.AVAILABLE
    assert "markers" in reason


def test_parse_captcha(fixtures_dir: Path) -> None:
    html = (fixtures_dir / "captcha.html").read_text(encoding="utf-8")
    outcome, _reason = parse_pasport_queue_html(html)
    assert outcome == CheckOutcome.CAPTCHA


def test_parse_structure_changed(fixtures_dir: Path) -> None:
    html = (fixtures_dir / "structure_changed.html").read_text(encoding="utf-8")
    outcome, _reason = parse_pasport_queue_html(html)
    assert outcome == CheckOutcome.STRUCTURE_CHANGED


def test_empty_response() -> None:
    outcome, reason = parse_pasport_queue_html("   ")
    assert outcome == CheckOutcome.EMPTY_RESPONSE
    assert reason == "empty_body"


def test_hash_stable(fixtures_dir: Path) -> None:
    html = (fixtures_dir / "no_slots.html").read_text(encoding="utf-8")
    assert hash_normalized_html(html) == hash_normalized_html(html)
