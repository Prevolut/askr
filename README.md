# askr

Simple, validated input prompts for the terminal.

Every function keeps asking until the answer is valid, so you never have to write
another `while True` / `try` / `except ValueError` loop around `input()` again.

- No dependencies
- Fully typed (`py.typed`, checked with `mypy --strict`)
- Defaults, custom validators and attempt limits on every prompt
- All texts replaceable, German translation included

## Installation

```bash
pip install askr
```

Requires Python 3.10 or newer.

## Quick start

```python
from askr import ask_choice, ask_int, ask_yn

age = ask_int("Your age: ", min_value=0, max_value=120, default=18)
mode = ask_choice("Difficulty?", ["Easy", "Medium", "Hard"], default="Medium")

if ask_yn("Start the game?"):
    ...
```

What the user sees:

```
Your age [18]: abc
Invalid entry. Please enter a whole number.
Your age [18]: 200
The number must be between 0 and 120.
Your age [18]: 25
Difficulty?
  1. Easy
  2. Medium (default)
  3. Hard
Your choice: hard
Start the game? Y/n:
```

## All functions

| Function | Returns | Checks |
|---|---|---|
| `ask_yn` | `bool` | y / yes / n / no; Enter returns `default` |
| `ask_int` | `int` | whole number, optional `min_value` / `max_value` |
| `ask_float` | `float` | finite number, optional `min_value` / `max_value` |
| `ask_str` | `str` | optional `min_length` / `max_length`; strips whitespace by default |
| `ask_email` | `str` | `name@domain.tld`, optional `allowed_domains` |
| `ask_url` | `str` | `https://` / `http://` (configurable), adds the scheme if missing |
| `ask_choice` | `str` | one option, by number or name |
| `ask_multi_choice` | `list[str]` | several options: `1, 3`, `1-3` or names |
| `ask_enum` | `Enum` member | one member, by number, name or value |
| `ask_list` | `list` | comma-separated values, converted with `int`, `float`, ... |
| `ask_password` | `str` | hidden input, confirmation, length, character classes, regex |
| `ask_path` | `Path` | must exist (optional), file or folder only (optional) |
| `ask_date` | `date` | one or more formats, optional `min_date` / `max_date` |
| `ask_time` | `time` | one or more formats, optional `min_time` / `max_time` |
| `ask_datetime` | `datetime` | one or more formats, optional bounds |
| `ask_confirm_text` | `bool` | asks once: did the user type the exact word? |

## Examples

```python
from datetime import date
from enum import Enum
import askr

# Text, email and URL
name = askr.ask_str("Name: ", min_length=1, max_length=40)
email = askr.ask_email("Email: ", allowed_domains=["prevolut.uk"])
site = askr.ask_url("Website: ")                    # "example.com" -> "https://example.com"

# Several values at once
tags = askr.ask_list("Tags: ", unique=True)          # "python, cli" -> ["python", "cli"]
scores = askr.ask_list("Scores: ", int, min_items=3)
days = askr.ask_multi_choice("Days?", ["Mon", "Tue", "Wed", "Thu", "Fri"])  # "1-3, fri"

# Enums
class Size(Enum):
    SMALL = "small"
    LARGE = "large"

size = askr.ask_enum("Size?", Size, default=Size.SMALL)

# Passwords
password = askr.ask_password(confirm=True, min_length=8, require_upper=True,
                             require_digit=True, require_special=True)
pin = askr.ask_password("PIN: ", pattern=r"\d{4}", pattern_hint="be exactly 4 digits")

# Files, dates and times
config = askr.ask_path("Config file: ", kind="file")
birthday = askr.ask_date("Birthday: ", ("%Y-%m-%d", "%d.%m.%Y"), max_date=date.today())
alarm = askr.ask_time("Alarm: ", ("%H:%M", "%I:%M %p"))

# Safety check before something dangerous
if askr.ask_confirm_text("Type 'delete' to remove all data: ", "delete"):
    ...
```

## Options available on (almost) every prompt

```python
# default: Enter returns it, and the prompt shows it
port = askr.ask_int("Port: ", default=8080)          # Port [8080]:

# validator + error: your own rule on top of the built-in checks
even = askr.ask_int("Even number: ", validator=lambda n: n % 2 == 0, error="Must be even.")

# max_attempts: give up instead of asking forever
try:
    code = askr.ask_int("Code: ", max_attempts=3)
except askr.TooManyAttemptsError:
    print("Too many wrong attempts.")
```

## Translating and rewording

```python
import dataclasses
import askr

askr.set_messages(askr.Messages.german())            # complete German translation

# or change single texts
askr.set_messages(dataclasses.replace(askr.get_messages(), empty="Please type something."))
```

## Colors

Error messages are red when the output is a terminal. They stay plain if the
[`NO_COLOR`](https://no-color.org) environment variable is set. Force it with
`askr.set_color(True)` or `askr.set_color(False)`.

## Good to know

- Mistakes by the programmer (for example `min_value` greater than `max_value`) raise
  a `ValueError` immediately instead of asking the user forever.
- `Ctrl+C` and `Ctrl+D` are not caught, so your program can handle
  `KeyboardInterrupt` and `EOFError` the way it wants.

## License

MIT
