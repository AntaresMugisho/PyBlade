from django.shortcuts import render


# Create your views here.
def app(request, id):
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

    return render(request, "app.subfolder.page", context)