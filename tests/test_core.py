"""Tests for askr. Run with: pytest"""

import dataclasses
from collections.abc import Iterable, Iterator
from datetime import date, datetime, time
from enum import Enum
from pathlib import Path

import pytest

import askr
from askr import core


@pytest.fixture(autouse=True)
def _reset_config() -> Iterator[None]:
    """Every test starts with English messages and automatic color."""
    askr.set_messages(askr.Messages())
    askr.set_color(None)
    yield
    askr.set_messages(askr.Messages())
    askr.set_color(None)


def feed(monkeypatch: pytest.MonkeyPatch, answers: Iterable[str]) -> list[str]:
    """Replace input() and getpass() with fixed answers; returns the prompts shown."""
    it = iter(answers)
    prompts: list[str] = []

    def fake(prompt: str = "") -> str:
        prompts.append(prompt)
        return next(it)

    monkeypatch.setattr("builtins.input", fake)
    monkeypatch.setattr(core, "getpass", fake)
    return prompts


# ask_yn

@pytest.mark.parametrize(("answers", "default", "expected"), [
    (["y"], True, True),
    (["YES"], False, True),
    (["n"], True, False),
    ([" No "], True, False),
    ([""], True, True),
    ([""], False, False),
    (["maybe", "y"], True, True),
])
def test_ask_yn(monkeypatch, answers, default, expected):
    feed(monkeypatch, answers)
    assert askr.ask_yn("?", default=default) is expected


def test_ask_yn_hint(monkeypatch):
    prompts = feed(monkeypatch, ["y", "y"])
    askr.ask_yn("Go?")
    askr.ask_yn("Go?", default=False)
    assert prompts == ["Go? Y/n: ", "Go? y/N: "]


# ask_int / ask_float

def test_ask_int_retries_until_valid(monkeypatch, capsys):
    feed(monkeypatch, ["abc", "", "1.5", "0", "11", "7"])
    assert askr.ask_int("n: ", min_value=1, max_value=10) == 7
    out = capsys.readouterr().out
    assert "whole number" in out
    assert "between 1 and 10" in out


def test_ask_int_one_sided_bounds(monkeypatch, capsys):
    feed(monkeypatch, ["-1", "5"])
    assert askr.ask_int("n: ", min_value=0) == 5
    assert "at least 0" in capsys.readouterr().out


def test_ask_int_returns_int(monkeypatch):
    feed(monkeypatch, [" 42 "])
    value = askr.ask_int("n: ")
    assert value == 42
    assert isinstance(value, int)


def test_ask_int_default(monkeypatch):
    prompts = feed(monkeypatch, ["   "])
    assert askr.ask_int("Age: ", default=18) == 18
    assert prompts == ["Age [18]: "]


def test_ask_int_default_zero(monkeypatch):
    feed(monkeypatch, [""])
    assert askr.ask_int("n: ", default=0) == 0


def test_ask_int_validator(monkeypatch, capsys):
    feed(monkeypatch, ["3", "4"])
    assert askr.ask_int("n: ", validator=lambda n: n % 2 == 0, error="Must be even.") == 4
    assert "Must be even." in capsys.readouterr().out


def test_validator_default_message(monkeypatch, capsys):
    feed(monkeypatch, ["3", "4"])
    askr.ask_int("n: ", validator=lambda n: n > 3)
    assert "Invalid entry." in capsys.readouterr().out


def test_ask_float_rejects_nan_and_inf(monkeypatch):
    feed(monkeypatch, ["nan", "inf", "-inf", "2.5"])
    assert askr.ask_float("x: ") == 2.5


def test_number_bounds_are_checked():
    with pytest.raises(ValueError, match="min_value"):
        askr.ask_int("n: ", min_value=10, max_value=1)


# max_attempts

def test_max_attempts(monkeypatch):
    feed(monkeypatch, ["a", "b", "c"])
    with pytest.raises(askr.TooManyAttemptsError):
        askr.ask_int("n: ", max_attempts=3)


def test_max_attempts_success_on_last_try(monkeypatch):
    feed(monkeypatch, ["a", "5"])
    assert askr.ask_int("n: ", max_attempts=2) == 5


def test_max_attempts_must_be_positive(monkeypatch):
    feed(monkeypatch, ["1"])
    with pytest.raises(ValueError):
        askr.ask_int("n: ", max_attempts=0)


