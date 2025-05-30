import sys
from typing import Generator, Optional, Union

import pytest
from pydantic_xml import BaseXmlModel, element

from assertical.asserts.generator import assert_class_instance_equality
from assertical.asserts.type import assert_list_type
from assertical.fake.generator import (
    CollectionType,
    PropertyGenerationDetails,
    check_class_instance_equality,
    clone_class_instance,
    enumerate_class_properties,
    generate_class_instance,
    generate_value,
    get_first_generatable_primitive,
    get_generatable_class_base,
    is_generatable_type,
)


class BaseXmlModelWithNS(BaseXmlModel):
    model_config = {"arbitrary_types_allowed": True}

    def __init_subclass__(
        cls,
        *args,
        **kwargs,
    ):
        super().__init_subclass__(*args, **kwargs)
        cls.__xml_nsmap__ = {
            "": "urn:foo:bar",
        }


class IntExtension(int):
    pass


class FurtherIntExtension(IntExtension):
    pass


class StringExtension(str):
    pass


class ChildXmlClass(BaseXmlModelWithNS):
    childInt: IntExtension = element()
    childList: Optional[list[str]] = element()


class SiblingXmlClass(BaseXmlModelWithNS):
    siblingStr: StringExtension = element()


class XmlClass(BaseXmlModelWithNS):
    myInt: Optional[FurtherIntExtension] = element()
    myStr: StringExtension = element()
    myChildren: list[ChildXmlClass] = element()
    myOptionalChildren: Optional[list[ChildXmlClass]] = element()
    mySibling: SiblingXmlClass = element()
    myOptionalSibling: Optional[SiblingXmlClass] = element(default=None)


class FurtherXmlClass(XmlClass):
    myOtherInt: IntExtension = element()


class ForwardReferenceClass(BaseXmlModelWithNS):
    """Uses Forward References to define the relationships"""

    optional_list: Optional[list["ChildXmlClass"]] = element()
    optional_sibling: Optional["SiblingXmlClass"] = element()


def test_xml_types_cant_generate_value():
    with pytest.raises(Exception):
        generate_value(ChildXmlClass, 1)


def test_is_generatable_type_extension_type():
    """Do the XML extension types register as the underlying ints"""
    assert is_generatable_type(IntExtension)
    assert is_generatable_type(FurtherIntExtension)
    assert is_generatable_type(StringExtension)
    assert is_generatable_type(Optional[FurtherIntExtension])


def test_get_generatable_class_base():
    assert get_generatable_class_base(XmlClass) == BaseXmlModel
    assert get_generatable_class_base(FurtherXmlClass) == BaseXmlModel
    assert get_generatable_class_base(ChildXmlClass) == BaseXmlModel
    assert get_generatable_class_base(Optional[ChildXmlClass]) == BaseXmlModel
    assert get_generatable_class_base(Optional[FurtherXmlClass]) == BaseXmlModel

    assert get_generatable_class_base(str) is None
    assert get_generatable_class_base(FurtherIntExtension) is None
    assert get_generatable_class_base(Optional[str]) is None
    assert get_generatable_class_base(Optional[FurtherIntExtension]) is None


def test_get_first_generatable_primitive_xml_extension_types():
    """Tests the XML extension types behave correctly"""

    # With include_optional enabled
    assert get_first_generatable_primitive(int, include_optional=True) == int
    assert get_first_generatable_primitive(str, include_optional=True) == str
    assert get_first_generatable_primitive(IntExtension, include_optional=True) == int
    assert get_first_generatable_primitive(FurtherIntExtension, include_optional=True) == int
    assert get_first_generatable_primitive(StringExtension, include_optional=True) == str
    assert (
        get_first_generatable_primitive(Optional[Union[StringExtension, int]], include_optional=True) == Optional[str]
    )

    # With include_optional disabled
    assert get_first_generatable_primitive(IntExtension, include_optional=False) == int
    assert get_first_generatable_primitive(FurtherIntExtension, include_optional=False) == int
    assert get_first_generatable_primitive(StringExtension, include_optional=False) == str
    assert get_first_generatable_primitive(Optional[FurtherIntExtension], include_optional=False) == int


