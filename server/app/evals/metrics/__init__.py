"""Evaluation metrics.

Each metric is a pure function over plain data. Each returns a dict and
never raises: the caller is a request path, and an evaluation failure
must degrade to "no score" rather than break a generation.
"""