@pytest.mark.parametrize("call", [
    lambda: askr.ask_yn("?", max_attempts=1),
    lambda: askr.ask_str("s: ", min_length=5, max_attempts=1),
    lambda: askr.ask_choice("?", ["A", "B"], max_attempts=1),
    lambda: askr.ask_email("e: ", max_attempts=1),
    lambda: askr.ask_date("d: ", max_attempts=1),
])
def test_max_attempts_everywhere(monkeypatch, call):
    feed(monkeypatch, ["xyz"])
    with pytest.raises(askr.TooManyAttemptsError):
        call()


# ask_str

def test_ask_str_length(monkeypatch, capsys):
    feed(monkeypatch, ["   ", "toolong", "ok"])
    assert askr.ask_str("s: ", min_length=1, max_length=4) == "ok"
    out = capsys.readouterr().out
    assert "cannot be empty" in out
    assert "between 1 and 4" in out


def test_ask_str_without_strip(monkeypatch):
    feed(monkeypatch, ["  hi  "])
    assert askr.ask_str("s: ", strip=False) == "  hi  "


def test_ask_str_allows_empty_by_default(monkeypatch):
    feed(monkeypatch, [""])
    assert askr.ask_str("s: ") == ""


def test_ask_str_default(monkeypatch):
    prompts = feed(monkeypatch, [""])
    assert askr.ask_str("Name: ", min_length=1, default="Lev") == "Lev"
    assert prompts == ["Name [Lev]: "]


def test_default_prompt_without_colon(monkeypatch):
    prompts = feed(monkeypatch, [""])
    askr.ask_str("Name?", default="Lev")
    assert prompts == ["Name? [Lev] "]


# ask_email

@pytest.mark.parametrize(("text", "expected"), [
    ("lev@Example.COM", "lev@example.com"),
    (" a.b+tag@mail.co.uk ", "a.b+tag@mail.co.uk"),
    ("hans@müller.de", "hans@müller.de"),
])
def test_ask_email_valid(monkeypatch, text, expected):
    feed(monkeypatch, [text])
    assert askr.ask_email("e: ") == expected


@pytest.mark.parametrize("text", [
    "plain", "a@b", "a@b.c", "a b@c.de", "a@@b.de", ".a@b.de", "a..b@c.de", "a@-b.de",
    "a@b.12", f"{'x' * 65}@b.de",
])
def test_ask_email_invalid(monkeypatch, capsys, text):
    feed(monkeypatch, [text, "ok@ok.de"])
    assert askr.ask_email("e: ") == "ok@ok.de"
    assert "valid email" in capsys.readouterr().out


def test_ask_email_allowed_domains(monkeypatch, capsys):
    feed(monkeypatch, ["a@gmail.com", "a@Prevolut.uk"])
    assert askr.ask_email("e: ", allowed_domains=["prevolut.uk", "@example.com"]) == "a@prevolut.uk"
    assert "example.com or prevolut.uk" in capsys.readouterr().out


def test_ask_email_empty_domains():
    with pytest.raises(ValueError):
        askr.ask_email("e: ", allowed_domains=[])


# ask_url

@pytest.mark.parametrize(("text", "expected"), [
    ("https://example.com/path?q=1", "https://example.com/path?q=1"),
    ("example.com", "https://example.com"),
    ("localhost:8000", "https://localhost:8000"),
    ("HTTP://Example.com", "HTTP://Example.com"),
])
def test_ask_url_valid(monkeypatch, text, expected):
    feed(monkeypatch, [text])
    assert askr.ask_url("u: ") == expected


@pytest.mark.parametrize("text", [
    "ftp://example.com", "https://", "https://exa mple.com", "https://example.com:99999",
    "https://-/", "",
])
def test_ask_url_invalid(monkeypatch, capsys, text):
    feed(monkeypatch, [text, "https://ok.de"])
    assert askr.ask_url("u: ") == "https://ok.de"
    assert "https:// or http://" in capsys.readouterr().out


def test_ask_url_without_add_scheme(monkeypatch):
    feed(monkeypatch, ["example.com", "http://example.com"])
    assert askr.ask_url("u: ", schemes="http", add_scheme=False) == "http://example.com"


# ask_confirm_text

@pytest.mark.parametrize(("answer", "case_sensitive", "expected"), [
    ("delete", True, True),
    (" delete ", True, True),
    ("DELETE", True, False),
    ("DELETE", False, True),
    ("", True, False),
])
def test_ask_confirm_text(monkeypatch, answer, case_sensitive, expected):
    feed(monkeypatch, [answer])
    assert askr.ask_confirm_text("?", "delete", case_sensitive=case_sensitive) is expected


# ask_choice / ask_enum / ask_multi_choice

OPTIONS = ["Easy", "Medium", "Hard"]


