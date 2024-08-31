import sys
from datetime import datetime
from enum import IntFlag, auto
from itertools import product
from typing import Generator, Optional

import pytest
from sqlalchemy import (
    BOOLEAN,
    FLOAT,
    INTEGER,
    VARCHAR,
    DateTime,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    DeclarativeBaseNoMeta,
    Mapped,
    mapped_column,
    relationship,
)

from assertical.asserts.generator import assert_class_instance_equality
from assertical.asserts.type import assert_list_type
from assertical.fake.generator import (
    CollectionType,
    PropertyGenerationDetails,
    check_class_instance_equality,
    clone_class_instance,
    enumerate_class_properties,
    generate_class_instance,
    get_generatable_class_base,
    is_optional_type,
    remove_passthrough_type,
)


class CustomFlags(IntFlag):
    """Various bit flags"""

    FLAG_1 = auto()
    FLAG_2 = auto()
    FLAG_3 = auto()
    FLAG_4 = auto()


class Base(DeclarativeBase):
    pass


class BaseNoMeta(DeclarativeBaseNoMeta):
    pass


class ParentClass(Base):
    """This is to stress test our data faking tools. It will never be installed in a database"""

    __tablename__ = "_parent"

    parent_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(VARCHAR(length=11), nullable=False)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    deleted: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    disabled: Mapped[bool] = mapped_column(BOOLEAN, nullable=False)
    total: Mapped[float] = mapped_column(FLOAT, nullable=False)
    children: Mapped[list["ChildClass"]] = relationship(back_populates="parent")

    UniqueConstraint("name", "created", name="name_created")


