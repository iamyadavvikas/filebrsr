#!/bin/bash
# Deploy FileBRSR to Google Cloud Run
# Prerequisites: gcloud CLI installed and authenticated
# Usage: ./deploy-gcp.sh

set -e

# --- Configuration ---
PROJECT_ID="${GCP_PROJECT_ID:-filebrsr}"
REGION="asia-south1"  # Mumbai (closest to India users)
BACKEND_SERVICE="filebrsr-api"
FRONTEND_SERVICE="filebrsr-web"

echo "=== FileBRSR GCP Cloud Run Deployment ==="
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo ""

# Check gcloud is authenticated
if ! gcloud auth print-identity-token &>/dev/null; then
  echo "❌ Not authenticated. Run: gcloud auth login"
  exit 1
fi

# Set project
gcloud config set project "$PROJECT_ID"

# Enable required APIs
echo "→ Enabling APIs..."
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  --quiet

# Create Artifact Registry repo (if not exists)
echo "→ Setting up Artifact Registry..."
gcloud artifacts repositories describe filebrsr --location="$REGION" 2>/dev/null || \
  gcloud artifacts repositories create filebrsr \
    --repository-format=docker \
    --location="$REGION" \
    --description="FileBRSR container images"

REGISTRY="${REGION}-docker.pkg.dev/${PROJECT_ID}/filebrsr"

# --- Build & Deploy Backend ---
echo ""
echo "=== Building Backend ==="
cd "$(dirname "$0")/backend"

gcloud builds submit \
  --tag "${REGISTRY}/${BACKEND_SERVICE}:latest" \
  --timeout=600s \
  --quiet

echo "=== Deploying Backend ==="
gcloud run deploy "$BACKEND_SERVICE" \
  --image "${REGISTRY}/${BACKEND_SERVICE}:latest" \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --timeout 300 \
  --min-instances 1 \
  --max-instances 5 \
  --set-env-vars "SUPABASE_URL=${SUPABASE_URL}" \
  --set-env-vars "SUPABASE_SERVICE_KEY=${SUPABASE_SERVICE_KEY}" \
  --set-env-vars "GEMINI_API_KEY=${GEMINI_API_KEY}" \
  --set-env-vars "GROQ_API_KEY=${GROQ_API_KEY}" \
  --set-env-vars "ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}" \
  --set-env-vars "ALLOWED_ORIGINS=https://www.filebrsr.com,https://filebrsr.com,http://localhost:3000" \
  --set-env-vars "MAX_FILE_SIZE_MB=50" \
  --quiet

BACKEND_URL=$(gcloud run services describe "$BACKEND_SERVICE" --region "$REGION" --format='value(status.url)')
echo "✅ Backend deployed: $BACKEND_URL"

# --- Build & Deploy Frontend ---
echo ""
echo "=== Building Frontend ==="
cd "$(dirname "$0")/../frontend"

gcloud builds submit \
  --tag "${REGISTRY}/${FRONTEND_SERVICE}:latest" \
  --timeout=600s \
  --build-arg "NEXT_PUBLIC_SUPABASE_URL=${NEXT_PUBLIC_SUPABASE_URL}" \
  --build-arg "NEXT_PUBLIC_SUPABASE_ANON_KEY=${NEXT_PUBLIC_SUPABASE_ANON_KEY}" \
  --build-arg "NEXT_PUBLIC_API_URL=${BACKEND_URL}" \
  --quiet

echo "=== Deploying Frontend ==="
gcloud run deploy "$FRONTEND_SERVICE" \
  --image "${REGISTRY}/${FRONTEND_SERVICE}:latest" \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --timeout 300 \
  --min-instances 1 \
  --max-instances 10 \
  --set-env-vars "BACKEND_URL=${BACKEND_URL}" \
  --set-env-vars "NEXT_PUBLIC_SUPABASE_URL=${NEXT_PUBLIC_SUPABASE_URL}" \
  --set-env-vars "NEXT_PUBLIC_SUPABASE_ANON_KEY=${NEXT_PUBLIC_SUPABASE_ANON_KEY}" \
  --set-env-vars "SUPABASE_SERVICE_ROLE_KEY=${SUPABASE_SERVICE_KEY}" \
  --quiet

FRONTEND_URL=$(gcloud run services describe "$FRONTEND_SERVICE" --region "$REGION" --format='value(status.url)')
echo "✅ Frontend deployed: $FRONTEND_URL"

echo ""
echo "=== Deployment Complete ==="
echo "Frontend: $FRONTEND_URL"
echo "Backend:  $BACKEND_URL"
echo ""
echo "Next steps:"
echo "  1. Map your domain: gcloud run domain-mappings create --service=$FRONTEND_SERVICE --domain=filebrsr.com --region=$REGION"
echo "  2. Update Supabase OAuth redirect URLs to include the Cloud Run URL"
echo "  3. Update ALLOWED_ORIGINS if needed"
