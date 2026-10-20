# Anycubic S1 MQTT Bridge

This project provides a bridge between Anycubic Kobra S1 3D printers and Home Assistant using MQTT. It allows for monitoring and controlling the printer through Home Assistant, enabling features such as printer status updates, light control, print pause/resume/cancel, and video streaming.

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Docker Setup](#docker-setup)
- [Home Assistant Integration](#home-assistant-integration)
- [Contributing](#contributing)

## Installation

1. Clone the repository:

   ```
   git clone https://github.com/metheos/anycubic-s1-mqtt-bridge.git
   cd anycubic-s1-mqtt-bridge
   ```

2. Create a `.env` file based on the `.env.example` file and fill in the required environment variables.

3. Install the required Python packages:
   ```
   pip install -r requirements.txt
   ```

## Usage

To run the application, execute the following command:

```
python asm.py
```

Make sure your printer is connected and configured properly.

## Configuration

The application uses environment variables for configuration. You can set the following variables in your `.env` file:

- `ANYCUBIC_S1_IP`: Your S1 IP
- `HA_BROKER`: Your.HomeAssistant.MQTT.Address
- `HA_PORT`: 1883
- `HA_USER`: Your Home Assistant MQTT username.
- `HA_PASS`: Your Home Assistant MQTT password.
- `SNAPSHOT_INTERVAL_IDLE`: Interval for taking snapshots when printer is idle.
- `SNAPSHOT_INTERVAL_BUSY`: Interval for taking snapshots when printer is busy.
- `INFO_UPDATE_INTERVAL`: Interval for updating printer information.

### Obico ML (Home Assistant add-on)

Install and start the Obico ML API add-on from
[mattjacobson6/ha-addons](https://github.com/mattjacobson6/ha-addons) (the
`obico-ml-api` folder). In this bridge add-on's configuration, enable
**Obico ML**. Enter only the Obico add-on hostname (default `localhost`); the
bridge automatically adds `http://`, port `3333`, and `/detect/`. For example,
use `0d2ff00d-obico-ml` as the hostname in your setup. Complete API URLs are
still accepted. The bridge checks the API's `/hc/` health endpoint every 30
seconds and reports Obico entities unavailable when it cannot reach the
backend. This confirms API availability, not whether Supervisor reports the
add-on as installed.

Set the detection interval and threshold as needed. The threshold is between
`0` and `1` (default `0.2`). The bridge registers a communication switch,
failure binary sensor, confidence sensor, and detection image in Home Assistant
through MQTT discovery. Detection only runs while the printer state is `busy`.
When Obico detects a failure during `busy`, the bridge presses the existing
Pause Print button once for that failure.

## Docker Setup

To run the application using Docker, you can use the provided `Dockerfile` and `docker-compose.yml`.

1. Build the Docker image:

   ```
   docker-compose build
   ```

2. Start the application:
   ```
   docker-compose up
   ```

This will start the application in a Docker container, allowing for easy deployment and management.

## Home Assistant Integration

The repository includes an example Home Assistant view configuration that you can use to monitor your Anycubic S1 printer:

![Home Assistant View Example](HA_Example.PNG)

To use this view:

1. Copy the content from the [home_assistant_view_example.yaml](home_assistant_view_example.yaml) file
2. Paste it into the view yaml editor and click **Save**

This view uses elements from https://github.com/piitaya/lovelace-mushroom for the AMS spool visualization and badges.

The camera is manually configured in configuration.yaml as below

```
camera:
  - platform: ffmpeg
    name: "Anycubic S1 Printer Camera"
    input: "http://<Anycubic S1 IP>:18088/flv"
    extra_arguments: "-analyzeduration 1000000 -probesize 1000000 -fflags nobuffer -flags low_delay -strict experimental -fflags +genpts+discardcorrupt"
```

You may need to adjust entity IDs to match the ones created by your specific printer.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any improvements or bug fixes.
