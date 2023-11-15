from langchain.chat_models import ChatOpenAI
from langchain.schema.messages import HumanMessage, SystemMessage
from langchain.document_loaders import PythonLoader, DirectoryLoader
from pathlib import Path
import tqdm
import ast
import os
import aiohttp
from gidgethub.aiohttp import GitHubAPI
import git
import logging
import uuid
from pathlib import Path
import shutil
import datetime

logger = logging.getLogger(__name__)


BASE_DIR = Path.cwd() / "cached-repos"
logging.basicConfig()


class CodeParser:
    def parse(self, text: str) -> tuple[str, bool]:
        if text.startswith("```\n") or text.startswith("```python\n"):
            text = "\n".join(text.splitlines()[1:])
        if text.endswith("\n```"):
            text = text.strip("\n```").strip()

        if "```\n" in text:
            parts = text.split("```\n")
            if len(parts) == 2 and not parts[1].startswith("#"):
                text = parts[0]
            elif "Output" in parts[1]:
                text = parts[0]

        try:
            ast.parse(text)
            return text, True
        except Exception as e:
            print(e)
            print("Error parsing text as code")
            print(text)
        return text, False


system_message = SystemMessage(
    content="""You are an experienceed django and pytest developer. \
You have been given a set of python files in a django project \
You are expected to generate pytest compliant tests for a file specified by the user.

The project is loaded in the format

```python
# filenane here. 
Content of file here
```

For example:
```pythhon
# file1.py
from rest_framework import viewsets
from .models import Bot
from .serializers import BotSerializer

def content():
    pass
    
class BotViewSet(viewsets.ModelViewSet):
    model = Bot
    queryset = Bot.objects.all()
    serializer_class = BotSerializer

    def get_queryset(self):
        queryset = self.queryset
        queryset = queryset.filter(tenant=self.kwargs["org"])
        return super().get_queryset()
```
```pythhon
# file2.py
def conent():
    pass
```

You are then expected to generate pytests for a file among these lists as specified by the user.

For example:
Generate pytest compatible test file for file1.py

The output you yield must contain only the code output for the generated tests. Do not include any extra content. \
Make sure your output is python compliant and wrapped in starting ```python\n and ending with \n```
Do not forget to use "@pytest.mark.django_db" decorator on all tests
Also wherever you need a reference to the `User` models, use django.contrib.auth.get_user_model to get the user model.

For example
```python
# test for file1.py
import pytest
from django.contrib.auth  import get_user_model
User = get_user_model()

@pytest.mark.django_db
def test_content():
    pass
    
@pytest.mark.django_db
class TestBotViewSet:
    @classmethod
    def setup_method(cls):
        pass
    def test_unauthorized_call_raises_error(self):
        pass
```

In cases where the file mentioned by the user is empty, return the following output:
```python
# filename.py
# Empty
 file
```

Also if tests for a specific file already exists, include both the existing written tests and your own tests in the output test you writes.
Also you can use the contents of existing test files to know if there are any external functions or components you can call.
Also ensure that you return only the test file contents and not any extra content.
"""
)


