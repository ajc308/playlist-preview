import boto
import os
import random
import requests
import string
import tempfile

from auth import get_apix_auth_headers
from boto.s3.key import Key
from flask import Flask, render_template, request
from playlists import get_all_genre_playlists
from pydub import AudioSegment
from urllib.request import urlopen

app = Flask(__name__)
app.config.update(
    DEBUG=True
)

AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')

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

playlists = get_all_genre_playlists()

def process_sounds(sounds, file_format, bucket, s3_extension, sample_duration, fade_duration, sample_start):
    preview = AudioSegment.empty()

    for count, sound in enumerate(sounds, 1):
        print('\nProcessing {} of {}, {:.0f}% complete'.format(count, len(sounds), (count / len(sounds)) * 100))
        print(sound['name'], sound['url'])

        key = bucket.get_key(sound['id'] + s3_extension if s3_extension else sound['id'])
        with urlopen(key.generate_url(expires_in=1000)) as f:
            song = AudioSegment.from_file(f, format=file_format)

            #SAMPLE_DURATION second long sample starting at SAMPLE_START% into the song
            sample = song[int(sound['duration'] * sample_start): int(sound['duration'] * sample_start) + sample_duration * one_second]

            #Append sample with cross fade
            preview = preview.append(sample, crossfade=fade_duration * one_second) if preview else sample

    return preview


@app.route('/')
def index():
    return render_template(
        'index.html',
        playlists=playlists
    )


@app.route('/', methods=['POST'])
def generate_playlist_preview():
    """
    sound_start: Set to 0 or None to start at first song in playlist
    sound_end: Set to None to go to last song in playlist
    """
    playlist_url = request.form['playlist_url'] or None
    file_format = request.form['file_format'] or 'mp4'
    sound_start = int(request.form['sound_start']) - 1 if request.form['sound_start'] else None
    sound_end = int(request.form['sound_end']) if request.form['sound_end'] else None
    fade_duration = int(request.form['fade_duration'])
    sample_duration = int(request.form['sample_duration'])
    sample_start = int(request.form['sample_start']) / 100
    print(playlist_url)
    if playlist_url:
        playlist_id = playlist_url.split('/')[-1]

        if file_format not in audio_files.keys():
            raise ValueError('Unsupported file format. Supported: {}'.format(audio_files.keys()))

        bucket_name = audio_files[file_format]['aws_storage_bucket_name']
        conn = boto.connect_s3(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
        bucket = conn.get_bucket(bucket_name)



        playlist_api_url = '{}/lists/sounds/{}'.format(base_url, playlist_id)
        print('Getting playlist: {}'.format(playlist_api_url))
        playlist_response = requests.get(playlist_api_url, headers=get_apix_auth_headers())
        playlist_sounds = playlist_response.json()['items']
        playlist_name = playlist_response.json()['name']

        sound_ids = [sound['id'] for sound in playlist_sounds[sound_start:sound_end]]
        s3_extension = audio_files[file_format]['s3_extension']

        print('Processing playlist: {}'.format(playlist_response.json()['name']))
        preview = process_sounds(playlist_sounds[sound_start:sound_end], file_format, bucket, s3_extension, sample_duration, fade_duration, sample_start)

        preview = preview.fade_in(duration=3 * one_second)
        preview = preview.fade_out(duration=3 * one_second)
        audio_file_name = 'playlist-preview/{}/{}.{}'.format(
            playlist_id,
            ''.join(random.choice(string.ascii_letters + string.digits) for i in range(5)),
            file_format
        )

        target_bucket_name = 'newport-homepage'
        target_bucket = conn.get_bucket(target_bucket_name)
        target_key = Key(target_bucket)
        target_key.key = audio_file_name

        print('Uploading preview to S3: {}'.format(audio_file_name))
        f = tempfile.NamedTemporaryFile(suffix='.{}'.format(file_format))
        preview.export(f, format=file_format)
        target_key.set_contents_from_file(f)

        return render_template(
            'index.html',
            audio_file_name=target_key.generate_url(expires_in=1000),
            playlist_url = playlist_url,
            file_format=file_format,
            sound_start=sound_start or 0,
            sound_end=sound_end or len(playlist_sounds),
            playlist_name = playlist_name,
            sound_ids = sound_ids,
            sample_duration=sample_duration,
            fade_duration=fade_duration,
            sample_start=sample_start*100,
            playlists=playlists
        )
    else:
        return render_template(
            'index.html',
            playlists=playlists
        )


if __name__ == '__main__':
    app.debug = True
    app.run()



