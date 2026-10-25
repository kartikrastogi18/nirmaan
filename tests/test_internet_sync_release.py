from pathlib import Path


def test_frontend_contains_auto_sync_and_status():
    app_js = Path('app/static/js/app.js').read_text(encoding='utf-8')
    css = Path('app/static/css/style.css').read_text(encoding='utf-8')
    assert 'SYNC_INTERVAL_MS = 15000' in app_js
    assert 'syncFromServer' in app_js
    assert 'renderSyncStatus' in app_js
    assert 'window.addEventListener("online"' in app_js
    assert 'window.addEventListener("offline"' in app_js
    assert '.sync-status' in css


def test_deployment_uses_shared_database_and_s3_configuration():
    render = Path('render.yaml').read_text(encoding='utf-8')
    env = Path('.env.example').read_text(encoding='utf-8')
    assert 'DATABASE_URL' in render
    assert 'STORAGE_BACKEND' in render and 's3' in render
    assert 'S3_BUCKET' in render
    assert 'DATABASE_URL' in env and 'S3_ENDPOINT_URL' in env
