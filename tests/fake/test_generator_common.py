import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import IntEnum, IntFlag, auto
from typing import Generator, List, Optional, Union

import pytest
from sqlalchemy.orm import Mapped

from assertical.asserts.type import assert_list_type
from assertical.fake.generator import (
    PropertyGenerationDetails,
    _PlaceholderDataclassBase,
    enumerate_class_properties,
    generate_value,
    get_enum_type,
    get_first_generatable_primitive,
    get_generatable_class_base,
    get_optional_type_argument,
    is_generatable_type,
    is_optional_type,
    is_passthrough_type,
    remove_passthrough_type,
)


class CustomFlags(IntFlag):
    """Various bit flags"""

    FLAG_1 = auto()
    FLAG_2 = auto()
    FLAG_3 = auto()
    FLAG_4 = auto()


class CustomIntEnum(IntEnum):
    VALUE_1 = auto()
    VALUE_2 = auto()
    VALUE_3 = 998


ALL_ENUM_TYPES: list[type] = [CustomFlags, CustomIntEnum]

# StrEnum is something we want support for but it's was only introduced in python 3.11
if sys.version_info >= (3, 11):
    from enum import StrEnum

    class CustomStringEnum(StrEnum):
        VALUE_1 = "My Custom Value 1"
        VALUE_2 = "My Custom Value 2"
        VALUE_3 = "VALUE_3"

    ALL_ENUM_TYPES.append(CustomStringEnum)


class RandomOtherClass:
    myInt: int

    def __init__(self, myInt) -> None:
        self.myInt = myInt


@dataclass(frozen=True)
class ReferenceDataclass:
    myOptInt: Optional[int]
    myInt: int


def test_generate_value():
    """This won't exhaustively test all types - it's just a quick sanity check on the generation code"""
    assert isinstance(generate_value(int, 1), int)
    assert generate_value(int, 1) != generate_value(int, 2)
    assert generate_value(int, 1, True) != generate_value(int, 2, True)
    assert generate_value(Optional[int], 1, True) is None
    assert generate_value(Optional[int], 2, True) is None

    assert isinstance(generate_value(str, 1), str)
    assert generate_value(str, 1) != generate_value(str, 2)
    assert generate_value(str, 1, True) != generate_value(str, 2, True)
    assert generate_value(Optional[str], 1, True) is None
    assert generate_value(Optional[str], 2, True) is None

    # unknown types should error out
    with pytest.raises(Exception):
        generate_value(ReferenceDataclass, 1)
    with pytest.raises(Exception):
        generate_value(RandomOtherClass, 1)
    with pytest.raises(Exception):
        generate_value(list[int], 1)

    assert generate_value(str, 1, True) == generate_value(str, 1, True)
    assert generate_value(str, 1, True) is not generate_value(str, 1, True)


def test_get_enum_type_non_enums():
    assert get_enum_type(None, True) is None
    assert get_enum_type(None, False) is None
    assert get_enum_type(Union[int, str], True) is None
    assert get_enum_type(Union[int, str], False) is None
    assert get_enum_type(int, True) is None
    assert get_enum_type(int, False) is None
    assert get_enum_type(Optional[int], True) is None
    assert get_enum_type(Optional[int], False) is None
    assert get_enum_type(Mapped[Optional[int]], True) is None
    assert get_enum_type(Mapped[Optional[int]], False) is None


@pytest.mark.parametrize("t", ALL_ENUM_TYPES)
def test_get_enum_type_with_enums(t):
    assert get_enum_type(t, False) == t
    assert get_enum_type(Optional[t], False) == t
    assert get_enum_type(Mapped[Optional[t]], False) == t
    assert get_enum_type(Mapped[t], False) == t
    assert get_enum_type(Union[int, str, t], False) == t
    assert get_enum_type(Union[int, str, Optional[t]], False) == t

    assert get_enum_type(t, True) == t
    assert get_enum_type(Optional[t], True) == Optional[t]
    assert get_enum_type(Mapped[Optional[t]], True) == Optional[t]
    assert get_enum_type(Mapped[t], True) == t
    assert get_enum_type(Union[int, str, t], True) == t
    assert get_enum_type(Union[int, str, Optional[t]], True) == Optional[t]


