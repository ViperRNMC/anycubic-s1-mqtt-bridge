import base64
import unittest
from unittest.mock import Mock, patch

from obico import detect_image, printer_is_busy


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


if __name__ == "__main__":
    unittest.main()