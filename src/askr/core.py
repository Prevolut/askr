"""Simple, validated input prompts for the terminal."""

import math
import os
import re
import sys
from collections.abc import Callable, Iterable, Sequence
from datetime import date, datetime, time
from enum import Enum
from getpass import getpass
from pathlib import Path
from typing import Any, Literal, TypeVar, overload
from urllib.parse import urlsplit

from .messages import Messages

T = TypeVar("T")
E = TypeVar("E", bound=Enum)
_Number = TypeVar("_Number", int, float)
_Temporal = TypeVar("_Temporal", date, time, datetime)

# Reference moment used to show the user an example for each accepted format.
# Day 27 cannot be a month, so day and month are never confused in the example.
_EXAMPLE_MOMENT = datetime(2026, 9, 27, 14, 30, 0)

# Pragmatic email check: something@domain.tld, no spaces, no second "@".
# Full RFC 5322 validation accepts addresses no real mail provider hands out.
# Domain labels may contain Unicode letters (e.g. "müller.de"); the TLD needs 2+ letters.
_EMAIL_RE = re.compile(r"[^@\s]+@(?:[^\W_](?:[\w-]*[^\W_])?\.)+[^\W\d_]{2,}")
_HOSTNAME_RE = re.compile(r"[\w.:-]+")

_RED = "\033[31m"
_RESET = "\033[0m"


class TooManyAttemptsError(Exception):
    """Raised when the user gave max_attempts invalid answers in a row."""


class _Invalid(Exception):
    """Raised by parsers; the message is shown to the user."""


# Configuration

_messages = Messages()
_color: bool | None = None


def set_messages(messages: Messages) -> None:
    """Replace all texts shown to the user, e.g. with Messages.german()."""
    global _messages
    _messages = messages


def get_messages() -> Messages:
    """Return the texts currently shown to the user."""
    return _messages


def set_color(enabled: bool | None) -> None:
    """Force colored error messages on (True) or off (False).

    None (the default) detects it automatically: errors are red when the
    output is a terminal and the NO_COLOR environment variable is not set.
    """
    global _color
    _color = enabled


# Yes / no

def ask_yn(prompt: str, default: bool = True, *, max_attempts: int | None = None) -> bool:
    """Ask a yes/no question until a valid answer is given.

    Accepts "y", "yes", "n" and "no" (case-insensitive, configurable via
    Messages). Pressing Enter without input returns the default.

    Args:
        prompt: The question shown to the user.
        default: The value returned when the user just presses Enter.
        max_attempts: Give up after this many invalid answers, or None to ask forever.

    Returns:
        True for yes, False for no.

    Raises:
        TooManyAttemptsError: If max_attempts invalid answers were given.
    """
    m = _messages
    hint = m.yes_no_hint_yes if default else m.yes_no_hint_no

    def parse(text: str) -> bool:
        answer = text.strip().lower()
        if answer in m.yes_answers:
            return True
        if answer in m.no_answers:
            return False
        raise _Invalid(m.yes_no_error)

    return _loop(lambda: input(f"{prompt} {hint}: "), parse,
                 default=default, max_attempts=max_attempts)


# Numbers

def ask_int(prompt: str, min_value: int | None = None, max_value: int | None = None, *,
            default: int | None = None, validator: Callable[[int], bool] | None = None,
            error: str | None = None, max_attempts: int | None = None) -> int:
    """Ask for a whole number until a valid one is entered.

    Args:
        prompt: The text shown to the user.
        min_value: The smallest accepted number (inclusive), or None.
        max_value: The largest accepted number (inclusive), or None.
        default: Returned when the user just presses Enter, or None.
        validator: Extra check; the number is rejected if it returns False.
        error: The message shown when validator returns False.
        max_attempts: Give up after this many invalid answers, or None to ask forever.

    Returns:
        The number entered by the user.

    Raises:
        ValueError: If min_value is greater than max_value.
        TooManyAttemptsError: If max_attempts invalid answers were given.
    """
    return _ask_number(prompt, int, _messages.invalid_int, min_value, max_value,
                       default, validator, error, max_attempts)


