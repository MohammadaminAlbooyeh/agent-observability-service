# SDK Usage

Placeholder for SDK integration documentation.

## Installation

```bash
pip install agent-observability-sdk
```

## Basic Usage

```python
from agent_observability import Tracer, ObservabilityClient

client = ObservabilityClient(base_url="http://localhost:8000", api_key="your-key")
tracer = Tracer(client)

with tracer.span("tool_call"):
    # do work
    pass

client.flush()
```