@pytest.mark.parametrize(("answers", "expected"), [
    (["1"], "Easy"),
    (["hard"], "Hard"),
    (["0", "4", "x", "²", "2"], "Medium"),
])
def test_ask_choice(monkeypatch, answers, expected):
    feed(monkeypatch, answers)
    assert askr.ask_choice("?", OPTIONS) == expected


def test_ask_choice_default(monkeypatch, capsys):
    feed(monkeypatch, [""])
    assert askr.ask_choice("?", OPTIONS, default="Medium") == "Medium"
    assert "2. Medium (default)" in capsys.readouterr().out


def test_ask_choice_default_first_option(monkeypatch):
    feed(monkeypatch, [""])
    assert askr.ask_choice("?", OPTIONS, default="Easy") == "Easy"


def test_ask_choice_prefers_names_over_numbers(monkeypatch):
    feed(monkeypatch, ["2"])
    assert askr.ask_choice("?", ["2", "1"]) == "2"


def test_ask_choice_invalid_arguments():
    with pytest.raises(ValueError):
        askr.ask_choice("?", [])
    with pytest.raises(ValueError):
        askr.ask_choice("?", OPTIONS, default="Nightmare")
    with pytest.raises(ValueError, match="duplicates"):
        askr.ask_choice("?", ["a", "A"])
    with pytest.raises(TypeError):
        askr.ask_choice("?", "abc")


class Color(Enum):
    RED = "red"
    DARK_GREEN = "dark green"


class Level(Enum):
    LOW = 1
    HIGH = 2


@pytest.mark.parametrize(("answer", "expected"), [
    ("1", Color.RED),
    ("dark green", Color.DARK_GREEN),
    ("DARK_GREEN", Color.DARK_GREEN),
    ("red", Color.RED),
])
def test_ask_enum(monkeypatch, answer, expected):
    feed(monkeypatch, [answer])
    assert askr.ask_enum("?", Color) is expected


def test_ask_enum_labels_and_default(monkeypatch, capsys):
    feed(monkeypatch, ["", ])
    assert askr.ask_enum("?", Level, default=Level.HIGH) is Level.HIGH
    out = capsys.readouterr().out
    assert "1. LOW" in out
    assert "2. HIGH (default)" in out


def test_ask_enum_invalid_default():
    with pytest.raises(ValueError):
        askr.ask_enum("?", Level, default=Color.RED)  # type: ignore[arg-type]


@pytest.mark.parametrize(("answer", "expected"), [
    ("1, 3", ["Easy", "Hard"]),
    ("3,1,1", ["Easy", "Hard"]),
    ("1-3", ["Easy", "Medium", "Hard"]),
    ("hard, 1-2", ["Easy", "Medium", "Hard"]),
    ("medium", ["Medium"]),
])
def test_ask_multi_choice(monkeypatch, answer, expected):
    feed(monkeypatch, [answer])
    assert askr.ask_multi_choice("?", OPTIONS) == expected


def test_ask_multi_choice_errors(monkeypatch, capsys):
    feed(monkeypatch, ["", "1, x", "3-1", "1-4", "1,2,3", "2"])
    assert askr.ask_multi_choice("?", OPTIONS, max_selections=2) == ["Medium"]
    out = capsys.readouterr().out
    assert out.count("between 1 and 2") == 2  # empty answer and three options
    assert "'x' is not a valid option." in out
    assert "'3-1' is not a valid option." in out
    assert "'1-4' is not a valid option." in out


def test_ask_multi_choice_minimum_message(monkeypatch, capsys):
    feed(monkeypatch, ["", "1"])
    askr.ask_multi_choice("?", OPTIONS)
    assert "must be at least 1" in capsys.readouterr().out


def test_ask_multi_choice_optional(monkeypatch):
    feed(monkeypatch, [""])
    assert askr.ask_multi_choice("?", OPTIONS, min_selections=0) == []


def test_ask_multi_choice_default(monkeypatch, capsys):
    feed(monkeypatch, [""])
    assert askr.ask_multi_choice("?", OPTIONS, default=["Hard", "Easy"]) == ["Easy", "Hard"]
    out = capsys.readouterr().out
    assert "1. Easy (default)" in out
    assert "2. Medium\n" in out


def test_ask_multi_choice_hyphenated_name(monkeypatch):
    feed(monkeypatch, ["sci-fi"])
    assert askr.ask_multi_choice("?", ["Drama", "Sci-Fi"]) == ["Sci-Fi"]


# ask_list

def test_ask_list_strings(monkeypatch):
    feed(monkeypatch, [" red, green ,, blue "])
    assert askr.ask_list("Colors: ") == ["red", "green", "blue"]


