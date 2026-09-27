# Records docs/demo.gif. Run from the project root:  vhs docs/demo.tape
Output docs/demo.gif

Set Shell "bash"
Set FontSize 22
Set Width 1100
Set Height 680
Set Padding 30
Set Theme "Catppuccin Mocha"
Set TypingSpeed 70ms

# Hide the setup so the GIF starts with a clean prompt.
Hide
Type "export PS1='$ ' && clear" Enter
Show

Type "python docs/demo.py" Sleep 400ms Enter
Sleep 1s

# ask_int: two wrong answers, then a valid one
Type "abc" Sleep 300ms Enter
Sleep 1.2s
Type "200" Sleep 300ms Enter
Sleep 1.2s
Type "25" Sleep 300ms Enter
Sleep 1s

# ask_multi_choice: a range and a name
Type "1-2, fri" Sleep 400ms Enter
Sleep 1s

# ask_choice: by name, case-insensitive
Type "hard" Sleep 300ms Enter
Sleep 1s

# ask_yn: Enter accepts the default
Sleep 500ms Enter
Sleep 3s
