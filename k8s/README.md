# Kubernetes Deployment Guide

This guide explains how to deploy the FastAPI demo application with CloudNativePG.

## Prerequisites Installation

### 1. Install kubectl
```bash
# macOS with Homebrew
brew install kubectl

# Linux
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# Windows with Chocolatey
choco install kubernetes-cli
```

### 2. Install Helm
```bash
# macOS with Homebrew
brew install helm

# Linux
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Windows with Chocolatey
choco install kubernetes-helm
```

### 3. Set up a Kubernetes cluster

Choose one of these options:

#### Option A: Local Development with minikube
```bash
# Install minikube
# macOS
brew install minikube

# Linux
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube

# Windows with Chocolatey
choco install minikube

# Start minikube
minikube start --memory=4096 --cpus=2
```

#### Option B: Local Development with Docker Desktop
1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/)
2. Enable Kubernetes in Docker Desktop settings
3. Wait for Kubernetes to start

### 4. Set up S3-compatible storage for backups

You can use one of these options:
- AWS S3: Create an account and bucket at [AWS Console](https://aws.amazon.com/)
- MinIO: For local development
```bash
# Install MinIO locally using Docker
docker run -d \
  -p 9000:9000 \
  -p 9001:9001 \
  -e "MINIO_ROOT_USER=minioadmin" \
  -e "MINIO_ROOT_PASSWORD=minioadmin" \
  minio/minio server /data --console-address ":9001"

# Create a bucket using MinIO Client
docker run --rm -it minio/mc alias set myminio http://localhost:9000 minioadmin minioadmin
docker run --rm -it minio/mc mb myminio/cloudnativepg-backup
```

### 5. Verify Prerequisites
```bash
# Check kubectl installation
kubectl version --client

# Check Helm installation
helm version

# Check Kubernetes connection
kubectl cluster-info

# Check S3 access (if using AWS S3)
aws s3 ls s3://your-bucket/
```

## Deployment Steps

1. Add the CloudNativePG Helm repository:
```bash
helm repo add cloudnative-pg https://cloudnative-pg.github.io/charts
helm repo update
```

2. Install CloudNativePG operator:
```bash
helm install cloudnative-pg cloudnative-pg/cloudnative-pg \
  --namespace cnpg-system \
  --create-namespace
```

3. Update secrets in `secrets.yaml`:
   - Change the database password
   - Update S3 credentials for backups
   ```bash
   # If using MinIO locally
   sed -i '' 's/your-access-key/minioadmin/' secrets.yaml
   sed -i '' 's/your-secret-key/minioadmin/' secrets.yaml
   
   # Also update cluster.yaml for MinIO
   sed -i '' 's|https://s3.amazonaws.com|http://host.docker.internal:9000|' cluster.yaml
   sed -i '' 's|s3://your-bucket/|s3://cloudnativepg-backup/|' cluster.yaml
   ```

4. Apply the secrets:
```bash
kubectl apply -f secrets.yaml
```

5. Deploy the PostgreSQL cluster:
```bash
kubectl apply -f cluster.yaml
```

6. Generate database connection URLs:
```bash
./generate-db-urls.sh
```

7. Build and push the FastAPI application image:
```bash
# For local development with minikube
eval $(minikube docker-env)  # Use minikube's Docker daemon
docker build -t fastapi-demo:latest .

# For Docker Desktop or remote registry
docker build -t your-registry/fastapi-demo:latest .
docker push your-registry/fastapi-demo:latest
```

8. Update the image in `app-deployment.yaml` and deploy:
```bash
# Update the image field in app-deployment.yaml
kubectl apply -f app-deployment.yaml
```

## Verifying the Deployment

1. Check CloudNativePG operator status:
```bash
kubectl get pods -n cnpg-system
```

2. Check PostgreSQL cluster status:
```bash
kubectl get cluster pg-demo-cluster
kubectl get pods -l postgresql=pg-demo-cluster
```

3. Check application status:
```bash
kubectl get pods -l app=fastapi-demo
```

4. Access the application:
```bash
kubectl port-forward svc/fastapi-demo 8000:80
```
The application will be available at http://localhost:8000

## Connection Information

- Primary (write) endpoint: pg-demo-cluster-rw:5432
- Replica (read) endpoint: pg-demo-cluster-ro:5432

## Monitoring

The PostgreSQL cluster exposes metrics for Prometheus at port 9187. You can configure your Prometheus instance to scrape these metrics using the PodMonitor created by CloudNativePG.

## Backup and Recovery

Backups are configured to use S3 storage and are retained for 30 days. To create a manual backup:

```bash
kubectl apply -f - <<EOF
apiVersion: postgresql.cnpg.io/v1
kind: Backup
metadata:
  name: pg-demo-backup
spec:
  cluster:
    name: pg-demo-cluster
EOF
```

## Scaling

To scale the number of replicas:

```bash
kubectl patch cluster pg-demo-cluster --type merge \
  -p '{"spec":{"instances": 4}}'
```

## Troubleshooting

1. If using minikube and can't access services:
```bash
# Get minikube IP
minikube ip
# Update /etc/hosts to add the IP
echo "$(minikube ip) host.docker.internal" | sudo tee -a /etc/hosts
```

2. If MinIO is not accessible:
```bash
# Check MinIO status
docker ps | grep minio
# Check MinIO logs
docker logs $(docker ps -q --filter name=minio)
```

3. If database pods are not starting:
```bash
# Check pod events
kubectl describe pod -l postgresql=pg-demo-cluster
# Check operator logs
kubectl logs -n cnpg-system -l app.kubernetes.io/name=cloudnative-pg
```

## Environment Variables

The application requires the following environment variables:

- `PRIMARY_DB_URL`: URL for the primary database node
- `REPLICA_DB_URL`: URL for the replica database node(s)
- `APP_NAME`: Application name (default: "cloudnativepg-demo")
- `APP_PORT`: Application port (default: 8000)

### How Environment Variables are Managed

1. Database URLs (`PRIMARY_DB_URL` and `REPLICA_DB_URL`):
   - These are automatically generated by the `generate-db-urls.sh` script
   - The script creates a Kubernetes secret named `app-db-urls` containing these values
   - The application deployment (`app-deployment.yaml`) references these from the secret

2. Application Settings (`APP_NAME` and `APP_PORT`):
   - These have default values in `app/core/config.py`
   - To override them, you can either:
     ```bash
     # Option 1: Create a .env file before building the container
     echo "APP_NAME=my-custom-name" > .env
     echo "APP_PORT=8080" >> .env
     
     # Option 2: Add them to the deployment manifest
     # Edit app-deployment.yaml and add under 'env:'
     - name: APP_NAME
       value: "my-custom-name"
     - name: APP_PORT
       value: "8080"
     ```

### Verifying Environment Variables

To check if the environment variables are properly set:

1. Check the database URL secret:
```bash
kubectl get secret app-db-urls -o yaml
```

2. Check environment variables in a running pod:
```bash
# Get pod name
POD_NAME=$(kubectl get pod -l app=fastapi-demo -o jsonpath='{.items[0].metadata.name}')

# Check environment variables
kubectl exec $POD_NAME -- env | grep -E 'PRIMARY_DB_URL|REPLICA_DB_URL|APP_NAME|APP_PORT'
``` 