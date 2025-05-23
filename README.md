# CloudNativePG Python Application Demo

This demo application showcases how to work with CloudNativePG using Python, FastAPI and SQLAlchemy. It demonstrates various features including connection to multiple database nodes, read/write operations, load balancing, and failover handling.

## Features

- FastAPI-based REST API
- Connection to multiple database nodes (primary/replica)
- Read/write operation examples
- Load balancing demonstration
- Failover handling
- Prometheus metrics integration
- Health check endpoint

## Prerequisites Installation

### 1. Install Python
```bash
# macOS with Homebrew
brew install python@3.11
# Verify installation
python3 --version
# Install pip if not already installed
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
python3 get-pip.py

# Linux (Ubuntu/Debian)
sudo apt update
sudo apt install python3 python3-pip
# Verify installation
python3 --version
pip3 --version

# Windows with Chocolatey
choco install python
# Verify installation
python --version
pip --version

# Optional: Create a virtual environment (recommended)
python3 -m venv venv
# macOS/Linux
source venv/bin/activate
# Windows
.\venv\Scripts\activate
```

### 2. Install kubectl
```bash
# macOS with Homebrew
brew install kubectl

# Linux
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# Windows with Chocolatey
choco install kubernetes-cli
```

### 3. Install Helm
```bash
# macOS with Homebrew
brew install helm

# Linux
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Windows with Chocolatey
choco install kubernetes-helm
```

### 4. Set up a Kubernetes cluster

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

### 5. Set up S3-compatible storage for backups

