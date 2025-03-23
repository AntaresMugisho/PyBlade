from django.shortcuts import render

from .forms import ContactForm


def index(request):
    if request.method == "POST":
        form = ContactForm(request.POST, request.FILES)

        if form.is_valid():
            form = ContactForm()  # Reset form after successful submission
    else:
        form = ContactForm()

    context = {
        "form": form,
        "name": "Antares",
        "html": "<strong>Bold</strong> text.",
        "items": ["a", "b", "c", "d", "f"],
        "online": True,
        "repetitives": ["a", "a", "a", "b", "c", "c", "c", "d", "d"],
        "countries": [
            {"name": "DRC", "continent": "Africa", "population": 1000},
            {"name": "France", "continent": "Europe", "population": 3000},
            {"name": "Rwanda", "continent": "Africa", "population": 500},
            {"name": "Chine", "continent": "Asia", "population": 5000},
        ],
    }

    return render(request, "index", context)
