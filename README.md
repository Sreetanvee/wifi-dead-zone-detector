# Wi-Fi Dead Zone Detector (DevOps mini project)

A small web app for recording Wi-Fi RSSI measurements by location. Values at or below -75 dBm are marked as weak coverage. A reading is entered manually, so the application works without special Wi-Fi hardware permissions. It is a survey/logging demo, not an automatic radio scanner.

## Run locally

Requires Python 3.10+.

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Open http://localhost:5000. Add a location and RSSI measurement such as `-82` dBm. `/health` is the health endpoint; `/api/readings` returns JSON; the page exports CSV. Data is held in memory and resets when the process restarts.

## Run with Docker

Requires Docker Desktop (or Docker Engine) with Compose:

```powershell
docker compose up --build -d
docker compose ps
```

Open http://localhost:5000. Stop with `docker compose down`. The container uses a non-root user and a slim Python base image.

## Jenkins CI pipeline

1. Push this project to a Git repository (steps below).
2. Install/start Jenkins and ensure the Jenkins agent has Docker installed and can run `docker` commands. Docker access is a host/agent setup requirement.
3. In Jenkins, choose **New Item → Pipeline → Pipeline script from SCM**, select Git, enter the repository URL and credentials if private, and set **Script Path** to `Jenkinsfile`.
4. Save and select **Build Now**. Pipeline checks out code, builds an image tagged with the Jenkins build number, starts a temporary container, checks `/health`, then removes the container.

The Jenkinsfile is written for a Windows Jenkins agent using `bat` and PowerShell. On Linux agents change `bat` to `sh`, replace `%BUILD_NUMBER%` with `$BUILD_NUMBER`, and adjust the smoke-test commands.

## Git workflow

Run these from this project folder:

```powershell
git init
git add .
git commit -m "Build Wi-Fi dead zone detector"
git branch -M main
git remote add origin https://github.com/YOUR-USER/wifi-dead-zone-detector.git
git push -u origin main
```

Replace the remote URL with a repository you created. For later changes use `git add .`, `git commit -m "Describe change"`, and `git push`.

## Explain the DevOps parts in your viva

- **Git** versions source changes and records commits.
- **Jenkins** automates checkout, image build, and a health-check smoke test on each pipeline run.
- **Docker** packages the app and pinned Python dependency into a repeatable image.
- **Compose** provides a simple repeatable way to run the container.
- **CI flow:** commit/push → Jenkins checkout → Docker build → start container → call health endpoint → cleanup.
- **Monitoring hook:** `/health` is a basic liveness endpoint that a deployment or monitoring system can query.

For a stronger next step, persist readings in SQLite or add a deployment stage after successful CI. Avoid claiming real automatic Wi-Fi scanning: this version records signal measurements supplied by the user/device.
