"""CLI entry for running the Strands workflow."""

import json
import sys

from orchestrator.workflow import run_workflow


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python -m orchestrator.run <input.json>")

    input_path = sys.argv[1]
    with open(input_path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)

    result = run_workflow(payload)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