def test_ask_list_converts_items(monkeypatch, capsys):
    feed(monkeypatch, ["1, two, 3", "1, 2, 3"])
    assert askr.ask_list("Numbers: ", int) == [1, 2, 3]
    assert "'two' is not a valid entry." in capsys.readouterr().out


def test_ask_list_rules(monkeypatch, capsys):
    feed(monkeypatch, ["a", "a;b;a", "a;b;c;d", "a; b"])
    result = askr.ask_list("Tags: ", separator=";", min_items=2, max_items=3, unique=True)
    assert result == ["a", "b"]
    out = capsys.readouterr().out
    assert "between 2 and 3" in out
    assert "more than once" in out


def test_ask_list_default_and_validator(monkeypatch, capsys):
    prompts = feed(monkeypatch, ["", ])
    assert askr.ask_list("N: ", int, default=[1, 2]) == [1, 2]
    assert prompts == ["N [1, 2]: "]

    feed(monkeypatch, ["3, 1", "1, 3"])
    assert askr.ask_list("N: ", int, validator=lambda v: v == sorted(v), error="Sort!") == [1, 3]
    assert "Sort!" in capsys.readouterr().out


def test_ask_list_invalid_arguments():
    with pytest.raises(ValueError):
        askr.ask_list("x", separator="")
    with pytest.raises(ValueError):
        askr.ask_list("x", min_items=3, max_items=1)


# ask_password

def test_ask_password_reports_all_broken_rules(monkeypatch, capsys):
    feed(monkeypatch, ["abc", "Abcdefg1!", "Abcdefg1!"])
    result = askr.ask_password(confirm=True, min_length=8, require_upper=True,
                               require_lower=True, require_digit=True,
                               require_special=True)
    assert result == "Abcdefg1!"
    out = capsys.readouterr().out
    for rule in ("8 characters", "uppercase", "digit", "special"):
        assert rule in out
    assert "lowercase" not in out


def test_ask_password_confirmation_mismatch(monkeypatch, capsys):
    feed(monkeypatch, ["secret", "typo", "secret", "secret"])
    assert askr.ask_password(confirm=True) == "secret"
    assert "do not match" in capsys.readouterr().out


def test_ask_password_umlaut_counts_as_letter(monkeypatch):
    feed(monkeypatch, ["Äbc"])
    assert askr.ask_password(require_upper=True) == "Äbc"


def test_ask_password_pattern(monkeypatch, capsys):
    feed(monkeypatch, ["12345", "abcd", "1234"])
    assert askr.ask_password(pattern=r"\d{4}", pattern_hint="be 4 digits") == "1234"
    assert "be 4 digits" in capsys.readouterr().out


def test_ask_password_validator(monkeypatch, capsys):
    feed(monkeypatch, ["password", "tr0ub4dor"])
    result = askr.ask_password(validator=lambda p: p != "password", error="Too common.")
    assert result == "tr0ub4dor"
    assert "Too common." in capsys.readouterr().out


def test_ask_password_invalid_pattern():
    with pytest.raises(ValueError, match="regular expression"):
        askr.ask_password(pattern="[")


# ask_path

def test_ask_path_kinds(monkeypatch, tmp_path):
    file = tmp_path / "my file.txt"
    file.write_text("x")
    folder = tmp_path / "sub"
    folder.mkdir()

    feed(monkeypatch, ["", str(tmp_path / "missing"), str(folder), f"'{file}'"])
    assert askr.ask_path("f: ", kind="file") == file

    feed(monkeypatch, [str(file), str(folder)])
    assert askr.ask_path("d: ", kind="dir") == folder


def test_ask_path_new_file(monkeypatch, tmp_path):
    target = tmp_path / "new.txt"
    feed(monkeypatch, [str(target)])
    assert askr.ask_path("f: ", must_exist=False, kind="file") == target


def test_ask_path_expands_home(monkeypatch):
    feed(monkeypatch, ["~"])
    assert askr.ask_path("p: ").is_absolute()


def test_ask_path_default(monkeypatch):
    feed(monkeypatch, [""])
    assert askr.ask_path("p: ", default="~") == Path.home()


def test_ask_path_invalid_kind():
    with pytest.raises(ValueError):
        askr.ask_path("p: ", kind="folder")  # type: ignore[arg-type]


# ask_date / ask_time / ask_datetime

def test_ask_date_formats(monkeypatch, capsys):
    feed(monkeypatch, ["27/09/2026", "2026-02-30", "27.09.2026"])
    assert askr.ask_date("d: ", ("%Y-%m-%d", "%d.%m.%Y")) == date(2026, 9, 27)
    assert "2026-09-27 or 27.09.2026" in capsys.readouterr().out


