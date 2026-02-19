import inspect
import sys
from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal
from enum import Enum
from typing import (
    Any,
    Callable,
    Generator,
    Optional,
    TypeVar,
    Union,
    cast,
    get_args,
    get_origin,
    get_type_hints,
)

try:
    from types import NoneType
except ImportError:
    NoneType = type(None)  # type: ignore


try:
    from types import UnionType
except ImportError:
    UnionType = type(None)  # type: ignore

try:
    from pydantic import BaseModel
except ImportError:
    BaseModel = None  # type: ignore

try:
    from pydantic_xml import BaseXmlModel
except ImportError:
    BaseXmlModel = None  # type: ignore

try:
    from sqlalchemy.orm import DeclarativeBase, DeclarativeBaseNoMeta, Mapped
except ImportError:
    DeclarativeBase = None  # type: ignore
    DeclarativeBaseNoMeta = None  # type: ignore
    Mapped = None  # type: ignore

from enum import IntEnum, auto


class CollectionType(IntEnum):
    """Describes a type of collection that can hold a type that can be generated"""

    REQUIRED_LIST = auto()  # For type T - represents list[T]
    OPTIONAL_LIST = auto()  # For type T - represents list[Optional[T]]
    REQUIRED_SET = auto()  # For type T - represents set[T]
    OPTIONAL_SET = auto()  # For type T - represents set[Optional[T]]


@dataclass
class PropertyGenerationDetails:
    """Details about a property on a class/type that can be generated"""

    name: str  # The property name

    # The raw type declared on property
    # If None, then there has been an error resolving the type for this property.
    declared_type: Optional[type]

    # The type to generate for this property. For basic properties this will match the type hint on the property
    # For list properties, it will be the element type
    # For optional properties, it will be the non optional part of the Optional Union eg Optional[str] -> str
    # If None, then there has been an error resolving the type for this property.
    type_to_generate: Optional[type]

    # If true, the property can be generate via PRIMITIVE_VALUE_GENERATORS
    # Only valid if type_to_generate is not None
    is_primitive_type: bool

    # If True, the type_to_generate supports "None" as a valid alternative
    # Only valid if type_to_generate is not None
    is_optional: bool

    # If non None, indicates that type_to_generate should be encapsulated by some form of collection when instantiated
    # For example, a list[int] would have type_to_generate as int and this property as REQUIRED_LIST
    collection_type: Optional[CollectionType]


@dataclass
class _PlaceholderDataclassBase:
    """Dataclass has no base class - instead we fall back to using this as a placeholder"""


AnyType = TypeVar("AnyType")


def safe_is_subclass(class_to_check: Optional[type], parent_class: type) -> bool:
    if class_to_check is None:
        return False
    try:
        return issubclass(class_to_check, parent_class)
    except TypeError:
        # This is working around some quirks with Python
        # eg - issubclass(list[int], ParentClass) will return False
        #      issubclass(typing.List[int], ParentClass) will raise a TypeError
        #      issubclass(Optional[int], ParentClass) will raise a TypeError
        return False


def get_enum_type(t: Optional[type], include_optional: bool) -> Optional[type]:
    """If t is an enum type (ignoring Optional/Passthrough types) - return the underlying
    subclass of Enum. Otherwise return None. include_optional = True will cause any Optional[] wrappers around the
    enum type to be returned - otherwise just the raw enum_type will be returned


    Eg get_enum_type(Mapped[Optional[MyIntEnum]], False) will return MyIntEum
    Eg get_enum_type(Mapped[Optional[MyIntEnum]], True) will return Optional[MyIntEum]
    Eg get_enum_type(MyIntEum, False) will return MyIntEum
    Eg get_enum_type(MyIntEum, True) will return MyIntEum
    Eg get_enum_type(Mapped[int], True) will return None
    """
    if t is None:
        return None

    if is_passthrough_type(t):
        t = remove_passthrough_type(t)

    # If t is Optional[MyEnum] or just MyEnum - inner_enum_type will be MyEnum in either case
    inner_enum_type: Optional[type] = t
    optional = False
    if is_optional_type(t):
        optional = True
        inner_enum_type = get_optional_type_argument(t)
        assert inner_enum_type is not None

    t_origin = get_origin(t)
    is_union = (t_origin == Union or t_origin == UnionType) and len([a for a in get_args(t) if a is not NoneType]) > 1
    if is_union:
        for union_arg in get_args(t):
            arg_enum = get_enum_type(union_arg, include_optional)
            if arg_enum is not None:
                if optional and include_optional:
                    return Optional[arg_enum]  # type: ignore
                else:
                    return arg_enum
    elif safe_is_subclass(inner_enum_type, Enum):
        if include_optional:
            return t
        else:
            return inner_enum_type

    return None


