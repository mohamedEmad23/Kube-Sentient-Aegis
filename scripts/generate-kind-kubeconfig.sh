#!/usr/bin/env bash
set -euo pipefail

context="kind-aegis-demo"
output="deploy/docker/kubeconfig-docker.yaml"

# Get kubeconfig for kind cluster
kubectl config view --raw --minify --context "${context}" -o yaml > "${output}"

# For kind, the API is accessible at the published port on localhost
# Kind automatically exposes the API on a random high port (e.g., 37071)
# This works from both host and Docker containers with host networking

echo "Generated ${output} for kind cluster"
echo "Kind cluster API will be accessible from Docker containers using host networking mode"