@pytest.mark.parametrize("t", ALL_ENUM_TYPES)
def test_get_enum_type_with_enums_py310_optional(t):
    """Tests the py310+ version of describing optional types as 'int | None' instead of Optional[int]"""

    if sys.version_info < (3, 10):
        return

    assert get_enum_type(t | None, False) == t
    assert get_enum_type(None | t, False) == t
    assert get_enum_type(Mapped[t | None], False) == t
    assert get_enum_type(Mapped[None | t], False) == t
    assert get_enum_type(int | str | t, False) == t
    assert get_enum_type(int | str | (t | None), False) == t
    assert get_enum_type(int | str | (None | t), False) == t
    assert get_enum_type(t | None, True) == t | None
    assert get_enum_type(None | t, True) == (None | t)
    assert get_enum_type(Mapped[t | None], True) == t | None
    assert get_enum_type(Mapped[None | t], True) == (None | t)
    assert get_enum_type(int | str | (t | None), True) == t | None
    assert get_enum_type(int | str | (None | t), True) == (None | t)


@pytest.mark.parametrize("t", ALL_ENUM_TYPES)
def test_generate_value_enums(t: type):
    """Tests that generate_value plays nice with enum values"""

    COUNT = len(t) * 3
    assert COUNT > 0
    generated_items: list = []
    for i in range(COUNT):
        v = generate_value(t, i)
        assert isinstance(v, t)
        assert v == generate_value(Optional[t], i, optional_is_none=False)
        assert v == generate_value(Mapped[Optional[t]], i, optional_is_none=False)
        assert v == generate_value(Mapped[t], i, optional_is_none=True)
        assert generate_value(Optional[t], i, optional_is_none=True) is None

        generated_items.append(v)

    assert len(generated_items) == COUNT

    unique_items = set(generated_items)
    assert len(unique_items) < COUNT
    assert len(unique_items) == len(t)
    assert all([v in t for v in generated_items]), "All generated values should be enum members"


def test_get_generatable_class_base():
    assert get_generatable_class_base(ReferenceDataclass) == _PlaceholderDataclassBase
    assert get_generatable_class_base(Optional[ReferenceDataclass]) == _PlaceholderDataclassBase

    assert get_generatable_class_base(Optional[RandomOtherClass]) is None
    assert get_generatable_class_base(RandomOtherClass) is None
    assert get_generatable_class_base(str) is None
    assert get_generatable_class_base(Optional[str]) is None


def test_get_optional_type_argument():
    assert get_optional_type_argument(Optional[datetime]) == datetime
    assert get_optional_type_argument(Optional[int]) == int
    assert get_optional_type_argument(Optional[str]) == str
    assert get_optional_type_argument(Union[type(None), str]) == str
    assert get_optional_type_argument(Union[str, type(None)]) == str
    assert get_optional_type_argument(Mapped[Optional[str]]) == str

    assert get_optional_type_argument(RandomOtherClass) is None
    assert get_optional_type_argument(ReferenceDataclass) is None
    assert get_optional_type_argument(Union[int, str]) is None


def test_get_optional_type_argument_py310():
    """Tests the py310+ version of describing optional types as 'int | None' instead of Optional[int]"""
    if sys.version_info < (3, 10):
        return

    assert get_optional_type_argument(datetime | None) == datetime
    assert get_optional_type_argument(None | datetime) == datetime
    assert get_optional_type_argument(int | None) == int
    assert get_optional_type_argument(None | int) == int
    assert get_optional_type_argument(str | None) == str
    assert get_optional_type_argument(None | str) == str
    assert get_optional_type_argument(ReferenceDataclass | None) == ReferenceDataclass
    assert get_optional_type_argument(None | ReferenceDataclass) == ReferenceDataclass


def test_is_optional_type():
    assert is_optional_type(Optional[datetime])
    assert is_optional_type(Optional[int])
    assert is_optional_type(Optional[str])
    assert is_optional_type(Optional[ReferenceDataclass])
    assert is_optional_type(Union[type(None), str])
    assert is_optional_type(Union[str, type(None)])
    assert is_optional_type(Mapped[Optional[str]])
    assert is_optional_type(Mapped[Optional[ReferenceDataclass]])

    assert not is_optional_type(RandomOtherClass)
    assert not is_optional_type(ReferenceDataclass)
    assert not is_optional_type(Union[int, str])


