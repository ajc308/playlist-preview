import os
import requests

from auth import get_apix_auth_headers

base_url = 'https://apix.beatport.com'

def get_playlists_from_page(url):
    print(url)
    response = requests.get(url, headers=get_apix_auth_headers()).json()
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
            subitems = requests.get(item['url'], headers=get_apix_auth_headers()).json()['items']
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


def get_all_genre_playlists():
    genres_url = '{}/genres?has_list=True&sort_by=name'.format(base_url)
    genres = requests.get(genres_url, headers=get_apix_auth_headers()).json()['items']

    all_playlists = get_playlists_from_page('{}/lists/homepage'.format(base_url))
    for genre in genres:
        all_playlists += get_playlists_from_page(genre['list'])

    return all_playlists