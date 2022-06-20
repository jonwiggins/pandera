"""Check backend for pandas."""

from functools import partial
from typing import Any, Dict, List, Optional, Union

import pandas as pd
from multimethod import multimethod

from pandera.core.base.checks import BaseCheck, CheckResult
from pandera.backends.base import BaseCheckBackend


GroupbyObject = Union[
    pd.core.groupby.SeriesGroupBy, pd.core.groupby.DataFrameGroupBy
]


class PandasCheckBackend(BaseCheckBackend):

    def __init__(self, check: BaseCheck):
        self.check: BaseCheck = check
        self.check_fn = partial(check._check_fn, **check._check_kwargs)

    def groupby(self, check_obj: pd.DataFrame):
        """Implements groupby behavior for check object."""
        if isinstance(self.check.groupby, str):
            return check_obj.groupby(self.check.groupby)
        return self.check.groupby(check_obj)

    def query(self, check_obj):
        """Implements querying behavior to produce subset of check object."""
        # TODO
        ...

    def aggregate(self, check_obj):
        """Implements aggregation behavior for check object."""
        # TODO
        ...

    @staticmethod
    def _format_groupby_input(
        groupby_obj: GroupbyObject,
        groups: Optional[List[str]],
    ) -> Dict[str, Union[pd.Series, pd.DataFrame]]:
        """Format groupby object into dict of groups to Series or DataFrame.

        :param groupby_obj: a pandas groupby object.
        :param groups: only include these groups in the output.
        :returns: dictionary mapping group names to Series or DataFrame.
        """
        # TODO: this behavior should be deprecated such that the user deals with pandas
        # groupby objects instead of dicts.
        if groups is None:
            return dict(list(groupby_obj))
        group_keys = set(group_key for group_key, _ in groupby_obj)
        invalid_groups = [g for g in groups if g not in group_keys]
        if invalid_groups:
            raise KeyError(
                f"groups {invalid_groups} provided in `groups` argument not a valid group "
                f"key. Valid group keys: {group_keys}"
            )
        return {
            group_key: group
            for group_key, group in groupby_obj
            if group_key in groups
        }

    @multimethod
    def preprocess(self, check_obj: pd.Series, key: None) -> pd.Series:
        """Preprocesses a check object before applying the check function."""
        assert key is None
        # This handles the case of Series validation, which has no other context except
        # for the index to groupby on. Right now grouping by the index is not allowed.
        return check_obj

    @multimethod
    def preprocess(
        self,
        check_obj: pd.DataFrame,
        key: str,
    ) -> Union[pd.Series, Dict[str, pd.Series]]:
        check_obj = check_obj[key]
        if self.check.groupby is None:
            return check_obj
        return self._format_groupby_input(self.groupby(check_obj), self.groups)

    @multimethod
    def preprocess(
        self,
        check_obj: pd.DataFrame,
        key: None,
    ) -> Union[pd.DataFrame, Dict[str, pd.DataFrame]]:
        assert key is None
        if self.check.groupby is None:
            return check_obj
        return self._format_groupby_input(self.groupby(check_obj), self.groups)
    
    @multimethod
    def apply(self, check_obj: pd.Series):
        """Apply the check function to a check object."""
        if self.check.element_wise:
            return check_obj.map(self.check_fn)
        return self.check_fn(check_obj)

    @multimethod
    def apply(self, check_obj: pd.DataFrame):
        if self.check.element_wise:
            return check_obj.apply(self.check_fn, axis=1)
        return self.check_fn(check_obj)

    @multimethod
    def postprocess(self, check_obj: Any, check_output: bool) -> CheckResult:
        """Postprocesses the result of applying the check function."""
        return CheckResult(
            check_output=check_output,
            check_passed=check_output,
            checked_object=check_obj,
            failure_cases=None
        )

    def _get_series_failure_cases(self, check_obj, check_output: pd.Series) -> pd.Series:
        failure_cases = check_obj[~check_output]
        if not failure_cases.empty and self.check.n_failure_cases is not None:
            # NOTE: this is a hack to support pyspark.pandas and modin, since you
            # can't use groupby on a dataframe with another dataframe
            if type(failure_cases).__module__.startswith(("pyspark.pandas", "modin.pandas")):
                failure_cases = (
                    failure_cases.rename("failure_cases")
                    .to_frame()
                    .assign(check_output=check_output)
                    .groupby("check_output")
                    .head(self.check.n_failure_cases)["failure_cases"]
                )
            else:
                failure_cases = failure_cases.groupby(check_output).head(
                    self.check.n_failure_cases
                )
        return failure_cases

    @multimethod
    def postprocess(
        self,
        check_obj: pd.Series,
        check_output: pd.Series,
    ) -> CheckResult:
        """Postprocesses the result of applying the check function."""
        if self.check.ignore_na:
            check_output = check_output | check_obj.isna()
        return CheckResult(
            check_output,
            check_output.all(),
            check_obj,
            self._get_series_failure_cases(check_obj, check_output)
        )

    @multimethod
    def postprocess(
        self,
        check_obj: pd.DataFrame,
        check_output: pd.Series,
    ) -> CheckResult:
        """Postprocesses the result of applying the check function."""
        if self.check.ignore_na:
            check_output = check_output | check_obj.isna().any(axis="columns")
        return CheckResult(
            check_output,
            check_output.all(),
            check_obj,
            self._get_series_failure_cases(check_obj, check_output)
        )

    @multimethod
    def postprocess(
        self,
        check_obj: pd.DataFrame,
        check_output: pd.DataFrame,
    ) -> CheckResult:
        """Postprocesses the result of applying the check function."""
        assert check_obj.shape == check_output.shape
        check_obj = check_obj.unstack()
        check_output = check_output.unstack()
        if self.check.ignore_na:
            check_output = check_output | check_obj.isna()
        failure_cases = (
            check_obj[~check_output]
            .rename("failure_case")
            .rename_axis(["column", "index"])
            .reset_index()
        )
        if not failure_cases.empty and self.check.n_failure_cases is not None:
            failure_cases = failure_cases.drop_duplicates().head(self.check.n_failure_cases)
        return CheckResult(
            check_output,
            check_output.all(axis=None),
            check_obj,
            failure_cases,
        )

    @multimethod
    def postprocess(self, check_obj: Any, check_output: Any):
        """Postprocesses the result of applying the check function."""
        raise TypeError(
            f"output type of check_fn not recognized: {type(check_output)}"
        )

    def __call__(
        self,
        check_obj: Union[pd.Series, pd.DataFrame],
        key: Optional[str] = None,
    ) -> CheckResult:
        check_obj = self.preprocess(check_obj, key)
        check_output = self.apply(check_obj)
        return self.postprocess(check_obj, check_output)
