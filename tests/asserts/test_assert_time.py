from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

import pytest

from assertical.asserts.time import (
    assert_datetime_equal,
    assert_fuzzy_datetime_match,
    assert_nowish,
)


@pytest.mark.parametrize(
    "lhs, rhs, fuzz_seconds, assert_pass",
    [
        (1, 2, 3, True),
        (1, 3, 1, False),
        (1718093580, 1718093594, 20, True),
        (1718093580, 1718093594, 10, False),
        (
            datetime(2023, 1, 2, 18, 15, 00),
            datetime(2023, 1, 2, 18, 15, 5),
            10,
            True,
        ),
        (
            datetime(2024, 6, 11, 18, 15, 00, tzinfo=ZoneInfo("Australia/Brisbane")),
            datetime(2024, 6, 11, 18, 15, 5, tzinfo=ZoneInfo("Australia/Brisbane")),
            10,
            True,
        ),
        (
            datetime(2024, 6, 11, 18, 15, 00, tzinfo=ZoneInfo("Australia/Brisbane")),
            1718093700.5,
            10,
            True,
        ),
        (
            datetime(2024, 6, 11, 18, 15, 00, tzinfo=ZoneInfo("Australia/Brisbane")),
            1718093800.5,
            10,
            False,
        ),
    ],
)
def test_assert_fuzzy_datetime_match(lhs: Any, rhs: Any, fuzz_seconds: int, assert_pass: bool):
    assert_fuzzy_datetime_match(rhs, rhs, fuzz_seconds)  # Should match with self
    assert_fuzzy_datetime_match(lhs, lhs, fuzz_seconds)  # Should match with self

    if assert_pass:
        assert_fuzzy_datetime_match(lhs, rhs, fuzz_seconds)
        assert_fuzzy_datetime_match(rhs, lhs, fuzz_seconds)
    else:
        with pytest.raises(AssertionError):
            assert_fuzzy_datetime_match(lhs, rhs, fuzz_seconds)
        with pytest.raises(AssertionError):
            assert_fuzzy_datetime_match(rhs, lhs, fuzz_seconds)


@pytest.mark.parametrize("tz", [None, timezone.utc, ZoneInfo("Australia/Brisbane")])
def test_assert_nowish(tz):
    now = datetime.now(tz=tz)

    assert_nowish(now)
    assert_nowish(now.timestamp())

    with pytest.raises(AssertionError):
        assert_nowish(now + timedelta(seconds=100))
    with pytest.raises(AssertionError):
        assert_nowish(now - timedelta(seconds=100))

    assert_nowish(now + timedelta(seconds=100), 200)
    assert_nowish(now - timedelta(seconds=100), 200)


@pytest.mark.parametrize(
    "lhs, rhs, assert_pass",
    [
        (1, 1, True),
        (1, 2, False),
        (1718093580, 1718093580.0, True),
        (1718093580, 1718093580.5, False),
        (
            datetime(2022, 1, 2, 18, 15, 0),
            datetime(2022, 1, 2, 18, 15, 0),
            True,
        ),
        (
            datetime(2022, 1, 2, 18, 16, 0),
            datetime(2022, 1, 2, 18, 15, 0),
            False,
        ),
        (
            datetime(2022, 1, 2, 18, 16, 0, tzinfo=timezone.utc),
            datetime(2022, 1, 2, 18, 16, 0, tzinfo=timezone.utc),
            True,
        ),
        (
            datetime(2022, 1, 2, 18, 16, 0, tzinfo=timezone.utc),
            1641147360,
            True,
        ),
        (
            datetime(2022, 1, 2, 18, 16, 0, tzinfo=timezone.utc),
            1641147361,
            False,
        ),
        (
            datetime(2022, 1, 2, 18, 16, 0, tzinfo=timezone.utc),
            1641147360.5,
            False,
        ),
    ],
)
def test_assert_datetime_equal(lhs: Any, rhs: Any, assert_pass: bool):

    if assert_pass:
        assert_datetime_equal(lhs, rhs)
        assert_datetime_equal(rhs, lhs)
    else:
        with pytest.raises(AssertionError):
            assert_datetime_equal(lhs, rhs)
        with pytest.raises(AssertionError):
            assert_datetime_equal(rhs, lhs)

    assert_datetime_equal(lhs, lhs)  # should match with itself
    assert_datetime_equal(rhs, rhs)  # should match with itself
