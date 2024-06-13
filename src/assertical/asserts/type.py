from typing import Any, Optional, get_origin


def assert_list_type(expected_element_type: type, obj: Any, count: Optional[int] = None) -> None:
    """Asserts that obj is not None, is a list and every element is expected_element_type

    if count is specified - an additional assert will be made on the count of elements in obj"""
    assert obj is not None
    assert (
        isinstance(obj, list) or get_origin(type(obj)) == list
    ), f"Expected a list type for obj but got {type(obj)} instead"
    assert_iterable_type(expected_element_type, obj, count=count)


def assert_dict_type(expected_key_type: type, expected_value_type: type, obj: Any, count: Optional[int] = None) -> None:
    """Asserts that obj is not None, is a dict and every key is expected_key_type and every value is expected_value_type

    if count is specified - an additional assert will be made on the count of elements in obj"""
    assert obj is not None
    assert (
        isinstance(obj, dict) or get_origin(type(obj)) == dict
    ), f"Expected a dict type for obj but got {type(obj)} instead"
    assert_iterable_type(expected_key_type, obj.keys(), count=count)
    assert_iterable_type(expected_value_type, obj.values(), count=count)


def assert_iterable_type(expected_element_type: type, obj: Any, count: Optional[int] = None) -> None:
    """Asserts that obj is not None, is iterable and every element is expected_element_type

    if count is specified - an additional assert will be made on the count of elements in obj"""
    assert obj is not None

    try:
        iter(obj)
    except TypeError as ex:
        assert False, f"Expected {type(obj)} to be iterable but calling iter(obj) raises {ex}"

    enumerated_item_count = 0
    for i, val in enumerate(obj):
        enumerated_item_count += 1
        assert isinstance(
            val, expected_element_type
        ), f"obj[{i}]: Element has type {type(val)} instead of {expected_element_type}"

    if count is not None:
        assert enumerated_item_count == count
