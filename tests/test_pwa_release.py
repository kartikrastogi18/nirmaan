from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
def test_manifest_and_icons_exist():
    m=json.loads((ROOT/'app/static/manifest.webmanifest').read_text())
    assert m['name']=='Nirmaan Software'
    assert m['display']=='standalone'
    for size in (192,512): assert (ROOT/f'app/static/icons/icon-{size}.png').exists()
def test_service_worker_never_caches_api_writes():
    s=(ROOT/'app/static/sw.js').read_text()
    assert 'req.method !== "GET"' in s
    assert 'url.pathname.startsWith("/api/")' in s
def test_index_registers_manifest():
    s=(ROOT/'app/static/index.html').read_text()
    assert '/manifest.webmanifest' in s and 'Nirmaan Software' in s
def test_restore_tool_is_guarded():
    s=(ROOT/'restore_personal.py').read_text()
    assert 'DATABASE_URL' in s and '--yes' in s and 'integrity_check' in s
