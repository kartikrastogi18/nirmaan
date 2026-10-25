"""
Registers error handlers on the Flask app so *every* route gets a clean,
consistent JSON error response -- this is deliberately a centralized
safety net rather than a try/except copy-pasted into each route.

The old codebase had try/except in 2 of its 31 routes; the other 29 relied
on nobody sending malformed input. A per-route try/except is easy to forget
on route #30; a handler registered once on the app is not. Routes still use
their own try/except where they want a *specific*, actionable message (see
app/routes/auth.py's duplicate-phone handling) -- this module is what
catches everything else instead of leaking a raw traceback.

Flask matches handlers by exception-type specificity, not registration
order, so IntegrityError (the most specific, a subclass of Exception via
SQLAlchemyError) is tried before HTTPException, which is tried before the
bare Exception catch-all.
"""
import logging

from flask import jsonify
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import HTTPException, RequestEntityTooLarge

logger = logging.getLogger(__name__)


def register_error_handlers(app):
    @app.errorhandler(RequestEntityTooLarge)
    def handle_upload_too_large(_err):
        return jsonify(error="That upload is too large. Keep the total upload under 25 MB."), 413

    @app.errorhandler(IntegrityError)
    def handle_integrity_error(err):
        from app.extensions import db

        db.session.rollback()
        logger.warning("IntegrityError: %s", err)
        return (
            jsonify(error="That conflicts with existing data (duplicate or invalid reference)."),
            409,
        )

    @app.errorhandler(HTTPException)
    def handle_http_exception(err):
        # Preserves the real status/message for abort(404), Flask-JWT-
        # Extended's own aborts, etc. -- just guarantees it's JSON, not
        # Flask's default HTML error page.
        return jsonify(error=err.description), err.code

    @app.errorhandler(Exception)
    def handle_unexpected_error(err):
        from app.extensions import db

        db.session.rollback()
        logger.exception("Unhandled exception")
        return jsonify(error="Something went wrong on our end. Please try again."), 500
