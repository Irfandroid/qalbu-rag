"""Turn Kemenag portal responses (JSON or HTML fragments) into verse records."""

import html
import re
from html.parser import HTMLParser
from typing import Any

import httpx

# Field labels used by the Kemenag "getAyat" HTML fragment.
HTML_FIELDS = (
    "Ayat ID",
    "Surah ID",
    "No Ayat",
    "No Juz",
    "Halaman",
    "Text MSI Usmani",
    "Transliterasi",
    "Terjemahan",
    "No Foot",
    "Teks Foot",
    "Keterangan",
    "Tafsir Ringkas",
    "Tafsir Tahlili",
)
# Any of these marks a JSON object as a verse record.
VERSE_MARKERS = ("Ayat ID", "No Ayat", "Text MSI Usmani")

_AYAH_ID_PATTERN = re.compile(r"(?=Ayat ID\s*:)", flags=re.IGNORECASE)
_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")


class TableParser(HTMLParser):
    """Collect table rows as flattened cell text, used as a last-resort parser."""

    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._cell = []

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._cell is not None and self._row is not None:
            self._row.append(" ".join("".join(self._cell).split()))
            self._cell = None
        elif tag == "tr" and self._row:
            self.rows.append(self._row)
            self._row = None


def parse_payload(response: httpx.Response) -> list[dict[str, Any]]:
    """Extract verse records from a JSON response, falling back to HTML parsing."""
    try:
        candidates = _candidate_dicts(response.json())
    except ValueError:
        candidates = _parse_labelled_html(response.text) or _parse_html_tables(response.text)
    if not candidates:
        raise RuntimeError("Kemenag API returned no ayat payload")
    return candidates


def _candidate_dicts(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        candidates = (
            [value] if any(key in value for key in VERSE_MARKERS) else []
        )
        for child in value.values():
            candidates.extend(_candidate_dicts(child))
        return candidates
    if isinstance(value, list):
        return [candidate for child in value for candidate in _candidate_dicts(child)]
    return []


def _parse_labelled_html(source: str) -> list[dict[str, Any]]:
    """Parse Kemenag's authenticated response, which is an HTML fragment, not JSON."""
    label = "|".join(re.escape(field) for field in HTML_FIELDS)
    field_pattern = re.compile(
        rf"(?P<label>{label})\s*:\s*(?:<b[^>]*>(?P<bold>.*?)</b>|(?P<plain>.*?))"
        r"(?=<br\s*/?>|$)",
        re.IGNORECASE | re.DOTALL,
    )
    records: list[dict[str, Any]] = []
    for fragment in _AYAH_ID_PATTERN.split(source)[1:]:
        record: dict[str, Any] = {}
        for match in field_pattern.finditer(fragment):
            value = match.group("bold") or match.group("plain") or ""
            value = _HTML_TAG_PATTERN.sub("", value)
            record[match.group("label")] = html.unescape(value).strip()
        if "Ayat ID" in record:
            records.append(record)
    return records


def _parse_html_tables(source: str) -> list[dict[str, Any]]:
    parser = TableParser()
    parser.feed(source)
    candidates: list[dict[str, Any]] = []
    for row in parser.rows:
        if len(row) >= 2:
            candidates.append(dict(zip(row[::2], row[1::2], strict=False)))
    for index, headers in enumerate(parser.rows[:-1]):
        next_row = parser.rows[index + 1]
        if len(headers) == len(next_row) and any("Ayat" in header for header in headers):
            candidates.append(dict(zip(headers, next_row, strict=True)))
    return candidates


def number(record: dict[str, Any], *fields: str) -> int | None:
    """Return the first non-empty integer field from ``record``."""
    for field in fields:
        value = record.get(field)
        if value is not None and str(value).strip().isdigit():
            return int(str(value).strip())
    return None


def text(record: dict[str, Any], *fields: str) -> str:
    """Return the first non-empty text field from ``record``."""
    for field in fields:
        value = record.get(field)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""
