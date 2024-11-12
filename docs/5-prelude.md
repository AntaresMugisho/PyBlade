# PyBlade: Template Engine

::: danger ⚠️ Warning: Experimental Feature
PyBlade is currently in experimental mode. While we are actively developing and testing its features, please be aware that it may contain bugs or incomplete functionality. We recommend using PyBlade exclusively in test environments or with caution in production environments.

Your feedback is invaluable as we work toward a stable release. Thank you for helping us improve PyBlade!
:::

## PyBlade as a template engine

PyBlade is a lightweight yet powerful template engine tailored for Python web applications.

Unlike some templating engines, PyBlade keeps things simple while staying flexible, allowing you to use familiar Python syntax and expressions directly in your templates.

Each PyBlade template is compiled into HTML code and cached to ensure optimal performance, meaning PyBlade adds virtually no overhead to your application.

PyBlade templates use the `.pyblade` file extension and are typically stored within the `templates` directory of your app.

In Django or Flask applications, PyBlade views can be rendered directly within views or controllers, keeping data handling and template rendering clean and straightforward.

Just pass the data you need as context, and PyBlade takes care of the rest, providing a seamless, Pythonic approach to building dynamic, secure web templates.

Check out the next section to learn more about [PyBlade Directives](/6-displaying-data).
