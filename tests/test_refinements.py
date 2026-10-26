import unittest
from unittest.mock import Mock, patch

import requests

from bridge_helpers import (
    discover_mqtt_settings,
    global_filament_index,
    get_color_box_id,
    normalize_box_slot_index,
    print_speed_mode_name,
)


class PrintSpeedModeTests(unittest.TestCase):
    def test_maps_anycubic_speed_enum(self):
        self.assertEqual(print_speed_mode_name(1), "Silent")
        self.assertEqual(print_speed_mode_name(2), "Standard")
        self.assertEqual(print_speed_mode_name(3), "Sport")

    def test_unknown_mode_stays_explicit(self):
        self.assertEqual(print_speed_mode_name(7), "Unknown (7)")


class ColorBoxIdTests(unittest.TestCase):
    def test_uses_firmware_box_id(self):
        self.assertEqual(get_color_box_id({"id": 1}, 0), 1)

    def test_falls_back_to_payload_position(self):
        self.assertEqual(get_color_box_id({}, 1), 1)
        self.assertEqual(get_color_box_id({"id": None}, 1), 1)

    def test_maps_four_local_slots_into_global_filament_numbers(self):
        self.assertEqual(global_filament_index(0, 0), 0)
        self.assertEqual(global_filament_index(0, 3), 3)
        self.assertEqual(global_filament_index(1, 0), 4)
        self.assertEqual(global_filament_index(1, 3), 7)

    def test_normalizes_box_two_global_slot_indexes(self):
        self.assertEqual(normalize_box_slot_index(4, 1), 0)
        self.assertEqual(normalize_box_slot_index(7, 1), 3)


class MqttServiceTests(unittest.TestCase):
    def setUp(self):
        self.fallback = {
            "broker": "manual-host",
            "port": 1883,
            "user": "manual-user",
            "password": "manual-pass",
        }

    @patch("bridge_helpers.requests.get")
    def test_uses_supervisor_service_and_credentials(self, get):
        response = Mock()
        response.json.return_value = {
            "addon": "core_mosquitto",
            "host": "core-mosquitto",
            "port": 1883,
            "username": "addons",
            "password": "supervisor-pass",
        }
        get.return_value = response

        settings, message = discover_mqtt_settings("token", self.fallback)

        self.assertEqual(settings["broker"], "core-mosquitto")
        self.assertEqual(settings["port"], 1883)
        self.assertEqual(settings["user"], "addons")
        self.assertEqual(settings["password"], "supervisor-pass")
        self.assertIn("core-mosquitto:1883", message)
        self.assertEqual(
            get.call_args.kwargs["headers"],
            {"Authorization": "Bearer token"},
        )

    @patch("bridge_helpers.requests.get")
    def test_uses_fallback_if_supervisor_service_is_missing(self, get):
        get.side_effect = requests.HTTPError(response=Mock(status_code=404))

        settings, message = discover_mqtt_settings("token", self.fallback)

        self.assertEqual(settings, self.fallback)
        self.assertIn("HTTP 404", message)

    @patch("bridge_helpers.requests.get")
    def test_uses_fallback_if_supervisor_token_is_missing(self, get):
        settings, message = discover_mqtt_settings("", self.fallback)

        self.assertEqual(settings, self.fallback)
        self.assertIn("TOKEN unavailable", message)
        get.assert_not_called()


if __name__ == "__main__":
    unittest.main()