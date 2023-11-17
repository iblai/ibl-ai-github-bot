import click
import asyncio
import os
from ibl_github_bot.tests_generator import create_tests_for_repo
from dotenv import load_dotenv, find_dotenv
import logging
logging.basicConfig(level=logging.INFO)


load_dotenv(find_dotenv())


@click.command()
@click.option(
    "--repo",
    type=str,
    help="Repository to clone. Must be of the format username/reponame. eg. ibleducation/ibl-ai-github-bot",
)
@click.option(
    "--branch", type=str, default="main", help="Branch to clone repository from."
)
@click.option(
    "--file",
    "-f", 
    multiple=True, help="Target file in repository to test. Defaults to all files. You can pass multiple files with -f file1 -f file2"
)
@click.option(
    "--cleanup",
    is_flag=True,
    default=False,
    help="Delete cloned repository after test generation.",
)
@click.option(
    "--github-token",
    type=str,
    default=None,
    help="Github token used to authenticate and clone repository. Token must have write access to the repository.",
)

@click.option(
    "--github-username",
    type=str,
    default=None,
    help="Username associated with the github token"
)
def main(repo: str, branch: str, github_token: str, github_username: str, cleanup: bool = True, file: list[str]=None):
    if not github_token:
        github_token = os.getenv("GH_TOKEN")
    if not github_token:
        raise ValueError(
            "Please provide a github token or store it as `GH_TOKEN` environment variable."
        )
    if not github_username:
        github_username = os.getenv("GH_USERNAME")
    if not github_username:
        raise ValueError(
            "Please provide a github username or store it as `GH_USERNAME` environment variable."
        )
    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        create_tests_for_repo(
            github_username, repo, branch, token=github_token, cleanup=cleanup,
            target_files=file
        )
    )


if __name__ == "__main__":
    main()
