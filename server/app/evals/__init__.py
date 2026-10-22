"""Offline evaluation harness for the BRD pipeline.

Everything in this package takes plain dicts and dataclasses and returns
plain dicts: no database session, no network, no FastAPI. That is what
lets the metrics be unit-tested without fixtures from the app, and it is
what makes them safe to call from a request path — a scoring bug must
never be able to break a user's generation.

Phase 0 ships the metrics only. The generation hook, the benchmark
runner, the reports and the dev-only routes build on top of them.
"""
