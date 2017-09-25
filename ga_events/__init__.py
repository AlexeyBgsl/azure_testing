"""
GA event tracker implementation
"""
import logging
from flask import Blueprint
import ga_events.event_tracker

GA_EVENTS_ROOT = '/ga_events'

ga_events_bp = Blueprint('gaeventsbp', __name__)
ga_tracker = ga_events.event_tracker.EventTracker()

def create_ga_tracker(app):
    logging.info("Creating GA event tracker")

    # Register the GA events blueprint.
    app.register_blueprint(ga_events_bp, url_prefix=GA_EVENTS_ROOT)

    logging.info("Done")
    return app

@ga_events_bp.route('/')
def TrackerTestHandler():
    print("Sending GA tracker event!")
    ga_tracker.track_event('UA-102279423-4', 1, 1)
    return "GA tracker event reported"
