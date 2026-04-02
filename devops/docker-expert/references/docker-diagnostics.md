# Docker Common Issue Diagnostics

Symptom-based troubleshooting guide for common Docker problems.

## Build Performance Issues
**Symptoms:** Slow builds (10+ minutes), frequent cache invalidation
**Root causes:** Poor layer ordering, large build context, no caching strategy
**Solutions:**
- Reorder COPY instructions: dependencies before source code
- Add comprehensive .dockerignore to reduce build context
- Use `--mount=type=cache` for package manager caches
- Split into multi-stage builds to parallelize work

## Security Vulnerabilities
**Symptoms:** Security scan failures, exposed secrets, root execution
**Root causes:** Outdated base images, hardcoded secrets, default user
**Solutions:**
- Pin and regularly update base images; run `docker scout` or Trivy scans
- Use `--mount=type=secret` for build-time secrets; Docker secrets for runtime
- Create non-root user with explicit UID/GID; add `USER` directive
- Drop all capabilities, add back only what is needed

## Image Size Problems
**Symptoms:** Images over 1GB, slow deployments, high registry storage
**Root causes:** Unnecessary files, build tools in production, poor base selection
**Solutions:**
- Switch to distroless or Alpine base images for production
- Use multi-stage builds; copy only artifacts to final stage
- Clean package manager caches in the same RUN layer as install
- Audit with `docker history --no-trunc` to find large layers

## Networking Issues
**Symptoms:** Service communication failures, DNS resolution errors
**Root causes:** Missing networks, port conflicts, service naming issues
**Solutions:**
- Define custom bridge networks; use `internal: true` for backend isolation
- Use service names (not IPs) for inter-container DNS resolution
- Check port bindings with `docker port <container>`
- Add health checks so dependent services wait for readiness

## Development Workflow Problems
**Symptoms:** Hot reload failures, debugging difficulties, slow iteration
**Root causes:** Volume mounting issues, port configuration, environment mismatch
**Solutions:**
- Use bind mounts for source code; anonymous volumes for node_modules
- Expose debug ports (e.g. 9229 for Node.js inspector)
- Separate development and production Compose targets
- Match host and container user IDs to avoid permission issues
