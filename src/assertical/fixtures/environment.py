import os
from contextlib import contextmanager
from typing import Callable, Generator

from assertical.snapshot import snapshot_kvp_store


def delete_environment_variable(name: str) -> None:
    """Deletes/unsets an environment variable with the specified name. If name DNE, nothing happens"""

    # Yes, we need to maintain the env AND the os.environ for deletion
    os.unsetenv(name)
    if name in os.environ:
        del os.environ[name]


@contextmanager
def environment_snapshot() -> Generator[dict[str, str], None, None]:
    """This class is designed to snapshot the current state of the os.environ with the expectation of resetting
    the os.environ to this state in the future.

    usage:
    with environment_snapshot():
        os.environ["MY_ENV"] = new_value
        os.environ["PATH"] = '/new/path'
        # Do test body

    # At this point the env modifications are reset (as soon as the with statement exits)
    """

    snapshot_env: Callable = lambda: dict(os.environ.items())

    def update_env(name: str, value: str) -> None:
        os.environ[name] = value

    with snapshot_kvp_store(snapshot_env, update_env, delete_environment_variable) as original_snapshot:
        yield original_snapshot
