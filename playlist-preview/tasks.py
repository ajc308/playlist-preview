import boto
import os
import random
import requests
import string

from celery import Celery
from flask import Flask, render_template, request
from pydub import AudioSegment



app = Flask(__name__)
app.config.update(
    CELERY_BROKER_URL='redis://localhost:6379',
    CELERY_RESULT_BACKEND='redis://localhost:6379',
    CELERY_IMPORTS=('tasks', )
)

headers = {'Authorization': 'Token {}'.format(os.environ.get('APIX_AUTH_TOKEN'))}
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


def get_all_genre_playlists():
    genres_url = '{}/genres?has_list=True&sort_by=name'.format(base_url)
    genres = requests.get(genres_url, headers=headers).json()['items']

    all_playlists = get_playlists_from_page('{}/lists/homepage'.format(base_url))
    for genre in genres:
        all_playlists += get_playlists_from_page(genre['list'])

    return all_playlists


def get_playlists_from_page(url):
    print(url)
    response = requests.get(url, headers=headers).json()
    items = response['items']
    lists = []
    for item in items:
        if item['url'].split('/')[-2] == 'sounds':
            lists.append(
                {
                    'page': response['name'],
                    'name': item['name'],
                    'url': item['url']
                }
            )
        if item['url'].split('/')[-2] not in ['artists', 'sounds', 'promos', 'genres']:
            subitems = requests.get(item['url'], headers=headers).json()['items']
            for subitem in subitems:
                if subitem['url'].split('/')[-2] == 'sounds':
                    lists.append(
                        {
                            'page': response['name'],
                            'name': subitem['name'],
                            'url': subitem['url']
                        }
                    )
    return lists

def make_celery(app):
    c = Celery(app.import_name, broker=app.config['CELERY_BROKER_URL'])
    c.conf.update(app.config)
    TaskBase = c.Task
    class ContextTask(TaskBase):
        abstract = True
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)
    c.Task = ContextTask
    return c

celery = make_celery(app)
celery_inspector = celery.control.inspect()


def wait(function):
    task_count = get_task_count(function)
    while task_count:
        print('Processing waiting for {0} {1} celery tasks to complete'.format(
            task_count,
            function.__name__ if function else ''
        ))
        task_count = get_task_count(function)


def get_task_count(function):

    # reserved are not yet scheduled, scheduled are not yet active
    reserved = get_reserved_tasks().get(function.name, {})
    scheduled = get_scheduled_tasks().get(function.name, {})
    active = get_active_tasks().get(function.name, {})

    return len(reserved) + len(scheduled) + len(active)


def get_reserved_tasks():
    """ This function exists to be called from ipython as part of debugging efforts
    """
    reserved = organize_tasks(celery_inspector.reserved())
    return reserved


def get_scheduled_tasks():
    """ This function exists to be called from ipython as part of debugging efforts
    """
    scheduled = organize_tasks(celery_inspector.scheduled())
    return scheduled


def get_active_tasks():
    """ This function exists to be called from ipython as part of debugging efforts
    """
    active = organize_tasks(celery_inspector.active())
    return active


def organize_tasks(collection):
    """
    This gets all tasks for the given celery_inspector state
    :param collection: celery_inspector state (celery_inspector.active(), celery_inspector.scheduled(), etc.)
    :return: worker and ID#s for the collection
    """
    results = {}
    if collection:
        for worker, tasks in collection.items():
            for task in tasks:
                function = task['name']
                celery_id = task['id']
                celery_worker = task['hostname']
                if function not in results.keys():
                    results[function] = []
                data = {'celery_worker': celery_worker, 'celery_id': celery_id}
                results[function].append(data)
    return results


def download_sounds(sounds, bucket, s3_extension):

    for count, sound in enumerate(sounds, 1):
        print('\nDownloading {} of {}, {:.0f}% complete'.format(count, len(sounds), (count / len(sounds)) * 100))
        print(sound['name'], sound['url'])
        key_name = sound['id'] + s3_extension if s3_extension else sound['id']

        download_sound.delay(bucket, key_name)

    wait(download_sound)


def process_sounds(sounds, file_format, s3_extension, sample_duration, fade_duration, sample_start):
    preview = AudioSegment.empty()

    for count, sound in enumerate(sounds, 1):
        print('\nProcessing {} of {}, {:.0f}% complete'.format(count, len(sounds), (count / len(sounds)) * 100))
        print(sound['name'], sound['url'])
        key_name = sound['id'] + s3_extension if s3_extension else sound['id']

        song = AudioSegment.from_file(('static/audio_files/songs/{}'.format(key_name)), format=file_format)

        #SAMPLE_DURATION second long sample starting at SAMPLE_START% into the song
        sample = song[int(sound['duration'] * sample_start): int(sound['duration'] * sample_start) + sample_duration * one_second]

        #Append sample with cross fade
        preview = preview.append(sample, crossfade=fade_duration * one_second) if preview else sample

        os.remove('static/audio_files/songs/{}'.format(key_name))

    return preview


@celery.task(name="tasks.download_sound")
def download_sound(bucket, key_name):
    bucket.get_key(key_name).get_contents_to_filename('static/audio_files/songs/{}'.format(key_name))


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
        playlist_response = requests.get(playlist_api_url, headers=headers)
        playlist_sounds = playlist_response.json()['items']
        playlist_name = playlist_response.json()['name']

        sound_ids = [sound['id'] for sound in playlist_sounds[sound_start:sound_end]]
        s3_extension = audio_files[file_format]['s3_extension']

        print('Processing playlist: {}'.format(playlist_response.json()['name']))
        download_sounds(playlist_sounds[sound_start:sound_end], bucket, s3_extension)
        preview = process_sounds(playlist_sounds[sound_start:sound_end], file_format, s3_extension, sample_duration, fade_duration, sample_start)

        preview = preview.fade_in(duration=3 * one_second)
        preview = preview.fade_out(duration=3 * one_second)
        audio_file_name = 'audio_files/previews/{}_{}.{}'.format(
            playlist_id,
            ''.join(random.choice(string.ascii_letters + string.digits) for i in range(5)),
            file_format
        )
        preview.export('static/{}'.format(audio_file_name), format=file_format)

        return render_template(
            'index.html',
            audio_file_name=audio_file_name,
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



