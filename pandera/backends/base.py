"""Base functions for Parsing, Validation, and Error Reporting Backends.

This class should implement a common interface of operations needed for
data validation. These operations are exposed as methods that are composed
together to implement the pandera schema specification.
"""

from abc import ABC
from functools import singledispatch
from typing import Optional, Sequence

import pandas as pd

from pandera.checks import Check
from pandera.dtypes import DataType


class BaseSchemaBackend(ABC):
    """Abstract base class for a schema backend implementation."""

    def preprocess(
        self,
        check_obj,
        name: str = None,
        inplace: bool = False,
    ):
        """Preprocesses a check object before applying check functions."""
        pass

    def subsample(
        self,
        check_obj,
        head: Optional[int] = None,
        tail: Optional[int] = None,
        sample: Optional[int] = None,
        random_state: Optional[int] = None,
    ):
        """Subsamples a check object before applying check functions."""
        pass

    def validate(
        self,
        check_obj,
        name: Optional[str] = None,
        head: Optional[int] = None,
        tail: Optional[int] = None,
        sample: Optional[int] = None,
        random_state: Optional[int] = None,
        lazy: bool = False,
        inplace: bool = False,
    ):
        """
        Parse and validate a check object, returning type-coerced and validated object.
        """
        pass

    def coerce_dtype(
        self,
        check_obj,
        *,
        schema = None,
        error_handler = None,
    ):
        """Coerce the data type of the check object."""
        pass

    def run_check(
        self,
        check_obj,
        schema,
        check,
        check_index: int,
        *args,
    ):
        """Run a single check on the check object."""
        pass

    def run_checks(
        self,
        check_obj,
        schema,
        checks: Sequence[Check],
        name: Optional[str] = None,
    ):
        """Run a list of checks on the check object."""
        pass

    def check_name(self, check_obj, name: Optional[str] = None):
        """Core check that checks the name of the check object."""
        pass

    def check_nullable(self, check_obj, nullable: bool = False):
        """Core check that checks the nullability of a check object."""
        pass

    def check_unique(self, check_obj, unique: bool = False):
        """Core check that checks the uniqueness of values in a check object."""
        pass

    def check_dtype(self, check_obj, dtype: DataType):
        """Core check that checks the data type of a check object."""
        pass


class BaseCheckBackend(ABC):
    """Abstract base class for a check backend implementation."""

    def query(self, check_obj, query_fn):
        """Implements querying behavior to produce subset of check object."""
        pass

    def groupby(self, check_obj, groupby_fn):
        """Implements groupby behavior for check object."""
        pass

    def aggregate(self, check_obj, agg_fn):
        """Implements aggregation behavior for check object."""
        pass

    def preprocess(self, check_obj, key):
        """Preprocesses a check object before applying the check function."""
        pass

    def postprocess(self, check_obj, key):
        """Postprocesses the result of applying the check function."""
        pass

    def __call__(self, check_obj):
        """Apply the check function to a check object."""
        pass

    def statistics(self):
        """Check statistics property."""
        pass

    def strategy(self):
        """Return a data generation strategy."""
        pass
