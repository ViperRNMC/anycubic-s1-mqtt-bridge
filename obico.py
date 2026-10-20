import base64

import requests


def printer_is_busy(printer_state):
    return isinstance(printer_state, str) and printer_state.strip().lower() == "busy"


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