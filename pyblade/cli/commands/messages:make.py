import os
import re
from pathlib import Path

import polib

from pyblade.cli import BaseCommand
from pyblade.engine.lexer import Lexer
from pyblade.engine.parser import Parser


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
            required=True,
        )
        self.add_option(
            "--domain",
            "-d",
            help="The gettext domain to use (default: 'pyblade')",
            required=False,
            default="pyblade",
        )
        self.add_option(
            "--extensions",
            "-e",
            help="Comma-separated list of file extensions to parse (default: 'html,py')",
            required=False,
            default="html,py",
        )
        self.add_option(
            "--all",
            "-a",
            help="Create messages for all locales found in locale directory",
            is_flag=True,
            required=False,
        )
        self.add_option(
            "--ignore",
            "-i",
            help="Comma-separated list of directories to ignore",
            required=False,
            default="venv,env,.git,node_modules",
        )
        self.add_option(
            "--no-obsolete",
            help="Remove obsolete messages from .po files",
            is_flag=True,
            required=False,
        )

    def handle(self, **kwargs):
        """Execute the 'pyblade messages:make' command"""
        locale = kwargs.get("locale")
        domain = kwargs.get("domain", "pyblade")
        extensions = kwargs.get("extensions", "html,py").split(",")
        all_locales = kwargs.get("all", False)
        ignore_dirs = kwargs.get("ignore", "venv,env,.env,.venv,.git,node_modules").split(",")
        no_obsolete = kwargs.get("no_obsolete", False)

        # Determine locale directory
        locale_dir = self._find_locale_dir()
        if not locale_dir:
            self.error("Could not find locale directory. Please create a 'locale' directory.")
            return

        # Determine which locales to process
        locales_to_process = []
        if all_locales:
            locales_to_process = self._get_all_locales(locale_dir)
            if not locales_to_process:
                self.warning("No locales found in locale directory.")
                return
        elif locale:
            locales_to_process = [locale]
        else:
            self.error("You must specify either --locale or --all")
            return

        # Find all template files
        templates_dir = self._find_templates_dir()
        if not templates_dir:
            self.error("Could not find templates directory.")
            return

        template_files = self._find_template_files(templates_dir, extensions, ignore_dirs)
        if not template_files:
            self.warning("No template files found.")
            return

        self.info(f"Found {len(template_files)} template files")

        # Extract translatable strings from templates
        all_messages = {}
        for template_file in template_files:
            messages = self._extract_from_template(template_file)
            for msgid, metadata in messages.items():
                if msgid not in all_messages:
                    all_messages[msgid] = metadata
                else:
                    # Merge metadata
                    all_messages[msgid]["occurrences"].extend(metadata["occurrences"])

        self.info(f"Extracted {len(all_messages)} translatable strings")

        # Process each locale
        for loc in locales_to_process:
            self._process_locale(locale_dir, loc, domain, all_messages, no_obsolete)

        self.success("Message files created/updated successfully")

    def _find_locale_dir(self):
        """Find the locale directory"""
        # Check common locations
        for path in ["i18n", "locale", "conf/locale", "app/locale"]:
            if os.path.exists(path):
                return Path(path)
        return None

    def _find_templates_dir(self):
        """Find the templates directory"""
        for path in ["templates", "app/templates"]:
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

    def _find_template_files(self, templates_dir, extensions, ignore_dirs):
        """Find all template files with given extensions"""
        template_files = []
        ignore_dirs_set = set(ignore_dirs)

        for root, dirs, files in os.walk(templates_dir):
            # Remove ignored directories from traversal
            dirs[:] = [d for d in dirs if d not in ignore_dirs_set]

            for file in files:
                if any(file.endswith(f".{ext}") for ext in extensions):
                    template_files.append(Path(root) / file)

        return template_files

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
        from pyblade.engine.nodes import TranslateNode, BlockTranslateNode

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
        placeholder_pattern = re.compile(r'\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}')
        message = placeholder_pattern.sub(r'%(\1)s', message)

        return message

    def _process_locale(self, locale_dir, locale, domain, messages, no_obsolete):
        """Process a single locale: create/update .po file"""
        locale_path = locale_dir / locale / "LC_MESSAGES"
        locale_path.mkdir(parents=True, exist_ok=True)

        po_file = locale_path / f"{domain}.po"

        # Load existing .po file or create new one
        if po_file.exists():
            po = polib.pofile(str(po_file))
            if no_obsolete:
                # Remove obsolete entries
                po.obsolete_entries = []
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
        self.info(f"Updated {po_file}")

