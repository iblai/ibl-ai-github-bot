# test_configuration.py
import pytest
from ibl_github_bot.configuration import Config, DependencyGraph, HARD_EXCLUDE, DEFAULT_CONFIGURATION
from collections import defaultdict
from pathlib import Path

@pytest.fixture
def default_config():
    return Config(
        exclude=HARD_EXCLUDE + ["tests", "migrations", "requirements"],
        test_library="pytest",
        frameworks=["django", "djangorestframework"],
        dependencies=defaultdict(set),
        language="python",
    )

@pytest.fixture
def dependency_graph(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text("")
    return DependencyGraph(config_file=config_file)

def test_default_configuration(default_config):
    assert DEFAULT_CONFIGURATION == default_config

def test_hard_exclude():
    assert "tests" in HARD_EXCLUDE

@pytest.mark.parametrize("module_name, expected", [
    ("module1", None),
    ("module2", None),
])
def test_get_settings(dependency_graph, module_name, expected):
    assert dependency_graph.get_settings(module_name) == expected

@pytest.mark.parametrize("module_name, expected", [
    ("module1", None),
    ("module2", None),
])
def test_get_dependencies(dependency_graph, module_name, expected):
    assert dependency_graph.get_dependencies(module_name) == expected

def test_load_config(dependency_graph):
    # Assuming the config file is empty or has default values
    dependency_graph.load_config()
    assert dependency_graph.global_settings == DEFAULT_CONFIGURATION

def test_build_dependency_graph(dependency_graph):
    # Assuming no modules are defined
    dependency_graph.build_dependency_graph()
    assert dependency_graph.dependencies == defaultdict(set)

@pytest.mark.parametrize("module, expected", [
    ("module1", HARD_EXCLUDE + ["tests", "migrations", "requirements"]),
    ("module2", HARD_EXCLUDE + ["tests", "migrations", "requirements"]),
])
def test_get_all_excludes(dependency_graph, module, expected):
    assert set(dependency_graph.get_all_excludes(module)) == set(expected)

@pytest.mark.parametrize("module, expected", [
    ("module1", []),
    ("module2", []),
])
def test_get_direct_dependencies(dependency_graph, module, expected):
    assert dependency_graph.get_direct_dependencies(module) == expected

@pytest.mark.parametrize("module, expected", [
    ("module1", []),
    ("module2", []),
])
def test_get_all_dependencies(dependency_graph, module, expected):
    assert dependency_graph.get_all_dependencies(module) == expected

def test_get_global_settings(dependency_graph):
    assert dependency_graph.get_global_settings() == DEFAULT_CONFIGURATION