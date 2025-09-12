# import os

from django.urls import URLPattern, URLResolver

from pyblade.cli import BaseCommand

# from yblade.config import settings


class Command(BaseCommand):
    """
    Show all registered routes information.
    """

    name = "route:list"
    aliases = []  # Other possible names for the command

    def config(self):
        """Setup command arguments and options here"""
        pass

    def _get_routes(self, url_patterns, prefix=""):
        routes = []
        for pattern in url_patterns:

            if isinstance(pattern, URLPattern):
                path = prefix + str(pattern.pattern)
                name = pattern.name or ""
                routes.append({"path": path, "name": name})
            elif isinstance(pattern, URLResolver):
                nested_prefix = prefix + str(pattern.pattern)
                routes.extend(self._get_routes(pattern.url_patterns, nested_prefix))
        return routes

    def handle(self, **kwargs):
        """Execute the 'pyblade route:list' command"""

        # if not os.environ.get("DJANGO_SETTINGS_MODULE"):
        # os.environ.setdefault("DJANGO_SETTINGS_MODULE", "")
        # print(os.environ.get("DJANGO_SETTINGS_MODULE"))

        # resolver = get_resolver()
        # # all_routes = self._get_routes(resolver.url_patterns)

        # print(resolver)
        # return

        # if not all_routes:
        #     self.line("No routes found.")
        #     return

        # self.line("Registered Routes:")
        # self.line("------------------")

        # Filter out routes without a name if a 'named' option is added later
        # For now, we show all routes.

        # Determine column widths for formatting
        # max_path_len = 0
        # max_name_len = 0
        # for route in all_routes:
        #     if len(route["path"]) > max_path_len:
        #         max_path_len = len(route["path"])
        #     if len(route["name"]) > max_name_len:
        #         max_name_len = len(route["name"])

        # # Header
        # header = f"{'URL Pattern'.ljust(max_path_len)}   {'Route Name'.ljust(max_name_len)}"
        # self.line(header)
        # self.line("-" * len(header))

        # # Rows
        # for route in sorted(all_routes, key=lambda x: x["path"]):
        #     path = route["path"].ljust(max_path_len)
        #     name = route["name"].ljust(max_name_len)
        #     self.line(f"{path}   {name}")
