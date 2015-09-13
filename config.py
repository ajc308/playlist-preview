import os

base_url = 'https://apix.beatport.com'
one_second = 1000
audio_files = {
    'wav': {
        'file_format': 'wav',
        'aws_storage_bucket_name': 'beatport-prod-api-original',
        's3_extension': None
    },
    'mp4': {
        'file_format': 'mp4',
        'aws_storage_bucket_name': 'beatport-prod-api-encoded',
        's3_extension': '.mp4'
    }
}
target_bucket_name = 'newport-homepage'
headers = {'Authorization': 'Token {}'.format(os.environ.get('APIX_AUTH_TOKEN'))}

AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
