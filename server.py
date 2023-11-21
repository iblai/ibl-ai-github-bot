import datetime
import os
import shutil
import uuid
import aiohttp

from aiohttp import web
from ibl_github_bot.configuration import DependencyGraph
from ibl_github_bot.tests_generator import create_tests_for_repo, generate_tests
from gidgethub import routing, sansio
from gidgethub import aiohttp as gh_aiohttp
from gidgethub import apps
import os
import gidgethub.routing
from gidgethub import aiohttp as gh_aiohttp
from aiohttp import web
import cachetools
from pathlib import Path
from dotenv import load_dotenv, find_dotenv
import logging
import git

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv(find_dotenv())

BASE_DIR = Path(__file__).parent / "cached-repos"
BASE_DIR.mkdir(exist_ok=True)

router = gidgethub.routing.Router()
routes = web.RouteTableDef()

cache = cache = cachetools.LRUCache(maxsize=500)
secret = os.environ.get("GH_SECRET", "somepassword")
app_id = os.environ.get("GH_APP_ID")

with open("iblai-django-tester.2023-11-21.private-key.pem", "r") as f:
    private_key = f.read()




@router.register("installation", action="created")
async def repo_installation_added(event, gh: gh_aiohttp.GitHubAPI, *args, **kwargs):
    installation_id = event.data["installation"]["id"]

    installation_access_token = await apps.get_installation_access_token(
        gh,
        installation_id=installation_id,
        app_id=app_id,
        private_key=private_key,
    )
    repo_name = event.data["repositories"][0]["full_name"]
    url = f"/repos/{repo_name}/issues"
    await gh.post(
        url,
        data={
            "title": "Thanks for installing my bot",
            "body": "Thanks!",
        },
        oauth_token=installation_access_token["token"],
    )


@routes.post("/")
async def main(request):
    body = await request.read()

    event = sansio.Event.from_http(request.headers, body, secret=secret)

    async with aiohttp.ClientSession() as session:
        gh = gh_aiohttp.GitHubAPI(session, "Joetib/webapp")
        await router.dispatch(event, gh)
    return web.Response(status=200)


async def get_token(event, gh):
    installation_id = event.data["installation"]["id"]

    installation_access_token = await apps.get_installation_access_token(
        gh,
        installation_id=installation_id,
        app_id=app_id,
        private_key=private_key,
    )
    return installation_access_token["token"]


@router.register("pull_request", action="opened")
@router.register("pull_request", action="reopened")
@router.register("pull_request", action="closed")
async def handle_pull_request_event(event, gh: gh_aiohttp.GitHubAPI, *args, **kwargs):
    print("received pull request data", event, gh, args, kwargs)

    installation_id = event.data["installation"]["id"]

    installation_access_token = await apps.get_installation_access_token(
        gh,
        installation_id=installation_id,
        app_id=app_id,
        private_key=private_key,
    )

    # Retrieve necessary information from the event payload
    repo = event.data["repository"]["full_name"]
    action = event.data["action"]
    pull_request_number = event.data["pull_request"]["number"]

    if not "opened" in action:
        logger.info("Exiting because action is not 'opened'")
        return

    await gh.post(
        f"/repos/{repo}/issues/{pull_request_number}/comments",
        data={"body": "Thanks for the pull request!"},
        oauth_token=installation_access_token["token"],
    )
    target_files = []
    repo_username, repo_name = repo.split("/")
    index = str(uuid.uuid4())
    while (BASE_DIR / index).exists():
        index = str(uuid.uuid4())
    local_dir = BASE_DIR / index
    target_file_paths = [local_dir / file for file in target_files]

    local_dir.mkdir(parents=True)
    logging.info("Cloning repository into %s", local_dir)

    branch = event.data["pull_request"]["head"]["ref"] 
    token = await get_token(event, gh)

    repo_url = f"https://{token}@github.com/{repo}.git"
    logging.info("Cloning repo url [%s]", repo_url)
    new_branch = f"auto-tests-iblai-{index}"
    local_repo = git.Repo.clone_from(repo_url, local_dir, branch=branch)
    remote = local_repo.remote("origin")
    local_repo.git.checkout(branch)
    remote.pull()
    new_branch = branch
    # local_repo.git.checkout("-b", new_branch)
    dependency_graph = DependencyGraph(local_dir / "ibl_test_config.yaml")

    logging.info("Successfully cloned repository into %s", local_dir)
    date = datetime.datetime.today().strftime("%A %B %d %Y, %X")
    logging.info("generating tests")
    created_commit = False
    for directory in local_dir.iterdir():
        if (
            directory.is_dir()
            and directory.name not in dependency_graph.get_global_settings()["exclude"]
        ):
            success = generate_tests(
                directory=local_dir,
                dependency_graph=dependency_graph,
                sub_path=directory,
                test_dir=directory / "tests",
                target_files=target_file_paths,
            )
            if not success:
                continue

            local_repo.index.add((directory / "tests").relative_to(local_dir))
            local_repo.index.commit(
                f"auto-generated tests for {directory.relative_to(local_dir)} on {date}"
            )
            logging.info(
                f"Created commit with message: auto-generated tests for {directory.relative_to(local_dir)} on {date}"
            )
            created_commit = True
            break
    if not created_commit:
        logging.info("No tests generated")
        return
    logging.info("Pushing to remote branch %s" % new_branch)

    # with the assumption that at this point the oauth token may have expired,
    # we generate a new token for our use.
    token = await get_token(event, gh)
    repo_url = f"https://{token}@github.com/{repo}.git"
    logger.info("Changing repo url as token may have expired: New url [%s]", repo_url)
    local_repo.remote().set_url(repo_url)

    logging.info("Pushing to remote branch %s" % new_branch)
    local_repo.remote().push("{}:{}".format(new_branch, new_branch)).raise_if_error()

    logging.info("Successfully generated and pushed tests in %s", repo)
    results = await gh.post(
        f"/repos/{repo}/pulls",
        data={
            "title": f"Auto-tests generated by ibl.ai ⚡",
            "body": """> [!IMPORTANT] \
                        \n> Remember to check out the pull request and run the tests before merging. \
                        \n> Thank you.
                        """,
            "head": f"{repo_username}:{new_branch}",
            "base": branch,
        },
    )
    logging.info("Created pull request at %s" % results["url"])

    # uncomment to clean up cloned repository
    shutil.rmtree(local_dir)




if __name__ == "__main__":
    app = web.Application()
    app.add_routes(routes)
    port = os.environ.get("PORT", "8080")
    port = int(port)
    web.run_app(app, port=port)
