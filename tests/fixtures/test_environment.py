import os
from typing import Optional

import pytest

from assertical.fixtures.environment import (
    environment_snapshot,
    update_environment_variable,
)

NEVER_EXISTS_NAME = "92y539hgf3_123akjh"
ALWAYS_EXISTS_NAME = "PATH"
if ALWAYS_EXISTS_NAME not in os.environ:
    ALWAYS_EXISTS_NAME = os.environ.keys()[0]


@pytest.mark.parametrize(
    "kvps",
    [
        [],
        [(NEVER_EXISTS_NAME, "value_1")],
        [(NEVER_EXISTS_NAME, "value_1 updated"), ("VARIABLE_2", "value_2"), ("VARIABLE_3", None)],
        [(NEVER_EXISTS_NAME, "value_1 updated"), ("VARIABLE_2", None)],
        [(NEVER_EXISTS_NAME, ""), (ALWAYS_EXISTS_NAME, ""), ("VARIABLE_3", "abc_123,def13'\"xas")],
        [(NEVER_EXISTS_NAME, None), (ALWAYS_EXISTS_NAME, None)],
        [(NEVER_EXISTS_NAME, None), (ALWAYS_EXISTS_NAME, "new_value")],
    ],
)
def test_environment_snapshot(kvps: list[tuple[str, Optional[str]]]):
    """This is a bit of a weird test - we deliberately define test cases that might interfere with each other as
    the environment is preserved between tests"""
    original_always_exists = os.environ[ALWAYS_EXISTS_NAME]  # Assume we always have a variable
    original_snapshot = sorted(os.environ.items())
    with pytest.raises(KeyError):
        os.environ[NEVER_EXISTS_NAME]

    # update our environment
    with environment_snapshot():

        # Mess with the environment
        for k, v in kvps:
            update_environment_variable(k, v)

            if v is not None:
                assert os.environ[k] == v
            else:
                with pytest.raises(KeyError):
                    os.environ[k]

    # Environment should now be reset now that the context has exited
    assert original_always_exists == os.environ[ALWAYS_EXISTS_NAME]
    assert original_snapshot == sorted(os.environ.items())
    with pytest.raises(KeyError):
        os.environ[NEVER_EXISTS_NAME]