def generate_tests(
    directory: Path,
    sub_path: Path = None,
    test_dir: Path = None,
    exclude_dirs=[
        "migrations",
    ],
):
    if sub_path == None:
        sub_path = directory
    if test_dir == None:
        test_dir = sub_path / "tests"

    documents = DirectoryLoader(
        path=directory,
        glob="*.py",
        recursive=True,
        show_progress=True,
        loader_cls=PythonLoader,
    ).load()
    print("Removing migration files")
    length = len(documents)
    documents = [
        document
        for document in documents
        if Path(document.metadata["source"]).parent.name not in exclude_dirs
    ]
    print("Removed %d files" % (len(documents) - length))
    if not documents:
        print("No documents left after removing migration files")
        return
    test_dir.mkdir(exist_ok=True)
    if not (test_dir / "__init__.py").exists():
        (test_dir / "__init__.py").touch()
    files_messages = [
        HumanMessage(
            content=[
                {
                    "type": "text",
                    "text": "# %s\n%s"
                    % (
                        Path(document.metadata["source"]).relative_to(directory),
                        document.page_content,
                    ),
                },
            ]
        )
        for document in documents
    ]

    # print(files_messages)

    messages = [
        system_message,
        *files_messages,
    ]

    chain = ChatOpenAI(
        model="gpt-4-1106-preview",
        temperature=0,
    )
    for document in tqdm.tqdm(
        [
            document
            for document in documents
            if Path(document.metadata["source"]).is_relative_to(sub_path)
            and document.page_content.strip() != ""
            and Path(document.metadata["source"]).parent.name
            not in [*exclude_dirs, "tests"]
        ]
    ):
        msg = chain.invoke(
            [
                *messages,
                HumanMessage(
                    content=[
                        {
                            "type": "text",
                            "text": "Generate pytest compatible test file for %s"
                            % Path(document.metadata["source"]).relative_to(directory),
                        }
                    ]
                ),
            ]
        )
        content, success = CodeParser().parse(msg.content)
        if not success:
            print("Failed to generate test for %s", document.metadata["source"])
            continue
        # print(content)
        if not content.strip():
            print(
                "skipping %s no tests generated"
                % Path(document.metadata["source"]).relative_to(directory)
            )
            continue
        print(
            "Generated tests for %s"
            % Path(document.metadata["source"]).relative_to(directory)
        )
        with open(
            test_dir
            / (
                "test_"
                + str(Path(document.metadata["source"]).relative_to(sub_path)).replace(
                    "/", "_"
                )
            ),
            "w",
        ) as f:
            f.write(content)


async def create_tests_for_repo(
    username: str,
    repo: str,
    branch: str = "main",
    token: str = os.getenv("GH_TOKEN"),
    cleanup: bool = True,
):
    """
    Asynchronously creates tests for a repository.
    The passed repository will be cloned to a temporary `cached-repos` directory.
    Args:
        username (str): The username of the repository owner.
        repo (str): The name of the repository.
        branch (str, optional): The branch to clone the repository from. Defaults to "main".
        token (str, optional): The GitHub token used for authentication. Defaults to the value of the "GH_TOKEN" environment variable.

    Returns:
        None
    """
    repo_username, repo_name = repo.split("/")
    index = str(uuid.uuid4())
    while (BASE_DIR / index).exists():
        index = str(uuid.uuid4())
    local_dir = BASE_DIR / index

    local_dir.mkdir(parents=True)
    logging.info("Cloning repository into %s", local_dir)
    repo_url = f"https://{token}@github.com/{repo}.git"
    logging.info("Cloning repo url [%s]", repo_url)
    new_branch = f"auto-tests-{index}"
    local_repo = git.Repo.clone_from(repo_url, local_dir, branch=branch)
    remote = local_repo.remote("origin")
    local_repo.git.checkout(branch)
    remote.pull()
    local_repo.git.checkout("-b", new_branch)
    logging.info("Successfully cloned repository into %s", local_dir)
    date = datetime.datetime.today().isoformat()
    logging.info("generating tests")
    for directory in local_dir.iterdir():
        if directory.is_dir() and directory.name not in [
            ".git",
            "tests",
            "migrations",
            "__pycache__",
        ]:
            generate_tests(
                directory=local_dir, sub_path=directory, test_dir=directory / "tests"
            )
            local_repo.index.add((directory / "tests").relative_to(local_dir))
            local_repo.index.commit(
                f"auto-generated tests for {directory.relative_to(local_dir)} on {date}"
            )
    logging.info("Pushing to remote branch %s" % new_branch)
    local_repo.remote().push("{}:{}".format(new_branch, new_branch)).raise_if_error()

    logging.info("Successfully generated and pushed tests in %s", repo)

    async with aiohttp.ClientSession(trust_env=True) as session:
        gh = GitHubAPI(session, username, oauth_token=os.getenv("GH_AUTH"))
        results = await gh.post(
            f"/repos/{repo}/pulls",
            data={
                "title": f"Auto-test from ibl_test_generator on {date}",
                "body": "Dear Admin I have generated tests for you. Thank you. And would be glad if you could check them out. \n ♡ ♥💕❤😘",
                "head": f"{repo_username}:{new_branch}",
                "base": branch,
            },
        )
        logging.info("Created pull request at %s" % results["url"])

    # uncomment to clean up cloned repository
    if cleanup:
        shutil.rmtree(local_dir)
