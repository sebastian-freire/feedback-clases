pipeline {
  agent any
  options { disableConcurrentBuilds() }

  environment {
    NS = 'alumno-team3'
    DOCKERHUB = credentials('dockerhub')  // define DOCKERHUB_USR y DOCKERHUB_PSW
    RUN_ID = "ci-${env.BUILD_NUMBER}"
  }

  stages {
    stage('Test') {
      steps {
        // Los tests necesitan una Postgres; se levanta una temporal solo para este build.
        sh '''
          docker network create $RUN_ID
          docker run -d --name $RUN_ID-db --network $RUN_ID -e POSTGRES_PASSWORD=test -e POSTGRES_DB=test postgres:17-alpine
          until docker exec $RUN_ID-db pg_isready -h 127.0.0.1 -U postgres; do sleep 1; done
          docker create --name $RUN_ID-tests --network $RUN_ID -w /app \
            -e DATABASE_URL=postgresql+psycopg://postgres:test@$RUN_ID-db:5432/postgres \
            -e TEST_DATABASE_URL=postgresql+psycopg://postgres:test@$RUN_ID-db:5432/test \
            -e JWT_SECRET=jwt-solo-para-los-tests-de-jenkins-0123456789 \
            ghcr.io/astral-sh/uv:python3.13-bookworm-slim \
            sh -c "uv sync --locked && uv run pytest"
          docker cp backend/. $RUN_ID-tests:/app
          docker start -a $RUN_ID-tests
        '''
      }
    }

    stage('Build') {
      steps {
        sh '''
          TAG=$(git rev-parse --short HEAD)
          docker build -t $DOCKERHUB_USR/feedback-backend:$TAG backend
          docker build -t $DOCKERHUB_USR/feedback-frontend:$TAG frontend
        '''
      }
    }

    stage('Push') {
      steps {
        sh '''
          TAG=$(git rev-parse --short HEAD)
          echo "$DOCKERHUB_PSW" | docker login -u "$DOCKERHUB_USR" --password-stdin
          docker push $DOCKERHUB_USR/feedback-backend:$TAG
          docker push $DOCKERHUB_USR/feedback-frontend:$TAG
        '''
      }
    }

    stage('Deploy') {
      steps {
        sh '''
          TAG=$(git rev-parse --short HEAD)
          kubectl -n $NS set image deployment/backend backend=$DOCKERHUB_USR/feedback-backend:$TAG
          kubectl -n $NS set image deployment/frontend frontend=$DOCKERHUB_USR/feedback-frontend:$TAG
          kubectl -n $NS rollout status deployment/backend --timeout=300s
          kubectl -n $NS rollout status deployment/frontend --timeout=300s
        '''
      }
    }
  }

  post {
    always {
      sh 'docker rm -f $RUN_ID-db $RUN_ID-tests || true; docker network rm $RUN_ID || true'
    }
  }
}
