from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Generator

import pytest

from assertical.asserts.type import assert_list_type, assert_set_type
from assertical.fake.generator import (
    CollectionType,
    PropertyGenerationDetails,
    clone_class_instance,
    enumerate_class_properties,
    generate_class_instance,
)


@dataclass(frozen=True)
class ReferenceDataclass:
    myOptInt: int | None
    myInt: int


@dataclass
class OptionalCollectionsClass:
    """Lots of variations on lists and optional"""

    ints: list[int]
    optional_int_vals: list[int | None]
    optional_int_list: list[int] | None
    optional_optional_ints: list[int | None] | None
    refs: set[ReferenceDataclass]
    optional_refs_vals: set[ReferenceDataclass | None]
    optional_refs_list: set[ReferenceDataclass] | None
    optional_optional_refs: set[ReferenceDataclass | None] | None


def test_clone_class_instance_dataclass():
    original = generate_class_instance(ReferenceDataclass, generate_relationships=True)
    clone = clone_class_instance(original)

    assert clone
    assert clone is not original
    assert isinstance(clone, ReferenceDataclass)

    assert clone.myInt is original.myInt
    assert clone.myOptInt is original.myOptInt


@pytest.mark.parametrize(
    "t, expected",
    [
        (
            OptionalCollectionsClass,
            [
                PropertyGenerationDetails("ints", list[int], int, True, False, CollectionType.REQUIRED_LIST),
                PropertyGenerationDetails(
                    "optional_int_vals", list[int | None], int, True, True, CollectionType.REQUIRED_LIST
                ),
                PropertyGenerationDetails(
                    "optional_int_list", list[int] | None, int, True, False, CollectionType.OPTIONAL_LIST
                ),
                PropertyGenerationDetails(
                    "optional_optional_ints",
                    list[int | None] | None,
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
                    set[ReferenceDataclass | None],
                    ReferenceDataclass,
                    False,
                    True,
                    CollectionType.REQUIRED_SET,
                ),
                PropertyGenerationDetails(
                    "optional_refs_list",
                    set[ReferenceDataclass] | None,
                    ReferenceDataclass,
                    False,
                    False,
                    CollectionType.OPTIONAL_SET,
                ),
                PropertyGenerationDetails(
                    "optional_optional_refs",
                    set[ReferenceDataclass | None] | None,
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
