from dataclasses import dataclass
from typing import Any, Iterable, Optional

import pytest

from assertical.asserts.type import (
    assert_dict_type,
    assert_iterable_type,
    assert_list_type,
    assert_set_type,
)


@dataclass(frozen=True)
class MyClass:
    num: int
    name: str


@pytest.mark.parametrize(
    "el_type, obj, count, assert_pass",
    [
        (int, None, None, False),
        (int, [], None, True),
        (float, [], 0, True),
        (float, [], 1, False),
        (float, [1.2, 1.3], None, True),
        (float, [1.2, 1.3], 2, True),
        (float, [1.2, 1, 1.4], None, False),  # Has an int
        (MyClass, [1.2, 1.4], None, False),
        (MyClass, [MyClass(1, "1"), MyClass(2, "2")], None, True),
        (MyClass, [MyClass(1, "1"), "MyClass", MyClass(2, "2")], None, False),
        (str, [MyClass(1, "1")], None, False),
        (str, (s for s in ["s1", "s2"]), 2, True),  # Use a generator
        (MyClass, (e for e in [MyClass(1, "b")]), 1, True),  # Use a generator
        (MyClass, (e for e in []), 0, True),  # Use a empty generator
    ],
)
def test_assert_iterable_type(el_type: type, obj: Iterable, count: Optional[int], assert_pass: bool):
    if assert_pass:
        assert_iterable_type(el_type, obj, count)
    else:
        with pytest.raises(AssertionError):
            assert_iterable_type(el_type, obj, count)


@pytest.mark.parametrize(
    "el_type, obj, count, assert_pass",
    [
        (int, None, None, False),
        (int, [], None, True),
        (int, [], 0, True),
        (int, set([1, 2]), None, False),  # Set doesn't match
        (int, (v for v in [1, 2]), None, False),  # Generator doesn't match
        (int, [1, 2, 3], None, True),
        (int, [1, 2, 3], 3, True),
        (int, [1, 2.2, 3], None, False),  # float in list of ints
        (MyClass, [MyClass(1, "a"), MyClass(2, "b")], 2, True),
    ],
)
def test_assert_list_type(el_type: type, obj: Any, count: Optional[int], assert_pass: bool):
    if assert_pass:
        assert_list_type(el_type, obj, count)
    else:
        with pytest.raises(AssertionError):
            assert_list_type(el_type, obj, count)


@pytest.mark.parametrize(
    "el_type, obj, count, assert_pass",
    [
        (int, None, None, False),
        (int, [], None, False),  # not a set
        (int, set([]), None, True),
        (int, set([]), 0, True),
        (int, [1, 2], None, False),  # list doesn't match
        (int, (v for v in [1, 2]), None, False),  # Generator doesn't match
        (int, set([1, 2, 3]), None, True),
        (int, set([1, 2, 3]), 3, True),
        (int, set([1, 2.2, 3]), None, False),  # float in list of ints
        (MyClass, set([MyClass(1, "a"), MyClass(2, "b")]), 2, True),
    ],
)
def test_assert_set_type(el_type: type, obj: Any, count: Optional[int], assert_pass: bool):
    if assert_pass:
        assert_set_type(el_type, obj, count)
    else:
        with pytest.raises(AssertionError):
            assert_set_type(el_type, obj, count)


@pytest.mark.parametrize(
    "key_type, val_type, obj, count, assert_pass",
    [
        (str, str, None, None, False),
        (str, int, {}, None, True),
        (str, int, {}, 0, True),
        (str, int, set([1, 2]), None, False),  # Set doesn't match
        (str, int, (v for v in [("a", 1)]), None, False),  # Generator doesn't match
        (str, int, {"a": 1, "b": 2}, None, True),
        (str, int, {"a": 1, "b": 2}, 2, True),
        (str, int, {"a": 1, "b": 2.2}, 2, False),  # float value
        (str, int, {"a": 1, 222: 2}, 2, False),  # int key
        (str, MyClass, {"a": MyClass(11, "aa"), "b": MyClass(1, "a")}, 2, True),
    ],
)
def test_assert_dict_type(key_type: type, val_type: type, obj: Any, count: Optional[int], assert_pass: bool):
    if assert_pass:
        assert_dict_type(key_type, val_type, obj, count)
    else:
        with pytest.raises(AssertionError):
            assert_dict_type(key_type, val_type, obj, count)
