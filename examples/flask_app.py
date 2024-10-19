from pathlib import Path

from flask import Flask, render_template_string
from pyblade import PyBlade


app = Flask(__name__)

BASE_DIR = Path(__file__).parent.parent

TEMPLATES_DIR = BASE_DIR.joinpath("templates")


@app.route("/")
def home():
    context = {
        "user": {
            "name": "Antares",
            "email": "antaresmugisho@gmail.com"
        },
        "name": "Antares",
        "last_name": "Mugisho",
        "age": 20,
        "items": ["apple", "banana", "cherry"],
        "favorites": [],
        "html": "<strong>This is a HTML code</strong>"
    }

    pyblade = PyBlade()
    output = pyblade.render(template=str(TEMPLATES_DIR.joinpath("test_template.html")), context=context)
    return render_template_string(output)


if __name__ == "__main__":
    app.run(debug=True)
