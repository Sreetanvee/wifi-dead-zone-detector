# Wi-Fi Dead Zone Detector

A Windows Wi-Fi survey app that reads real RSSI from the laptop's currently connected Wi-Fi adapter, labels each measurement with a room name, and flags weak readings. The threshold is **-75 dBm** for this demo; at or below that value is flagged as weak. RSSI values are negative, and values closer to zero are stronger.

## What reads the Wi-Fi signal?

The web app runs in Docker, which isolates it from the Windows Wi-Fi adapter. `wifi_agent.py` is a small Windows-side sensor that uses the Windows WLAN API to read the connected adapter's RSSI and sends it to the web app every five seconds while a survey is active. The person enters the room label on the web page; Windows cannot tell whether the laptop is in a bedroom. The helper is launched in a minimized window by `Start-Demo.bat`, so there is no terminal interaction.

The sensor measures the network the laptop is connected to. It does not scan every nearby network or measure internet speed. Availability and precision depend on the wireless adapter and driver.

## Run the demo

Requirements: Windows, Python 3.10+, and Docker Desktop with its engine running.

Start Docker Desktop and wait until its engine is running. Double-click `Start-Demo.bat`. It builds and starts the web app, starts the Windows sensor helper in a minimized window, and opens the app in your browser.

Open http://localhost:5000 if the browser does not open automatically. Enter a room label in the web page and click **Start survey**. RSSI measurements appear automatically every five seconds. Click **Stop survey** before entering a different room label.

To start the web app manually instead of using the launcher, go to this folder in PowerShell and run:

```powershell
docker compose up --build -d
```

Stop the web app with `docker compose down`. Readings are held in memory and reset when the app container restarts. Use **Download CSV** to save the current survey.

## Docker and Jenkins

- `Dockerfile` packages the Flask web app and pinned Flask dependency as an image.
- `compose.yaml` runs the web app locally on port 5000, bound to this computer.
- `Jenkinsfile` checks out the GitHub repository, builds a Docker image, starts a temporary container, calls `/health`, and removes the test container.
- `wifi_agent.py` runs directly on Windows because a Linux Docker container cannot call the host's Windows WLAN API. The web page controls when it measures and supplies the room label.

For a public website, each visitor would need a local helper installed on their own device. A normal website cannot read raw Wi-Fi RSSI directly from visitors' laptops; a domain alone does not grant that access.

Jenkins is configured as a local Windows service. The pipeline's Docker executable location may need adjustment if Docker Desktop is installed in a different folder on another computer.

## GitHub

Project repository: https://github.com/Sreetanvee/wifi-dead-zone-detector
