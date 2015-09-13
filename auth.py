import os
def get_apix_auth_headers():
    return {'Authorization': 'Token {}'.format(os.environ.get('APIX_AUTH_TOKEN'))}
