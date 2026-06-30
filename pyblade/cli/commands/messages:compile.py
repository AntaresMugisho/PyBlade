import os
from pathlib import Path

import polib

from pyblade.cli import BaseCommand


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
            help="The locale to compile messages for (e.g., 'fr', 'de', 'es'). If not specified, compiles all locales.",
            required=False,
        )
        self.add_option(
            "--domain",
            "-d",
            help="The gettext domain to use (default: 'pyblade')",
            required=False,
            default="pyblade",
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
        domain = kwargs.get("domain", "pyblade")
        ignore_dirs = kwargs.get("ignore", "venv,env,.git,node_modules").split(",")
        fuzzy = kwargs.get("fuzzy", False)

        # Determine locale directory
        locale_dir = self._find_locale_dir()
        if not locale_dir:
            self.error("Could not find locale directory. Please create a 'locale' directory.")
            return

        # Determine which locales to process
        locales_to_process = []
        if locale:
            locales_to_process = [locale]
        else:
            locales_to_process = self._get_all_locales(locale_dir)
            if not locales_to_process:
                self.warning("No locales found in locale directory.")
                return

        # Process each locale
        compiled_count = 0
        for loc in locales_to_process:
            if self._compile_locale(locale_dir, loc, domain, fuzzy):
                compiled_count += 1

        if compiled_count > 0:
            self.success(f"Compiled {compiled_count} locale(s) successfully")
        else:
            self.warning("No .po files found to compile")

    def _find_locale_dir(self):
        """Find the locale directory"""
        for path in ["i18n", "locale", "conf/locale", "app/locale"]:
            if os.path.exists(path):
                return Path(path)
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

        try:
            # Load the .po file
            po = polib.pofile(str(po_file))

            # Handle fuzzy translations
            if not fuzzy:
                # Remove fuzzy entries before compiling
                po = polib.POFile()
                po.metadata = polib.pofile(str(po_file)).metadata
                for entry in polib.pofile(str(po_file)):
                    if not "fuzzy" in entry.flags:
                        po.append(entry)

            # Compile to .mo file
            po.save_as_mofile(str(mo_file))
            self.info(f"Compiled {po_file} -> {mo_file}")
            return True

        except Exception as e:
            self.error(f"Could not compile {po_file}: {e}")
            return False
