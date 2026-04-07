pipeline {
    agent any

    environment {
        IMAGE_NAME    = "docuquery-api"
        IMAGE_TAG     = "${env.BUILD_NUMBER}"
        NAMESPACE     = "docuquery-dev"
        HELM_CHART    = "./docuquery-api"
        KUBECONFIG    = "/var/jenkins_home/.kube/config"
    }

    stages {

        stage("Checkout") {
            steps {
                checkout scm
            }
        }

        stage("Run tests") {
            steps {
                sh """
                    python -m venv .venv
                    . .venv/bin/activate
                    pip install -r requirements.txt
                    pytest tests/ -v --tb=short
                """
            }
        }

        stage("Performance Test") {
            environment {
                APP_API_KEY = credentials("app-api-key")
            }
            steps {
                sh """
                    . .venv/bin/activate
                    pip install reportlab
                    python -c "
                    import os
                    from reportlab.lib.pagesizes import letter
                    from reportlab.pdfgen import canvas
                    os.makedirs('tests/locust', exist_ok=True)
                    c = canvas.Canvas('tests/locust/sample.pdf', pagesize=letter)
                    c.drawString(72, 720, 'This is a sample document for performance testing.')
                    c.drawString(72, 700, 'The main topic is document analysis and processing.')
                    c.save()
                    " 2>/dev/null || echo "{}" > tests/locust/sample.pdf
                    locust -f tests/locust/locustfile.py \
                      --host \${LOCUST_TARGET_HOST:-http://localhost:8000} \
                      --headless \
                      --users 50 \
                      --spawn-rate 5 \
                      --run-time 3m \
                      --html locust-report.html \
                      --csv locust-results \
                      --stop-timeout 30
                """
                archiveArtifacts artifacts: "locust-report.html,locust-results*.csv", allowEmptyArchive: true
            }
            post {
                always {
                    publishHTML(target: [
                        reportDir: ".",
                        reportFiles: "locust-report.html",
                        reportName: "Locust Performance Report"
                    ])
                }
            }
        }

        stage("Build Docker image") {
            steps {
                sh "docker build -t ${IMAGE_NAME}:${IMAGE_TAG} ."
                sh "docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${IMAGE_NAME}:latest"
            }
        }

        stage("Helm lint") {
            steps {
                sh "helm lint ${HELM_CHART} -f ${HELM_CHART}/values.yaml -f ${HELM_CHART}/values-dev.yaml"
            }
        }

        stage("Deploy to dev") {
            steps {
                withCredentials([
                    string(credentialsId: "gemini-api-key",  variable: "GEMINI_API_KEY"),
                    string(credentialsId: "app-api-key",     variable: "APP_API_KEY"),
                    string(credentialsId: "redis-password",  variable: "REDIS_PASSWORD"),
                    string(credentialsId: "mongo-password",  variable: "MONGO_PASSWORD")
                ]) {
                    sh """
                        helm upgrade --install ${IMAGE_NAME} ${HELM_CHART} \
                            -f ${HELM_CHART}/values.yaml \
                            -f ${HELM_CHART}/values-dev.yaml \
                            --namespace ${NAMESPACE} \
                            --set secrets.geminiApiKey="\${GEMINI_API_KEY}" \
                            --set secrets.appApiKey="\${APP_API_KEY}" \
                            --set secrets.redisPassword="\${REDIS_PASSWORD}" \
                            --set secrets.mongoPassword="\${MONGO_PASSWORD}" \
                            --set image.tag="${IMAGE_TAG}" \
                            --wait \
                            --timeout 3m
                    """
                }
            }
        }

        stage("Verify deployment") {
            steps {
                sh """
                    kubectl rollout status deployment/${IMAGE_NAME} \
                        -n ${NAMESPACE} \
                        --timeout=120s
                """
            }
        }
    }

    post {
        success {
            echo "Pipeline succeeded — ${IMAGE_NAME}:${IMAGE_TAG} deployed to ${NAMESPACE}"
        }
        failure {
            echo "Pipeline failed — rolling back"
            sh "helm rollback ${IMAGE_NAME} -n ${NAMESPACE} || true"
        }
        always {
            sh "docker image prune -f"  // clean up dangling images
        }
    }
}