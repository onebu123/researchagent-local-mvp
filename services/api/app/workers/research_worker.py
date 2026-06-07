from __future__ import annotations

import json

from app.tools.production_scaffold import run_worker_smoke


def main() -> None:
    print(json.dumps(run_worker_smoke(), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
