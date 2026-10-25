from pathlib import Path
import py_compile
import sys

ROOT = Path(__file__).resolve().parent
failures = []
for path in list((ROOT / "app").rglob("*.py")) + list((ROOT / "tests").rglob("*.py")):
    try:
        py_compile.compile(str(path), doraise=True)
    except Exception as exc:
        failures.append(f"{path.relative_to(ROOT)}: {exc}")

required = [
    "requirements.txt", "render.yaml", "wsgi.py", "app/static/index.html",
    "app/static/js/app.js", "app/static/js/media.js", "app/routes/health.py",
    "app/static/manifest.webmanifest", "app/static/sw.js", "app/static/icons/icon-192.png",
    "app/static/icons/icon-512.png", "restore_personal.py", "USER_GUIDE.md", "ADMIN_SETUP.md",
]
for rel in required:
    if not (ROOT / rel).exists():
        failures.append(f"missing required file: {rel}")

if failures:
    print("RELEASE CHECK FAILED")
    print("\n".join(f"- {x}" for x in failures))
    sys.exit(1)
print("RELEASE CHECK PASSED: Python compiles and required release files are present.")
