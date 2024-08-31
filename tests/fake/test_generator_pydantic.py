from datetime import datetime
from itertools import product
from typing import Optional

import pytest
from pydantic import BaseModel

from assertical.asserts.type import assert_list_type
from assertical.fake.generator import generate_class_instance


class ChildType(BaseModel):

    child_id: int
    period_start: datetime
    duration_seconds: int


class ParentType(BaseModel):
    """Billing readings are a total across all phases for the period"""

    parent_id: int
    name: str
    long_name: Optional[str]
    duration_seconds: int
    children: list[ChildType]
    optional_children: Optional[list[ChildType]]


@pytest.mark.parametrize("optional_is_none, generate_relationships", product([True, False], [True, False]))
def test_generate_pydantic_parents(optional_is_none: bool, generate_relationships: bool):
    """Basic test - other tests should give more detail, this should catch a high level error"""
    p1 = generate_class_instance(
        ParentType, seed=1, optional_is_none=optional_is_none, generate_relationships=generate_relationships
    )
    p2 = generate_class_instance(
        ParentType, seed=2, optional_is_none=optional_is_none, generate_relationships=generate_relationships
    )
    assert isinstance(p1, ParentType)
    assert isinstance(p2, ParentType)

    assert p1.parent_id != p2.parent_id
    assert p1.name != p2.name

    if generate_relationships:
        assert_list_type(ChildType, p1.children, count=1)
    else:
        assert p1.children == []

    if not optional_is_none and generate_relationships:
        assert_list_type(ChildType, p1.optional_children, count=1)
    elif optional_is_none:
        assert p1.optional_children is None
    else:
        assert p1.optional_children == []
