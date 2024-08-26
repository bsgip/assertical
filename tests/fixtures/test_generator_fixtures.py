from dataclasses import dataclass

import pytest

from assertical.fake.generator import (
    DEFAULT_CLASS_INSTANCE_GENERATOR,
    DEFAULT_MEMBER_FETCHER,
    generate_class_instance,
    register_base_type,
    register_value_generator,
)
from assertical.fixtures.generator import generator_registry_snapshot


@dataclass
class MyDataClass:
    my_id: int


class MyBaseClass:
    pass


class MySimpleClass:
    diff_id: int = 1

    def __init__(self, diff_id: int) -> None:
        self.diff_id = diff_id


class MyGenerationClass(MyBaseClass):
    my_id: int = 1
    my_str: str = "a"
    my_simple_class: MySimpleClass = None

    def __init__(self, my_id: int, my_str: str, my_simple_class: MySimpleClass) -> None:
        super().__init__()

        self.my_id = my_id
        self.my_str = my_str
        self.my_simple_class = my_simple_class


def test_generator_registry_snapshot():

    with pytest.raises(Exception):
        generate_class_instance(MyGenerationClass)  # Initially this type won't work
    assert isinstance(generate_class_instance(MyDataClass), MyDataClass)  # but this type will as it's a dataclass

    with generator_registry_snapshot():
        # Nothing has changed yet
        with pytest.raises(Exception):
            generate_class_instance(MyGenerationClass)
        assert isinstance(generate_class_instance(MyDataClass), MyDataClass)

        # Now register the types and recheck
        register_value_generator(MySimpleClass, lambda seed: MySimpleClass(seed))
        register_base_type(MyBaseClass, DEFAULT_CLASS_INSTANCE_GENERATOR, DEFAULT_MEMBER_FETCHER)
        assert isinstance(generate_class_instance(MyDataClass), MyDataClass)  # Should continue to work
        assert isinstance(generate_class_instance(MyGenerationClass), MyGenerationClass)  # Should now work

    # Now we've exited the context-  the registrations should've been removed
    with pytest.raises(Exception):
        generate_class_instance(MyGenerationClass)  # Registration should've been unwound
    assert isinstance(generate_class_instance(MyDataClass), MyDataClass)  # This should continue to work
