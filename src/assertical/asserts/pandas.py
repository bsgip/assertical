from typing import Any, Optional, Union

try:
    import pandas as pd
except ImportError:
    pd = None  # type: ignore


def assert_dataframe(
    df: Any, assert_has_data: Optional[bool] = None, index: Optional[Union[list[str], str]] = None
) -> None:
    """Asserts that an unknown object is a DataFrame and optionally whether it's empty or not

    assert_has_data: If None - no assertion, If True, assert df has >0 rows If False, assert df has 0 rows
    index: If set - asserts that the index on df is on the specified column names (as a list or single)
    """
    assert pd is not None, "Install assertical[pandas]"
    assert df is not None, "dataframe is None"
    assert type(df) == pd.DataFrame, f"df type is {type(df)} instead of {type(pd.DataFrame)}"  # noqa: E721

    if assert_has_data is True:
        assert len(df.index) != 0, "assert_has_data is True and the dataframe is empty"
    elif assert_has_data is False:
        assert len(df.index) == 0, "assert_has_data is False and the dataframe has data"

    if index is not None:
        if isinstance(index, str):
            index = [index]

        actual_index = None
        if hasattr(df.index, "name"):
            actual_index = [df.index.name]
        else:
            actual_index = df.index.names
        assert index == actual_index


def assert_dataframe_contains(
    df: Any, col_values: dict[str, Any], expected_min_count: Optional[int] = 1, expected_max_count: Optional[int] = None
) -> None:
    """Asserts that the dataframe contains at least 1 row with the specified column values (comparison on ==)

    Ranges of valid counts can be additionally asserted by setting expected_min_count and expected_max_count (None
    will mean unbounded)

    Other column values will NOT be considered"""
    assert pd is not None, "Install assertical[pandas]"

    def print_val(v: Any) -> str:
        if v is None:
            return "NONE"
        elif type(v) == str:  # noqa: E721
            return f"'{v}'"
        elif v < 0:
            return f"(0-{-v})"  # workaround https://github.com/pandas-dev/pandas/issues/16363
        else:
            return str(v)

    if len(col_values) == 0:
        query = "N/A"
        count = len(df.index)
    else:
        query = " & ".join([f"`{k}`=={print_val(v)}" for k, v in col_values.items()])
        try:
            count = len(df.query(query))
        except Exception:
            raise AssertionError(f"Column(s) don't exist. col_values: {col_values}")

    if expected_min_count is not None:
        assert (
            count >= expected_min_count
        ), f"Expected at least {expected_min_count} match(es) for {query}\n{df[list(col_values.keys())].to_string()}"

    if expected_max_count is not None:
        assert (
            count <= expected_max_count
        ), f"Expected at most {expected_max_count} match(es) for {query}\n{df[list(col_values.keys())].to_string()}"
