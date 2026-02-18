from __future__ import annotations

import sys
from dataclasses import dataclass, field
from datetime import datetime, time
from typing import Generator, Optional

import pytest

from assertical.asserts.type import assert_list_type, assert_set_type
from assertical.fake.generator import (
    CollectionType,
    PropertyGenerationDetails,
    check_class_instance_equality,
    clone_class_instance,
    enumerate_class_properties,
    generate_class_instance,
)


@dataclass
class ParentDataclass:
    myOptInt: Optional[int]
    myInt: int
    myOtherInt: int
    myDate: datetime
    myStr: str
    myList: list[int]
    myTime: time


@dataclass(frozen=True)
class ReferenceDataclass:
    myOptInt: Optional[int]
    myInt: int


@dataclass
class OptionalCollectionsClass:
    """Lots of variations on lists and optional"""

    ints: list[int]
    optional_int_vals: list[Optional[int]]
    optional_int_list: Optional[list[int]]
    optional_optional_ints: Optional[list[Optional[int]]]
    refs: set[ReferenceDataclass]
    optional_refs_vals: set[Optional[ReferenceDataclass]]
    optional_refs_list: Optional[set[ReferenceDataclass]]
    optional_optional_refs: Optional[set[Optional[ReferenceDataclass]]]


@dataclass
class InitRestrictionsDataclass:
    myInt: int  # init = True by default
    myRestrictedInt1: int = field(default=1, init=False)  # set by default
    myRestrictedInt2: int = field(init=False)  # set by __post_init__

    def __post_init__(self):
        self.myRestrictedInt2 = 2


def test_clone_class_instance_dataclass():
    original = generate_class_instance(ReferenceDataclass, generate_relationships=True)
    clone = clone_class_instance(original)

    assert clone
    assert clone is not original
    assert isinstance(clone, ReferenceDataclass)

    assert clone.myInt is original.myInt
    assert clone.myOptInt is original.myOptInt


def test_check_class_instance_equality():

    # Check basic equality
    assert (
        check_class_instance_equality(
            ParentDataclass,
            generate_class_instance(ParentDataclass, seed=1, generate_relationships=True, optional_is_none=True),
            generate_class_instance(ParentDataclass, seed=1, generate_relationships=True, optional_is_none=True),
        )
        == []
    )

    assert (
        check_class_instance_equality(
            OptionalCollectionsClass,
            generate_class_instance(
                OptionalCollectionsClass, seed=5, generate_relationships=True, optional_is_none=False
            ),
            generate_class_instance(
                OptionalCollectionsClass, seed=5, generate_relationships=True, optional_is_none=False
            ),
        )
        == []
    )

    # check every property being mismatched
    assert (
        len(
            check_class_instance_equality(
                ParentDataclass,
                generate_class_instance(ParentDataclass, seed=1, generate_relationships=False, optional_is_none=True),
                generate_class_instance(ParentDataclass, seed=2, generate_relationships=True, optional_is_none=True),
            )
        )
        != 0
    )

    # check a single property being out
    expected = generate_class_instance(ParentDataclass, seed=1, generate_relationships=False, optional_is_none=True)
    actual = generate_class_instance(ParentDataclass, seed=1, generate_relationships=False, optional_is_none=True)
    actual.myStr = actual.myStr + "-changed"
    assert (
        len(
            check_class_instance_equality(
                ParentDataclass,
                expected,
                actual,
            )
        )
        == 1
    )

    # check ignoring works ok
    assert len(check_class_instance_equality(ParentDataclass, expected, actual, ignored_properties=set(["myStr"]))) == 0


def test_generate_dataclass_basic_values():
    p1 = generate_class_instance(ParentDataclass)

    assert p1.myInt is not None
    assert p1.myOptInt is not None
    assert p1.myOtherInt is not None
    assert p1.myStr is not None
    assert p1.myDate is not None
    assert p1.myList is not None
    assert p1.myTime is not None
    assert p1.myInt != p1.myOtherInt, "Checking that fields of the same type get unique values"

    # create a new instance with a different seed
    p2 = generate_class_instance(ParentDataclass, seed=123)

    assert p2.myInt is not None
    assert p2.myOptInt is not None
    assert p2.myOtherInt is not None
    assert p2.myStr is not None
    assert p2.myDate is not None
    assert p2.myList is not None
    assert p2.myTime is not None
    assert p2.myInt != p2.myOtherInt, "Checking that fields of the same type get unique values"

    assert p1.myInt != p2.myInt, "Checking that different seed numbers yields different results"
    assert p1.myOtherInt != p2.myOtherInt, "Checking that different seed numbers yields different results"
    assert p1.myStr != p2.myStr, "Checking that different seed numbers yields different results"
    assert p1.myList != p2.myList, "Checking that different seed numbers yields different results"
    assert p1.myTime != p2.myTime, "Checking that different seed numbers yields different results"

    p3 = generate_class_instance(ParentDataclass, seed=456, optional_is_none=True)
    assert p3.myOptInt is None, "This field is optional and optional_is_none=True"
    assert p3.myOtherInt is not None
    assert p3.myStr is not None
    assert p3.myList is not None
    assert p3.myTime is not None

    p4 = generate_class_instance(InitRestrictionsDataclass)
    assert p4.myInt is not None
    assert p4.myRestrictedInt1 == 1
    assert p4.myRestrictedInt2 == 2


