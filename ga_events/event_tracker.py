# Copyright 2017 Locano. All Rights Reserved.
import requests

EVENT_TRACKER_DST_FB = 1
EVENT_TRACKER_DST_AZ = 2
EVENT_TRACKER_DST_GA = 4

class EventTracker:
    def __init__(self, tracking_mode=EVENT_TRACKER_MODE_FB):
        self.TrackingMode = tracking_mode

    def __track_event_fb(self, tracking_id, category, action, client_id, event_label, event_value, experiment_id, experiment_key):
        pass

    def __track_event_az(self, tracking_id, category, action, client_id, event_label, event_value, experiment_id, experiment_key):
        pass

    def __track_event_ga(self, tracking_id, category, action, client_id, event_label, event_value, experiment_id, experiment_key):
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

    def track_event(self, tracking_id, category, action, client_id='555', event_label=None, event_value=0, experiment_id=None, experiment_key=None):
        if self.TrackingMode & EVENT_TRACKER_MODE_FB:
            self.__track_event_fb(tracking_id, category, action, client_id, event_label, event_value, experiment_id, experiment_key)
        if self.TrackingMode & EVENT_TRACKER_MODE_AZ:
            self.__track_event_az(tracking_id, category, action, client_id, event_label, event_value, experiment_id, experiment_key)
        if self.TrackingMode & EVENT_TRACKER_MODE_GA:
            self.__track_event_ga(tracking_id, category, action, client_id, event_label, event_value, experiment_id, experiment_key)