@pytest.mark.parametrize(("kwargs", "message"), [
    ({"min_date": date(2025, 1, 1)}, "on or after 2025-01-01"),
    ({"max_date": date(2020, 1, 1)}, "on or before 2020-01-01"),
    ({"min_date": date(2025, 1, 1), "max_date": date(2025, 12, 31)},
     "between 2025-01-01 and 2025-12-31"),
])
def test_ask_date_range_messages(monkeypatch, capsys, kwargs, message):
    feed(monkeypatch, ["2024-06-15", "2019-06-15", "2025-06-15"])
    askr.ask_date("d: ", **kwargs)
    assert message in capsys.readouterr().out


def test_ask_date_bounds_use_first_format(monkeypatch, capsys):
    feed(monkeypatch, ["01.01.2020", "01.01.2030"])
    askr.ask_date("d: ", "%d.%m.%Y", min_date=date(2025, 1, 1))
    assert "on or after 01.01.2025" in capsys.readouterr().out


def test_ask_date_default(monkeypatch):
    prompts = feed(monkeypatch, [""])
    assert askr.ask_date("d: ", "%d.%m.%Y", default=date(2026, 9, 27)) == date(2026, 9, 27)
    assert prompts == ["d [27.09.2026]: "]


def test_ask_date_invalid_arguments():
    with pytest.raises(ValueError):
        askr.ask_date("d: ", formats=())
    with pytest.raises(ValueError):
        askr.ask_date("d: ", min_date=date(2026, 1, 2), max_date=date(2026, 1, 1))


def test_ask_time(monkeypatch, capsys):
    feed(monkeypatch, ["25:00", "07:30", "9:05"])
    assert askr.ask_time("t: ", min_time=time(8, 0)) == time(9, 5)
    out = capsys.readouterr().out
    assert "like 14:30" in out
    assert "not earlier than 08:00" in out


def test_ask_time_several_formats(monkeypatch):
    feed(monkeypatch, ["02:15 PM"])
    assert askr.ask_time("t: ", ("%H:%M", "%I:%M %p")) == time(14, 15)


def test_ask_datetime(monkeypatch, capsys):
    feed(monkeypatch, ["2026-09-27", "2026-09-27 23:00", "2026-09-27 18:45"])
    result = askr.ask_datetime("dt: ", max_datetime=datetime(2026, 9, 27, 20, 0))
    assert result == datetime(2026, 9, 27, 18, 45)
    out = capsys.readouterr().out
    assert "like 2026-09-27 14:30" in out
    assert "not later than 2026-09-27 20:00" in out


# Messages and color

def test_german_messages(monkeypatch, capsys):
    askr.set_messages(askr.Messages.german())
    prompts = feed(monkeypatch, ["vielleicht", "ja", "x", "5"])
    assert askr.ask_yn("Weiter?") is True
    assert askr.ask_int("Zahl: ") == 5
    out = capsys.readouterr().out
    assert "Bitte mit ja oder nein antworten." in out
    assert "ganze Zahl" in out
    assert prompts[0] == "Weiter? J/n: "


def test_single_message_override(monkeypatch, capsys):
    askr.set_messages(dataclasses.replace(askr.get_messages(), empty="Say something!"))
    feed(monkeypatch, ["", "hi"])
    askr.ask_str("s: ", min_length=1)
    assert "Say something!" in capsys.readouterr().out


def test_every_message_is_translated():
    english, german = askr.Messages(), askr.Messages.german()
    same = [f.name for f in dataclasses.fields(english)
            if getattr(english, f.name) == getattr(german, f.name)]
    assert same == []


def test_color_forced(monkeypatch, capsys):
    askr.set_color(True)
    feed(monkeypatch, ["x", "1"])
    askr.ask_int("n: ")
    assert "\033[31mInvalid entry" in capsys.readouterr().out


def test_color_off_when_not_a_terminal(monkeypatch, capsys):
    feed(monkeypatch, ["x", "1"])
    askr.ask_int("n: ")
    assert "\033[" not in capsys.readouterr().out


def test_no_color_env(monkeypatch):
    monkeypatch.setattr(core.sys.stdout, "isatty", lambda: True)
    monkeypatch.setenv("NO_COLOR", "1")
    assert core._use_color() is False
    monkeypatch.delenv("NO_COLOR")
    monkeypatch.setenv("TERM", "xterm")
    assert core._use_color() is True


# package

def test_public_api():
    public = {name for name in dir(askr) if not name.startswith("_")}
    public -= {"core", "messages"}
    assert sorted(askr.__all__) == sorted(public)
