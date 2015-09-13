import os
def get_apix_auth_headers():
    return {'Authorization': 'Token {}'.format(os.environ.get('APIX_AUTH_TOKEN') or 'd1185029eeb8fd261e630e3d796ca71928ad33b4')}
