pipeline {
    agent any
    options { timestamps() }
    environment { DOCKER_CLI = 'C:\\Users\\sreet\\AppData\\Local\\Programs\\DockerDesktop\\resources\\bin\\docker.exe' }
    stages {
        stage('Checkout') {
            steps { checkout scm }
        }
        stage('Build Docker image') {
            steps { bat '"%DOCKER_CLI%" build -t wifi-dead-zone-detector:%BUILD_NUMBER% .' }
        }
        stage('Smoke test') {
            steps {
                bat '''
                "%DOCKER_CLI%" rm -f wifi-detector-ci 2>NUL || exit /b 0
                "%DOCKER_CLI%" run -d --name wifi-detector-ci -p 5001:5000 wifi-dead-zone-detector:%BUILD_NUMBER%
                powershell -NoProfile -Command "$ok=$false; for($i=0;$i -lt 20;$i++){try{$r=Invoke-RestMethod http://localhost:5001/health; if($r.status -eq 'ok'){$ok=$true;break}}catch{}; Start-Sleep -Seconds 1}; if(-not $ok){exit 1}"
                "%DOCKER_CLI%" rm -f wifi-detector-ci
                '''
            }
        }
    }
    post { always { bat '"%DOCKER_CLI%" rm -f wifi-detector-ci 2>NUL || exit /b 0' } }
}