def test_is_passthrough_type():
    assert is_passthrough_type(Mapped[int])
    assert is_passthrough_type(Mapped[Optional[int]])
    assert is_passthrough_type(Mapped[Union[str, int]])

    assert not is_passthrough_type(Union[str, int])
    assert not is_passthrough_type(str)
    assert not is_passthrough_type(list[int])


def test_remove_passthrough_type():
    assert remove_passthrough_type(str) == str
    assert remove_passthrough_type(Optional[str]) == Optional[str]
    assert remove_passthrough_type(Mapped[Optional[str]]) == Optional[str]
    assert remove_passthrough_type(Mapped[str]) == str
    assert remove_passthrough_type(list[str]) == list[str]
    assert remove_passthrough_type(list[ReferenceDataclass]) == list[ReferenceDataclass]
    assert remove_passthrough_type(Mapped[list[ReferenceDataclass]]) == list[ReferenceDataclass]
    assert remove_passthrough_type(dict[str, int]) == dict[str, int]


def test_is_generatable_type():
    """Simple test cases for common is_generatable_type values"""
    assert is_generatable_type(int)
    assert is_generatable_type(str)
    assert is_generatable_type(bool)
    assert is_generatable_type(datetime)
    assert is_generatable_type(CustomFlags)
    assert is_generatable_type(Optional[CustomFlags])
    assert is_generatable_type(Mapped[CustomFlags])
    assert is_generatable_type(Optional[int])
    assert is_generatable_type(Union[int, str])
    assert is_generatable_type(Union[type(None), str])
    assert is_generatable_type(Mapped[Optional[int]])
    assert is_generatable_type(Mapped[Optional[datetime]])
    assert is_generatable_type(Optional[timedelta])

    assert not is_generatable_type(ReferenceDataclass)
    assert not is_generatable_type(RandomOtherClass)
    assert not is_generatable_type(Mapped[ReferenceDataclass])
    assert not is_generatable_type(Mapped[Optional[ReferenceDataclass]])

    # check collections
    assert not is_generatable_type(Optional[list[ReferenceDataclass]])
    assert not is_generatable_type(Optional[List[ReferenceDataclass]])
    assert not is_generatable_type(list[ReferenceDataclass])
    assert not is_generatable_type(list[int])
    assert not is_generatable_type(set[datetime])
    assert not is_generatable_type(dict[str, int])


def test_get_first_generatable_primitive():
    """Enumerating a ton of test cases in order to provide certainty about the behaviour of this function (especially
    when dealing with some complex generic type combos)"""

    # With include_optional enabled
    assert get_first_generatable_primitive(int, include_optional=True) == int
    assert get_first_generatable_primitive(datetime, include_optional=True) == datetime
    assert get_first_generatable_primitive(str, include_optional=True) == str
    assert get_first_generatable_primitive(CustomFlags, include_optional=True) == CustomFlags
    assert get_first_generatable_primitive(Optional[CustomFlags], include_optional=True) == Optional[CustomFlags]
    assert get_first_generatable_primitive(Optional[int], include_optional=True) == Optional[int]
    assert get_first_generatable_primitive(Union[int, str], include_optional=True) == int
    assert get_first_generatable_primitive(Union[Optional[str], int], include_optional=True) == Optional[str]
    assert get_first_generatable_primitive(Mapped[str], include_optional=True) == str
    assert get_first_generatable_primitive(Mapped[Optional[str]], include_optional=True) == Optional[str]
    assert get_first_generatable_primitive(Mapped[CustomFlags], include_optional=True) == CustomFlags
    assert (
        get_first_generatable_primitive(Mapped[Optional[CustomFlags]], include_optional=True) == Optional[CustomFlags]
    )
    assert get_first_generatable_primitive(Mapped[Optional[Union[str, int]]], include_optional=True) == Optional[str]

    assert get_first_generatable_primitive(Mapped[ReferenceDataclass], include_optional=True) is None
    assert get_first_generatable_primitive(ReferenceDataclass, include_optional=True) is None
    assert get_first_generatable_primitive(list[str], include_optional=True) is None
    assert get_first_generatable_primitive(list[int], include_optional=True) is None
    assert get_first_generatable_primitive(Mapped[list[str]], include_optional=True) is None

    # With include_optional disabled
    assert get_first_generatable_primitive(int, include_optional=False) == int
    assert get_first_generatable_primitive(datetime, include_optional=False) == datetime
    assert get_first_generatable_primitive(str, include_optional=False) == str
    assert get_first_generatable_primitive(CustomFlags, include_optional=False) == CustomFlags
    assert get_first_generatable_primitive(Optional[CustomFlags], include_optional=False) == CustomFlags
    assert get_first_generatable_primitive(Optional[int], include_optional=False) == int
    assert get_first_generatable_primitive(Union[int, str], include_optional=False) == int
    assert get_first_generatable_primitive(Union[Optional[str], int], include_optional=False) == str
    assert get_first_generatable_primitive(Mapped[str], include_optional=False) == str
    assert get_first_generatable_primitive(Mapped[Optional[str]], include_optional=False) == str
    assert get_first_generatable_primitive(Mapped[CustomFlags], include_optional=False) == CustomFlags
    assert get_first_generatable_primitive(Mapped[Optional[CustomFlags]], include_optional=False) == CustomFlags
    assert get_first_generatable_primitive(Mapped[Optional[Union[str, int]]], include_optional=False) == str

    assert get_first_generatable_primitive(list[str], include_optional=False) is None
    assert get_first_generatable_primitive(list[int], include_optional=False) is None
    assert get_first_generatable_primitive(Mapped[list[str]], include_optional=False) is None