def test_generate_kwargs():
    p1 = generate_class_instance(ParentDataclass, seed=101, myInt=8587231, myStr="My Custom Str")
    assert p1.myInt == 8587231
    assert p1.myOptInt is not None
    assert p1.myOtherInt is not None
    assert p1.myStr == "My Custom Str"
    assert p1.myDate is not None
    assert p1.myList is not None
    assert p1.myInt != p1.myOtherInt, "Checking that fields of the same type get unique values"

    p2 = generate_class_instance(ParentDataclass, seed=202, myInt=8587231, myStr="My Custom Str")
    assert p2.myInt == 8587231
    assert p2.myOptInt is not None
    assert p2.myOtherInt is not None
    assert p2.myStr == "My Custom Str"
    assert p2.myDate is not None
    assert p2.myList is not None
    assert p2.myInt != p2.myOtherInt, "Checking that fields of the same type get unique values"

    assert p1.myOptInt != p2.myOptInt, "p1 should differ from p2 (for fields not under kwargs)"
    assert p1.myOtherInt != p2.myOtherInt, "p1 should differ from p2 (for fields not under kwargs)"
    assert p1.myDate != p2.myDate, "p1 should differ from p2 (for fields not under kwargs)"
    assert p1.myList != p2.myList, "p1 should differ from p2 (for fields not under kwargs)"

    # Add a type on "myDate" that should raise an error
    with pytest.raises(Exception):
        generate_class_instance(
            ParentDataclass, seed=202, myInt=8587231, myStr="My Custom Str", myDates=datetime(2022, 11, 10)
        )


@pytest.mark.parametrize(
    "t, expected",
    [
        (
            OptionalCollectionsClass,
            [
                PropertyGenerationDetails("ints", list[int], int, True, False, CollectionType.REQUIRED_LIST),
                PropertyGenerationDetails(
                    "optional_int_vals", list[Optional[int]], int, True, True, CollectionType.REQUIRED_LIST
                ),
                PropertyGenerationDetails(
                    "optional_int_list", Optional[list[int]], int, True, False, CollectionType.OPTIONAL_LIST
                ),
                PropertyGenerationDetails(
                    "optional_optional_ints",
                    Optional[list[Optional[int]]],
                    int,
                    True,
                    True,
                    CollectionType.OPTIONAL_LIST,
                ),
                PropertyGenerationDetails(
                    "refs", set[ReferenceDataclass], ReferenceDataclass, False, False, CollectionType.REQUIRED_SET
                ),
                PropertyGenerationDetails(
                    "optional_refs_vals",
                    set[Optional[ReferenceDataclass]],
                    ReferenceDataclass,
                    False,
                    True,
                    CollectionType.REQUIRED_SET,
                ),
                PropertyGenerationDetails(
                    "optional_refs_list",
                    Optional[set[ReferenceDataclass]],
                    ReferenceDataclass,
                    False,
                    False,
                    CollectionType.OPTIONAL_SET,
                ),
                PropertyGenerationDetails(
                    "optional_optional_refs",
                    Optional[set[Optional[ReferenceDataclass]]],
                    ReferenceDataclass,
                    False,
                    True,
                    CollectionType.OPTIONAL_SET,
                ),
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


def test_generate_OptionalCollectionsClass_relationships():
    all_set = generate_class_instance(OptionalCollectionsClass, generate_relationships=True, optional_is_none=False)
    optional = generate_class_instance(OptionalCollectionsClass, generate_relationships=True, optional_is_none=True)

    assert_list_type(int, all_set.ints, count=1)
    assert_list_type(int, all_set.optional_int_list, count=1)
    assert_list_type(int, all_set.optional_int_vals, count=1)
    assert_list_type(int, all_set.optional_optional_ints, count=1)

    assert_list_type(int, optional.ints, count=1)
    assert len(optional.optional_int_vals) == 1 and optional.optional_int_vals[0] is None
    assert optional.optional_int_list is None
    assert optional.optional_optional_ints is None

    assert_set_type(ReferenceDataclass, all_set.refs, count=1)
    assert_set_type(ReferenceDataclass, all_set.optional_refs_list, count=1)
    assert_set_type(ReferenceDataclass, all_set.optional_refs_vals, count=1)
    assert_set_type(ReferenceDataclass, all_set.optional_optional_refs, count=1)

    assert_set_type(ReferenceDataclass, optional.refs, count=1)
    assert len(optional.optional_refs_vals) == 1 and list(optional.optional_refs_vals)[0] is None
    assert optional.optional_refs_list is None
    assert optional.optional_optional_refs is None
