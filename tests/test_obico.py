import base64
import unittest
from unittest.mock import Mock, patch

import requests

from obico import check_api_health, detect_image, printer_is_busy


class DetectImageTests(unittest.TestCase):
    @patch("obico.requests.post")
    def test_posts_image_and_threshold_and_returns_detections(self, post):
        response = Mock()
        response.json.return_value = {
            "detections": [["box", 0.8], ["box", 0.6]],
            "image_with_detections": base64.b64encode(b"annotated").decode("ascii"),
        }
        post.return_value = response

        result = detect_image(b"snapshot", "http://obico/detect/", 0.25)

        post.assert_called_once_with(
            "http://obico/detect/",
            json={"img": base64.b64encode(b"snapshot").decode("ascii"), "threshold": 0.25},
            timeout=30,
        )
        response.raise_for_status.assert_called_once_with()
        self.assertEqual(
            result,
            {
                "error_detected": True,
                "avg_confidence": 70.0,
                "image_with_errors": b"annotated",
            },
        )

    @patch("obico.requests.post")
    def test_empty_detections_return_zero_confidence(self, post):
        response = Mock()
        response.json.return_value = {"detections": []}
        post.return_value = response

        result = detect_image(b"snapshot", "http://obico/detect/", 0.2)

        self.assertEqual(
            result,
            {
                "error_detected": False,
                "avg_confidence": 0,
                "image_with_errors": None,
            },
        )

    def test_rejects_threshold_outside_api_range(self):
        with self.assertRaises(ValueError):
            detect_image(b"snapshot", "http://obico/detect/", 1.1)


class PrinterStateTests(unittest.TestCase):
    def test_only_busy_state_allows_obico_detection(self):
        self.assertTrue(printer_is_busy("busy"))
        self.assertFalse(printer_is_busy("free"))
        self.assertFalse(printer_is_busy("unknown"))


class ObicoHealthTests(unittest.TestCase):
    @patch("obico.requests.get")
    def test_health_check_uses_backend_health_route(self, get):
        response = Mock(status_code=200, text="ok\n")
        get.return_value = response

        self.assertTrue(check_api_health("http://localhost:3333/detect/"))
        get.assert_called_once_with("http://localhost:3333/hc/", timeout=3)

    @patch("obico.requests.get")
    def test_health_check_returns_false_when_backend_is_unavailable(self, get):
        get.side_effect = requests.ConnectionError("unavailable")

        self.assertFalse(check_api_health("http://localhost:3333/detect/"))

    def test_health_check_rejects_host_without_scheme(self):
        self.assertFalse(check_api_health("localhost"))


if __name__ == "__main__":
    unittest.main()