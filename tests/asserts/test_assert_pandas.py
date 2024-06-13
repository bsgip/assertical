from typing import Any, Optional

import pandas as pd
import pytest

from assertical.asserts.pandas import assert_dataframe, assert_dataframe_contains

INDEXED_DF = pd.DataFrame(
    {"col_int": [1, 2, 3, 3], "col_str": ["a", "b", "c", "c"], "col_other": [111, 222, 333, 444]},
    index=pd.Index([11, 22, 33, 44], name="my_index"),
)
BASIC_DF = pd.DataFrame({"col_int": [1, 2, 3, 3], "col_str": ["a", "b", "c", "c"], "col_other": [111, 222, 333, 444]})
EMPTY_DF = pd.DataFrame({"col_int": [], "col_str": [], "col_other": []})


@pytest.mark.parametrize(
    "obj, assert_has_data, index, assert_pass",
    [
        (None, None, None, False),
        ({"not a df": 123}, None, None, False),
        ([(1, 2), (3, 4)], None, None, False),
        (EMPTY_DF, None, None, True),
        (EMPTY_DF, False, None, True),
        (EMPTY_DF, True, None, False),
        (BASIC_DF, None, None, True),
        (BASIC_DF, False, None, False),
        (BASIC_DF, True, None, True),
        (INDEXED_DF, None, None, True),
        (INDEXED_DF, False, None, False),
        (INDEXED_DF, True, None, True),
        (BASIC_DF, None, "my_index", False),
        (INDEXED_DF, None, "my_index", True),
        (INDEXED_DF, None, "my_index_DNE", False),
    ],
)
def test_assert_dataframe(obj: Any, assert_has_data: Optional[bool], index: Optional[list | str], assert_pass: bool):
    if assert_pass:
        assert_dataframe(obj, assert_has_data, index)
    else:
        with pytest.raises(AssertionError):
            assert_dataframe(obj, assert_has_data, index)


@pytest.mark.parametrize(
    "df, col_values, min_count, max_count, assert_pass",
    [
        (EMPTY_DF, {}, None, None, True),
        (EMPTY_DF, {}, 0, None, True),
        (EMPTY_DF, {}, 1, None, False),
        (EMPTY_DF, {}, 0, 1, True),
        (EMPTY_DF, {"col_int": 99}, 1, None, False),
        (EMPTY_DF, {"col_DNE": 99}, 1, None, False),
        (BASIC_DF, {"col_int": 3}, None, None, True),  # This will match two rows
        (BASIC_DF, {"col_int": 3}, 1, None, True),  # This will match two rows
        (BASIC_DF, {"col_int": 3}, 1, 2, True),  # This will match two rows
        (BASIC_DF, {"col_int": 3}, 2, 2, True),  # This will match two rows
        (BASIC_DF, {"col_int": 3}, None, 1, False),  # This will match two rows
        (BASIC_DF, {"col_int": 3, "col_other": 333}, 1, None, True),  # This will match one row
        (BASIC_DF, {"col_int": 3, "col_str": "c"}, 2, 2, True),  # This will match two rows
        (BASIC_DF, {"col_int": 3, "col_other": 333}, 2, 2, False),  # This will match one row
        (BASIC_DF, {"col_int": 3, "col_other": 111}, 1, None, False),  # This will match zero rows
        (BASIC_DF, {"col_int": 1}, 1, 1, True),  # This will match one row
        (BASIC_DF, {"col_str": "a"}, 1, 1, True),  # This will match one row
        (BASIC_DF, {"col_str": "c"}, 1, 1, False),  # This will match two rows
        (BASIC_DF, {"col_str": "c", "col_other": 444}, 1, 1, True),  # This will match one row
        (INDEXED_DF, {"col_str": "c", "col_other": 444}, 1, 1, True),  # This will match one row
    ],
)
def test_assert_dataframe_contains(
    df: pd.DataFrame, col_values: dict[str, Any], min_count: Optional[int], max_count: Optional[int], assert_pass: bool
):
    if assert_pass:
        assert_dataframe_contains(df, col_values, min_count, max_count)
    else:
        with pytest.raises(AssertionError):
            assert_dataframe_contains(df, col_values, min_count, max_count)
