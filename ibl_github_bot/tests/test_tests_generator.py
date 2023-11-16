# test_ibl_github_bot_tests_generator.py
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from ibl_github_bot.tests_generator import generate_tests, create_tests_for_repo, DependencyGraph

@pytest.fixture
def dependency_graph():
    return DependencyGraph()

@pytest.fixture
def directory(tmp_path):
    return tmp_path / "test_repo"

@pytest.fixture
def sub_path(directory):
    return directory / "sub_module"

@pytest.fixture
def test_dir(sub_path):
    return sub_path / "tests"

@pytest.mark.django_db
class TestGenerateTests:
    def test_generate_tests_with_valid_directory(self, directory, sub_path, test_dir, dependency_graph):
        # Setup a dummy directory structure
        directory.mkdir()
        sub_path.mkdir()
        test_dir.mkdir()
        (sub_path / "test_file.py").write_text("# Dummy test file content")

        # Mock dependency graph to return empty exclude list and dependencies
        dependency_graph.get_global_settings = MagicMock(return_value={"exclude": []})
        dependency_graph.get_all_excludes = MagicMock(return_value=[])
        dependency_graph.get_all_dependencies = MagicMock(return_value=[])

        # Run the test generation
        success = generate_tests(directory, dependency_graph, sub_path, test_dir)

        # Check if the function succeeded
        assert success

        # Check if the test file was created
        assert (test_dir / "test_test_file.py").exists()

    def test_generate_tests_with_excluded_directory(self, directory, sub_path, test_dir, dependency_graph):
        # Setup a dummy directory structure
        directory.mkdir()
        sub_path.mkdir()
        test_dir.mkdir()
        (sub_path / "test_file.py").write_text("# Dummy test file content")

        # Mock dependency graph to return exclude list containing the sub_path
        dependency_graph.get_global_settings = MagicMock(return_value={"exclude": [sub_path.name]})
        dependency_graph.get_all_excludes = MagicMock(return_value=[sub_path.name])
        dependency_graph.get_all_dependencies = MagicMock(return_value=[])

        # Run the test generation
        success = generate_tests(directory, dependency_graph, sub_path, test_dir)

        # Check if the function failed due to exclusion
        assert not success

@pytest.mark.django_db
class TestCreateTestsForRepo:
    @pytest.mark.asyncio
    async def test_create_tests_for_repo(self):
        # Mock the dependency graph
        dependency_graph = MagicMock(spec=DependencyGraph)
        dependency_graph.get_global_settings.return_value = {"exclude": []}
        dependency_graph.get_all_excludes.return_value = []
        dependency_graph.get_all_dependencies.return_value = []

        # Mock the GitHubAPI
        gh_api_mock = MagicMock(spec=GitHubAPI)

        # Mock the aiohttp session
        session_mock = MagicMock()
        session_mock.__aenter__.return_value = gh_api_mock

        # Patch the aiohttp ClientSession and the generate_tests function
        with patch('aiohttp.ClientSession', return_value=session_mock), \
             patch('ibl_github_bot.tests_generator.generate_tests', return_value=True):
            # Run the create_tests_for_repo coroutine
            await create_tests_for_repo(
                username="testuser",
                repo="testuser/testrepo",
                branch="main",
                token="testtoken",
                cleanup=True
            )

            # Check if the GitHubAPI was called to create a pull request
            gh_api_mock.post.assert_called_once()