def test_generate_xml_basic_values():
    p1 = generate_class_instance(FurtherXmlClass)

    assert p1.myInt is not None
    assert p1.myOtherInt is not None
    assert p1.myStr is not None
    assert p1.myChildren is not None and len(p1.myChildren) == 0, "generate_relationships is False"
    assert p1.mySibling is None, "generate_relationships is False so this should not populate"
    assert p1.myInt != p1.myOtherInt, "Checking that fields of the same type get unique values"

    # create a new instance with a different seed
    p2 = generate_class_instance(FurtherXmlClass, seed=123)

    assert p2.myInt is not None
    assert p2.myOtherInt is not None
    assert p2.myStr is not None
    assert p2.myChildren is not None and len(p1.myChildren) == 0, "generate_relationships is False"
    assert p2.mySibling is None, "generate_relationships is False so this should not populate"
    assert p2.myInt != p2.myOtherInt, "Checking that fields of the same type get unique values"

    assert p1.myInt != p2.myInt, "Checking that different seed numbers yields different results"
    assert p1.myOtherInt != p2.myOtherInt, "Checking that different seed numbers yields different results"
    assert p1.myStr != p2.myStr, "Checking that different seed numbers yields different results"

    p3 = generate_class_instance(FurtherXmlClass, seed=456, optional_is_none=True)
    assert p3.myInt is None, "This field is optional and optional_is_none=True"
    assert p3.myOtherInt is not None
    assert p3.myStr is not None
    assert p3.myChildren is not None and len(p1.myChildren) == 0, "generate_relationships is False"
    assert p3.mySibling is None, "generate_relationships is False so this should not populate"


def test_generate_xml_instance_relationships():
    p1 = generate_class_instance(FurtherXmlClass, generate_relationships=True, optional_is_none=False)
    assert p1.myChildren is not None and len(p1.myChildren) == 1 and isinstance(p1.myChildren[0], ChildXmlClass)
    assert p1.mySibling is not None and isinstance(p1.mySibling, SiblingXmlClass)
    assert p1.myOptionalSibling is not None and isinstance(p1.myOptionalSibling, SiblingXmlClass)
    assert p1.mySibling.siblingStr != p1.myOptionalSibling.siblingStr, "Different instances have different vals"

    p2 = generate_class_instance(FurtherXmlClass, seed=112, generate_relationships=True, optional_is_none=True)
    assert p2.myChildren is not None and len(p2.myChildren) == 1 and isinstance(p2.myChildren[0], ChildXmlClass)
    assert p2.mySibling is not None and isinstance(p2.mySibling, SiblingXmlClass)
    assert p2.myOptionalSibling is None

    assert p1.myChildren[0].childInt != p2.myChildren[0].childInt, "Differing seed values generate different results"
    assert p1.myChildren[0].childList != p2.myChildren[0].childList, "Differing seed values generate different results"
    assert p1.mySibling.siblingStr != p2.mySibling.siblingStr, "Differing seed values generate different results"


def test_clone_class_instance():
    """Check that cloned xml classes are properly shallow cloned"""
    original = generate_class_instance(XmlClass, generate_relationships=True)
    clone = clone_class_instance(original)

    assert clone
    assert clone is not original
    assert isinstance(clone, XmlClass)

    assert clone.myInt is original.myInt
    assert clone.myStr is original.myStr
    assert clone.mySibling is original.mySibling


def test_clone_class_instance_further():
    """Check that cloned xml classes are properly shallow cloned"""
    original = generate_class_instance(FurtherXmlClass, generate_relationships=True)
    clone = clone_class_instance(original)

    assert clone
    assert clone is not original
    assert isinstance(clone, FurtherXmlClass)

    assert clone.myInt is original.myInt
    assert clone.myStr is original.myStr
    assert clone.myChildren is original.myChildren
    assert clone.mySibling is original.mySibling
    assert clone.myOtherInt is original.myOtherInt


