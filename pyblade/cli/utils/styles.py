from questionary import Style

PYBLADE_STYLE = Style(
    [
        ("qmark", "fg:#673ab7 bold"),  # token in front of the question
        ("question", "bold"),  # question text
        ("answer", "fg:blue"),  # submitted answer text behind the question
        ("pointer", "fg:yellow bold"),  # pointer used in select and checkbox prompts
        ("highlighted", "fg:blue bold"),  # pointed-at choice in select and checkbox prompts
        ("selected", "fg:blue"),  # style for a selected item of a checkbox
        ("separator", "fg:#cc5454"),  # separator in lists
        ("instruction", "fg:gray italic"),  # user instructions for select, rawselect, checkbox
        ("text", ""),  # plain text
        ("disabled", "fg:#858585 italic"),  # disabled choices for select and checkbox prompts
        ("placeholder", "fg:#858585 italic"),
    ]
)
