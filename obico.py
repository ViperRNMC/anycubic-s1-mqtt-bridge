import base64
from urllib.parse import urlsplit, urlunsplit

import requests


DEFAULT_OBICO_API_URL = "http://localhost:3333/detect/"
DEFAULT_OBICO_API_HOST = "localhost"
SUPERVISOR_API_URL = "http://supervisor"


def build_api_url(api_host):
    value = (api_host or "").strip()
    if not value:
        value = DEFAULT_OBICO_API_HOST

    if "://" in value:
        return value

    parsed_host = urlsplit(f"http://{value}")
    if not parsed_host.netloc:
        raise ValueError("Obico API hostname is invalid")

    netloc = parsed_host.netloc
    if parsed_host.port is None:
        netloc = f"{netloc}:3333"
    path = parsed_host.path.rstrip("/")
    if not path or path == "/":
        path = "/detect/"
    elif path != "/detect":
        raise ValueError("Use only the Obico API hostname")
    else:
        path = "/detect/"

    return urlunsplit(("http", netloc, path, "", ""))


def discover_obico_api_url(supervisor_token, fallback_host, timeout=3):
    fallback_url = build_api_url(fallback_host)
    if not supervisor_token:
        return fallback_url

    headers = {"Authorization": f"Bearer {supervisor_token}"}
    try:
        response = requests.get(
            f"{SUPERVISOR_API_URL}/addons", headers=headers, timeout=timeout
        )
        response.raise_for_status()
        addons = response.json().get("data", {}).get("addons", [])
        obico_addon = next(
            (
                addon
                for addon in addons
                if addon.get("name", "").strip().casefold() == "obico ml"
                or addon.get("slug", "").endswith("_obico_ml")
            ),
            None,
        )
        if obico_addon is None:
            return fallback_url

        slug = obico_addon.get("slug")
        if not slug:
            return fallback_url

        info_response = requests.get(
            f"{SUPERVISOR_API_URL}/addons/{slug}/info",
            headers=headers,
            timeout=timeout,
        )
        info_response.raise_for_status()
        hostname = info_response.json().get("data", {}).get("hostname")
        return build_api_url(hostname) if hostname else fallback_url
    except (requests.RequestException, ValueError, TypeError, AttributeError):
        return fallback_url


def printer_is_busy(printer_state):
    return isinstance(printer_state, str) and printer_state.strip().lower() == "busy"


def should_press_pause_button(error_detected, printer_state, pause_already_requested):
    return (
        error_detected
        and printer_is_busy(printer_state)
        and not pause_already_requested
    )


def check_api_health(api_url, timeout=3):
    try:
        parsed_url = urlsplit(api_url)
        if parsed_url.scheme not in ("http", "https") or not parsed_url.netloc:
            return False
        health_url = urlunsplit(
            (parsed_url.scheme, parsed_url.netloc, "/hc/", "", "")
        )
        response = requests.get(health_url, timeout=timeout)
        return response.status_code == 200 and response.text.strip().lower() == "ok"
    except (requests.RequestException, ValueError):
        return False


def detect_image(image_data, api_url, threshold, timeout=30):
    if not api_url:
        raise ValueError("Obico API URL is required")
    if not 0 <= threshold <= 1:
        raise ValueError("Obico threshold must be between 0 and 1")

    response = requests.post(
        api_url,
        json={
            "img": base64.b64encode(image_data).decode("ascii"),
            "threshold": threshold,
        },
        timeout=timeout,
    )
    response.raise_for_status()

    detection_data = response.json()
    detections = detection_data.get("detections", [])
    confidence_values = [float(detection[1]) for detection in detections]
    average_confidence = (
        round(sum(confidence_values) / len(confidence_values) * 100, 2)
        if confidence_values
        else 0
    )

    image_with_errors = detection_data.get("image_with_detections")
    if image_with_errors:
        image_with_errors = base64.b64decode(image_with_errors, validate=True)

    return {
        "error_detected": bool(detections),
        "avg_confidence": average_confidence,
        "image_with_errors": image_with_errors,
    }