def ask_float(prompt: str, min_value: float | None = None, max_value: float | None = None, *,
              default: float | None = None, validator: Callable[[float], bool] | None = None,
              error: str | None = None, max_attempts: int | None = None) -> float:
    """Ask for a number (decimals allowed) until a valid one is entered.

    "nan" and "inf" are rejected. Arguments work like in ask_int.

    Returns:
        The number entered by the user.

    Raises:
        ValueError: If min_value is greater than max_value.
        TooManyAttemptsError: If max_attempts invalid answers were given.
    """
    return _ask_number(prompt, float, _messages.invalid_float, min_value, max_value,
                       default, validator, error, max_attempts)


# Text

def ask_str(prompt: str, min_length: int | None = None, max_length: int | None = None,
            strip: bool = True, *, default: str | None = None,
            validator: Callable[[str], bool] | None = None, error: str | None = None,
            max_attempts: int | None = None) -> str:
    """Ask for text until it meets the optional length requirements.

    Args:
        prompt: The text shown to the user.
        min_length: The minimum number of characters, or None. Use 1 to disallow empty input.
        max_length: The maximum number of characters, or None.
        strip: Remove leading and trailing whitespace before checking.
        default: Returned when the user just presses Enter, or None.
        validator: Extra check; the text is rejected if it returns False.
        error: The message shown when validator returns False.
        max_attempts: Give up after this many invalid answers, or None to ask forever.

    Returns:
        The text entered by the user.

    Raises:
        ValueError: If min_length is greater than max_length.
        TooManyAttemptsError: If max_attempts invalid answers were given.
    """
    _validate_bounds(min_length, max_length, "min_length", "max_length")
    m = _messages

    def parse(text: str) -> str:
        if strip:
            text = text.strip()
        if not text and min_length:
            raise _Invalid(m.empty)
        if not _check_range(len(text), min_length, max_length):
            raise _Invalid(m.length_range.format(range=_range_hint(min_length, max_length)))
        return text

    return _loop(_reader(prompt, default), parse, default=default, validator=validator,
                 error=error, max_attempts=max_attempts)


def ask_email(prompt: str, *, allowed_domains: Iterable[str] | None = None,
              default: str | None = None, validator: Callable[[str], bool] | None = None,
              error: str | None = None, max_attempts: int | None = None) -> str:
    """Ask for an email address until a plausible one is entered.

    The check is intentionally pragmatic (name@domain.tld). The domain part
    is returned in lowercase.

    Args:
        prompt: The text shown to the user.
        allowed_domains: Only accept addresses from these domains, or None for any.
        default, validator, error, max_attempts: See ask_str.

    Returns:
        The email address entered by the user.

    Raises:
        TooManyAttemptsError: If max_attempts invalid answers were given.
    """
    m = _messages
    allowed = None if allowed_domains is None else {d.lower().lstrip("@") for d in allowed_domains}
    if allowed is not None and not allowed:
        raise ValueError("allowed_domains must not be empty")

    def parse(text: str) -> str:
        text = text.strip()
        if len(text) > 254 or not _EMAIL_RE.fullmatch(text):
            raise _Invalid(m.invalid_email)
        local, domain = text.rsplit("@", 1)
        if len(local) > 64 or ".." in text or local.startswith(".") or local.endswith("."):
            raise _Invalid(m.invalid_email)
        domain = domain.lower()
        if allowed is not None and domain not in allowed:
            raise _Invalid(m.email_domain.format(domains=_join_or(sorted(allowed))))
        return f"{local}@{domain}"

    return _loop(_reader(prompt, default), parse, default=default, validator=validator,
                 error=error, max_attempts=max_attempts)


