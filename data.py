import spotipy
import json
from spotipy.oauth2 import SpotifyClientCredentials

with open('config/config.json') as config_file:
    config = json.load(config_file)

client_id = config['Api_Keys']['Spotify']['client-id']
client_secret = config['Api_Keys']['Spotify']['client-secret']

client_credentials_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)


def meta(name):
    results = sp.search(q=name, type="track")
    song = results['tracks']['items'][0]
    title = song['name']
    artist = song['artists'][0]['name']
    album = song['album']['name']
    duration_ms = song['duration_ms']
    release_date = song['album']['release_date']

    data = [title, artist, album, duration_ms, release_date]

    return data
