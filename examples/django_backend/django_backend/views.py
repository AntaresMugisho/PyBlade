from django.shortcuts import render

from .forms import ContactForm


def index(request):
    if request.method == "POST":
        form = ContactForm(request.POST, request.FILES)

        if form.is_valid():
            # For testing purposes, just print the cleaned data
            print(form.cleaned_data)
            # You would typically process the form data here
            form = ContactForm()  # Reset form after successful submission
    else:
        form = ContactForm()
        # print(form.email)

    context = {
        "form": form,
        "name": "Antares",
        "html": "<strong>Bold</strong> text.",
        "items": ["a", "b", "c", "d", "f"],
    }

    return render(request, "django_backend.index", context)
