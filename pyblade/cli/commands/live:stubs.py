from pathlib import Path

from pyblade.cli import BaseCommand
from pyblade.config import settings

#: What may be exported, and where each thing goes once it is
STUBS = {
    "pagination": {
        "source": "pagination",
        "target": Path("stubs") / "pagination",
        "files": {"tailwind.html.stub": "tailwind.html"},
        "describe": "the links that walk through a paginated list",
    },
}


class Command(BaseCommand):
    """
    Copy the templates PyBlade draws with into the project, to take them over.
    """

    name = "live:stubs"

    def config(self):
        """Setup command arguments and options here"""
        self.add_flag("--pagination", help="Export the pagination templates")
        self.add_flag("-f", "--force", help="Overwrite templates already exported")

    def handle(self, **kwargs):
        """Copy the chosen templates into the project's templates directory."""
        chosen = [name for name in STUBS if kwargs.get(name)]

        if not chosen:
            self.error("Say what to export. For now that is --pagination.")
            return

        for name in chosen:
            self._export(STUBS[name], force=kwargs.get("force"))

    def _export(self, stub, force=False):
        source_dir = settings.stubs_dir / stub["source"]
        target_dir = Path(settings.templates_dir) / stub["target"]
        target_dir.mkdir(parents=True, exist_ok=True)

        for source_name, target_name in stub["files"].items():
            source = source_dir / source_name
            target = target_dir / target_name

            if target.exists() and not force:
                self.warning(f"{target} is already there. Pass --force to write over it.")
                continue

            target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            self.success(f"Exported {target} — {stub['describe']}.")

        self.info(
            f"PyBlade will draw with your copy from now on, instead of its own."
        )
