import base64
import unittest
from unittest.mock import Mock, patch

import requests

from obico import (
    build_api_url,
    check_api_health,
    detect_image,
    discover_obico_api_url,
    printer_is_busy,
    resolve_print_job_state,
    resolve_printer_state,
    should_press_pause_button,
)


class ObicoUrlTests(unittest.TestCase):
    def test_hostname_expands_to_fixed_http_endpoint(self):
        self.assertEqual(
            build_api_url("0d2ff00d-obico-ml"),
            "http://0d2ff00d-obico-ml:3333/detect/",
        )

    def test_full_url_remains_compatible(self):
        url = "http://10.0.0.150:3333/detect/"
        self.assertEqual(build_api_url(url), url)

    def test_blank_hostname_uses_localhost(self):
        self.assertEqual(build_api_url(""), "http://localhost:3333/detect/")

    @patch("obico.requests.get")
    def test_discovers_installed_obico_hostname(self, get):
        addons_response = Mock()
        addons_response.json.return_value = {
            "data": {"addons": [{"slug": "0d2ff00d_obico_ml", "name": "Obico ML"}]}
        }
        info_response = Mock()
        info_response.json.return_value = {
            "data": {"hostname": "0d2ff00d-obico-ml"}
        }
        get.side_effect = [addons_response, info_response]

        result = discover_obico_api_url("supervisor-token", "localhost")

        self.assertEqual(result, "http://0d2ff00d-obico-ml:3333/detect/")
        self.assertEqual(get.call_count, 2)
        self.assertEqual(
            get.call_args_list[0].kwargs["headers"],
            {"Authorization": "Bearer supervisor-token"},
        )

    @patch("obico.requests.get")
    def test_uses_fallback_when_obico_is_not_installed(self, get):
        response = Mock()
        response.json.return_value = {"data": {"addons": []}}
        get.return_value = response

        self.assertEqual(
            discover_obico_api_url("supervisor-token", "my-obico"),
            "http://my-obico:3333/detect/",
        )

    @patch("obico.requests.get")
    def test_uses_fallback_when_supervisor_token_is_unavailable(self, get):
        self.assertEqual(
            discover_obico_api_url("", "my-obico"),
            "http://my-obico:3333/detect/",
        )
        get.assert_not_called()


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

    def test_active_print_wins_over_transient_idle_or_unknown_info(self):
        self.assertEqual(resolve_printer_state("free", "printing", "busy"), "busy")
        self.assertEqual(resolve_printer_state("unknown", "printing", "busy"), "busy")

    def test_missing_info_state_preserves_last_known_state(self):
        self.assertEqual(resolve_printer_state(None, "unknown", "busy"), "busy")
        self.assertEqual(resolve_printer_state("", "unknown", "free"), "free")

    def test_explicit_free_is_used_when_no_print_is_active(self):
        self.assertEqual(resolve_printer_state("free", "unknown", "busy"), "free")

    def test_slice_parameter_done_does_not_finish_print(self):
        self.assertEqual(
            resolve_print_job_state("getSliceParam", "done", "printing"),
            "printing",
        )

    def test_pause_button_only_pressed_once_for_busy_printer_failure(self):
        self.assertTrue(should_press_pause_button(True, "busy", False))
        self.assertFalse(should_press_pause_button(True, "free", False))
        self.assertFalse(should_press_pause_button(True, "busy", True))
        self.assertFalse(should_press_pause_button(False, "busy", False))


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