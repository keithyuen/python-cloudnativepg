#!/bin/bash

# Get the password from the secret
DB_PASSWORD=$(kubectl get secret app-user-secret -o jsonpath='{.data.password}' | base64 -d)
DB_USER=$(kubectl get secret app-user-secret -o jsonpath='{.data.username}' | base64 -d)

# Get the service names
PRIMARY_HOST="pg-demo-cluster-rw"  # Read-write service (primary)
REPLICA_HOST="pg-demo-cluster-ro"  # Read-only service (replicas)
DB_NAME="app_db"

# Generate the connection URLs
PRIMARY_DB_URL="postgresql://${DB_USER}:${DB_PASSWORD}@${PRIMARY_HOST}:5432/${DB_NAME}"
REPLICA_DB_URL="postgresql://${DB_USER}:${DB_PASSWORD}@${REPLICA_HOST}:5432/${DB_NAME}"

# Create the secret
kubectl create secret generic app-db-urls \
  --from-literal=PRIMARY_DB_URL="${PRIMARY_DB_URL}" \
  --from-literal=REPLICA_DB_URL="${REPLICA_DB_URL}" \
  --dry-run=client -o yaml | kubectl apply -f - 