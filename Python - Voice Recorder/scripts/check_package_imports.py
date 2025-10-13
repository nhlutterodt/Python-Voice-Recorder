import sys
import traceback
import importlib

print('Python', sys.version)
print('sys.path[0:5]=', sys.path[0:5])
try:
    m = importlib.import_module('voice_recorder.enhanced_editor')
    print('Imported voice_recorder.enhanced_editor; _cloud_available=', getattr(m, '_cloud_available', None))
    print('CloudUI in module=', hasattr(m, 'CloudUI'))
except Exception:
    print('Import voice_recorder.enhanced_editor failed:')
    traceback.print_exc()

try:
    am = importlib.import_module('voice_recorder.cloud.auth_manager')
    print('voice_recorder.cloud.auth_manager GOOGLE_APIS_AVAILABLE=', getattr(am, 'GOOGLE_APIS_AVAILABLE', None))
except Exception:
    print('Import voice_recorder.cloud.auth_manager failed:')
    traceback.print_exc()