def generate_value(t: type, seed: int = 1, optional_is_none: bool = False) -> Any:
    """Generates a seeded value based on the specified type. Throws an exception if it's not matched

    Feel free to expand this to new types as they come about"""
    if optional_is_none and is_optional_type(t):
        return None

    primitive_type = get_first_generatable_primitive(t, include_optional=False)

    # Enums are treated as a unique generation case - these are picked from the set of all possible enum vals
    enum_t = get_enum_type(t, False)
    if enum_t is not None:
        enum_values = list(enum_t)  # type: ignore
        return enum_values[seed % len(enum_values)]

    if primitive_type not in PRIMITIVE_VALUE_GENERATORS:
        raise Exception(f"Unsupported type {t} for seed {seed}")

    return PRIMITIVE_VALUE_GENERATORS[primitive_type](seed)


def get_first_generatable_primitive(t: type, include_optional: bool) -> Optional[type]:
    """Given a primitive type - return that type. Given a generic type, walk any union arguments looking for a
    primitive type

    if the type is optional and include_optional is True - the Optional[type] will be returned, otherwise just the type
    argument will be returned

    Types that inherit directly from a primitive type will be returned as the base primitive type

    Otherwise return None"""

    # if we can generate the type out of the box - we're done
    if t in PRIMITIVE_VALUE_GENERATORS:
        return t

    # if type is an enum - we generate this differently
    enum_t = get_enum_type(t, include_optional)
    if enum_t is not None:
        return enum_t

    # Check if the type is an extension of a primitive type
    if hasattr(t, "__bases__"):  # we need this check as types like Optional don't have this property
        for base in inspect.getmro(t):
            if base in PRIMITIVE_VALUE_GENERATORS:
                return base

    # certain types will just pass through looking at the arguments
    # eg: Mapped[Optional[int]] is really just Optional[int] for this function's purposes
    if is_passthrough_type(t):
        return get_first_generatable_primitive(remove_passthrough_type(t), include_optional=include_optional)

    # If we have an Optional[type] (which resolves to Union[NoneType, type]) we need to be careful about how we
    # extract the type
    origin_type = get_origin(t)
    include_optional_type = include_optional and is_optional_type(t)
    if origin_type == Union or origin_type == UnionType:
        for union_arg in get_args(t):
            prim_type = get_first_generatable_primitive(union_arg, include_optional=False)
            if prim_type is not None:
                return Optional[prim_type] if include_optional_type else prim_type  # type: ignore

    return None


def is_passthrough_type(t: type) -> bool:
    """This is for catching types like Mapped[int] which mainly just decorate the generic type argument
    without providing any useful information for the purposes of simple reading/writing values"""
    return Mapped is not None and get_origin(t) == Mapped


def remove_passthrough_type(t: type) -> type:
    """Given a generic PassthroughType[t] (identified by is_passthrough_type) - return t"""
    while is_passthrough_type(t):
        t = get_args(t)[0]
    return t


def is_generatable_type(t: type) -> bool:
    """Returns true if the type is generatable using generate_value (essentially is it a primitive type)"""
    primitive_type = get_first_generatable_primitive(t, include_optional=False)
    if get_enum_type(primitive_type, False) is not None:
        return True  # Enums are a special case
    return primitive_type in PRIMITIVE_VALUE_GENERATORS


def get_generatable_class_base(t: type) -> Optional[type]:
    """Given a class - look to see if it inherits from a key CLASS_INSTANCE_GENERATORS and return that key
    otherwise return None"""
    target_type = remove_passthrough_type(t)

    # we don't consider the Optional[MyType] - only the MyType
    optional_arg = get_optional_type_argument(target_type)
    if optional_arg is not None:
        target_type = optional_arg

    if not inspect.isclass(target_type):
        return None

    for base_class in inspect.getmro(target_type):
        if base_class in CLASS_INSTANCE_GENERATORS:
            return base_class

    # check for dataclass
    for base_class in inspect.getmro(target_type):
        if is_dataclass(base_class):
            return _PlaceholderDataclassBase

    return None


