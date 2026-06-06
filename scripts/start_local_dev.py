from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    print("ResearchAgent v1.0 Local MVP start commands")
    print("")
    print("Backend:")
    print("  cd services/api")
    print("  python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000")
    print("")
    print("Frontend:")
    print("  cd apps/web")
    print("  npm run dev -- --hostname 127.0.0.1 --port 3100")
    print("")
    print("Open:")
    print("  http://127.0.0.1:3100")
    print("  http://127.0.0.1:8000/health")
    print("")
    print("Demo and validation:")
    print("  python scripts/seed_demo.py")
    print("  python scripts/run_demo.py")
    print("  python scripts/export_project_zip.py --project-id demo_project")
    print("  python scripts/validate_v1.py")
    print("")
    print(f"Project root: {ROOT}")


if __name__ == "__main__":
    main()
