# Wi-Fi Dead Zone Detector

A Windows Wi-Fi survey app that reads real RSSI from the laptop's currently connected Wi-Fi adapter, labels each measurement with a room name, and flags weak readings. The threshold is **-75 dBm** for this demo; at or below that value is flagged as weak. RSSI values are negative, and values closer to zero are stronger.

## What reads the Wi-Fi signal?

The web app runs in Docker, which isolates it from the Windows Wi-Fi adapter. `wifi_agent.py` is a small Windows-side sensor that uses the Windows WLAN API to read the connected adapter's RSSI and sends it to the web app every five seconds. The room label is entered by the person running the agent; Windows cannot tell whether the laptop is in a bedroom.

The sensor measures the network the laptop is connected to. It does not scan every nearby network or measure internet speed. Availability and precision depend on the wireless adapter and driver.

## Run the demo

Requirements: Windows, Python 3.10+, and Docker Desktop with its engine running.

In PowerShell, go to this folder and start the web app:

```powershell
docker compose up --build -d
```

Open http://localhost:5000. In a **second** PowerShell window, open this same project folder and start the sensor:

```powershell
py wifi_agent.py
```

Enter a room label such as `Bedroom`. The sensor prints actual RSSI values every five seconds and the web page updates automatically. Walk to another room, stop the agent with Ctrl+C, run it again, and enter the new room label.

Stop the web app with `docker compose down`. Readings are held in memory and reset when the app container restarts. Use **Download CSV** to save the current survey.

## Docker and Jenkins

- `Dockerfile` packages the Flask web app and pinned Flask dependency as an image.
- `compose.yaml` runs the web app locally on port 5000, bound to this computer.
- `Jenkinsfile` checks out the GitHub repository, builds a Docker image, starts a temporary container, calls `/health`, and removes the test container.
- `wifi_agent.py` runs directly on Windows because a Linux Docker container cannot call the host's Windows WLAN API.

Jenkins is configured as a local Windows service. The pipeline's Docker executable location may need adjustment if Docker Desktop is installed in a different folder on another computer.

## GitHub

Project repository: https://github.com/Sreetanvee/wifi-dead-zone-detector