You can use one of these options:
- AWS S3: Create an account and bucket at [AWS Console](https://aws.amazon.com/)
- MinIO: For local development

#### Setting up MinIO:

1. Create a Docker network for MinIO:
```bash
docker network create minio-network
```

2. Start MinIO server:
```bash
# These are the default credentials we're setting:
# ACCESS_KEY_ID = minioadmin
# SECRET_KEY = minioadmin
docker run -d \
  --name minio \
  --network minio-network \
  -p 9000:9000 \
  -p 9001:9001 \
  -e "MINIO_ROOT_USER=minioadmin" \  # This is your ACCESS_KEY_ID
  -e "MINIO_ROOT_PASSWORD=minioadmin" \  # This is your SECRET_KEY
  minio/minio server /data --console-address ":9001"
```

3. Create a bucket using MinIO Client:
```bash
# For macOS/Linux
docker run --rm --network minio-network \
  minio/mc alias set myminio http://minio:9000 minioadmin minioadmin

docker run --rm --network minio-network \
  minio/mc mb myminio/cloudnativepg-backup

# For Windows PowerShell
docker run --rm --network minio-network `
  minio/mc alias set myminio http://minio:9000 minioadmin minioadmin

docker run --rm --network minio-network `
  minio/mc mb myminio/cloudnativepg-backup
```

4. Update credentials in secrets:
```bash
# Update k8s/secrets.yaml with MinIO credentials
cat > k8s/secrets.yaml << EOF
apiVersion: v1
kind: Secret
metadata:
  name: app-user-secret
type: Opaque
stringData:
  username: app_user
  password: change-me-in-production  # Change this in production!
---
apiVersion: v1
kind: Secret
metadata:
  name: s3-creds
type: Opaque
stringData:
  ACCESS_KEY_ID: minioadmin      # Same as MINIO_ROOT_USER
  ACCESS_SECRET_KEY: minioadmin   # Same as MINIO_ROOT_PASSWORD
EOF
```

5. Update cluster configuration:
   When using MinIO locally, update the following in `k8s/cluster.yaml`:
   ```yaml
   backup:
     barmanObjectStore:
       destinationPath: s3://cloudnativepg-backup/
       endpointURL: http://minio:9000  # Using service name in Docker network
       s3Credentials:
         accessKeyId:
           name: s3-creds
           key: ACCESS_KEY_ID
         secretAccessKey:
           name: s3-creds
           key: ACCESS_SECRET_KEY
   ```

6. Verify MinIO access:
```bash
# Check MinIO is running
docker ps | grep minio

# First, create the alias and verify it works
docker run --rm --network minio-network minio/mc alias set myminio http://minio:9000 minioadmin minioadmin

# Create the bucket
docker run --rm --network minio-network minio/mc mb --ignore-existing myminio/cloudnativepg-backup

# List all buckets (this should work now since we're using --ignore-existing above)
docker run --rm --network minio-network minio/mc ls myminio

# List the specific bucket contents
docker run --rm --network minio-network minio/mc ls myminio/cloudnativepg-backup

# Optional: You can also use the MinIO client to copy a test file
echo "test" > test.txt
docker run --rm --network minio-network -v $(pwd)/test.txt:/test.txt minio/mc cp /test.txt myminio/cloudnativepg-backup/
rm test.txt
```

Expected output should look like:
```
Added `myminio` successfully.
Bucket created successfully `myminio/cloudnativepg-backup`.
[2024-xx-xx xx:xx:xx]     0B cloudnativepg-backup/
```

You can also access the MinIO Console UI:
- URL: http://localhost:9001
- Username: minioadmin
- Password: minioadmin

Note: Each MinIO client command needs to be run separately because:
1. The MinIO client container is designed to run single commands
2. For automation, you might want to use the MinIO SDK instead
3. The Console UI is recommended for interactive management

Troubleshooting:
- If you see "connection refused" errors, make sure the MinIO server is running:
  ```bash
  docker ps | grep minio
  # If not running, start it again:
  docker run -d \
    --name minio \
    --network minio-network \
    -p 9000:9000 \
    -p 9001:9001 \
    -e "MINIO_ROOT_USER=minioadmin" \
    -e "MINIO_ROOT_PASSWORD=minioadmin" \
    minio/minio server /data --console-address ":9001"
  ```
- If you need to start fresh, you can remove and recreate the container:
  ```bash
  docker rm -f minio
  # Then start again from step 2
  ```

### 6. Verify Prerequisites
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

## Application Setup

1. Clone the repository

2. Set up Python environment:
   ```bash
   # Create virtual environment
   python3 -m venv venv
   
   # Activate virtual environment
   # macOS/Linux
   source venv/bin/activate
   # Windows
   .\venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   ```

## Kubernetes Deployment

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

3. Update secrets in `k8s/secrets.yaml`:
   - Change the database password
   - Update S3 credentials for backups
   ```bash
   # If using MinIO locally
   sed -i '' 's/your-access-key/minioadmin/' k8s/secrets.yaml
   sed -i '' 's/your-secret-key/minioadmin/' k8s/secrets.yaml
   
   # Also update cluster.yaml for MinIO
   sed -i '' 's|https://s3.amazonaws.com|http://host.docker.internal:9000|' k8s/cluster.yaml
   sed -i '' 's|s3://your-bucket/|s3://cloudnativepg-backup/|' k8s/cluster.yaml
   ```

4. Apply the secrets:
```bash
kubectl apply -f k8s/secrets.yaml
```

5. Deploy the PostgreSQL cluster:
```bash
kubectl apply -f k8s/cluster.yaml
```

6. Generate database connection URLs:
```bash
./k8s/generate-db-urls.sh
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

8. Update the image in `k8s/app-deployment.yaml` and deploy:
```bash
kubectl apply -f k8s/app-deployment.yaml
```

## Environment Variables

The application requires the following environment variables:

- `PRIMARY_DB_URL`: URL for the primary database node
- `REPLICA_DB_URL`: URL for the replica database node(s)
- `APP_NAME`: Application name (default: "cloudnativepg-demo")
- `APP_PORT`: Application port (default: 8000)

### How Environment Variables are Managed

1. Database URLs (`PRIMARY_DB_URL` and `REPLICA_DB_URL`):
   - These are automatically generated by the `k8s/generate-db-urls.sh` script
   - The script creates a Kubernetes secret named `app-db-urls` containing these values
   - The application deployment (`k8s/app-deployment.yaml`) references these from the secret

2. Application Settings (`APP_NAME` and `APP_PORT`):
   - These have default values in `app/core/config.py`
   - To override them, you can either:
     ```bash
     # Option 1: Create a .env file before building the container
     echo "APP_NAME=my-custom-name" > .env
     echo "APP_PORT=8080" >> .env
     
     # Option 2: Add them to the deployment manifest
     # Edit k8s/app-deployment.yaml and add under 'env:'
     - name: APP_NAME
       value: "my-custom-name"
     - name: APP_PORT
       value: "8080"
     ```

## API Endpoints

- `GET /health`: Health check endpoint
- `GET /metrics`: Prometheus metrics
- `POST /items`: Create a new item (writes to primary)
- `GET /items`: List all items (reads from replica)
- `GET /items/{id}`: Get specific item (reads from replica)
- `PUT /items/{id}`: Update an item (writes to primary)
- `DELETE /items/{id}`: Delete an item (writes to primary)

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

## Monitoring

The PostgreSQL cluster exposes metrics for Prometheus at port 9187. You can configure your Prometheus instance to scrape these metrics using the PodMonitor created by CloudNativePG.

The application also exposes its own metrics at the `/metrics` endpoint, including:
- Request latency
- Database operation counters
- Connection pool statistics

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

## Connecting to CloudNativePG Database

There are two ways to connect to the PostgreSQL database:

### Method 1: Using Port Forward
```bash
# Forward the PostgreSQL primary service port
kubectl port-forward svc/pg-demo-cluster-rw 5432:5432

# Connect using psql (if you have it installed locally)
PGPASSWORD=change-me-in-production psql -h localhost -p 5432 -U app_user -d app_db

# Or use PostgreSQL client via Docker
docker run -it --rm --network host postgres:15 psql "postgresql://app_user:change-me-in-production@localhost:5432/app_db"
```

### Method 2: Using Temporary Pod (Recommended)
```bash
# Connect to primary (read-write)
kubectl run psql-client --rm -it --image=postgres:15 -- psql "postgresql://app_user:change-me-in-production@pg-demo-cluster-rw:5432/app_db"

# Connect to replica (read-only)
kubectl run psql-client --rm -it --image=postgres:15 -- psql "postgresql://app_user:change-me-in-production@pg-demo-cluster-r:5432/app_db"
```

### Useful psql Commands
Once connected, you can use these psql commands:
```sql
-- List all tables
\dt

-- Show connection info
\conninfo

-- Show table schema
\d+ table_name

-- Create a test table
CREATE TABLE test (id serial primary key, name text);

-- Insert test data
INSERT INTO test (name) VALUES ('test1');

-- Query data
SELECT * FROM test;

-- Exit psql
\q
```

Note: The password `change-me-in-production` should be changed in production environments by updating the `app-user-secret` in `k8s/secrets.yaml`. 

## Cleanup

To clean up all resources after testing:

```bash
# Delete the FastAPI application
kubectl delete -f k8s/app-deployment.yaml

# Delete the PostgreSQL cluster (this will delete all PVCs and data)
kubectl delete -f k8s/cluster.yaml

# Delete secrets
kubectl delete -f k8s/secrets.yaml

# Delete MinIO service
kubectl delete -f k8s/minio-service.yaml

# Stop port-forwarding processes (if any)
pkill -f "kubectl port-forward"

# Stop and remove MinIO container
docker stop minio
docker rm minio

# Remove MinIO network
docker network rm minio-network

# Optional: Remove local Docker images
docker rmi fastapi-demo:latest
docker rmi minio/minio
docker rmi postgres:15

# Optional: Uninstall CloudNativePG operator
helm uninstall cloudnative-pg -n cnpg-system
kubectl delete namespace cnpg-system
```

Note: Be careful when running cleanup commands in a production environment. Make sure to backup any important data before deleting resources. 