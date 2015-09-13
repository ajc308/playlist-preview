import boto
import config
import random
import requests
import string
import tempfile

from boto.s3.key import Key
from celery_app import app, celery
from celery_tasks import wait
from flask import render_template, request
from playlists import get_all_genre_playlists
from pydub import AudioSegment


def process_sounds(sounds, file_format, bucket, s3_extension, sample_duration, fade_duration, sample_start):
    preview = AudioSegment.empty()

    tempfs = []
    for count, sound in enumerate(sounds, 1):
        print('\nDownloading {} of {}, {:.0f}% complete'.format(count, len(sounds), (count / len(sounds)) * 100))
        print(sound['name'], sound['url'])

        key = bucket.get_key(sound['id'] + s3_extension if s3_extension else sound['id'])
        tempf = tempfile.NamedTemporaryFile(prefix='/tmp/', suffix='.{}'.format(file_format))
        get_contents_to_file.delay(tempf.name, key)

        tempfs.append(tempf)

    wait(get_contents_to_file)

    for count, tempf in enumerate(tempfs, 1):
        print('\nProcessing {} of {}, {:.0f}% complete'.format(count, len(sounds), (count / len(sounds)) * 100))
        song = AudioSegment.from_file(tempf.name, format=file_format)

        #SAMPLE_DURATION second long sample starting at SAMPLE_START% into the song
        sample = song[int(sound['duration'] * sample_start): int(sound['duration'] * sample_start) + sample_duration * config.one_second]

        #Append sample with cross fade
        preview = preview.append(sample, crossfade=fade_duration * config.one_second) if preview else sample

    return preview


@celery.task(name="tasks.get_contents_to_file")
def get_contents_to_file(filename, key):
    key.get_contents_to_filename(filename)


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

    if playlist_url:
        playlist_id = playlist_url.split('/')[-1]

        if file_format not in config.audio_files.keys():
            raise ValueError('Unsupported file format. Supported: {}'.format(config.audio_files.keys()))

        bucket_name = config.audio_files[file_format]['aws_storage_bucket_name']
        conn = boto.connect_s3(config.AWS_ACCESS_KEY_ID, config.AWS_SECRET_ACCESS_KEY)
        bucket = conn.get_bucket(bucket_name)

        playlist_api_url = '{}/lists/sounds/{}'.format(config.base_url, playlist_id)
        print('Getting playlist: {}'.format(playlist_api_url))
        playlist_response = requests.get(playlist_api_url, headers=config.headers)
        playlist_sounds = playlist_response.json()['items']
        playlist_name = playlist_response.json()['name']

        sound_ids = [sound['id'] for sound in playlist_sounds[sound_start:sound_end]]
        s3_extension = config.audio_files[file_format]['s3_extension']

        print('Processing playlist: {}'.format(playlist_response.json()['name']))
        preview = process_sounds(playlist_sounds[sound_start:sound_end], file_format, bucket, s3_extension, sample_duration, fade_duration, sample_start)

        preview = preview.fade_in(duration=3 * config.one_second)
        preview = preview.fade_out(duration=3 * config.one_second)
        audio_file_name = 'playlist-preview/{}/{}.{}'.format(
            playlist_id,
            ''.join(random.choice(string.ascii_letters + string.digits) for i in range(5)),
            file_format
        )

        target_bucket = conn.get_bucket(config.target_bucket_name)
        target_key = Key(target_bucket)
        target_key.key = audio_file_name

        with tempfile.NamedTemporaryFile(prefix='/tmp/', suffix='.{}'.format(file_format)) as f:
            print('Exporting preview to temp file.')
            print(f.name)
            preview.export(f, format=file_format)
            print('Uploading preview to S3: {}'.format(audio_file_name))
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
    playlists = get_all_genre_playlists()
    app.run()



