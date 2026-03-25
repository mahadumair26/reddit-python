"""Custom middleware components."""

from fastapi import FastAPI


def register_middleware(app: FastAPI) -> None:
    """Hook for future middleware registration."""
    _ = app
