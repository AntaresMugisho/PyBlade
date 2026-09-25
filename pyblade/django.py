"""PyBlade in a Django project.

Django is bound by its template backend rather than by a render function: name
`pyblade.backends.PyBladeEngine` in the project's TEMPLATES setting and every
template under it is rendered by PyBlade, `django.shortcuts.render` and all.
"""

from pyblade.backends import PyBladeEngine

__all__ = ["PyBladeEngine"]
