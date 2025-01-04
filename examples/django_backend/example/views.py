from django.shortcuts import render


def home(request):
    context = {
        "user": {"name": "Antares", "email": "antaresmugisho@gmail.com"},
        "name": "Antares",
        "last_name": "Mugisho",
        "age": 50,
        "online": True,
        "status": "if",
        "items": ["Apple", "Banana", "Cherry"],
        "favorites": [],
        "html": "<strong>This is a HTML code</strong>",
        "menus": ["Contact", "About", "Contact", "Log in", "Sign in"],
    }
       
    return render(request, "example/index.html", context)