#!/bin/bash
echo "Deploying Agentic Cinema to Google Cloud Run..."

PROJECT_ID=$(gcloud config get-value project)
REGION="us-central1"

# Load env vars safely
if [ -f .env ]; then
  export $(cat .env | grep -v '#' | awk '/=/ {print $1}')
fi

gcloud run deploy agentic-cinema \
  --source . \
  --region $REGION \
  --allow-unauthenticated \
  --port 8080 \
  --set-env-vars="GCP_PROJECT_ID=${GCP_PROJECT_ID},PARALLEL_API_KEY=${PARALLEL_API_KEY},FIREBASE_WEB_API_KEY=${FIREBASE_WEB_API_KEY},RESEND_API_KEY=${RESEND_API_KEY},ALERT_EMAIL_ADDRESS=${ALERT_EMAIL_ADDRESS}"

echo "Deployment complete!"
