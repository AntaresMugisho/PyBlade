import os
import re
from pathlib import Path

import polib

from pyblade.cli import BaseCommand
from pyblade.config import settings
from pyblade.engine.lexer import Lexer
from pyblade.engine.parser import Parser
from pyblade.utils import get_project_root


class Command(BaseCommand):
    """
    Runs over the entire source tree of the current directory and pulls out all strings marked for translation.

    You must run this command with one of either the --locale, --exclude, or --all options.
    """

    name = "messages:make"
    aliases = ["make:messages"]

    def config(self):
        """Setup command arguments and options here"""
        self.add_option(
            "--locale",
            "-l",
            help="The locale to create messages for (e.g., 'fr', 'de', 'es')",
            required=False,
        )

        self.add_option(
            "--all",
            "-a",
            help="Create messages for all locales found in locale directory",
            is_flag=True,
            required=False,
        )

        self.add_option(
            "--exclude",
            "-x",
            help="Comma-separated list of locales to exclude from processing (e.g., 'fr,de')",
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
            "--extensions",
            "-e",
            help="Comma-separated list of file extensions to parse (default: 'html,py')",
            required=False,
            default="html,py",
        )

        self.add_option(
            "--ignore",
            "-i",
            help="Comma-separated list of files/directories to ignore",
            required=False,
            default="venv,env,.env,.venv,.git,node_modules",
        )

    def handle(self, **kwargs):
        """Execute the 'pyblade messages:make' command"""
        locale = kwargs.get("locale")
        all_locales = kwargs.get("all", False)
        excluded_locales = kwargs.get("exclude")
        domain = kwargs.get("domain")
        extensions = kwargs.get("extensions").split(",")
        ignore_dirs = kwargs.get("ignore").split(",")

        # Validate that at least one locale option is provided
        if not locale and not all_locales and not excluded_locales:
            self.error("You must specify one of: --locale, --all, or --exclude.")
            self.tip("Type [bright_black]pyblade make:messages --help[/bright_black] for usage information.")
            return

        # Determine locale directory
        locale_dir = self._find_locale_dir()
        if not locale_dir:
            self.error("Unable to find a locale path to store translations.")

            if settings.framework == "django":
                self.tip("Make sure the 'LOCALE_PATHS' setting is configured in your Django settings.")
            else:
                self.tip("Make sure the 'locale' directory exists or 'locale_dir' setting is set in pyblade.json")
            return

        # Create the locale dir if not exists
        locale_dir.mkdir(parents=True, exist_ok=True)

        # Determine which locales to process
        locales_to_process = []
        if all_locales:
            locales_to_process = self._get_all_locales(locale_dir)
            if not locales_to_process:
                self.warning("No locales found in locale directory.")
                return
        elif excluded_locales:
            all_locales_list = self._get_all_locales(locale_dir)
            excluded_list = excluded_locales.split(",")
            locales_to_process = [loc for loc in all_locales_list if loc not in excluded_list]
            if not locales_to_process:
                self.warning("No locales to process after excluding specified locales.")
                return
        elif locale:
            locales_to_process = locale.split(",")

        self.info(f"Processing {len(locales_to_process)} locale{'' if len(locales_to_process) == 1 else 's'}: \
                {', '.join(locales_to_process)}")

        # Get project root directory
        project_root = get_project_root()
        if not project_root:
            self.error("Could not determine project root directory.")
            return

        # Find all files with specified extensions
        source_files = self._find_source_files(project_root, extensions, ignore_dirs)
        if not source_files:
            self.warning("No source files found with the specified extensions.")
            return

        self.info(f"Found {len(source_files)} source files")

        # Extract translatable strings from source files
        all_messages = {}
        for source_file in source_files:
            messages = self._extract_from_template(source_file)
            for msgid, metadata in messages.items():
                if msgid not in all_messages:
                    all_messages[msgid] = metadata
                else:
                    # Merge metadata
                    all_messages[msgid]["occurrences"].extend(metadata["occurrences"])

        self.info(f"Extracted {len(all_messages)} translatable strings")

        # Process each locale
        for loc in locales_to_process:
            self._process_locale(locale_dir, loc, domain, all_messages)

        self.success("Message files created/updated successfully")

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

    def _find_source_files(self, root_dir, extensions, ignore_dirs):
        """Find all source files with given extensions in the project root"""
        _default_ignored_dirs = [
            ".git",
            "__pycache__",
            ".venv",
            ".env",
            "venv",
            "env",
            ".idea",
            ".vscode",
            ".DS_Store",
            "node_modules",
            "locale",
            ".pytest_cache",
        ]
        source_files = []
        ignore_dirs_set = set(ignore_dirs + _default_ignored_dirs)

        for root, dirs, files in os.walk(root_dir):
            # Remove ignored directories from traversal
            dirs[:] = [d for d in dirs if d not in ignore_dirs_set]

            for file in files:
                if any(file.endswith(f".{ext}") for ext in extensions):
                    source_files.append(Path(root) / file)

        return source_files

    def _extract_from_template(self, template_path):
        """Extract translatable strings from a template file"""
        messages = {}

        try:
            with open(template_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            self.warning(f"Could not read {template_path}: {e}")
            return messages

        # Tokenize and parse the template
        try:
            lexer = Lexer(content)
            tokens = lexer.tokenize()
            parser = Parser(tokens)
            ast = parser.parse()

            # Walk the AST and extract translatable strings
            for node in ast:
                self._extract_from_node(node, template_path, messages)

        except Exception as e:
            self.warning(f"Could not parse {template_path}: {e}")

        return messages

    def _extract_from_node(self, node, template_path, messages):
        """Recursively extract translatable strings from AST nodes"""
        from pyblade.engine.nodes import BlockTranslateNode, TranslateNode

        if isinstance(node, TranslateNode):
            # Extract the message string
            message = self._get_translate_message(node)
            if message:
                if message not in messages:
                    messages[message] = {
                        "msgid": message,
                        "msgstr": "",
                        "occurrences": [(str(template_path), node.line if node.line else 0)],
                        "context": node.context,
                    }
                else:
                    # Add occurrence if not already present
                    occ = (str(template_path), node.line if node.line else 0)
                    if occ not in messages[message]["occurrences"]:
                        messages[message]["occurrences"].append(occ)

        elif isinstance(node, BlockTranslateNode):
            # Extract block translation
            message = self._get_blocktranslate_message(node)
            if message:
                if message not in messages:
                    messages[message] = {
                        "msgid": message,
                        "msgstr": "",
                        "occurrences": [(str(template_path), node.line if node.line else 0)],
                        "context": node.context,
                    }
                else:
                    occ = (str(template_path), node.line if node.line else 0)
                    if occ not in messages[message]["occurrences"]:
                        messages[message]["occurrences"].append(occ)

    def _get_translate_message(self, node):
        """Extract the message string from a TranslateNode"""
        import re

        args_str = node.message.strip()
        if args_str.startswith("(") and args_str.endswith(")"):
            args_str = args_str[1:-1]

        # Extract the string literal from the arguments
        match = re.match(r'^\s*[\'"](.+?)[\'"]\s*$', args_str)
        if match:
            return match.group(1)

        return None

    def _get_blocktranslate_message(self, node):
        """Extract the message string from a BlockTranslateNode"""
        # Render the body to get the template string
        body_parts = []
        for child in node.body:
            if hasattr(child, "content"):
                body_parts.append(child.content)
            elif hasattr(child, "render"):
                # Try to get raw content
                if hasattr(child, "body"):
                    for subchild in child.body:
                        if hasattr(subchild, "content"):
                            body_parts.append(subchild.content)

        message = "".join(body_parts)

        # Normalize whitespace
        if node.trimmed:
            message = " ".join(message.split())

        # Convert {{ variable }} placeholders to %(variable)s
        placeholder_pattern = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")
        message = placeholder_pattern.sub(r"%(\1)s", message)

        return message

    def _process_locale(self, locale_dir, locale, domain, messages):
        """Process a single locale: create/update .po file"""
        locale_path = locale_dir / locale / "LC_MESSAGES"
        locale_path.mkdir(parents=True, exist_ok=True)

        po_file = locale_path / f"{domain}.po"

        # Load existing .po file or create new one
        if po_file.exists():
            po = polib.pofile(str(po_file))

        else:
            po = polib.POFile()
            po.metadata = {
                "Project-Id-Version": "1.0",
                "Report-Msgid-Bugs-To": "",
                "POT-Creation-Date": "",
                "PO-Revision-Date": "",
                "Last-Translator": "",
                "Language-Team": "",
                "Language": locale,
                "MIME-Version": "1.0",
                "Content-Type": "text/plain; charset=utf-8",
                "Content-Transfer-Encoding": "8bit",
            }

        # Add or update entries
        for msgid, metadata in messages.items():
            # Check if entry already exists
            entry = po.find(msgid, msgctxt=metadata["context"])
            if entry:
                # Update occurrences
                entry.occurrences = metadata["occurrences"]
            else:
                # Create new entry
                entry = polib.POEntry(
                    msgid=msgid,
                    msgstr="",
                    msgctxt=metadata["context"],
                    occurrences=metadata["occurrences"],
                )
                po.append(entry)

        # Save the .po file
        po.save(str(po_file))
        self.success(f"Updated {po_file}")
