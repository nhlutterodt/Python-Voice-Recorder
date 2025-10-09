import importlib.util
print('google_auth_oauthlib:', importlib.util.find_spec('google_auth_oauthlib') is not None)
print('google.oauth2.credentials:', importlib.util.find_spec('google.oauth2.credentials') is not None)
print('googleapiclient.discovery:', importlib.util.find_spec('googleapiclient.discovery') is not None)
print('google.auth.transport.requests:', importlib.util.find_spec('google.auth.transport.requests') is not None)
