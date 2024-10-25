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
        "active": True,
        "items": ["Apple", "Banana", "Cherry"],
        "favorites": [],
        "html": "<strong>This is a HTML code</strong>",
        "menus": ["Contact", "About", "Contact", "Log in", "Sign in"],
    }

    pyblade = PyBlade()
    output = pyblade.render(template="partials.page", context=context)
    return render_template_string(output)


if __name__ == "__main__":
    app.run(debug=True)
