from pathlib import Path

import polib

from pyblade.cli import BaseCommand
from pyblade.config import settings


class Command(BaseCommand):
    """
    Compiles .po files to .mo files for use with builtin gettext support.
    """

    name = "messages:compile"
    aliases = ["compile:messages"]

    def config(self):
        """Setup command arguments and options here"""
        self.add_option(
            "--locale",
            "-l",
            help="The locale to compile messages for (e.g., 'fr', 'de', 'es')",
            required=False,
        )

        self.add_option(
            "--exclude",
            "-x",
            help="Comma-separated list of locales to exclude from compilation (e.g., 'fr,de')",
            required=False,
        )
        self.add_option(
            "--domain",
            "-d",
            help="The gettext domain to use (default: 'django' for django projects or 'pyblade' for other frameworks)",
            required=False,
            default="django" if settings.framework == "django" else "pyblade",
        )
        self.add_option(
            "--ignore",
            "-i",
            help="Comma-separated list of directories to ignore",
            required=False,
            default="venv,env,.git,node_modules",
        )
        self.add_option(
            "--fuzzy",
            "-f",
            help="Compile fuzzy translations as well",
            is_flag=True,
            required=False,
        )

    def handle(self, **kwargs):
        """Execute the 'pyblade messages:compile' command"""
        locale = kwargs.get("locale")
        excluded_locales = kwargs.get("exclude")
        domain = kwargs.get("domain")
        fuzzy = kwargs.get("fuzzy", False)

        # Determine locale directory
        locale_dir = self._find_locale_dir()
        if not locale_dir:
            self.error("Unable to find a locale path to compile translations.")

            if settings.framework == "django":
                self.tip("Make sure the 'LOCALE_PATHS' setting is configured in your Django settings.")
            else:
                self.tip("Make sure the 'locale' directory exists or 'locale_dir' setting is set in pyblade.json")
            return

        # Determine which locales to process
        locales_to_process = []
        if excluded_locales:
            all_locales_list = self._get_all_locales(locale_dir)
            excluded_list = excluded_locales.split(",")
            locales_to_process = [loc for loc in all_locales_list if loc not in excluded_list]
            if not locales_to_process:
                self.warning("No locales to process after excluding specified locales.")
                return
        elif locale:
            locales_to_process = locale.split(",")
        else:
            locales_to_process = self._get_all_locales(locale_dir)

        self.info(f"Processing {len(locales_to_process)} locale{'' if len(locales_to_process) == 1 else 's'}: \
{', '.join(locales_to_process)}")

        # Process each locale
        compiled_count = 0
        with self.status("Compiling translations...") as status:
            for loc in locales_to_process:
                status.update(f"Compiling {loc}...")
                if self._compile_locale(locale_dir, loc, domain, fuzzy):
                    compiled_count += 1

        if compiled_count > 0:
            self.success(f"Successfully compiled {compiled_count} locale{'' if compiled_count == 1 else 's'}.")
        else:
            self.warning("No .po files found to compile")

    def _find_locale_dir(self):
        """Find the locale directory"""
        locale_paths = None

        # Find locale paths from Django settings
        if settings.framework == "django":
            try:
                from django.conf import settings as django_settings

                locale_paths = django_settings.LOCALE_PATHS
                return Path(locale_paths[0]) if locale_paths else None
            except Exception:
                pass

        # Fallback to the default 'locale' dir for other frameworks
        # or use the value in pyblade.json
        default_locale_dir = settings.locale_dir
        if default_locale_dir != Path(""):
            return Path(default_locale_dir)
        return None

    def _get_all_locales(self, locale_dir):
        """Get all locale directories"""
        locales = []
        if locale_dir.exists():
            for item in locale_dir.iterdir():
                if item.is_dir() and not item.name.startswith("."):
                    locales.append(item.name)
        return locales

    def _compile_locale(self, locale_dir, locale, domain, fuzzy):
        """Compile .po files for a single locale"""
        locale_path = locale_dir / locale / "LC_MESSAGES"
        if not locale_path.exists():
            self.warning(f"Locale directory not found: {locale_path}")
            return False

        po_file = locale_path / f"{domain}.po"
        mo_file = locale_path / f"{domain}.mo"

        if not po_file.exists():
            self.warning(f".po file not found: {po_file}")
            return False

        # Check if .mo file is already up to date
        if mo_file.exists():
            po_mtime = po_file.stat().st_mtime
            mo_mtime = mo_file.stat().st_mtime
            if mo_mtime >= po_mtime:
                self.info(f"The file {mo_file} is already up to date.")
                return True

        try:
            # Load the .po file
            po = polib.pofile(str(po_file))

            # Handle fuzzy translations
            if not fuzzy:
                # Remove fuzzy entries before compiling
                po = polib.POFile()
                po.metadata = polib.pofile(str(po_file)).metadata
                for entry in polib.pofile(str(po_file)):
                    if "fuzzy" not in entry.flags:
                        po.append(entry)

            # Compile to .mo file
            po.save_as_mofile(str(mo_file))
            self.success(f"Compiled {po_file} -> {mo_file}", bold=False)
            return True

        except Exception as e:
            self.error(f"Could not compile {po_file}: {e}")
            return False