def ask_url(prompt: str, *, schemes: Sequence[str] = ("https", "http"), add_scheme: bool = True,
            default: str | None = None, validator: Callable[[str], bool] | None = None,
            error: str | None = None, max_attempts: int | None = None) -> str:
    """Ask for a web address until a valid one is entered.

    Args:
        prompt: The text shown to the user.
        schemes: Accepted schemes. The first one is added if add_scheme is True.
        add_scheme: Turn "example.com" into "https://example.com".
        default, validator, error, max_attempts: See ask_str.

    Returns:
        The URL entered by the user, including the scheme.

    Raises:
        ValueError: If schemes is empty.
        TooManyAttemptsError: If max_attempts invalid answers were given.
    """
    if isinstance(schemes, str):
        schemes = (schemes,)
    if not schemes:
        raise ValueError("schemes must not be empty")
    accepted = tuple(s.lower() for s in schemes)
    m = _messages
    message = m.invalid_url.format(schemes=_join_or([f"{s}://" for s in accepted]))

    def parse(text: str) -> str:
        text = text.strip()
        if not text or any(c.isspace() for c in text):
            raise _Invalid(message)
        if add_scheme and "://" not in text:
            text = f"{accepted[0]}://{text}"
        try:
            parts = urlsplit(text)
            parts.port  # noqa: B018  # raises ValueError for an invalid port
        except ValueError:
            raise _Invalid(message) from None
        host = parts.hostname
        if (parts.scheme.lower() not in accepted or not host
                or not _HOSTNAME_RE.fullmatch(host) or not any(c.isalnum() for c in host)):
            raise _Invalid(message)
        return text

    return _loop(_reader(prompt, default), parse, default=default, validator=validator,
                 error=error, max_attempts=max_attempts)


def ask_confirm_text(prompt: str, expected: str, *, case_sensitive: bool = True) -> bool:
    """Ask the user to type a word to confirm a dangerous action.

    Asks only once: anything but the expected text counts as "no".

        if ask_confirm_text("Type 'delete' to confirm: ", "delete"):
            ...

    Args:
        prompt: The text shown to the user.
        expected: The exact text the user has to type.
        case_sensitive: Require the same upper and lower case.

    Returns:
        True if the user typed the expected text.
    """
    answer = input(prompt).strip()
    if case_sensitive:
        return answer == expected
    return answer.casefold() == expected.casefold()


# Passwords

def ask_password(prompt: str = "Password: ", confirm: bool = False,
                 min_length: int | None = None,
                 require_upper: bool = False, require_lower: bool = False,
                 require_digit: bool = False, require_special: bool = False,
                 pattern: str | None = None, pattern_hint: str | None = None, *,
                 validator: Callable[[str], bool] | None = None, error: str | None = None,
                 max_attempts: int | None = None) -> str:
    """Ask for a password without showing it on screen.

    All rules the password breaks are reported at once.

    Args:
        prompt: The text shown to the user.
        confirm: Ask a second time and require both entries to match.
        min_length: The minimum number of characters, or None.
        require_upper: Require at least one uppercase letter.
        require_lower: Require at least one lowercase letter.
        require_digit: Require at least one digit.
        require_special: Require at least one character that is neither a
            letter, a digit nor whitespace (e.g. ! ? # _).
        pattern: A regular expression the whole password must match.
        pattern_hint: The rule shown if pattern does not match.
        validator, error, max_attempts: See ask_str.

    Returns:
        The password entered by the user.

    Raises:
        ValueError: If pattern is not a valid regular expression.
        TooManyAttemptsError: If max_attempts invalid answers were given.
    """
    m = _messages
    rules: list[tuple[Callable[[str], bool], str]] = []
    if min_length is not None:
        rules.append((lambda p: len(p) >= min_length, m.password_min_length.format(n=min_length)))
    if require_upper:
        rules.append((lambda p: any(c.isupper() for c in p), m.password_upper))
    if require_lower:
        rules.append((lambda p: any(c.islower() for c in p), m.password_lower))
    if require_digit:
        rules.append((lambda p: any(c.isdigit() for c in p), m.password_digit))
    if require_special:
        rules.append((lambda p: any(not c.isalnum() and not c.isspace() for c in p),
                      m.password_special))
    if pattern is not None:
        try:
            compiled = re.compile(pattern)
        except re.error as exc:
            raise ValueError(f"pattern is not a valid regular expression: {exc}") from None
        rules.append((lambda p: compiled.fullmatch(p) is not None,
                      pattern_hint or m.password_pattern))

    def parse(password: str) -> str:
        broken = [message for check, message in rules if not check(password)]
        if broken:
            raise _Invalid("\n".join([m.password_header, *(f"  - {b}" for b in broken)]))
        if confirm and getpass(m.password_repeat) != password:
            raise _Invalid(m.password_mismatch)
        return password

    return _loop(lambda: getpass(prompt), parse, validator=validator, error=error,
                 max_attempts=max_attempts)