def get_optional_type_argument(t: type) -> Optional[type]:
    """If t is Optional[MyType] - return MyType - otherwise return None.

    If None is returned then t is NOT an optional type"""
    target_type = remove_passthrough_type(t)
    target_type_origin = get_origin(target_type)
    if target_type_origin != Union and target_type_origin != UnionType:
        return None

    # is this an Optional union?
    type_args = get_args(target_type)
    if type(None) not in type_args:
        return None

    # get the first non None type
    return [arg for arg in type_args if arg is not NoneType][0]


def is_optional_type(t: type) -> bool:
    """Returns true if t is an Optional type"""
    return get_optional_type_argument(t) is not None


def is_member_public(member_name: str) -> bool:
    """Simple heuristic to test if a member is public (True) or private/internal (False)"""
    return len(member_name) > 0 and member_name[0] != "_"


def enumerate_class_properties(t: type) -> Generator[PropertyGenerationDetails, None, None]:  # noqa: C901
    """Iterates through type t's properties returning the PropertyGenerationDetails for each discovered property.

    Only "public" properties that don't exist on the BaseType will be returned

    Will return (name, type, ) noting that:
        name: Will be a str
        type_for_name: May be None if the type hint can't be resolved, will be a type otherwise"""

    # We can only generate class instances of classes that inherit from a known base
    t_generatable_base = get_generatable_class_base(t)
    if t_generatable_base is None:
        raise Exception(f"Type {t} does not inherit from one of {CLASS_INSTANCE_GENERATORS.keys()}")

    type_hints = get_type_hints(t)

    for member_name in CLASS_MEMBER_FETCHERS[t_generatable_base](t):

        # Skip members that are private OR that are public members of the base class
        if not is_member_public(member_name):
            continue
        if member_name in BASE_CLASS_PUBLIC_MEMBERS[t_generatable_base]:
            continue

        declared_type: Optional[type] = None
        type_to_generate: Optional[type] = None
        collection_type: Optional[CollectionType] = None
        is_optional: bool = False
        is_primitive: bool = False
        if member_name in type_hints:
            declared_type = cast(type, type_hints[member_name])
            member_type = remove_passthrough_type(declared_type)
            optional_arg_type = get_optional_type_argument(member_type)
            is_optional = optional_arg_type is not None

            # Now lets see if this is a collection type and rework our parsed variables as required
            if is_optional:
                if get_origin(optional_arg_type) == list:
                    collection_type = CollectionType.OPTIONAL_LIST
                elif get_origin(optional_arg_type) == set:
                    collection_type = CollectionType.OPTIONAL_SET
            else:
                if get_origin(member_type) == list:
                    collection_type = CollectionType.REQUIRED_LIST
                elif get_origin(member_type) == set:
                    collection_type = CollectionType.REQUIRED_SET

            if collection_type is not None:
                member_type = get_args(optional_arg_type)[0] if is_optional else get_args(member_type)[0]
                optional_arg_type = get_optional_type_argument(member_type)
                is_optional = optional_arg_type is not None

            # Work around for SQLAlchemy forward references - hopefully we don't need many of these special cases
            #
            # if we are passed a string name of a type (such as SQL Alchemy relationships are want to do)
            # eg - list["ChildType"] we need to be able to resolve that
            # Currently we're digging around in the guts of the Base registry - there maybe an official way to do this?
            if t_generatable_base == DeclarativeBase:
                if isinstance(member_type, str):
                    member_type = t.registry._class_registry[member_type]
            if t_generatable_base == DeclarativeBaseNoMeta:
                if isinstance(member_type, str):
                    member_type = t.registry._class_registry[member_type]

            if is_generatable_type(member_type):
                type_to_generate = get_first_generatable_primitive(member_type, include_optional=False)
                assert (
                    type_to_generate is not None
                ), f"Error generating member {member_name}. Couldn't find type for {member_type}"
                is_primitive = True
            elif get_generatable_class_base(member_type) is not None:
                type_to_generate = optional_arg_type if is_optional else member_type
            else:
                type_to_generate = None

        yield PropertyGenerationDetails(
            name=member_name,
            declared_type=declared_type,
            type_to_generate=type_to_generate,
            is_primitive_type=is_primitive,
            is_optional=is_optional,
            collection_type=collection_type,
        )


