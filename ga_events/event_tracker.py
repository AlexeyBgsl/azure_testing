# Copyright 2017 Locano. All Rights Reserved.
import requests
class EventTracker:
    def __init__(self):
        pass
    def track_event(self, tracking_id, category, action, client_id='555', event_label=None, event_value=0, experiment_id=None, experiment_key=None):
        data = {
            'v': '1',                           # API Version.
            'tid': tracking_id,                 # Tracking ID / Property ID.
            'cid': client_id,                   # Client ID
            't': 'event',                       # Event hit type.
            'ec': category,                     # Event category.
            'ea': action,                       # Event action.
            'el': event_label,                  # Event label.
            'ev': event_value,                  # Event value, must be an integer
        }
        response = requests.post('http://www.google-analytics.com/collect', data=data)
        # If the request fails, this will raise a RequestException. Depending
        # on your application's needs, this may be a non-error and can be caught
        # by the caller.
        response.raise_for_status()
