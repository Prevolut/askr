"""All texts shown to the user, so programs can translate or reword them."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Messages:
    """Every text askr shows to the user.

    Placeholders in curly braces are filled in automatically. Change single
    texts with dataclasses.replace() and activate them with askr.set_messages():

        import dataclasses, askr
        askr.set_messages(dataclasses.replace(askr.get_messages(), empty="Say something!"))

    Messages.german() returns a complete German translation.
    """

    # ask_yn
    yes_answers: tuple[str, ...] = ("y", "yes")
    no_answers: tuple[str, ...] = ("n", "no")
    yes_no_hint_yes: str = "Y/n"
    yes_no_hint_no: str = "y/N"
    yes_no_error: str = "Please answer with yes or no."

    # Numbers
    invalid_int: str = "Invalid entry. Please enter a whole number."
    invalid_float: str = "Invalid entry. Please enter a number."
    number_range: str = "The number must be {range}."

    # Range wording, e.g. "at least 3", "between 1 and 10"
    at_least: str = "at least"
    at_most: str = "at most"
    between: str = "between {min} and {max}"
    or_word: str = "or"

    # Text
    empty: str = "Input cannot be empty."
    length_range: str = "Input must be {range} characters long."

    # Choices
    choice_prompt: str = "Your choice: "
    choice_default_marker: str = " (default)"
    choice_error: str = "Please enter a number from 1 to {count} or the name of an option."
    invalid_selection: str = "'{part}' is not a valid option."
    selection_count: str = "The number of selected options must be {range}."

    # Passwords
    password_header: str = "The password must:"
    password_min_length: str = "be at least {n} characters long"
    password_upper: str = "contain an uppercase letter"
    password_lower: str = "contain a lowercase letter"
    password_digit: str = "contain a digit"
    password_special: str = "contain a special character"
    password_pattern: str = "match the required format"
    password_repeat: str = "Repeat password: "
    password_mismatch: str = "The passwords do not match. Please try again."

    # Paths
    path_empty: str = "Please enter a path."
    path_missing: str = "This path does not exist. Please try again."
    path_not_file: str = "This is not a file. Please enter the path of a file."
    path_not_dir: str = "This is not a folder. Please enter the path of a folder."

    # Dates and times
    invalid_date: str = "Invalid date. Please use a format like {examples}."
    invalid_time: str = "Invalid time. Please use a format like {examples}."
    invalid_datetime: str = "Invalid date and time. Please use a format like {examples}."
    date_range: str = "The date must be {range}."
    time_range: str = "The time must be {range}."
    datetime_range: str = "The date and time must be {range}."
    date_after: str = "on or after"
    date_before: str = "on or before"
    time_after: str = "not earlier than"
    time_before: str = "not later than"

    # Email and URL
    invalid_email: str = "Please enter a valid email address."
    email_domain: str = "Please use an address from {domains}."
    invalid_url: str = "Please enter a valid URL starting with {schemes}."

    # Lists
    invalid_list_item: str = "'{item}' is not a valid entry."
    list_count: str = "The number of entries must be {range}."
    list_duplicates: str = "Please do not enter any value more than once."

    # Custom validators
    validator_failed: str = "Invalid entry."

    @classmethod
    def german(cls) -> "Messages":
        """Return a complete German translation."""
        return cls(
            yes_answers=("j", "ja", "y", "yes"),
            no_answers=("n", "nein", "no"),
            yes_no_hint_yes="J/n",
            yes_no_hint_no="j/N",
            yes_no_error="Bitte mit ja oder nein antworten.",
            invalid_int="Ungültige Eingabe. Bitte eine ganze Zahl eingeben.",
            invalid_float="Ungültige Eingabe. Bitte eine Zahl eingeben.",
            number_range="Die Zahl muss {range} sein.",
            at_least="mindestens",
            at_most="höchstens",
            between="zwischen {min} und {max}",
            or_word="oder",
            empty="Die Eingabe darf nicht leer sein.",
            length_range="Die Eingabe muss {range} Zeichen lang sein.",
            choice_prompt="Deine Wahl: ",
            choice_default_marker=" (Standard)",
            choice_error="Bitte eine Zahl von 1 bis {count} oder den Namen einer Option eingeben.",
            invalid_selection="'{part}' ist keine gültige Option.",
            selection_count="Die Anzahl gewählter Optionen muss {range} sein.",
            password_header="Das Passwort muss:",
            password_min_length="mindestens {n} Zeichen lang sein",
            password_upper="einen Großbuchstaben enthalten",
            password_lower="einen Kleinbuchstaben enthalten",
            password_digit="eine Ziffer enthalten",
            password_special="ein Sonderzeichen enthalten",
            password_pattern="dem geforderten Format entsprechen",
            password_repeat="Passwort wiederholen: ",
            password_mismatch="Die Passwörter stimmen nicht überein. Bitte erneut versuchen.",
            path_empty="Bitte einen Pfad eingeben.",
            path_missing="Dieser Pfad existiert nicht. Bitte erneut versuchen.",
            path_not_file="Das ist keine Datei. Bitte den Pfad einer Datei eingeben.",
            path_not_dir="Das ist kein Ordner. Bitte den Pfad eines Ordners eingeben.",
            invalid_date="Ungültiges Datum. Bitte ein Format wie {examples} verwenden.",
            invalid_time="Ungültige Uhrzeit. Bitte ein Format wie {examples} verwenden.",
            invalid_datetime="Ungültiger Zeitpunkt. Bitte ein Format wie {examples} verwenden.",
            date_range="Das Datum muss {range} liegen.",
            time_range="Die Uhrzeit muss {range} liegen.",
            datetime_range="Der Zeitpunkt muss {range} liegen.",
            date_after="am oder nach dem",
            date_before="am oder vor dem",
            time_after="nicht vor",
            time_before="nicht nach",
            invalid_email="Bitte eine gültige E-Mail-Adresse eingeben.",
            email_domain="Bitte eine Adresse von {domains} verwenden.",
            invalid_url="Bitte eine gültige URL eingeben, die mit {schemes} beginnt.",
            invalid_list_item="'{item}' ist kein gültiger Eintrag.",
            list_count="Die Anzahl der Einträge muss {range} sein.",
            list_duplicates="Bitte keinen Wert mehrfach eingeben.",
            validator_failed="Ungültige Eingabe.",
        )
