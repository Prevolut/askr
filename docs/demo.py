"""Short demo of askr, recorded as docs/demo.gif with VHS (see docs/demo.tape)."""

from askr import ask_choice, ask_int, ask_multi_choice, ask_yn

age = ask_int("Your age: ", min_value=0, max_value=120, default=18)
days = ask_multi_choice("Which days are you free?", ["Mon", "Tue", "Wed", "Thu", "Fri"])
level = ask_choice("Difficulty?", ["Easy", "Medium", "Hard"], default="Medium")

if ask_yn("Save these settings?"):
    print(f"\nSaved: age={age}, days={days}, level={level!r}")