def generate_class_instance(  # noqa: C901
    t: type[AnyType],
    seed: int = 1,
    optional_is_none: bool = False,
    generate_relationships: bool = False,
    _visited_type_stack: Optional[list[type]] = None,
    **kwargs: Any,
) -> AnyType:
    """Given a child class of a key to CLASS_INSTANCE_GENERATORS - generate an instance of that class
    with all properties being assigned unique values based off of seed. The values will match type hints

    Any "private" members beginning with '_' will be skipped

    generate_relationships will recursively generate relationships generating instances as required. (SQL ALchemy
    will handle assigning backreferences too)

    If the type cannot be instantiated due to missing type hints / other info exceptions will be raised

    Any additional specified "kwargs" will override the generated members. Eg generate_class_instance(Foo, my_arg="123")
    will generate a new instance of Foo as per normal but the named member "my_arg" will have value "123". Please note
    that this will change the way remaining values are allocated such that:
        generate_class_instance(Foo, my_arg="123") != (generate_class_instance(Foo).my_arg = "123")
    Specifying an invalid member name will raise an Exception

    _visited_type_stack should not be specified - it's for internal use only"""
    t = remove_passthrough_type(t)

    # stop back references from infinite looping
    if _visited_type_stack is None:
        _visited_type_stack = []
    if t in _visited_type_stack:
        return None  # type: ignore # This only happens in recursion - the top level object will never be None
    _visited_type_stack.append(t)

    # We can only generate class instances of classes that inherit from a known base
    t_generatable_base = get_generatable_class_base(t)
    if t_generatable_base is None:
        raise Exception(f"Type {t} does not inherit from one of {CLASS_INSTANCE_GENERATORS.keys()}")

    # We will be creating a dict of property names and their generated values
    # Those values can be basic primitive values or optionally populated
    current_seed = seed
    values: dict[str, Any] = {}
    kwargs_references: set[str] = set()  # For making sure we use all kwargs values to catch typos

    for member in enumerate_class_properties(t):

        # If there is a custom override for a member - apply it before going any further
        if member.name in kwargs:
            values[member.name] = kwargs[member.name]
            kwargs_references.add(member.name)
            continue

        if member.type_to_generate is None:
            raise Exception(
                f"Type {t} has property {member.name} with type {member.declared_type} that cannot be generated"
            )

        generated_value: Any = None
        empty_collection: bool = False
        collection_type: Optional[CollectionType] = member.collection_type

        if optional_is_none and (
            member.collection_type == CollectionType.OPTIONAL_LIST
            or member.collection_type == CollectionType.OPTIONAL_SET
        ):
            # We can short circuit some generation if we know the top level collection should be None
            # In this case - we just set everything to None
            generated_value = None
            collection_type = None  # Don't fill with None - just set the member value to None
            current_seed += 1
        elif optional_is_none and member.is_optional:
            # In this case the parent collection is NOT able to be set to None but does support adding items
            # that are None - so we just add a None to the parent collection (or just generate None)
            generated_value = None
            current_seed += 1
        elif member.is_primitive_type:
            generated_value = generate_value(
                member.type_to_generate, seed=current_seed, optional_is_none=optional_is_none
            )
            current_seed += 1
        else:
            if generate_relationships:
                generated_value = generate_class_instance(
                    member.type_to_generate,
                    seed=current_seed,
                    optional_is_none=optional_is_none,
                    generate_relationships=generate_relationships,
                    _visited_type_stack=_visited_type_stack,
                )

                # None can be generated when Type A has child B that includes a backreference to A. in these
                # circumstances the visited_types short circuit will just return None from generate_class_instance
                # (to stop infinite recursion) The way we handle this is to just generate an empty list (if this is
                # a list entity)
                if generated_value is None:
                    empty_collection = True
                    # collection_type = CollectionType.REQUIRED_LIST
            else:
                # In this case we have a complex type but we aren't generating relationships - throw in a placeholder
                empty_collection = True
                generated_value = None
            current_seed += 1000  # Rather than calculating how many seed values were utilised - set it arbitrarily high

        if collection_type == CollectionType.REQUIRED_LIST or collection_type == CollectionType.OPTIONAL_LIST:
            values[member.name] = [] if empty_collection else [generated_value]
        elif collection_type == CollectionType.REQUIRED_SET or collection_type == CollectionType.OPTIONAL_SET:
            values[member.name] = set([]) if empty_collection else set([generated_value])
        else:
            values[member.name] = generated_value

    expected_kwargs_references = set(kwargs.keys())
    if kwargs_references != expected_kwargs_references:
        raise Exception(f"The following kwargs were unused {expected_kwargs_references.difference(kwargs_references)}")

    _visited_type_stack.pop()  # When we finish generating a type, allow recursion back into that type
    return CLASS_INSTANCE_GENERATORS[t_generatable_base](t, values)


