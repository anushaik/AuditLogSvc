# Deployment and release maturity guide

## CI/CD
- GitHub Actions workflow is defined in .github/workflows/ci-cd.yml.
- The workflow runs tests, builds the container image, validates the health endpoint, and optionally deploys to Kubernetes when a kubeconfig secret is available.

## Container orchestration
- Kubernetes manifests are provided in k8s/ for a rolling deployment and a ClusterIP service.
- The deployment uses readiness and liveness probes, autoscaling-friendly resource requests/limits, and a two-replica baseline.

## Rolling deployment and rollback
1. Build and push a new image tag.
2. Update the image tag in k8s/deployment.yaml or use a deployment pipeline to do it automatically.
3. Apply the manifest with kubectl apply -f k8s/.
4. Monitor rollout with kubectl rollout status deployment/audit-log-service -n auditlog.
5. Roll back with kubectl rollout undo deployment/audit-log-service -n auditlog.

## Infrastructure as code
- Kubernetes manifests provide the base deployment definition.
- Future extensions can add Helm charts, Terraform, and environment-specific overlays.

## Capacity planning and sizing
- Baseline sizing: 2 replicas, 250m CPU / 256Mi requests, 500m CPU / 512Mi limits.
- Scale out based on latency and request volume; the existing /metrics endpoint can be scraped by Prometheus to drive autoscaling policies.
- For production, pair this with a managed PostgreSQL instance, persistent storage, and a secrets manager.
