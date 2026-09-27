# Changelog

## 0.2.0

### New functions
- `ask_email`: plausible email addresses, optionally limited to `allowed_domains`
- `ask_url`: web addresses; adds `https://` automatically if the scheme is missing
- `ask_time` and `ask_datetime`: like `ask_date`, with one or several formats
- `ask_multi_choice`: pick several options with `1, 3`, `1-3` or names
- `ask_list`: several values in one line, converted with e.g. `int`
- `ask_enum`: pick a member of an `Enum`
- `ask_confirm_text`: "type 'delete' to confirm" safety check

### New options
- `default=` for all prompts where it makes sense; shown in the prompt as `Age [18]: `
- `validator=` and `error=` for custom checks
- `max_attempts=` raises `TooManyAttemptsError` after too many invalid answers
- All texts can be replaced via `Messages`, `set_messages()` and `get_messages()`;
  `Messages.german()` ships a complete German translation
- Error messages are red in terminals; respects `NO_COLOR`, `set_color()` overrides

### Changes
- `ask_choice` now rejects option lists with duplicates (ignoring case)
- New keyword arguments are keyword-only, so existing calls keep working

## 0.1.0

First release: `ask_yn`, `ask_int`, `ask_float`, `ask_str`, `ask_choice`,
`ask_password`, `ask_path`, `ask_date`.