def clone_class_instance(obj: AnyType, ignored_properties: Optional[set[str]] = None) -> AnyType:
    """Given an instance of a child class of a key to CLASS_INSTANCE_GENERATORS - generate a new instance of that class
    using references to the values in the current public properties in obj (i.e. a shallow clone).

    Any public properties belonging to the base class will be skipped (i.e only properties generated by
    generate_class_instance) will

    if ignored_properties is set - any property name in that set will be skipped (not copied)

    Any "private" members beginning with '_' will be skipped"""
    t = type(obj)

    # We can only generate class instances of classes that inherit from a known base
    t_generatable_base = get_generatable_class_base(t)
    if t_generatable_base is None:
        raise Exception(f"Obj {obj} with type {t} does not inherit from one of {CLASS_INSTANCE_GENERATORS.keys()}")

    # We will be creating a dict of property names and their generated values
    # Those values can be basic primitive values or optionally populated

    values: dict[str, Any] = {}
    for member in enumerate_class_properties(t):
        # Skip members that are private OR that are public members of the base class
        if ignored_properties and member.name in ignored_properties:
            continue

        values[member.name] = getattr(obj, member.name)

    return CLASS_INSTANCE_GENERATORS[t_generatable_base](t, values)


def check_class_instance_equality(
    t: type,
    expected: Any,
    actual: Any,
    ignored_properties: Optional[set[str]] = None,
) -> list[str]:
    """Given a type t and two instances. Run through the public members of t and assert that the values all match up.
    This will only compare properties whose type passes is_generatable_type.

    Any "private" members beginning with '_' will be skipped

    ignored properties are a set of property names that will NOT be asserted for equality

    returns a list of error messages (or an empty list if expected == actual)"""

    if expected is None and actual is None:
        return []

    if expected is None:
        return [f"expected is None but actual is {actual}"]

    if actual is None:
        return [f"actual is None but expected is {expected}"]

    t = remove_passthrough_type(t)

    # We can only generate class instances of classes that inherit from a known base
    t_generatable_base = get_generatable_class_base(t)
    if t_generatable_base is None:
        raise Exception(f"Type {t} does not inherit from one of {CLASS_INSTANCE_GENERATORS.keys()}")

    # We will be creating a dict of property names and their generated values
    # Those values can be basic primitive values or optionally populated
    error_messages = []
    for member in enumerate_class_properties(t):
        if ignored_properties and member.name in ignored_properties:
            continue

        if member.type_to_generate is None:
            raise Exception(f"Type {t} has property {member.name} that is missing a type hint")

        if not is_generatable_type(member.type_to_generate):
            continue

        expected_val = getattr(expected, member.name)
        actual_val = getattr(actual, member.name)

        if expected_val is None and actual_val is None:
            continue

        if expected_val != actual_val:
            error_messages.append(f"{member.name}: {member.declared_type} expected {expected_val} but got {actual_val}")

    return error_messages


# ---------------------------------------
#
# The below global values describe the main extension points for adding support for more types to generate
# With a bit of luck - adding more support should be as simple as adding extensions to these lookups
#
# ---------------------------------------

# The set of generators (seed: int) -> typed value (keyed by the type that they generate)
PRIMITIVE_VALUE_GENERATORS: dict[type, Callable[[int], Any]] = {}


def register_value_generator(t: type, generator: Callable[[int], Any]) -> None:
    """Registers a type as being a primitive value generator that will allow methods in this module to generate
    a 'unique' instance of type t based on a seed inte value.

    generator should return NEW values for each call such that:
    generator(1) == generator(1) and generator(1) is not generator(1).

    If planning to use this to extend the types supported - please also consider using
    assertical.fixures.generator.generator_snapshot to unload the extensions after a test to avoid
    polluting the global registry"""
    PRIMITIVE_VALUE_GENERATORS[t] = generator