# Choices

def ask_choice(prompt: str, options: Sequence[str], default: str | None = None, *,
               max_attempts: int | None = None) -> str:
    """Show a numbered list and ask the user to pick one option.

    The user can answer with the option's number or its name (case-insensitive).

    Args:
        prompt: The question shown above the list.
        options: The options to choose from.
        default: An option returned when the user just presses Enter, or None.
        max_attempts: Give up after this many invalid answers, or None to ask forever.

    Returns:
        The chosen option, exactly as given in options.

    Raises:
        TypeError: If options is a single string instead of a list.
        ValueError: If options is empty, contains duplicates, or default is not an option.
        TooManyAttemptsError: If max_attempts invalid answers were given.
    """
    _validate_options(options)
    if default is not None and default not in options:
        raise ValueError("default must be one of the options")
    default_index = None if default is None else options.index(default)
    return options[_ask_index(prompt, list(options), [], default_index, max_attempts)]


def ask_enum(prompt: str, enum: type[E], default: E | None = None, *,
             max_attempts: int | None = None) -> E:
    """Show the members of an Enum and ask the user to pick one.

    Members are listed by their value if it is a string, otherwise by name.
    The user can answer with the number, the name or the value.

    Args:
        prompt: The question shown above the list.
        enum: The Enum class to choose from.
        default: A member returned when the user just presses Enter, or None.
        max_attempts: Give up after this many invalid answers, or None to ask forever.

    Returns:
        The chosen Enum member.

    Raises:
        ValueError: If the Enum has no members or default is not a member.
        TooManyAttemptsError: If max_attempts invalid answers were given.
    """
    members = list(enum)
    if not members:
        raise ValueError("enum must have at least one member")
    if default is not None and default not in members:
        raise ValueError("default must be a member of enum")
    labels = [str(member.value) if isinstance(member.value, str) else member.name
              for member in members]
    aliases = [member.name for member in members]
    index = _ask_index(prompt, labels, aliases,
                       None if default is None else members.index(default), max_attempts)
    return members[index]


def ask_multi_choice(prompt: str, options: Sequence[str], *, min_selections: int | None = 1,
                     max_selections: int | None = None, default: Sequence[str] | None = None,
                     max_attempts: int | None = None) -> list[str]:
    """Show a numbered list and let the user pick several options.

    Answers are separated by commas and can be numbers, names or number
    ranges, e.g. "1, 3" or "1-3" or "Easy, Hard".

    Args:
        prompt: The question shown above the list.
        options: The options to choose from.
        min_selections: The minimum number of options to pick, or None.
        max_selections: The maximum number of options to pick, or None.
        default: Options returned when the user just presses Enter, or None.
        max_attempts: Give up after this many invalid answers, or None to ask forever.

    Returns:
        The chosen options, in the order of options, without duplicates.

    Raises:
        TypeError: If options is a single string instead of a list.
        ValueError: For invalid options, bounds or default.
        TooManyAttemptsError: If max_attempts invalid answers were given.
    """
    _validate_options(options)
    _validate_bounds(min_selections, max_selections, "min_selections", "max_selections")
    if default is not None and any(d not in options for d in default):
        raise ValueError("every default must be one of the options")
    m = _messages
    labels = list(options)
    defaults = set() if default is None else {labels.index(d) for d in default}
    _show_options(prompt, labels, defaults)

    def parse(text: str) -> list[str]:
        selected: set[int] = set()
        for part in (p.strip() for p in text.split(",")):
            if not part:
                continue
            index = _resolve_option(part, labels, [])
            if index is not None:
                selected.add(index)
                continue
            span = _parse_span(part, len(labels))
            if span is None:
                raise _Invalid(m.invalid_selection.format(part=part))
            selected.update(span)
        if not _check_range(len(selected), min_selections, max_selections):
            raise _Invalid(m.selection_count.format(
                range=_range_hint(min_selections, max_selections)))
        return [labels[i] for i in sorted(selected)]

    chosen_default = None if default is None else [labels[i] for i in sorted(defaults)]
    return _loop(lambda: input(m.choice_prompt), parse, default=chosen_default,
                 max_attempts=max_attempts)


