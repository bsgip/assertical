from contextlib import contextmanager
from typing import Callable, Generator, TypeVar, cast

KeyType = TypeVar("KeyType")
ValueType = TypeVar("ValueType")


@contextmanager
def snapshot_kvp_store(
    snapshot: Callable[[], dict[KeyType, ValueType]],
    update: Callable[[KeyType, ValueType], None],
    delete: Callable[[KeyType], None],
) -> Generator[dict[KeyType, ValueType], None, None]:
    """This class is designed to be a general purpose context manager for snapshotting some key value store upon enter
    and then restoring the key value store to its snapshotted state upon release.

    It's general purpose as two callables must be supplied - one will perform a snapshot into a dict, the second
    will provide the ability to update/delete

    snapshot: When called, snapshot whatever KVP store and return the key/values as a dict. Please ensure that the
              returned value does NOT reference the original KVP store items.
    update: When called, update/insert whatever KVP store with this key/value pair.
    delete: When called, delete key from the whatever KVP store.

    usage:

    MY_KEY_VALUE_STORE = {"a": 1, "b": 2}
    with snapshot_kvp_store(
        lambda: dict(MY_KEY_VALUE_STORE),  # The snapshot function
        lambda k, v: MY_KEY_VALUE_STORE.update({k: v}), # The update function
        lambda k: MY_KEY_VALUE_STORE.pop(k), # The delete function
    ):
        print(MY_KEY_VALUE_STORE)  # {"a": 1, "b": 2} # Nothing has changed
        MY_KEY_VALUE_STORE["a"] = 11
        del MY_KEY_VALUE_STORE["b"]
        MY_KEY_VALUE_STORE["c"] = 3
        print(MY_KEY_VALUE_STORE)  # {"a": 11, "c": 3}  # Updates have been applied
    print(MY_KEY_VALUE_STORE)  # {"a": 1, "b": 2} # Everything reverted to original state
    """

    # Take a snapshot
    original_snapshot: dict[KeyType, ValueType] = snapshot()

    # Return snapshot but mainly wait until the context is exited
    yield original_snapshot

    # Reset environment to snapshot
    # Firstly iterate the current environment to see what we need to rectify
    final_snapshot: dict[KeyType, ValueType] = snapshot()
    visited_keys = set()
    for k, v in final_snapshot.items():
        visited_keys.add(k)

        if k in original_snapshot:
            old_value: ValueType = cast(ValueType, original_snapshot.get(k))
            update(k, old_value)
        else:
            delete(k)

    # Next iterate our stored snapshot to find keys that may have been deleted and didn't appear in our previous
    # enumeration
    for k, v in original_snapshot.items():
        if k in visited_keys:
            continue

        # At this point - we have a variable in the snapshot that didn't appear in the current env - restore it
        update(k, v)
