#!/bin/bash

set -e  # Exit on error

echo "Starting deployment process..."

# Check if Python virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Setup MinIO
echo "Setting up MinIO..."
docker network create minio-network || true
docker run -d \
    --name minio \
    --network minio-network \
    -p 9000:9000 \
    -p 9001:9001 \
    -e "MINIO_ROOT_USER=minioadmin" \
    -e "MINIO_ROOT_PASSWORD=minioadmin" \
    minio/minio server /data --console-address ":9001"

# Wait for MinIO to start
echo "Waiting for MinIO to start..."
sleep 5

# Create MinIO bucket
echo "Creating MinIO bucket..."
docker run --rm --network minio-network minio/mc alias set myminio http://minio:9000 minioadmin minioadmin
docker run --rm --network minio-network minio/mc mb --ignore-existing myminio/cloudnativepg-backup

# Build FastAPI application
echo "Building FastAPI application..."
docker build -t fastapi-demo:latest .

# Install CloudNativePG operator if not present
if ! kubectl get pods -n cnpg-system 2>/dev/null | grep -q 'cloudnative-pg'; then
    echo "Installing CloudNativePG operator..."
    helm repo add cloudnative-pg https://cloudnative-pg.github.io/charts
    helm repo update
    helm install cloudnative-pg cloudnative-pg/cloudnative-pg \
        --namespace cnpg-system \
        --create-namespace
fi

# Wait for operator to be ready
echo "Waiting for CloudNativePG operator to be ready..."
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=cloudnative-pg -n cnpg-system --timeout=120s

# Deploy Kubernetes resources
echo "Deploying Kubernetes resources..."
kubectl apply -f k8s/minio-service.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/cluster.yaml

# Wait for PostgreSQL cluster to be ready
echo "Waiting for PostgreSQL cluster to be ready..."
kubectl wait --for=condition=ready cluster/pg-demo-cluster --timeout=300s

# Deploy FastAPI application
echo "Deploying FastAPI application..."
kubectl apply -f k8s/app-deployment.yaml

# Wait for FastAPI deployment to be ready
echo "Waiting for FastAPI deployment to be ready..."
kubectl wait --for=condition=available deployment/fastapi-demo --timeout=120s

# Set up port forwarding
echo "Setting up port forwarding..."
kubectl port-forward svc/fastapi-demo 8000:80 &
kubectl port-forward svc/pg-demo-cluster-rw 5432:5432 &

echo "Deployment completed!"
echo "FastAPI application is available at: http://localhost:8000"
echo "PostgreSQL is available at: localhost:5432"
echo "MinIO console is available at: http://localhost:9001"
echo "MinIO credentials: minioadmin / minioadmin"
echo "PostgreSQL credentials: app_user / change-me-in-production" 