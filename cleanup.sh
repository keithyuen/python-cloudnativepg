#!/bin/bash

echo "Starting cleanup process..."

echo "Stopping port-forwarding processes..."
pkill -f "kubectl port-forward" || true

echo "Deleting Kubernetes resources..."
kubectl delete -f k8s/app-deployment.yaml || true
kubectl delete -f k8s/cluster.yaml || true
kubectl delete -f k8s/secrets.yaml || true
kubectl delete -f k8s/minio-service.yaml || true

echo "Cleaning up any remaining CloudNativePG clusters..."
kubectl delete cluster --all || true
kubectl delete pods -l postgresql=pg-demo-cluster || true
kubectl delete pods -l postgresql=pg-demo-cluster-1 || true
kubectl delete pvc -l postgresql=pg-demo-cluster || true
kubectl delete pvc -l postgresql=pg-demo-cluster-1 || true

echo "Cleaning up Docker resources..."
docker stop minio || true
docker rm minio || true
docker network rm minio-network || true

echo "Do you want to remove Docker images? (y/n)"
read -r remove_images
if [ "$remove_images" = "y" ]; then
    echo "Removing Docker images..."
    docker rmi fastapi-demo:latest || true
    docker rmi minio/minio || true
    docker rmi postgres:15 || true
fi

echo "Do you want to uninstall CloudNativePG operator? (y/n)"
read -r uninstall_operator
if [ "$uninstall_operator" = "y" ]; then
    echo "Uninstalling CloudNativePG operator..."
    helm uninstall cloudnative-pg -n cnpg-system || true
    kubectl delete namespace cnpg-system || true
fi

echo "Cleanup completed!" 