def test_assert_class_instance_equality():
    """test_check_class_instance_equality does the heavy lifting - this just ensures an assertion is raised"""
    assert_class_instance_equality(
        FurtherXmlClass,
        generate_class_instance(FurtherXmlClass, seed=1),
        generate_class_instance(FurtherXmlClass, seed=1),
    )

    with pytest.raises(Exception):
        assert_class_instance_equality(
            FurtherXmlClass,
            generate_class_instance(FurtherXmlClass, seed=1),
            generate_class_instance(FurtherXmlClass, seed=2),
        )


def test_check_class_instance_equality():

    # Check basic equality
    assert (
        check_class_instance_equality(
            FurtherXmlClass,
            generate_class_instance(FurtherXmlClass, seed=1, generate_relationships=True, optional_is_none=True),
            generate_class_instance(FurtherXmlClass, seed=1, generate_relationships=True, optional_is_none=True),
        )
        == []
    )

    # check a single property being out
    expected = generate_class_instance(FurtherXmlClass, seed=1, generate_relationships=False, optional_is_none=True)
    actual = generate_class_instance(FurtherXmlClass, seed=1, generate_relationships=False, optional_is_none=True)
    actual.myStr = actual.myStr + "-changed"
    assert (
        len(
            check_class_instance_equality(
                FurtherXmlClass,
                expected,
                actual,
            )
        )
        == 1
    )

    # check ignoring works ok
    assert len(check_class_instance_equality(FurtherXmlClass, expected, actual, ignored_properties=set(["myStr"]))) == 0


@pytest.mark.parametrize(
    "t, expected",
    [
        (SiblingXmlClass, [PropertyGenerationDetails("siblingStr", StringExtension, str, True, False, None)]),
        (
            XmlClass,
            [
                PropertyGenerationDetails("myInt", Optional[FurtherIntExtension], int, True, True, None),
                PropertyGenerationDetails("myStr", StringExtension, str, True, False, None),
                PropertyGenerationDetails(
                    "myChildren", list[ChildXmlClass], ChildXmlClass, False, False, CollectionType.REQUIRED_LIST
                ),
                PropertyGenerationDetails(
                    "myOptionalChildren",
                    Optional[list[ChildXmlClass]],
                    ChildXmlClass,
                    False,
                    False,
                    CollectionType.OPTIONAL_LIST,
                ),
                PropertyGenerationDetails("mySibling", SiblingXmlClass, SiblingXmlClass, False, False, None),
                PropertyGenerationDetails(
                    "myOptionalSibling", Optional[SiblingXmlClass], SiblingXmlClass, False, True, None
                ),
            ],
        ),
        (
            FurtherXmlClass,
            [
                PropertyGenerationDetails("myOtherInt", IntExtension, int, True, False, None),
                PropertyGenerationDetails("myInt", Optional[FurtherIntExtension], int, True, True, None),
                PropertyGenerationDetails("myStr", StringExtension, str, True, False, None),
                PropertyGenerationDetails(
                    "myChildren", list[ChildXmlClass], ChildXmlClass, False, False, CollectionType.REQUIRED_LIST
                ),
                PropertyGenerationDetails(
                    "myOptionalChildren",
                    Optional[list[ChildXmlClass]],
                    ChildXmlClass,
                    False,
                    False,
                    CollectionType.OPTIONAL_LIST,
                ),
                PropertyGenerationDetails("mySibling", SiblingXmlClass, SiblingXmlClass, False, False, None),
                PropertyGenerationDetails(
                    "myOptionalSibling", Optional[SiblingXmlClass], SiblingXmlClass, False, True, None
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


def test_forward_reference_class():
    all_set = generate_class_instance(ForwardReferenceClass, optional_is_none=False, generate_relationships=True)
    assert_list_type(ChildXmlClass, all_set.optional_list)
    assert isinstance(all_set.optional_sibling, SiblingXmlClass)

    none_set = generate_class_instance(ForwardReferenceClass, optional_is_none=True, generate_relationships=True)
    assert none_set.optional_list is None
    assert none_set.optional_sibling is None
