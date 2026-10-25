# Runbook: Pod CrashLoopBackOff

## Trigger
Pod restart count > 5 within 10 minutes. Alert from Prometheus `kube_pod_container_status_restarts_total`.

## Triage Steps
1. `kubectl describe pod <pod-name> -n <namespace>` - Check Events section for OOMKilled, config errors
2. `kubectl logs <pod-name> -n <namespace> --previous` - Check last crash logs
3. Check resource limits: `kubectl get pod <pod-name> -o jsonpath='{.spec.containers[*].resources}'`

## Common Causes & Fixes

### OOMKilled
- Increase memory limits in Helm values
- Create hotfix PR updating `resources.limits.memory`

### ConfigMap / Secret Missing
- Verify secret exists: `kubectl get secret <name> -n <namespace>`
- Re-sync via External Secrets Operator

### Application Startup Failure
- Check image tag is valid and present in registry
- Validate environment variables are injected correctly

## Escalation
If unresolved after 15 minutes, page on-call SRE via PagerDuty.
