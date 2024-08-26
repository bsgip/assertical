from contextlib import contextmanager
from typing import Generator

from assertical.fake.generator import (
    BASE_CLASS_PUBLIC_MEMBERS,
    CLASS_INSTANCE_GENERATORS,
    CLASS_MEMBER_FETCHERS,
    PRIMITIVE_VALUE_GENERATORS,
)
from assertical.snapshot import snapshot_kvp_store


@contextmanager
def _dict_snapshot(d: dict) -> Generator[None, None, None]:
    with snapshot_kvp_store(lambda: dict(d), lambda k, v: d.update({k: v}), lambda k: d.pop(k)):
        yield


@contextmanager
def generator_registry_snapshot() -> Generator[None, None, None]:
    """This class is designed to snapshot the current state of the installed assertical.fake.generator registrations so
    that a test can override/add to their behaviour without polluting the global registry values beyond the test scope

    usage:

    with generator_registry_snapshot():
        register_value_generator(MyPrimitiveType, lambda seed: MyPrimitiveType(seed))
        register_base_type(
            MyBaseType,
            DEFAULT_CLASS_INSTANCE_GENERATOR,
            DEFAULT_MEMBER_FETCHER,
        )

        # Do test body


    # At this point the registry modifications are reset (as soon as the with statement exits)
    """

    with _dict_snapshot(PRIMITIVE_VALUE_GENERATORS):
        with _dict_snapshot(CLASS_INSTANCE_GENERATORS):
            with _dict_snapshot(CLASS_MEMBER_FETCHERS):
                with _dict_snapshot(BASE_CLASS_PUBLIC_MEMBERS):
                    yield
