# Assertical (assertical)

Assertical is a library for helping write (async) integration/unit tests for fastapi/postgres/other projects. It has been developed by the Battery Storage and Grid Integration Program (BSGIP) at the Australian National University (https://bsgip.com/) for use with a variety of our internal libraries/packages.

It's attempting to be lightweight and modular, if you're not using `pandas` then just don't import the pandas asserts.

Contributions/PR's are welcome

## Example Usage

### Generating Class Instances

Say you have an SQLAlchemy model (the below also supports dataclasses, pydantic models and any type that expose its properties/types at runtime) 
```
class Student(DeclarativeBase):
    student_id: Mapped[int] = mapped_column(INTEGER, primary_key=True)
    date_of_birth: Mapped[datetime] = mapped_column(DateTime)
    name_full: Mapped[str] = mapped_column(VARCHAR(128))
    name_preferred: Mapped[Optional[str]] = mapped_column(VARCHAR(128), nullable=True)
    height: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(7, 2), nullable=True)
    weight: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(7, 2), nullable=True)
```
Instead of writing the following boilerplate in your tests:

```
def test_my_insert():
    # Arrange
    s1 = Student(student_id=1, date_of_birth=datetime(2014, 1, 25), name_full="Bobby Tables", name_preferred="Bob", height=Decimal("185.5"), weight=Decimal("85.2"))
    s2 = Student(student_id=2, date_of_birth=datetime(2015, 9, 23), name_full="Carly Chairs", name_preferred="CC", height=Decimal("175.5"), weight=Decimal("65"))
    # Act ... 
```

It can be simplified to:

```
def test_my_insert():
    # Arrange
    s1 = generate_class_instance(Student, seed=1)
    s2 = generate_class_instance(Student, seed=2)
    # Act ... 
```

Which will generate two instances of Student with every property being set with appropriately typed values and unique values. Eg s1/s2 will be proper `Student` instances with values like:

| field | s1 | s2 |
| ----- | -- | -- |
| student_id | 5 (int) | 6 (int) |
| date_of_birth | '2010-01-02T00:00:01Z' (datetime) | '2010-01-03T00:00:02Z' (datetime) |
| name_full | '3-str' (str) | '4-str' (str) |
| name_preferred | '4-str' (Decimal) | '5-str' (Decimal) |
| height | 2 (Decimal) | 3 (Decimal) |
| weight | 6 (Decimal) | 7 (Decimal) |

Passing property name/values via kwargs is also supported :

`generate_class_instance(Student, seed=1, height=Decimal("12.34"))` will generate a `Student` instance similar to `s1` above but where `height` is `Decimal("12.34")`

You can also control the behaviour of `Optional` properties - by default they will populate with the full type but using `generate_class_instance(Student, optional_is_none=True)` will generate a `Student` instance where `height`, `weight` and `name_preferred` are `None`.

Finally, say we add the following "child" class `TestResult`:

```
class TestResult(DeclarativeBase):
    test_result_id = mapped_column(INTEGER, primary_key=True)
    student_id: Mapped[int] = mapped_column(INTEGER)
    class: Mapped[str] = mapped_column(VARCHAR(128))
    grade: Mapped[str] = mapped_column(VARCHAR(8))
```

And assuming `Student` has a property `all_results: Mapped[list[TestResult]]`. `generate_class_instance(Student)` will NOT supply a value for `all_results`. But by setting `generate_class_instance(Student, generate_relationships=True)` the generation will recurse into any generatable / list of generatable type instances.


### Mocking HTTP AsyncClient

`MockedAsyncClient` is a duck typed equivalent to `from httpx import AsyncClient` that can be useful fo injecting into classes that depend on a AsyncClient implementation. 

Example usage that injects a MockedAsyncClient that will always return a `HTTPStatus.NO_CONTENT` for all requests:
```
mock_async_client = MockedAsyncClient(Response(status_code=HTTPStatus.NO_CONTENT))
with mock.patch("my_package.my_module.AsyncClient") as mock_client:
    # test body here
    assert mock_client.call_count_by_method[HTTPMethod.GET] > 0
```
The constructor for `MockedAsyncClient` allows you to setup either constant or varying responses. Eg: by supplying a list of responses you can mock behaviour that changes over multiple requests. 

Eg: This instance will raise an Exception, then return a HTTP 500 then a HTTP 200
```
MockedAsyncClient([
    Exception("My mocked error that will be raised"),
    Response(status_code=HTTPStatus.NO_CONTENT),
    Response(status_code=HTTPStatus.OK),
])
```
Response behavior can also be also be specified per remote uri:

```
MockedAsyncClient({
    "http://first.example.com/": [
        Exception("My mocked error that will be raised"),
        Response(status_code=HTTPStatus.NO_CONTENT),
        Response(status_code=HTTPStatus.OK),
    ],
    "http://second.example.com/": Response(status_code=HTTPStatus.NO_CONTENT),
})
```

### Environment Management

If you have tests that depend on environment variables, the `assertical.fixtures.environment` module has utilities to aid in snapshotting/restoring the state of the operating system environment variables.

Eg: This `environment_snapshot` context manager will snapshot the environment allowing a test to freely modify it and then reset everything to before the test run
```
import os
from assertical.fixtures.environment import environment_snapshot

def test_my_custom_test():
    with environment_snapshot():
        os.environ["MY_ENV"] = new_value
        # Do test body
```

This can also be simplified by using a fixture:
```
@pytest.fixture
def preserved_environment():
    with environment_snapshot():
        yield

def test_my_custom_test_2(preserved_environment):
    os.environ["MY_ENV"] = new_value
    # Do test body
```

### Assertion utilities

#### Generator assertical.asserts.generator.*

This package isn't designed to be a collection of all possible asserts, other packages handle that. What is included are a few useful asserts around typing

`assertical.asserts.generator.assert_class_instance_equality()` will allow the comparison of two objects, property by property using a class/type definition as the source of compared properties. Using the above earlier `Student` example:

```
s1 = generate_class_instance(Student, seed=1)
s1_dup = generate_class_instance(Student, seed=1)
s2 = generate_class_instance(Student, seed=2)

# This will raise an assertion error saying that certain Student properties don't match
assert_class_instance_equality(Student, s1, s2)

# This will NOT raise an assertion as each property will be the same value/type
assert_class_instance_equality(Student, s1, s1_dup)


# This will compare on all Student properties EXCEPT 'student_id'
assert_class_instance_equality(Student, s1, s1_dup, ignored_properties=set(['student_id]))
```

#### Time assertical.asserts.time.* 

contains some utilities for comparing times in different forms (eg timestamps, datetimes etc)

For example, the following asserts that a timestamp or datetime is "roughly now"
```
dt1 = datetime(2023, 11, 10, 1, 2, 0)
ts2 = datetime(2023, 11, 10, 1, 2, 3).timestamp()  # 3 seconds difference
ts2 = datetime(2023, 11, 10, 1, 2, 3).timestamp()  # 3 seconds difference
assert_fuzzy_datetime_match(dt1, ts2, fuzziness_seconds=5)  # This will pass (difference is <5 seconds)
assert_fuzzy_datetime_match(dt1, ts2, fuzziness_seconds=2)  # This will raise (difference is >2 seconds)
```

#### Type collections assertical.asserts.type.*

`assertical.asserts.type` contains some utilities for asserting collections of types are properly formed. 

For example, the following asserts that an instance is a list type, that only contains Student elements and that there are 5 total items.
```
my_custom_list = []
assert_list_type(Student, my_custom_list, count=5)
```

#### Pandas assertical.asserts.pandas.*

Contains a number of simple assertions for a dataframe for ensuring certain columns/rows exist

## Installation (for use)

`pip install assertical[all]`

## Installation (for dev)

`pip install -e .[all]`

## Modular Components

| **module** | **requires** |
| ---------- | ------------ |
| `asserts/generator` | `None`+ |
| `asserts/pandas` | `assertical[pandas]` |
| `fake/generator` | `None`+ |
| `fake/sqlalchemy` | `assertical[postgres]` |
| `fixtures/fastapi` | `assertical[fastapi]` |
| `fixtures/postgres` | `assertical[postgres]` |

+ No requirements are mandatory but additional types will be supported if `assertical[pydantic]`, `assertical[postgres]`, `assertical[xml]` are installed

All other types just require just the base `pip install assertical`

## Editors


### vscode

The file `vscode/settings.json` is an example configuration for vscode. To use these setting copy this file to `.vscode/settings,json`

The main features of this settings file are:
    - Enabling flake8 and disabling pylint
    - Autoformat on save (using the black and isort formatters)

Settings that you may want to change:
- Set the python path to your python in your venv with `python.defaultInterpreterPath`.
- Enable mypy by setting `python.linting.mypyEnabled` to true in settings.json.


