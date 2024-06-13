from typing import Any, Optional

from assertical.fake.generator import check_class_instance_equality


def assert_class_instance_equality(
    t: type,
    expected: Any,
    actual: Any,
    ignored_properties: Optional[set[str]] = None,
) -> None:
    """Given a type t and two instances. Run through the public members of t and assert that the values all match up.
    This will only compare properties whose type passes is_generatable_type.

    Any "private" members beginning with '_' will be skipped

    ignored properties are a set of property names that will NOT be asserted for equality"""
    errors = check_class_instance_equality(t, expected, actual, ignored_properties)
    assert len(errors) == 0, "\n".join(errors)