# Lists

@overload
def ask_list(prompt: str, item: Callable[[str], T], *, separator: str = ",",
             min_items: int | None = None, max_items: int | None = None, unique: bool = False,
             default: list[T] | None = None, validator: Callable[[list[T]], bool] | None = None,
             error: str | None = None, max_attempts: int | None = None) -> list[T]: ...
@overload
def ask_list(prompt: str, *, separator: str = ",",
             min_items: int | None = None, max_items: int | None = None, unique: bool = False,
             default: list[str] | None = None, validator: Callable[[list[str]], bool] | None = None,
             error: str | None = None, max_attempts: int | None = None) -> list[str]: ...
def ask_list(prompt: str, item: Callable[[str], Any] = str, *, separator: str = ",",
             min_items: int | None = None, max_items: int | None = None, unique: bool = False,
             default: list[Any] | None = None, validator: Callable[[list[Any]], bool] | None = None,
             error: str | None = None, max_attempts: int | None = None) -> list[Any]:
    """Ask for several values in one line, e.g. "red, green, blue".

    Empty entries are ignored and whitespace around each entry is removed.

    Args:
        prompt: The text shown to the user.
        item: Converts each entry, e.g. int or float. A ValueError marks it as invalid.
        separator: The text between entries.
        min_items: The minimum number of entries, or None.
        max_items: The maximum number of entries, or None.
        unique: Reject lists that contain the same value twice.
        default: Returned when the user just presses Enter, or None.
        validator: Extra check on the whole list; rejected if it returns False.
        error: The message shown when validator returns False.
        max_attempts: Give up after this many invalid answers, or None to ask forever.

    Returns:
        The converted entries.

    Raises:
        ValueError: If separator is empty or min_items is greater than max_items.
        TooManyAttemptsError: If max_attempts invalid answers were given.
    """
    if not separator:
        raise ValueError("separator must not be empty")
    _validate_bounds(min_items, max_items, "min_items", "max_items")
    m = _messages

    def parse(text: str) -> list[Any]:
        values: list[Any] = []
        for entry in (e.strip() for e in text.split(separator)):
            if not entry:
                continue
            try:
                values.append(item(entry))
            except ValueError:
                raise _Invalid(m.invalid_list_item.format(item=entry)) from None
        if not _check_range(len(values), min_items, max_items):
            raise _Invalid(m.list_count.format(range=_range_hint(min_items, max_items)))
        if unique and _has_duplicates(values):
            raise _Invalid(m.list_duplicates)
        return values

    shown = None if default is None else f"{separator} ".join(str(v) for v in default)
    return _loop(_reader(prompt, shown), parse, default=default, validator=validator,
                 error=error, max_attempts=max_attempts)


# Paths

