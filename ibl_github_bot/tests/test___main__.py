# test_ibl_github_bot___main__.py
import pytest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from ibl_github_bot.__main__ import main

@pytest.fixture
def mock_create_tests_for_repo():
    with patch('ibl_github_bot.__main__.create_tests_for_repo') as mock:
        yield mock

@pytest.fixture
def runner():
    return CliRunner()

@pytest.mark.django_db
def test_main_success(runner, mock_create_tests_for_repo):
    mock_create_tests_for_repo.return_value = None  # simulate async function
    result = runner.invoke(main, ['--repo', 'Joetib/webapp', '--branch', 'main'])
    assert result.exit_code == 0
    mock_create_tests_for_repo.assert_called_once()

@pytest.mark.django_db
def test_main_with_invalid_token(runner, mock_create_tests_for_repo):
    result = runner.invoke(main, ['--repo', 'Joetib/webapp', '--branch', 'main', '--github-token', ''])
    assert result.exit_code == 1
    assert 'Please provide a github token' in result.output
    mock_create_tests_for_repo.assert_not_called()

@pytest.mark.django_db
def test_main_with_cleanup_option(runner, mock_create_tests_for_repo):
    mock_create_tests_for_repo.return_value = None  # simulate async function
    result = runner.invoke(main, ['--repo', 'Joetib/webapp', '--branch', 'main', '--cleanup'])
    assert result.exit_code == 0
    mock_create_tests_for_repo.assert_called_once_with('Joetib', 'Joetib/webapp', 'main', token=None, cleanup=True)

@pytest.mark.django_db
def test_main_without_cleanup_option(runner, mock_create_tests_for_repo):
    mock_create_tests_for_repo.return_value = None  # simulate async function
    result = runner.invoke(main, ['--repo', 'Joetib/webapp', '--branch', 'main', '--no-cleanup'])
    assert result.exit_code == 0
    mock_create_tests_for_repo.assert_called_once_with('Joetib', 'Joetib/webapp', 'main', token=None, cleanup=False)