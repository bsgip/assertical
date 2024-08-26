from typing import Any

import pytest

from assertical.snapshot import snapshot_kvp_store

DELETE_VALUE = {"delete": "me"}


@pytest.mark.parametrize(
    "original_store, operations",
    [
        ({}, []),
        ({}, [("a", 1)]),
        ({}, [("a", 1), ("a", 2)]),
        ({"a": 1, "b": 2}, [("a", DELETE_VALUE), ("b", "stringval"), ("c", 99)]),
        ({"a": 1, "b": 2}, [("a", DELETE_VALUE), ("b", "stringval"), ("c", 99), ("c", 98), ("a", 1)]),
        ({"a": 1, "b": 2}, [("a", DELETE_VALUE), ("b", DELETE_VALUE)]),
        ({"a": None, "b": 2}, [("a", 1), ("b", None), ("c", None)]),
    ],
)
def test_snapshot_kvp_store(original_store: dict[str, Any], operations: list[tuple[str, Any]]):

    original_store_clone = dict(original_store)

    with snapshot_kvp_store(
        lambda: dict(original_store),  # The snapshot function
        lambda k, v: original_store.update({k: v}),  # The update function
        lambda k: original_store.pop(k),  # The delete function
    ):
        # Apply each operation to original_store
        for key, new_val in operations:
            if new_val is DELETE_VALUE:
                del original_store[key]
            else:
                original_store[key] = new_val

            assert original_store != original_store_clone, "Validate a mutation has occurred"

    # Ensure that after snapshot everything reverts
    assert original_store == original_store_clone
    assert original_store is not original_store_clone


def test_snapshot_kvp_store_docs_example():
    """Runs the basic example listed the docstring"""

    MY_KEY_VALUE_STORE = {"a": 1, "b": 2}
    saved_id = id(MY_KEY_VALUE_STORE)
    with snapshot_kvp_store(
        lambda: dict(MY_KEY_VALUE_STORE),  # The snapshot function
        lambda k, v: MY_KEY_VALUE_STORE.update({k: v}),  # The update function
        lambda k: MY_KEY_VALUE_STORE.pop(k),  # The delete function
    ):
        # Upon entering - nothing has changed
        assert MY_KEY_VALUE_STORE == {"a": 1, "b": 2}
        assert saved_id == id(MY_KEY_VALUE_STORE), "Reference is still the same"

        # Apply changes, ensure they stick
        MY_KEY_VALUE_STORE["a"] = 11
        assert MY_KEY_VALUE_STORE == {"a": 11, "b": 2}
        del MY_KEY_VALUE_STORE["b"]
        assert MY_KEY_VALUE_STORE == {"a": 11}
        MY_KEY_VALUE_STORE["c"] = 3
        assert MY_KEY_VALUE_STORE == {"a": 11, "c": 3}

    # Upon exiting - ensure everything reverts
    assert MY_KEY_VALUE_STORE == {"a": 1, "b": 2}
    assert saved_id == id(MY_KEY_VALUE_STORE), "Reference is still the same"
