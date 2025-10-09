import sys, traceback
from pathlib import Path
print('Python', sys.version)
print('CWD:', Path('.').resolve())
print('sys.path[0:5]=', sys.path[0:5])

try:
    import enhanced_editor as ee
    print('Imported enhanced_editor; _cloud_available=', getattr(ee, '_cloud_available', None))
    print('enhanced_editor has CloudUI attr =', hasattr(ee, 'CloudUI'))
except Exception:
    print('Import enhanced_editor failed:')
    traceback.print_exc()

try:
    import cloud.auth_manager as am
    print('Imported cloud.auth_manager; GOOGLE_APIS_AVAILABLE=', getattr(am, 'GOOGLE_APIS_AVAILABLE', None))
except Exception:
    print('Import cloud.auth_manager failed:')
    traceback.print_exc()

try:
    import cloud.cloud_ui as cui
    print('Imported cloud.cloud_ui; CloudUI exists =', hasattr(cui, 'CloudUI'))
except Exception:
    print('Import cloud.cloud_ui failed:')
    traceback.print_exc()

try:
    from cloud.auth_manager import GoogleAuthManager
    mgr = GoogleAuthManager(use_keyring=False)
    print('Created GoogleAuthManager; is_authenticated=', mgr.is_authenticated())
except Exception:
    print('Could not create GoogleAuthManager:')
    traceback.print_exc()
