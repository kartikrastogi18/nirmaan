"""Local dev entry point: `python run.py`.

For production, don't run this file directly -- use a real WSGI server
(gunicorn/waitress) pointed at wsgi:app, per the README. Flask's own dev
server prints its own "do not use in production" warning for a reason;
the old app ignored it and shipped with app.run() as the actual deployment.
"""
import os

from app import create_app

app = create_app(os.environ.get("FLASK_ENV", "development"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=app.config["DEBUG"])
