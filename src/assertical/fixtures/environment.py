import os
from contextlib import contextmanager
from typing import Generator, Optional


def update_environment_variable(name: str, new_value: Optional[str]) -> None:
    """Updates/Deletes an environment variable with name. This applies to the current environment

    name: The name of the environment variable to update
    new_value: If None - the environment variable is deleted. Otherwise sets the value to new_value"""
    if new_value is None:
        if name in os.environ:
            # Yes, we need to maintain the env AND the os.environ for deletion
            os.unsetenv(name)
            del os.environ[name]
    else:
        os.environ[name] = new_value


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

    # Take a snapshot
    snapshot: dict[str, str] = dict(os.environ.items())

    # Return snapshot but mainly wait until the context is exited
    yield snapshot

    # Reset environment to snapshot
    # Firstly iterate the current environment to see what we need to rectify
    visited_variables = set()
    snapshot: dict[str, str] = dict(os.environ.items())
    for k, v in os.environ.items():
        visited_variables.add(k)

        old_value = snapshot.get(k, None)
        if v != old_value:
            update_environment_variable(k, old_value)

    # Next iterate our stored snapshot to find keys that may have been deleted and didn't appear in our previous
    # enumeration
    for k, v in snapshot.items():
        if k in visited_variables:
            continue

        # At this point - we have a variable in the snapshot that didn't appear in the current env - restore it
        update_environment_variable(k, v)
