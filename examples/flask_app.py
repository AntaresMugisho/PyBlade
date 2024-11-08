from pathlib import Path

from flask import Flask, render_template_string

from pyblade import PyBlade

app = Flask(__name__)


@app.route("/")
def home():
    context = {
        "user": {"name": "Antares", "email": "antaresmugisho@gmail.com"},
        "name": "Antares",
        "last_name": "Mugisho",
        "age": 50,
        "online": True,
        "items": ["Apple", "Banana", "Cherry"],
        "favorites": [],
        "html": "<strong>This is a HTML code</strong>",
        "menus": ["Contact", "About", "Contact", "Log in", "Sign in"],
    }

    engine = PyBlade([Path("/home/antares/Documents/Coding/Python/PyBlade/templates")])
    template = engine.get_template("test_template")
    output = template.render(context)
    return render_template_string(output)


if __name__ == "__main__":
    app.run(debug=True)