class ChildClass(Base):
    """This is to stress test our data faking tools. It will never be installed in a database"""

    __tablename__ = "_child"

    child_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    parent_id: Mapped[int] = mapped_column(ForeignKey("_parent.parent_id"))
    name: Mapped[str] = mapped_column(VARCHAR(length=11), nullable=False)
    long_name: Mapped[Optional[str]] = mapped_column(VARCHAR(length=32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    flags: Mapped[CustomFlags] = mapped_column(INTEGER, nullable=False)
    optional_flags: Mapped[Optional[CustomFlags]] = mapped_column(INTEGER, nullable=True)
    parent: Mapped["ParentClass"] = relationship(back_populates="children")


class ClassWithNoMeta(BaseNoMeta):
    """This is to stress test our data faking tools. It will never be installed in a database"""

    __tablename__ = "_nometa"

    my_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(VARCHAR(length=11), nullable=False)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    deleted: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    disabled: Mapped[bool] = mapped_column(BOOLEAN, nullable=False)
    total: Mapped[float] = mapped_column(FLOAT, nullable=False)

    UniqueConstraint("name", "created", name="name_created")


@pytest.mark.parametrize(
    "sub_type, base_type",
    [
        (ParentClass, DeclarativeBase),
        (ChildClass, DeclarativeBase),
    ],
)
def test_get_generatable_class_base(sub_type: type, base_type: type):
    assert get_generatable_class_base(sub_type) == base_type
    assert get_generatable_class_base(ChildClass) == DeclarativeBase


def test_is_optional_type():
    assert not is_optional_type(ParentClass)
    assert not is_optional_type(ChildClass)


def test_remove_passthrough_type():
    assert remove_passthrough_type(list[ParentClass]) == list[ParentClass]
    assert remove_passthrough_type(Mapped[list[ParentClass]]) == list[ParentClass]


def test_generate_sql_alchemy_instance_nometa_values():
    """Simple sanity check on some models to make sure the basic assumptions of generate_sql_alchemy_instance hold"""

    c1: ClassWithNoMeta = generate_class_instance(ClassWithNoMeta)

    # Ensure we create values
    assert c1.name is not None
    assert c1.my_id is not None
    assert c1.created is not None
    assert c1.deleted is not None
    assert c1.disabled is not None
    assert c1.total is not None

    assert c1.created != c1.deleted, "Checking that fields of the same type get unique values"


def test_generate_sql_alchemy_instance_basic_values():
    """Simple sanity check on some models to make sure the basic assumptions of generate_sql_alchemy_instance hold"""

    c1: ChildClass = generate_class_instance(ChildClass)

    # Ensure we create values
    assert c1.name is not None
    assert c1.long_name is not None
    assert c1.child_id is not None
    assert c1.parent_id is not None
    assert c1.created_at is not None
    assert c1.deleted_at is not None
    assert c1.flags is not None
    assert c1.optional_flags is not None
    assert c1.parent is None, "generate_relationships is False so this should not populate"

    assert c1.name != c1.long_name, "Checking that fields of the same type get unique values"
    assert c1.child_id != c1.parent_id, "Checking that fields of the same type get unique values"
    assert c1.created_at != c1.deleted_at, "Checking that fields of the same type get unique values"
    assert c1.flags != c1.optional_flags, "Checking that fields of the same type get unique values"

    # create a new instance with a different seed
    c2: ChildClass = generate_class_instance(ChildClass, seed=123)
    assert c2.name is not None
    assert c2.long_name is not None
    assert c2.child_id is not None
    assert c2.parent_id is not None
    assert c2.created_at is not None
    assert c2.deleted_at is not None
    assert c2.flags is not None
    assert c2.optional_flags is not None
    assert c2.parent is None, "generate_relationships is False so this should not populate"

    assert c2.name != c2.long_name, "Checking that fields of the same type get unique values"
    assert c2.child_id != c2.parent_id, "Checking that fields of the same type get unique values"
    assert c2.created_at != c2.deleted_at, "Checking that fields of the same type get unique values"
    assert c2.flags != c2.optional_flags, "Checking that fields of the same type get unique values"

    # validate that c1 != c2
    assert c1.name != c2.name, "Checking that different seed numbers yields different results"
    assert c1.long_name != c2.long_name, "Checking that different seed numbers yields different results"
    assert c1.child_id != c2.child_id, "Checking that different seed numbers yields different results"
    assert c1.parent_id != c2.parent_id, "Checking that different seed numbers yields different results"
    assert c1.created_at != c2.created_at, "Checking that different seed numbers yields different results"
    assert c1.deleted_at != c2.deleted_at, "Checking that different seed numbers yields different results"
    assert c1.flags != c2.flags, "Checking that different seed numbers yields different results"
    assert c1.optional_flags != c2.optional_flags, "Checking that different seed numbers yields different results"

    # check optional_is_none
    c3: ChildClass = generate_class_instance(ChildClass, seed=456, optional_is_none=True)
    assert c3.name is not None
    assert c3.long_name is None, "optional_is_none is True and this is optional"
    assert c3.child_id is not None
    assert c3.parent_id is not None
    assert c3.parent is None, "generate_relationships is False so this should not populate"
    assert c3.created_at is not None
    assert c3.deleted_at is None, "optional_is_none is True and this is optional"
    assert c3.flags is not None
    assert c3.optional_flags is None, "optional_is_none is True and this is optional"


def test_generate_sql_alchemy_instance_single_relationships():
    """Sanity check that relationships can be generated as demanded"""

    c1: ChildClass = generate_class_instance(ChildClass, generate_relationships=True)

    assert c1.parent is not None, "generate_relationships is True so this should be populated"
    assert isinstance(c1.parent, ParentClass)
    assert c1.parent.name is not None
    assert c1.parent.created is not None
    assert c1.parent.deleted is not None
    assert c1.parent.disabled is not None
    assert c1.parent.children is not None and len(c1.parent.children) == 1, "Backreference should self reference"
    assert c1.parent.children[0] == c1, "Backreference should self reference"
    assert c1.parent.created != c1.parent.deleted, "Checking that fields of the same type get unique values"
    assert c1.parent.deleted != c1.parent.disabled, "Checking that fields of the same type get unique values"

    c2: ChildClass = generate_class_instance(ChildClass, seed=2, generate_relationships=True)
    assert c2.parent.name is not None
    assert c2.parent.created is not None
    assert c2.parent.deleted is not None
    assert c2.parent.disabled is not None
    assert c2.parent.children is not None and len(c2.parent.children) == 1, "Backreference should self reference"
    assert c2.parent.children[0] == c2, "Backreference should self reference"
    assert c2.parent.created != c2.parent.deleted, "Checking that fields of the same type get unique values"
    assert c2.parent.deleted != c2.parent.disabled, "Checking that fields of the same type get unique values"
    assert c1.parent.created != c2.parent.created, "Checking that different seed numbers yields different results"
    assert c1.parent.deleted != c2.parent.deleted, "Checking that different seed numbers yields different results"


@pytest.mark.parametrize("optional_is_none", [True, False])
def test_generate_sql_alchemy_instance_multi_relationships(optional_is_none: bool):
    """Sanity check that relationships can be generated as demanded"""

    p1: ParentClass = generate_class_instance(
        ParentClass, generate_relationships=True, optional_is_none=optional_is_none
    )
    # generate_relationships is True so this should be populated
    assert_list_type(ChildClass, p1.children, count=1)

    assert p1.children[0].child_id is not None
    assert p1.children[0].name is not None
    assert p1.children[0].created_at is not None
    if optional_is_none:
        assert p1.children[0].long_name is None
        assert p1.children[0].deleted_at is None
    else:
        assert p1.children[0].long_name is not None
        assert p1.children[0].deleted_at is not None
    assert p1.children[0].parent is not None and p1.children[0].parent == p1, "Backreference should self reference"
    assert (
        p1.children[0].created_at != p1.children[0].deleted_at
    ), "Checking that fields of the same type get unique values"
    assert p1.children[0].long_name != p1.children[0].name, "Checking that fields of the same type get unique values"

    p2: ParentClass = generate_class_instance(
        ParentClass, seed=2, generate_relationships=True, optional_is_none=optional_is_none
    )
    assert_list_type(ChildClass, p2.children, count=1)
    assert p2.children[0].child_id is not None
    assert p2.children[0].name is not None
    assert p2.children[0].created_at is not None
    if optional_is_none:
        assert p2.children[0].long_name is None
        assert p2.children[0].deleted_at is None
    else:
        assert p2.children[0].long_name is not None
        assert p2.children[0].deleted_at is not None
    assert p2.children[0].parent is not None and p2.children[0].parent == p2, "Backreference should self reference"
    assert (
        p2.children[0].created_at != p2.children[0].deleted_at
    ), "Checking that fields of the same type get unique values"
    assert p2.children[0].long_name != p2.children[0].name, "Checking that fields of the same type get unique values"
    assert (
        p1.children[0].created_at != p2.children[0].created_at
    ), "Checking that different seed numbers yields different results"

    if not optional_is_none:
        assert (
            p1.children[0].deleted_at != p2.children[0].deleted_at
        ), "Checking that different seed numbers yields different results"


def test_clone_class_instance_sql_alchemy():
    """Check that cloned sql alchemy classes are properly shallow cloned"""
    original: ParentClass = generate_class_instance(ParentClass, generate_relationships=True)
    clone: ParentClass = clone_class_instance(original)

    assert clone
    assert clone is not original
    assert isinstance(clone, ParentClass)

    assert clone.parent_id is original.parent_id
    assert clone.name is original.name
    assert clone.created is original.created
    assert clone.deleted is original.deleted
    assert clone.disabled is original.disabled
    assert clone.total is original.total

    clone_with_ignores: ParentClass = clone_class_instance(original, ignored_properties=set(["created", "total"]))
    assert clone_with_ignores
    assert clone_with_ignores is not original
    assert isinstance(clone_with_ignores, ParentClass)

    assert clone_with_ignores.parent_id is original.parent_id
    assert clone_with_ignores.name is original.name
    assert clone_with_ignores.created is None, "This property is ignored"
    assert clone_with_ignores.deleted is original.deleted
    assert clone_with_ignores.disabled is original.disabled
    assert clone_with_ignores.total is None, "This property is ignored"


@pytest.mark.parametrize(
    "t, optional_is_none, generate_relationships",
    product([ParentClass, ChildClass, ClassWithNoMeta], [True, False], [True, False]),
)
def test_assert_class_instance_equality(t: type, optional_is_none: bool, generate_relationships: bool):
    """test_check_class_instance_equality does the heavy lifting - this just ensures an assertion is raised"""
    assert_class_instance_equality(
        t,
        generate_class_instance(
            t, seed=1, optional_is_none=optional_is_none, generate_relationships=generate_relationships
        ),
        generate_class_instance(
            t, seed=1, optional_is_none=optional_is_none, generate_relationships=generate_relationships
        ),
    )

    with pytest.raises(Exception):
        assert_class_instance_equality(
            ParentClass,
            generate_class_instance(
                ParentClass, seed=1, optional_is_none=optional_is_none, generate_relationships=generate_relationships
            ),
            generate_class_instance(
                ParentClass, seed=2, optional_is_none=optional_is_none, generate_relationships=generate_relationships
            ),
        )


def test_check_class_instance_equality():
    assert (
        check_class_instance_equality(
            ChildClass,
            generate_class_instance(ChildClass, seed=2, generate_relationships=False, optional_is_none=True),
            generate_class_instance(ChildClass, seed=2, generate_relationships=False, optional_is_none=True),
        )
        == []
    )

    assert (
        check_class_instance_equality(
            ChildClass,
            generate_class_instance(ChildClass, seed=3, generate_relationships=False, optional_is_none=False),
            generate_class_instance(ChildClass, seed=3, generate_relationships=False, optional_is_none=False),
        )
        == []
    )

    assert (
        check_class_instance_equality(
            ParentClass,
            generate_class_instance(ParentClass, seed=4, generate_relationships=True, optional_is_none=True),
            generate_class_instance(ParentClass, seed=4, generate_relationships=True, optional_is_none=True),
        )
        == []
    )

    # check every property being mismatched
    assert (
        len(
            check_class_instance_equality(
                ParentClass,
                generate_class_instance(ParentClass, seed=1, generate_relationships=False, optional_is_none=True),
                generate_class_instance(ParentClass, seed=2, generate_relationships=True, optional_is_none=True),
            )
        )
        != 0
    )

    # check a single property being out
    expected: ParentClass = generate_class_instance(
        ParentClass, seed=1, generate_relationships=False, optional_is_none=True
    )
    actual: ParentClass = generate_class_instance(
        ParentClass, seed=1, generate_relationships=False, optional_is_none=True
    )
    actual.name = actual.name + "-changed"
    assert (
        len(
            check_class_instance_equality(
                ParentClass,
                expected,
                actual,
            )
        )
        == 1
    )

    # check ignoring works ok
    assert len(check_class_instance_equality(ParentClass, expected, actual, ignored_properties=set(["name"]))) == 0


def test_generate_kwargs():
    custom_created = datetime(2022, 11, 1, 3, 4, 5)
    custom_deleted = datetime(2023, 12, 4, 5, 6, 7)
    c1: ChildClass = generate_class_instance(ChildClass, seed=101, created_at=custom_created, deleted_at=custom_deleted)
    assert c1.created_at == custom_created
    assert c1.deleted_at == custom_deleted
    assert c1.parent_id != c1.child_id, "Checking that fields of the same type get unique values"

    c2: ChildClass = generate_class_instance(ChildClass, seed=202, name="My Custom Str")
    assert c2.name == "My Custom Str"
    assert c2.parent_id != c2.child_id, "Checking that fields of the same type get unique values"

    assert c1.flags != c2.flags, "c1 should differ from c2 (for fields not under kwargs)"

    # invalid kwargs should raise
    with pytest.raises(Exception):
        generate_class_instance(ChildClass, seed=202, field_dne=8587231, name="My Custom Str")


@pytest.mark.parametrize(
    "t, expected",
    [
        (
            ParentClass,
            [
                PropertyGenerationDetails("parent_id", Mapped[int], int, True, False, None),
                PropertyGenerationDetails("name", Mapped[str], str, True, False, None),
                PropertyGenerationDetails("created", Mapped[datetime], datetime, True, False, None),
                PropertyGenerationDetails("deleted", Mapped[datetime], datetime, True, False, None),
                PropertyGenerationDetails("disabled", Mapped[bool], bool, True, False, None),
                PropertyGenerationDetails("total", Mapped[float], float, True, False, None),
                PropertyGenerationDetails(
                    "children", Mapped[list[ChildClass]], ChildClass, False, False, CollectionType.REQUIRED_LIST
                ),
            ],
        ),
        (
            ChildClass,
            [
                PropertyGenerationDetails("child_id", Mapped[int], int, True, False, None),
                PropertyGenerationDetails("parent_id", Mapped[int], int, True, False, None),
                PropertyGenerationDetails("name", Mapped[str], str, True, False, None),
                PropertyGenerationDetails("long_name", Mapped[Optional[str]], str, True, True, None),
                PropertyGenerationDetails("created_at", Mapped[datetime], datetime, True, False, None),
                PropertyGenerationDetails("deleted_at", Mapped[Optional[datetime]], datetime, True, True, None),
                PropertyGenerationDetails("flags", Mapped[CustomFlags], CustomFlags, True, False, None),
                PropertyGenerationDetails(
                    "optional_flags", Mapped[Optional[CustomFlags]], CustomFlags, True, True, None
                ),
                PropertyGenerationDetails("parent", Mapped[ParentClass], ParentClass, False, False, None),
            ],
        ),
        (
            ClassWithNoMeta,
            [
                PropertyGenerationDetails("my_id", Mapped[int], int, True, False, None),
                PropertyGenerationDetails("name", Mapped[str], str, True, False, None),
                PropertyGenerationDetails("created", Mapped[datetime], datetime, True, False, None),
                PropertyGenerationDetails("deleted", Mapped[datetime], datetime, True, False, None),
                PropertyGenerationDetails("disabled", Mapped[bool], bool, True, False, None),
                PropertyGenerationDetails("total", Mapped[float], float, True, False, None),
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