def ask_path(prompt: str, must_exist: bool = True,
             kind: Literal["any", "file", "dir"] = "any", *,
             default: str | Path | None = None, validator: Callable[[Path], bool] | None = None,
             error: str | None = None, max_attempts: int | None = None) -> Path:
    """Ask for a file system path until a valid one is entered.

    Surrounding quotes and a leading "~" are handled, so paths pasted or
    dragged in from a file manager work as expected.

    Args:
        prompt: The text shown to the user.
        must_exist: Require the path to exist.
        kind: "file" or "dir" to accept only files or folders, "any" for both.
            Only checked if the path exists.
        default, validator, error, max_attempts: See ask_str.

    Returns:
        The entered path, with "~" expanded.

    Raises:
        ValueError: If kind is not "any", "file" or "dir".
        TooManyAttemptsError: If max_attempts invalid answers were given.
    """
    if kind not in ("any", "file", "dir"):
        raise ValueError('kind must be "any", "file" or "dir"')
    m = _messages

    def parse(text: str) -> Path:
        raw = text.strip().strip("'\"")
        if not raw:
            raise _Invalid(m.path_empty)
        # Terminals on macOS and Linux escape spaces as "\ " on drag and drop.
        # On Windows a backslash is the path separator and must stay untouched.
        if os.name != "nt":
            raw = raw.replace("\\ ", " ")
        path = Path(raw).expanduser()
        if must_exist and not path.exists():
            raise _Invalid(m.path_missing)
        if path.exists() and kind == "file" and not path.is_file():
            raise _Invalid(m.path_not_file)
        if path.exists() and kind == "dir" and not path.is_dir():
            raise _Invalid(m.path_not_dir)
        return path

    default_path = None if default is None else Path(default).expanduser()
    return _loop(_reader(prompt, default), parse, default=default_path, validator=validator,
                 error=error, max_attempts=max_attempts)


# Dates and times

def ask_date(prompt: str, formats: str | Sequence[str] = "%Y-%m-%d",
             min_date: date | None = None, max_date: date | None = None, *,
             default: date | None = None, validator: Callable[[date], bool] | None = None,
             error: str | None = None, max_attempts: int | None = None) -> date:
    """Ask for a date in one of the accepted formats.

    Args:
        prompt: The text shown to the user.
        formats: One strftime format or several, tried in order,
            e.g. ("%Y-%m-%d", "%d.%m.%Y").
        min_date: The earliest accepted date, or None.
        max_date: The latest accepted date, or None.
        default, validator, error, max_attempts: See ask_str.

    Returns:
        The entered date.

    Raises:
        ValueError: If formats is empty or min_date is later than max_date.
        TooManyAttemptsError: If max_attempts invalid answers were given.
    """
    m = _messages
    return _ask_temporal(prompt, formats, datetime.date, min_date, max_date,
                         m.invalid_date, m.date_range, m.date_after, m.date_before,
                         default, validator, error, max_attempts)


def ask_time(prompt: str, formats: str | Sequence[str] = "%H:%M",
             min_time: time | None = None, max_time: time | None = None, *,
             default: time | None = None, validator: Callable[[time], bool] | None = None,
             error: str | None = None, max_attempts: int | None = None) -> time:
    """Ask for a time of day in one of the accepted formats.

    Arguments work like in ask_date, e.g. formats=("%H:%M", "%I:%M %p").

    Returns:
        The entered time.

    Raises:
        ValueError: If formats is empty or min_time is later than max_time.
        TooManyAttemptsError: If max_attempts invalid answers were given.
    """
    m = _messages
    return _ask_temporal(prompt, formats, datetime.time, min_time, max_time,
                         m.invalid_time, m.time_range, m.time_after, m.time_before,
                         default, validator, error, max_attempts)


def ask_datetime(prompt: str, formats: str | Sequence[str] = "%Y-%m-%d %H:%M",
                 min_datetime: datetime | None = None, max_datetime: datetime | None = None, *,
                 default: datetime | None = None,
                 validator: Callable[[datetime], bool] | None = None,
                 error: str | None = None, max_attempts: int | None = None) -> datetime:
    """Ask for a date and time in one of the accepted formats.

    Arguments work like in ask_date. The result has no time zone.

    Returns:
        The entered date and time.

    Raises:
        ValueError: If formats is empty or min_datetime is later than max_datetime.
        TooManyAttemptsError: If max_attempts invalid answers were given.
    """
    m = _messages
    return _ask_temporal(prompt, formats, lambda moment: moment, min_datetime, max_datetime,
                         m.invalid_datetime, m.datetime_range, m.time_after, m.time_before,
                         default, validator, error, max_attempts)


