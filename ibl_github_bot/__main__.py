import click
import asyncio
import os
from ibl_github_bot.tests_generator import create_tests_for_repo
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())


@click.command()
@click.option(
    "--repo",
    type=str,
    default="Joetib/webapp",
    help="Repository to clone. Must be of the format username/reponame. eg. ibleducation/ibl-ai-bot-app",
)
@click.option(
    "--branch", type=str, default="main", help="Branch to clone repository from."
)
@click.option(
    "--github-token",
    type=str,
    default=None,
    help="Github token used to authenticate and clone repository. Token must have write access to the repository.",
)
@click.option(
    "--cleanup",
    is_flag=True,
    default=False,
    help="Delete cloned repository after test generation.",
)
def main(repo: str, branch: str, github_token: str, cleanup: bool = True):
    if not github_token:
        github_token = os.getenv("GH_TOKEN")
    if not github_token:
        raise ValueError(
            "Please provide a github token or store it as `GH_TOKEN` environment variable."
        )
    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        create_tests_for_repo(
            "Joetib", repo, branch, token=github_token, cleanup=cleanup
        )
    )


if __name__ == "__main__":
    main()
