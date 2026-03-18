# Implementations

This folder contains in-repo reference implementations for ACR (the documentation remains in this repository).

## Start Here (Fastest Path to a Working Demo)

The in-repo implementation you can run locally is the **ACR Control Plane**. See:
`./acr-control-plane/README.md`

If you want the shortest “get to a browser” path from the repo root:

```bash
cd implementations/acr-control-plane
cp .env.example .env
docker-compose up --build

# Verify health
curl http://localhost:8000/acr/health

# Open console
# http://localhost:8000/console
```

## ACR Control Plane

Runtime reference implementation of the ACR six-pillar control plane.

- Location: `./acr-control-plane`
- Messaging/spec alignment: https://autonomouscontrol.io/control-plane

Key idea: ACR provides runtime-enforced governance (identity, policy enforcement, drift detection, observability, containment, and human authority) for agentic AI that takes real actions.