def test_get_first_generatable_primitive_py310_optional():
    """Tests the py310+ version of describing optional types as 'int | None' instead of Optional[int]"""
    if sys.version_info < (3, 10):
        return

    # With include_optional enabled
    assert get_first_generatable_primitive(CustomFlags | None, include_optional=True) == CustomFlags | None
    assert get_first_generatable_primitive(None | CustomFlags, include_optional=True) == (None | CustomFlags)
    assert get_first_generatable_primitive(int | None, include_optional=True) == int | None
    assert get_first_generatable_primitive(None | int, include_optional=True) == (None | int)
    assert get_first_generatable_primitive(int | str, include_optional=True) == int
    assert get_first_generatable_primitive((str | None) | int, include_optional=True) == str | None
    assert get_first_generatable_primitive(Mapped[str | None], include_optional=True) == str | None
    assert get_first_generatable_primitive(Mapped[CustomFlags | None], include_optional=True) == CustomFlags | None

    # With include_optional disabled
    assert get_first_generatable_primitive(CustomFlags | None, include_optional=False) == CustomFlags
    assert get_first_generatable_primitive(None | CustomFlags, include_optional=False) == CustomFlags
    assert get_first_generatable_primitive(int | None, include_optional=False) == int
    assert get_first_generatable_primitive(None | int, include_optional=False) == int
    assert get_first_generatable_primitive(int | str, include_optional=False) == int
    assert get_first_generatable_primitive((str | None) | int, include_optional=False) == str
    assert get_first_generatable_primitive(Mapped[str | None], include_optional=False) == str
    assert get_first_generatable_primitive(Mapped[CustomFlags | None], include_optional=False) == CustomFlags


@pytest.mark.parametrize(
    "t, expected",
    [
        (
            ReferenceDataclass,
            [
                PropertyGenerationDetails("myOptInt", Optional[int], int, True, True, None),
                PropertyGenerationDetails("myInt", int, int, True, False, None),
            ],
        ),
    ],
)
def test_enumerate_class_properties(t: type, expected: list[PropertyGenerationDetails]):
    """Tests the enumerate_class_properties outputs against known classes of different configuration"""

    iter = enumerate_class_properties(t)
    assert isinstance(iter, Generator)

    sorted_actual = list(sorted(iter, key=lambda n: n.name))
    assert_list_type(PropertyGenerationDetails, sorted_actual, count=len(expected))

    sorted_expected = list(sorted(expected, key=lambda n: n.name))
    if sys.version_info < (3, 11):
        # Forward string references don't dereference as nicely under older python version
        # so we have to hamstring the test for these
        for a, e in zip(sorted_actual, sorted_expected):
            if not e.is_primitive_type:
                e.declared_type = a.declared_type

    assert sorted_actual == sorted_expected
