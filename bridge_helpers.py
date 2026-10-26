import requests


SUPERVISOR_API_URL = "http://supervisor"
PRINT_SPEED_MODE_NAMES = {
    1: "Silent",
    2: "Standard",
    3: "Sport",
}


def print_speed_mode_name(value):
    try:
        mode = int(value)
    except (TypeError, ValueError):
        return "Unknown"
    return PRINT_SPEED_MODE_NAMES.get(mode, f"Unknown ({mode})")


def get_color_box_id(box_data, fallback_index):
    try:
        return int(box_data.get("id", fallback_index))
    except (AttributeError, TypeError, ValueError):
        return int(fallback_index)


def normalize_box_slot_index(slot_index, box_id, slots_per_box=4):
    try:
        index = int(slot_index)
        box = int(box_id)
    except (TypeError, ValueError):
        return None

    if 0 <= index < slots_per_box:
        return index

    local_index = index - (slots_per_box * box)
    if 0 <= local_index < slots_per_box:
        return local_index
    return None


def global_filament_index(box_id, local_slot_index, slots_per_box=4):
    return int(box_id) * slots_per_box + int(local_slot_index)


def discover_mqtt_settings(supervisor_token, fallback_settings, timeout=3):
    fallback = dict(fallback_settings)
    if not supervisor_token:
        return fallback, "SUPERVISOR_TOKEN unavailable; using configured MQTT settings"

    try:
        response = requests.get(
            f"{SUPERVISOR_API_URL}/services/mqtt",
            headers={"Authorization": f"Bearer {supervisor_token}"},
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
        service = payload.get("data", payload)
        host = service.get("host")
        port = service.get("port")
        if not host or port is None:
            return fallback, "Supervisor MQTT service has no host/port; using configured settings"

        settings = {
            "broker": str(host),
            "port": int(port),
            "user": service.get("username") or fallback.get("user"),
            "password": service.get("password") or fallback.get("password"),
        }
        return settings, f"Supervisor MQTT service found at {settings['broker']}:{settings['port']}"
    except requests.HTTPError as err:
        status = err.response.status_code if err.response is not None else "unknown"
        return fallback, f"Supervisor MQTT lookup returned HTTP {status}; using configured settings"
    except requests.RequestException as err:
        return fallback, f"Supervisor MQTT lookup failed ({type(err).__name__}); using configured settings"
    except (ValueError, TypeError, AttributeError):
        return fallback, "Supervisor MQTT lookup returned invalid data; using configured settings"