from questionary import Style

PYBLADE_STYLE = Style(
    [
        ("question", "fg:#4B8BBE bold"),
        ("answered_question", "#00AA00"),
        ("instruction", "fg:#4B8BBE"),
        ("pointer", "fg:#4B8BBE bold"),
        ("highlighted", "fg:#4B8BBE bold"),
        ("selected", "fg:#4B8BBE bold"),
        ("answer", "fg:#4B8BBE bold"),
    ]
)


custom_style = Style(
    [
        ("qmark", "fg:#673ab7 bold"),  # token in front of the question
        ("question", "bold"),  # question text
        ("answer", "fg:#673ab7 bold"),  # submitted answer text behind the question
        ("pointer", "fg:yellow bold"),  # pointer used in select and checkbox prompts
        ("highlighted", "fg:#673ab7 bold"),  # pointed-at choice in select and checkbox prompts
        ("selected", "fg:#673ab7"),  # style for a selected item of a checkbox
        ("separator", "fg:#cc5454"),  # separator in lists
        ("instruction", "fg:gray"),  # user instructions for select, rawselect, checkbox
        ("text", ""),  # plain text
        ("disabled", "fg:#858585 italic"),  # disabled choices for select and checkbox prompts
        ("placeholder", "fg:#858585 italic"),
    ]
)
