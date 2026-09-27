"""Simple, validated input prompts for the terminal."""

from importlib.metadata import PackageNotFoundError as _PackageNotFoundError
from importlib.metadata import version as _version

from .core import (
    TooManyAttemptsError,
    ask_choice,
    ask_confirm_text,
    ask_date,
    ask_datetime,
    ask_email,
    ask_enum,
    ask_float,
    ask_int,
    ask_list,
    ask_multi_choice,
    ask_password,
    ask_path,
    ask_str,
    ask_time,
    ask_url,
    ask_yn,
    get_messages,
    set_color,
    set_messages,
)
from .messages import Messages

__all__ = [
    "Messages",
    "TooManyAttemptsError",
    "ask_choice",
    "ask_confirm_text",
    "ask_date",
    "ask_datetime",
    "ask_email",
    "ask_enum",
    "ask_float",
    "ask_int",
    "ask_list",
    "ask_multi_choice",
    "ask_password",
    "ask_path",
    "ask_str",
    "ask_time",
    "ask_url",
    "ask_yn",
    "get_messages",
    "set_color",
    "set_messages",
]
# Read the version from the installed package metadata, so pyproject.toml
# is the only place where the version number has to be changed.
try:
    __version__ = _version("askr")
except _PackageNotFoundError:  # running from source without installing
    __version__ = "0.0.0"
