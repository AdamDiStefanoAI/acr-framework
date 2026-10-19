"""Disposable CI fixture only; never deploy this ledger endpoint in production.

Uses the real protected executor app and authorization dependencies. Only final
enterprise tools are replaced by synthetic local file effects. No database,
policy, gateway auth, approval, containment, or signing behavior is mocked.
One uvicorn worker is mandatory so the observer sees every synthetic effect.
"""

import json
from copy import deepcopy
from pathlib import Path

from examples.protected_executor import app as executor

app = executor.app
_ledger_path = Path("/tmp/acr-full-stack-ledger.jsonl")


def _read():
    return (
        [json.loads(line) for line in _ledger_path.read_text().splitlines()]
        if _ledger_path.exists()
        else []
    )


def _tool(name):
    def execute(**parameters):
        record = {"tool_name": name, "parameters": deepcopy(parameters)}
        with _ledger_path.open("a") as stream:
            stream.write(json.dumps(record) + "\n")
        return {"fixture": "synthetic-only", "sequence": len(_read()), **record}

    return execute


for name in ("query_customer_db", "issue_refund", "delete_customer"):
    executor._ALLOWED_TOOLS[name] = _tool(name)


@app.get("/__test/ledger")
async def ledger():
    return _read()
