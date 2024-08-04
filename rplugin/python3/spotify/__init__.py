import time
from typing import OrderedDict
from urllib.parse import urlencode
import os
import pynvim

from . import bottle
from .spotify_api import SpotifyApi
import multiprocessing
import random
import requests
import json
import distutils.spawn
import platform

scopes = ["user-read-playback-state", "user-modify-playback-state", "user-read-currently-playing", "playlist-read-private", "playlist-read-collaborative", "user-library-read"]

def jump(state, client_id):
    def _jump():
        q = OrderedDict(
            response_type="code",
            client_id=client_id,
            scope=" ".join(scopes),
            redirect_uri="http://localhost:8080/auth",
            state=state
        )
        queryString = urlencode(q)
        bottle.redirect(f"https://accounts.spotify.com/authorize?{queryString}")
    return _jump

def auth(value, state):
    def _auth():
        try:
            code = bottle.request.query['code']
            s = bottle.request.query['state']
            if s != state:
                return f"Invalid state: {s} != {state}"
            value.value = code
        except Exception as e:
            return e
        return "Authenticated!"
    return _auth

def startServer(value, client_id):
    b = bottle.Bottle()
    bottle.debug(True)
    state = "".join(random.choices("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=16))
    b.route('/auth', 'GET', auth(value, state))
    b.route('/', 'GET', jump(state, client_id))
    b.run(host='localhost', port=8080)

@pynvim.plugin
class SpotifyPlugin:
    nvim: pynvim.Nvim
    api: SpotifyApi | None = None

    client_id: str | None = None
    client_secret: str | None = None

    def __init__(self, nvim):
        self.nvim = nvim
        if 'spotify_client_id' in self.nvim.vars and 'spotify_client_secret' in self.nvim.vars:
            self.client_id = self.nvim.vars['spotify_client_id']
            self.client_secret = self.nvim.vars['spotify_client_secret']
            self.api = SpotifyApi(self.client_id, self.client_secret)
        else:
            self.nvim.command('echo "Please set client_id and client_secret"')
            return

    def _request_access_token(self, code):
        if self.client_id is None or self.client_secret is None or self.api is None:
            self.nvim.command('echo "Please set client_id and client_secret"')
            return (None, None, None, None)
        
        return self.api.authenticate(code)

    def _check_auth(self) -> SpotifyApi | None:
        if self.api is None:
            self.nvim.command('echo "Please set client_id and client_secret"')
            return None

        if self.api.access_token is None:
            self.api.load_user()
            if self.api.access_token is None:
                self.nvim.command('echo "Not authenticated yet, please run :SpotifyAuth first"')
                return None
        return self.api

    @pynvim.command('SpotifyAuth')
    def auth(self):
        api = self._check_auth()
        if api is None:
            self.nvim.command('echo "Please set client_id and client_secret"')
            return;

        value = multiprocessing.Manager().Value('s', None)
        proc = multiprocessing.Process(target=startServer, args=(value, self.client_id), daemon=True)
        proc.start()

        if platform.system() == 'Windows':
            os.system('start http://localhost:8080')
        elif distutils.spawn.find_executable('xdg-open'):
            os.system('xdg-open http://localhost:8080')
        elif distutils.spawn.find_executable('open'):
            os.system('open http://localhost:8080')
        else:
            self.nvim.command('echo "Could not open browser, please open it manually and navigate to http://localhost:8080"')
            return

        result = None
        while result == None:
            time.sleep(1)
            result = value.get()
            pass
        proc.kill()
        self.nvim.command('echo "Getting access token..."')
        api.authenticate(result)
        self.nvim.command(f'echo "Authenticated!"')

    @pynvim.command("SpotifyPlaylist")
    def getPlaylists(self):
        api = self._check_auth()
        if api is None:
            return

        names = api.get_playlists()
        names.append({ "name": "Liked Songs", "uri": "__liked__", "id": "__liked__" })

        self.nvim.exec_lua("require('spotify').showPlaylists(...)", names)
        pass

    def _get_liked_songs(self):
        api = self._check_auth()
        if api is None:
            return

        return api.get_liked_songs()

    def _add_to_queue(self, uri):
        api = self._check_auth()
        if api is None:
            return

        api.add_to_queue(uri)

    @pynvim.command("SpotifyPlay", nargs="*")
    def play(self, args):
        api = self._check_auth()
        if api is None:
            return

        if len(args) == 0:
            api.play()
            self.nvim.command(f'echo "resume playing"')
            return

        uri = args[0]
        if uri == "__liked__":
            uris = self._get_liked_songs()
            api.play(uris)
        elif uri.startswith("spotify:track:"):
            self._add_to_queue(uri)
        else:
            self.nvim.command(f'echo "Playing uri: {uri}"')
            api.play(uri)

    @pynvim.command("SpotifyPause")
    def pause(self):
        api = self._check_auth()
        if api is None:
            return
        
        api.pause()

    @pynvim.function("SpotifyGetPlaylistTracks", sync=True)
    def get_playlist_tracks(self, args):
        api = self._check_auth()
        if api is None:
            raise Exception("Not authenticated yet, please run :SpotifyAuth first")

        data = api.get_playlist_tracks(args[0])
        tracks = [track['track'] for track in data]

        return tracks

