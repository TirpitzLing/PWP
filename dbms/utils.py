"""
Utility functions for the DBMS API.
"""

from flask import request
from werkzeug.exceptions import BadRequest


def get_pagination_args(default_limit=10, default_offset=0):
    """
    Safely extract and validate 'limit' and 'offset' from query parameters.
    Raises a 400 BadRequest if the parameters are non-integers or negative.
    """
    raw_limit = request.args.get("limit")
    raw_offset = request.args.get("offset")

    try:
        limit = int(raw_limit) if raw_limit is not None else default_limit
        offset = int(raw_offset) if raw_offset is not None else default_offset
    except ValueError as exc:
        # "?limit=abc": 400
        raise BadRequest(
            description="Query parameters 'limit' and 'offset' must be valid integers."
        ) from exc

    if limit < 0 or offset < 0:
        # for negative params, avoiding 500
        raise BadRequest(
            description="Query parameters 'limit' and 'offset' cannot be negative."
        )

    return limit, offset
