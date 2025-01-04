# ui/styles.py
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