# Internal helpers

def _loop(read: Callable[[], str], parse: Callable[[str], T], *, default: T | None = None,
          validator: Callable[[T], bool] | None = None, error: str | None = None,
          max_attempts: int | None = None) -> T:
    """Ask until parse and validator accept the answer; shared by all prompts."""
    if max_attempts is not None and max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")
    failures = 0
    while True:
        text = read()
        if default is not None and not text.strip():
            return default
        try:
            value = parse(text)
            if validator is not None and not validator(value):
                raise _Invalid(error or _messages.validator_failed)
            return value
        except _Invalid as exc:
            _print_error(str(exc))
            failures += 1
            if max_attempts is not None and failures >= max_attempts:
                raise TooManyAttemptsError(
                    f"no valid answer after {max_attempts} attempt(s)") from None


def _ask_number(prompt: str, converter: Callable[[str], _Number], invalid: str,
                min_value: float | None, max_value: float | None, default: _Number | None,
                validator: Callable[[_Number], bool] | None, error: str | None,
                max_attempts: int | None) -> _Number:
    """Shared implementation of ask_int and ask_float."""
    _validate_bounds(min_value, max_value, "min_value", "max_value")
    m = _messages

    def parse(text: str) -> _Number:
        try:
            value = converter(text)
        except ValueError:
            raise _Invalid(invalid) from None
        # "nan" and "inf" are valid for float() but never a sensible answer.
        if not math.isfinite(value):
            raise _Invalid(invalid)
        if not _check_range(value, min_value, max_value):
            raise _Invalid(m.number_range.format(range=_range_hint(min_value, max_value)))
        return value

    return _loop(_reader(prompt, default), parse, default=default, validator=validator,
                 error=error, max_attempts=max_attempts)


def _ask_temporal(prompt: str, formats: str | Sequence[str],
                  convert: Callable[[datetime], _Temporal],
                  min_value: _Temporal | None, max_value: _Temporal | None,
                  invalid: str, range_message: str, after: str, before: str,
                  default: _Temporal | None, validator: Callable[[_Temporal], bool] | None,
                  error: str | None, max_attempts: int | None) -> _Temporal:
    """Shared implementation of ask_date, ask_time and ask_datetime."""
    if isinstance(formats, str):
        formats = (formats,)
    if not formats:
        raise ValueError("formats must not be empty")
    _validate_bounds(min_value, max_value, "the minimum", "the maximum")
    first = formats[0]
    examples = _join_or([_EXAMPLE_MOMENT.strftime(fmt) for fmt in formats])

    def show(value: _Temporal) -> str:
        return value.strftime(first)

    def parse(text: str) -> _Temporal:
        text = text.strip()
        for fmt in formats:
            try:
                value = convert(datetime.strptime(text, fmt))
                break
            except ValueError:
                continue
        else:
            raise _Invalid(invalid.format(examples=examples))
        if not _check_range(value, min_value, max_value):
            hint = _range_hint(min_value, max_value, after, before, show)
            raise _Invalid(range_message.format(range=hint))
        return value

    shown = None if default is None else show(default)
    return _loop(_reader(prompt, shown), parse, default=default, validator=validator,
                 error=error, max_attempts=max_attempts)


def _ask_index(prompt: str, labels: list[str], aliases: list[str], default: int | None,
               max_attempts: int | None) -> int:
    """Show labels as a numbered list and return the index the user picked."""
    m = _messages
    _show_options(prompt, labels, set() if default is None else {default})

    def parse(text: str) -> int:
        index = _resolve_option(text.strip(), labels, aliases)
        if index is None:
            raise _Invalid(m.choice_error.format(count=len(labels)))
        return index

    return _loop(lambda: input(m.choice_prompt), parse, default=default,
                 max_attempts=max_attempts)


def _show_options(prompt: str, labels: Sequence[str], defaults: set[int]) -> None:
    """Print the question and a numbered list of options."""
    print(prompt)
    for number, label in enumerate(labels, start=1):
        marker = _messages.choice_default_marker if number - 1 in defaults else ""
        print(f"  {number}. {label}{marker}")


