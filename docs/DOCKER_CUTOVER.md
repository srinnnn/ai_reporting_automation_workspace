# Docker Cutover

Docker is not part of the current Windows production runtime because the production workstation cannot run Docker Desktop or Docker Engine under corporate policy.

Future cutover target:

```text
GitHub Actions -> GHCR SHA image -> approved Docker host -> 127.0.0.1:8785
```

Cutover must not require:

- React rewrite
- FastAPI rewrite
- API rewrite
- route rewrite

Only the deployment runtime changes. The application entry remains `backend.main:app`, and the externally visible port remains `8785`.

GHCR publication remains gated until Product Owner explicitly approves package-write publication to the target registry namespace.
