pipeline {
    agent any
    stages {
        stage('Verify') {
            steps {
                sh 'python -m pip install --upgrade pip'
                sh 'python -m pip install -r requirements-dev.txt -c requirements-lock.txt'
                sh 'python scripts/check.py'
            }
        }
    }
}