def _resolve_option(text: str, labels: Sequence[str], aliases: Sequence[str]) -> int | None:
    """Return the index for a label, alias or number, or None if nothing matches."""
    wanted = text.casefold()
    # Names are checked first, so an option called "2" is not mistaken for a number.
    for names in (labels, aliases):
        for index, name in enumerate(names):
            if name.casefold() == wanted:
                return index
    number = _parse_int(text)
    if number is not None and 1 <= number <= len(labels):
        return number - 1
    return None


def _parse_span(text: str, count: int) -> range | None:
    """Turn "2-4" into the indices 1, 2, 3, or return None if it is not a valid range."""
    start_text, dash, end_text = text.partition("-")
    start, end = _parse_int(start_text.strip()), _parse_int(end_text.strip())
    if not dash or start is None or end is None or not 1 <= start <= end <= count:
        return None
    return range(start - 1, end)


def _validate_options(options: Sequence[str]) -> None:
    """Raise if options cannot be shown as a list to choose from."""
    # A plain string is a Sequence[str] too, but would list single characters.
    if isinstance(options, str):
        raise TypeError("options must be a list of strings, not a single string")
    if not options:
        raise ValueError("options must not be empty")
    folded = [option.casefold() for option in options]
    if len(set(folded)) != len(folded):
        raise ValueError("options must not contain duplicates (ignoring case)")


def _reader(prompt: str, default: object) -> Callable[[], str]:
    """Return a function that asks with the default shown in brackets."""
    shown = prompt if default is None else _with_default(prompt, str(default))
    return lambda: input(shown)


def _with_default(prompt: str, shown: str) -> str:
    """Insert "[default]" before a trailing colon: "Age: " becomes "Age [18]: "."""
    text = prompt.rstrip()
    trailing = prompt[len(text):] or " "
    if text.endswith(":"):
        return f"{text[:-1]} [{shown}]:{trailing}"
    return f"{text} [{shown}]{trailing}"


def _print_error(message: str) -> None:
    """Print an error message, in red if the terminal supports it."""
    print(f"{_RED}{message}{_RESET}" if _use_color() else message)


def _use_color() -> bool:
    """Decide whether error messages are printed in color."""
    if _color is not None:
        return _color
    # https://no-color.org: any non-empty value disables color.
    if os.environ.get("NO_COLOR") or os.environ.get("TERM") == "dumb":
        return False
    return sys.stdout.isatty()


def _has_duplicates(values: list[Any]) -> bool:
    """Return True if any value occurs twice; works for unhashable values too."""
    return any(value in values[:index] for index, value in enumerate(values))


def _join_or(items: Sequence[str]) -> str:
    """Join items as "a, b or c"."""
    if len(items) <= 1:
        return "".join(items)
    return f"{', '.join(items[:-1])} {_messages.or_word} {items[-1]}"


def _parse_int(text: str) -> int | None:
    """Return text as an int, or None if it is not a whole number."""
    try:
        return int(text)
    except ValueError:
        return None


def _validate_bounds(min_value: Any, max_value: Any, min_name: str, max_name: str) -> None:
    """Raise ValueError if the lower bound is greater than the upper bound."""
    if min_value is not None and max_value is not None and min_value > max_value:
        raise ValueError(f"{min_name} must not be greater than {max_name}")


def _check_range(value: Any, min_value: Any, max_value: Any) -> bool:
    """Return True if value lies within the optional bounds."""
    return (min_value is None or value >= min_value) and (max_value is None or value <= max_value)


def _range_hint(min_value: Any, max_value: Any, at_least: str | None = None,
                at_most: str | None = None, show: Callable[[Any], str] = str) -> str:
    """Describe a range in words, e.g. 'at least 3' or 'between 1 and 10'."""
    m = _messages
    if min_value is None:
        return f"{at_most or m.at_most} {show(max_value)}"
    if max_value is None:
        return f"{at_least or m.at_least} {show(min_value)}"
    return m.between.format(min=show(min_value), max=show(max_value))