register_value_generator(int, lambda seed: int(seed))
register_value_generator(str, lambda seed: f"{seed}-str")
register_value_generator(float, lambda seed: float(seed))
register_value_generator(bool, lambda seed: (seed % 2) == 0)
register_value_generator(Decimal, lambda seed: Decimal(seed))
register_value_generator(
    datetime, lambda seed: datetime(2010, 1, 1, tzinfo=timezone.utc) + timedelta(days=seed) + timedelta(seconds=seed)
)
register_value_generator(time, lambda seed: time(seed % 24, seed % 60, (seed + 1) % 60))
register_value_generator(timedelta, lambda seed: timedelta(seconds=seed))


# the set of all generators (target: type, kwargs: dict[str, Any) -> class instance (keyed by the base type of
# the generated type))
CLASS_INSTANCE_GENERATORS: dict[type, Callable[[type, dict[str, Any]], Any]] = {}
# the set of functions for accessing all members of a class (keyed by the base class for accessing those members)
CLASS_MEMBER_FETCHERS: dict[type, Callable[[type], list[str]]] = {}
# the set all base class public members keyed by the base class that generated them
BASE_CLASS_PUBLIC_MEMBERS: dict[type, set[str]] = {}
DEFAULT_CLASS_INSTANCE_GENERATOR: Callable[[type, dict[str, Any]], Any] = lambda target, kwargs: target(**kwargs)
DEFAULT_MEMBER_FETCHER: Callable[[type], list[str]] = lambda target: [name for (name, _) in inspect.getmembers(target)]


def register_base_type(
    base_type: type,
    instance_generator: Callable[[type, dict[str, Any]], Any],
    member_fetcher: Callable[[type], list[str]],
) -> None:
    """Registers a type that will allow all subclasses to be generated/cloned by functions in this module.

    instance_generator: Turn kwargs into a NEW instance of the specified target type. target type will always be a
                        subclass of base_type. DEFAULT_CLASS_INSTANCE_GENERATOR is a sensible default for most types
    member_fetcher: Should fetch a list of strings with each string value representing a property on the target type. If
                    this base_type is compatible with the inspect module, DEFAULT_MEMBER_FETCHER should work

    If planning to use this to extend the types supported - please also consider using
    assertical.fixures.generator.generator_snapshot to unload the extensions after a test to avoid
    polluting the global registry"""
    CLASS_INSTANCE_GENERATORS[base_type] = instance_generator
    CLASS_MEMBER_FETCHERS[base_type] = member_fetcher
    BASE_CLASS_PUBLIC_MEMBERS[base_type] = set([m for m in member_fetcher(base_type) if is_member_public(m)])


# Base type registration
register_base_type(
    _PlaceholderDataclassBase,
    DEFAULT_CLASS_INSTANCE_GENERATOR,
    lambda target: [f.name for f in fields(target) if f.init],
)

if "pydantic_xml" in sys.modules:
    register_base_type(
        BaseXmlModel,
        lambda target, kwargs: target.model_construct(**kwargs),  # type: ignore
        lambda target: list(target.model_fields.keys()),  # type: ignore
    )

if "pydantic" in sys.modules:
    register_base_type(
        BaseModel,
        lambda target, kwargs: target.model_construct(**kwargs),  # type: ignore
        lambda target: list(target.model_fields.keys()),  # type: ignore
    )

if "sqlalchemy" in sys.modules:
    register_base_type(DeclarativeBase, DEFAULT_CLASS_INSTANCE_GENERATOR, DEFAULT_MEMBER_FETCHER)
    register_base_type(DeclarativeBaseNoMeta, DEFAULT_CLASS_INSTANCE_GENERATOR, DEFAULT_MEMBER_FETCHER)

    # SQL Alchemy does some dynamic class construction that inspect.getmembers() can't pickup
    # This is our Workaround to ensure that the BASE_CLASS_PUBLIC_MEMBERS is properly populated
    for sql_alchemy_type in [DeclarativeBase, DeclarativeBaseNoMeta]:
        BASE_CLASS_PUBLIC_MEMBERS[sql_alchemy_type].update(["metadata", "registry"])
