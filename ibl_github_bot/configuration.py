import json
from pathlib import Path
from typing import TypedDict, DefaultDict
import yaml
from collections import defaultdict
import logging
# hard exclude represent know directories that must not in any way
# be included in the tests.
# For example includig .git directory will make the bot unable to push
# the final commit as the .git directory will be included in the git index
logger  = logging.getLogger(__name__)
HARD_EXCLUDE = ["__pycache__", ".git", "tests", "tests.py", ".github", ".vscode"]


class Config(TypedDict):
    exclude: list[str]
    test_library: str
    frameworks: list[str]
    dependencies: DefaultDict[str, set]
    language: str


DEFAULT_CONFIGURATION: Config = {
    "exclude": [
        *HARD_EXCLUDE,
        "tests",
        "migrations",
        "requirements",
    ],
    "test_library": "pytest",
    "frameworks": ["django", "djangorestframework"],
    "dependencies": defaultdict(set),
    "language": "python",
}


class DependencyGraph:
    global_settings: Config
    modules: dict[str, Config]
    dependencies: DefaultDict[str, set]

    def __init__(self, config_file: Path | None = None):
        self.config_file = config_file
        self.modules = {}
        self.global_settings = {}

        self.dependencies = defaultdict(set)
        self.global_settings = DEFAULT_CONFIGURATION
        if not config_file.exists():
            self.load_config()
            self.build_dependency_graph()

    def __str__(self):
        return json.dumps(
            {
                "config_file": self.config_file,
                "modules": self.modules,
                "dependency_graph": {k: list(v) for k, v in self.dependencies.items()},
                "global_settings": self.global_settings,
            },
            indent=4,
        )

    def get_settings(self, module_name: str) -> dict | None:
        try:
            return self.modules[module_name]
        except:
            return None

    def get_dependencies(self, module_name: str) -> dict | None:
        try:
            return self.dependencies[module_name]
        except:
            return None

    def load_config(self):
        if not self.config_file.exists():
            logging.warning("No config file found")
            return
        with open(self.config_file, "r") as file:
            config: dict = yaml.safe_load(file)
            exclude = config.get("exclude", [])
            if not exclude:
                exclude = DEFAULT_CONFIGURATION["exclude"]
            exclude += HARD_EXCLUDE
            self.global_settings = {
                "exclude": exclude,
                "test_library": config.get(
                    "test_library", DEFAULT_CONFIGURATION["test_library"]
                ),
                "frameworks": config.get(
                    "frameworks", DEFAULT_CONFIGURATION["frameworks"]
                ),
                "language": config.get("language", DEFAULT_CONFIGURATION["language"]),
            }

            modules = config.get("modules", {})
            for module, data in modules.items():
                module_data = {
                    "depends_on": data.get("depends_on", []),
                    "exclude": data.get("exclude", []),
                }
                self.modules[module] = module_data

    def build_dependency_graph(self):
        for module, data in self.modules.items():
            for dependency in data["depends_on"]:
                self.dependencies[module].add(dependency)

    def get_all_excludes(self, module: str):
        base = self.global_settings["exclude"]
        settings = self.get_settings(module)
        if settings and settings.get("exclude"):
            base += ["module/" + exclude for exclude in settings["exclude"]]
        return base

    def get_direct_dependencies(self, module):
        return list(self.dependencies.get(module, []))

    def get_all_dependencies(self, module, visited=None):
        if visited is None:
            visited = set()
        visited.add(module)
        all_dependencies = set(self.dependencies[module])

        for dependency in self.dependencies[module]:
            if dependency not in visited:
                all_dependencies |= set(self.get_all_dependencies(dependency, visited))
        return list(all_dependencies)

    def get_global_settings(self):
        return self.global_settings
