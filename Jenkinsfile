pipeline {
    agent any

    environment {
        IMAGE_NAME    = "docuquery-api"
        IMAGE_TAG     = "${env.BUILD_NUMBER}"
        NAMESPACE     = "docuquery-dev"
        HELM_CHART    = "./helm"
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
                            --set secrets.geminiApiKey="${GEMINI_API_KEY}" \
                            --set secrets.appApiKey="${APP_API_KEY}" \
                            --set secrets.redisPassword="${REDIS_PASSWORD}" \
                            --set secrets.mongoPassword="${MONGO_PASSWORD}" \
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