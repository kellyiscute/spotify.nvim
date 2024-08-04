import time
from typing import OrderedDict
from urllib.parse import urlencode
from imp import os
import pynvim
from . import bottle
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
    userId: str | None = None
    access_token: str | None = None
    token_type: str | None = None
    expires_in: int | None = None
    refresh_token: str | None = None

    client_id: str | None = None
    client_secret: str | None = None

    def __init__(self, nvim):
        self.nvim = nvim
        if 'spotify_client_id' in self.nvim.vars and 'spotify_client_secret' in self.nvim.vars:
            self.client_id = self.nvim.vars['spotify_client_id']
            self.client_secret = self.nvim.vars['spotify_client_secret']
        else:
            self.nvim.command('echo "Please set client_id and client_secret"')
            return

    def _request_access_token(self, code):
        session = requests.Session()

        if self.client_id is None or self.client_secret is None:
            self.nvim.command('echo "Please set client_id and client_secret"')
            return (None, None, None, None)

        session.auth = (self.client_id, self.client_secret)
        res = session.post("https://accounts.spotify.com/api/token", data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": "http://localhost:8080/auth",
        }, headers={
            "Content-Type": "application/x-www-form-urlencoded",
        })
        data = res.json()
        access_token = data['access_token']
        token_type = data['token_type']
        expires_in = data['expires_in']
        refresh_token = data['refresh_token']

        return (access_token, token_type, expires_in, refresh_token)

    def _get_config_path(self):
        script_path = __file__.split('/')
        script_path.pop()
        path = os.path.join("/".join(script_path), 'access_token.json')
        return path

    def _refresh_access_token(self):
        if self.client_id is None or self.client_secret is None:
            self.nvim.command('echo "Please set client_id and client_secret"')
            return
        session = requests.Session()
        session.auth = (self.client_id, self.client_secret)

        res = session.post("https://accounts.spotify.com/api/token", data={
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token
        }, headers={
            "Content-Type": "application/x-www-form-urlencoded"
        })
        data = res.json()
        self.access_token = data['access_token']

    def _save_user(self):
        try:
            f = open(self._get_config_path(), 'w')
            json.dump({
                "access_token": self.access_token,
                "token_type": self.token_type,
                "expires_in": self.expires_in,
                "refresh_token": self.refresh_token,
                "user_id": self.userId
            }, f)
            f.flush()
            f.close()
        except FileNotFoundError:
            self.nvim.command('echo "Failed to save access token"')
            return

    def _load_user(self):
        try:
            f = open(self._get_config_path(), 'r')
            data = json.load(f)
            self.access_token = data['access_token']
            self.token_type = data['token_type']
            self.expires_in = data['expires_in']
            self.refresh_token = data['refresh_token']
            self.userId = data['user_id']
            f.close()
        except FileNotFoundError:
            self.nvim.command('echo "Not authenticated yet, please run :SpotifyAuth first"')
        self._refresh_access_token()

    def _check_auth(self):
        if self.access_token is None:
            self._load_user()
            if self.access_token is None:
                self.nvim.command('echo "Not authenticated yet, please run :SpotifyAuth first"')
                return False
        return True

    @pynvim.command('SpotifyAuth')
    def auth(self):
        if self.client_id is None or self.client_secret is None:
            self.nvim.command('echo "Please set client_id and client_secret"')
            return

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
        self.nvim.command(f'echo "Authenticated!"')
        (access_token, token_type, expires_in, refresh_token) = self._request_access_token(result)
        self.access_token = access_token
        self.token_type = token_type
        self.expires_in = expires_in
        self.refresh_token = refresh_token
        userId = self._get_profile()
        self.userId = userId
        self._save_user()

    def _get_profile(self):
        res = requests.get("https://api.spotify.com/v1/me", headers={
            "Authorization": f"Bearer {self.access_token}"
        })
        data = res.json()
        return data['id']

    @pynvim.command("SpotifyPlaylist")
    def getPlaylists(self):
        if not self._check_auth():
            return

        res = requests.get(f"https://api.spotify.com/v1/users/{self.userId}/playlists", headers={"Authorization": f"Bearer {self.access_token}"})
        data = res.json()
        playlists = data['items']
        names = [{ "name": playlist['name'], "uri": playlist['uri'], "id": playlist['id'] } for playlist in playlists]
        names.append({ "name": "Liked Songs", "uri": "__liked__", "id": "__liked__" })

        self.nvim.exec_lua("require('spotify').showPlaylists(...)", names)
        pass

    def _get_liked_songs(self):
        if not self._check_auth():
            return

        res = requests.get("https://api.spotify.com/v1/me/tracks", headers={ "Authorization": f"Bearer {self.access_token}" })
        data = res.json()
        uris = [track['track']['uri'] for track in data['items']]

        return uris

    @pynvim.command("SpotifyPlay", nargs="*")
    def play(self, args):
        if not self._check_auth():
            return

        if len(args) == 0:
            requests.put("https://api.spotify.com/v1/me/player/play", headers={ "Authorization": f"Bearer {self.access_token}" })
            return

        uri = args[0]
        if uri == "__liked__":
            uris = self._get_liked_songs()
            requests.put("https://api.spotify.com/v1/me/player/play", headers={ "Authorization": f"Bearer {self.access_token}" }, json={ "uris": uris })
        else:
            requests.put("https://api.spotify.com/v1/me/player/play", headers={ "Authorization": f"Bearer {self.access_token}" }, json={ "context_uri": uri })

    @pynvim.command("SpotifyPause")
    def pause(self):
        if not self._check_auth():
            return

        requests.put("https://api.spotify.com/v1/me/player/pause", headers={ "Authorization": f"Bearer {self.access_token}" })

