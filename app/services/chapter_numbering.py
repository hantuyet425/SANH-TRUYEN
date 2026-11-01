"""Normalize chapter numbering across multi-volume RAW files.

Volume headings are deliberately not treated as chapters. Chapter headings are
numbered by their appearance in the source, so a new volume that starts again
at chapter 1 continues the global sequence instead of resetting it.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any


_CN_DIGITS = {
    "零": 0, "〇": 0, "○": 0,
    "一": 1, "二": 2, "两": 2, "兩": 2,
    "三": 3, "四": 4, "五": 5, "六": 6,
    "七": 7, "八": 8, "九": 9,
}
_CN_SMALL_UNITS = {
    "十": 10, "百": 100, "千": 1000,
}
_CN_LARGE_UNITS = {
    "万": 10_000, "萬": 10_000,
    "亿": 100_000_000, "億": 100_000_000,
}
_CN_NUMBER_CHARS = "零〇○一二两兩三四五六七八九十百千万萬亿億"
_CN_NUMBER_PATTERN = r"[0-9０-９" + _CN_NUMBER_CHARS + r"]+"

# Match a chapter heading only when it occupies its own line. 卷/部/篇 are
# intentionally excluded: they are volume/part headings, not chapter headings.
_CHINESE_CHAPTER_RE = re.compile(
    r"^(?P<indent>[ 	]*)(?P<prefix>第[ 	]*)"
    r"(?P<number>" + _CN_NUMBER_PATTERN + r")"
    r"(?P<gap>[ 	]*)(?P<unit>章|章节|回|节|節|集|话|話)"
    r"(?P<suffix>.*)$"
)
_LOCAL_CHAPTER_RE = re.compile(
    r"^(?P<indent>[ 	]*)(?P<label>Chương|Chapter|Chap\.?|Hồi)"
    r"(?P<gap>[ 	]+)(?P<number>[0-9０-９]+)(?P<suffix>.*)$",
    re.IGNORECASE,
)


def _parse_number(value: str) -> int | None:
    """Parse Arabic/full-width digits or common Chinese numerals."""
    if not value:
        return None

    if all(char.isdigit() for char in value):
        try:
            return int("".join(str(unicodedata.digit(char)) for char in value))
        except (TypeError, ValueError):
            return None

    if all(char in _CN_DIGITS for char in value):
        return int("".join(str(_CN_DIGITS[char]) for char in value))

    total = 0
    section = 0
    number = 0
    for char in value:
        if char in _CN_DIGITS:
            number = _CN_DIGITS[char]
        elif char in _CN_SMALL_UNITS:
            unit = _CN_SMALL_UNITS[char]
            if number == 0 and unit == 10:
                number = 1
            section += number * unit
            number = 0
        elif char in _CN_LARGE_UNITS:
            section += number
            number = 0
            unit = _CN_LARGE_UNITS[char]
            if section == 0:
                section = 1
            total += section * unit
            section = 0
        else:
            return None
    return total + section + number


def _under_10_000_to_chinese(number: int) -> str:
    digits = "零一二三四五六七八九"
    units = ("", "十", "百", "千")
    if number == 0:
        return "零"

    result = []
    zero_pending = False
    for position in range(3, -1, -1):
        digit = (number // (10 ** position)) % 10
        if digit:
            if zero_pending and result:
                result.append("零")
            # Chinese normally writes 10–19 as 十/十一, not 一十/一十一.
            if not (position == 1 and digit == 1 and not result):
                result.append(digits[digit])
            result.append(units[position])
            zero_pending = False
        elif result and number % (10 ** position):
            zero_pending = True
    return "".join(result)


def _format_chinese_number(number: int) -> str:
    if number < 10_000:
        return _under_10_000_to_chinese(number)
    if number < 100_000_000:
        high, low = divmod(number, 10_000)
        result = _under_10_000_to_chinese(high) + "万"
        if low:
            if low < 1000:
                result += "零"
            result += _under_10_000_to_chinese(low)
        return result
    high, low = divmod(number, 100_000_000)
    result = _format_chinese_number(high) + "亿"
    if low:
        if low < 10_000_000:
            result += "零"
        result += _format_chinese_number(low)
    return result


def count_chapters(text: str) -> int:
    """Count recognizable chapter-heading lines in a text block."""
    count = 0
    for line in text.splitlines():
        body = line.rstrip("\r\n")
        match = _CHINESE_CHAPTER_RE.match(body) or _LOCAL_CHAPTER_RE.match(body)
        if match and _parse_number(match.group("number")) is not None:
            count += 1
    return count


def renumber_chapters(
    text: str,
    start_number: int = 1,
) -> tuple[str, dict[str, Any]]:
    """Renumber chapter headings continuously in their source order.

    The input is not modified on disk. The returned report contains chapter
    counts, how many headings changed, detected numbering resets, and a
    compact old/new mapping useful to the UI and tests.
    """
    if start_number < 1:
        raise ValueError("start_number phải lớn hơn hoặc bằng 1")

    output: list[str] = []
    mapping: list[dict[str, Any]] = []
    previous_original_number: int | None = None
    changed_count = 0
    reset_count = 0
    chapter_index = 0

    for original_line in text.splitlines(keepends=True):
        line_ending = ""
        line = original_line
        if line.endswith("\r\n"):
            line, line_ending = line[:-2], "\r\n"
        elif line.endswith("\n") or line.endswith("\r"):
            line, line_ending = line[:-1], original_line[-1:]

        match = _CHINESE_CHAPTER_RE.match(line)
        heading_kind = "chinese"
        if not match:
            match = _LOCAL_CHAPTER_RE.match(line)
            heading_kind = "local"

        if not match:
            output.append(original_line)
            continue

        original_number = _parse_number(match.group("number"))
        if original_number is None:
            output.append(original_line)
            continue

        chapter_index += 1
        global_number = start_number + chapter_index - 1
        is_reset = (
            previous_original_number is not None
            and original_number <= previous_original_number
        )
        if is_reset:
            reset_count += 1

        if heading_kind == "chinese":
            old_number_text = match.group("number")
            if any(char in _CN_NUMBER_CHARS for char in old_number_text):
                new_number_text = _format_chinese_number(global_number)
            else:
                new_number_text = str(global_number)
        else:
            new_number_text = str(global_number)

        if new_number_text != match.group("number"):
            changed_count += 1

        normalized_line = (
            line[:match.start("number")]
            + new_number_text
            + line[match.end("number"):]
        )
        output.append(normalized_line + line_ending)
        mapping.append({
            "old_number": original_number,
            "new_number": global_number,
            "reset": is_reset,
            "heading": line.strip(),
        })
        previous_original_number = original_number

    return "".join(output), {
        "chapter_count": chapter_index,
        "changed_count": changed_count,
        "reset_count": reset_count,
        "mapping": mapping,
    }
