from functools import cache
import requests
import json
import os
import time
import math

class SpotifyApi:
    client_id: str
    client_secret: str

    userId: str | None = None
    access_token: str | None = None
    token_type: str | None = None
    expires_in: int | None = None
    expires_at: int | None = None
    refresh_token: str | None = None

    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret

    @cache
    def _get_config_path(self):
        script_path = __file__.split('/')
        script_path.pop()
        path = os.path.join("/".join(script_path), 'access_token.json')
        return path

    def load_user(self):
        f = open(self._get_config_path(), 'r')
        data = json.load(f)
        self.access_token = data['access_token']
        self.token_type = data['token_type']
        self.expires_in = data['expires_in']
        self.refresh_token = data['refresh_token']
        self.userId = data['user_id']
        self.expires_at = 0
        f.close()
        self.refresh_access_token()

    def save_user(self):
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

    def authenticate(self, code):
        session = requests.Session()
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

        self.access_token = access_token
        self.token_type = token_type
        self.expires_in = expires_in
        self.expires_at = math.floor(time.time() + expires_in)
        self.refresh_token = refresh_token
        userId = self._get_profile()
        self.userId = userId

        self.save_user()

    def refresh_access_token(self):
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
        self.expires_at = math.floor(time.time() + data['expires_in'])
        self.save_user()

    def _check_expiration(self):
        if self.expires_at is None:
            return
        if self.expires_at - 60 < time.time():
            self.refresh_access_token()

    def _get_profile(self):
        self._check_expiration()
        res = requests.get("https://api.spotify.com/v1/me", headers={
            "Authorization": f"Bearer {self.access_token}"
        })
        data = res.json()
        return data['id']

    def get_playlists(self):
        self._check_expiration()
        res = requests.get(f"https://api.spotify.com/v1/users/{self.userId}/playlists", headers={"Authorization": f"Bearer {self.access_token}"}, params={ "limit": 50 })
        data = res.json()
        playlists = data['items']
        names = [{ "name": playlist['name'], "uri": playlist['uri'], "id": playlist['id'] } for playlist in playlists]

        return names
    
    def get_liked_songs(self):
        self._check_expiration()
        res = requests.get("https://api.spotify.com/v1/me/tracks", headers={ "Authorization": f"Bearer {self.access_token}" })
        data = res.json()
        uris = [track['track'] for track in data['items']]

        return uris

    def add_to_queue(self, uri):
        self._check_expiration()
        requests.post("https://api.spotify.com/v1/me/player/queue", headers={ "Authorization": f"Bearer {self.access_token}" }, params={ "uri": uri })

    def play(self, uri: str | list[str] | None = None, offset: str | None = None):
        self._check_expiration()
        if uri is None:
            requests.put("https://api.spotify.com/v1/me/player/play", headers={ "Authorization": f"Bearer {self.access_token}" })
        if type(uri) is str:
            if offset is None:
                requests.put("https://api.spotify.com/v1/me/player/play", headers={ "Authorization": f"Bearer {self.access_token}" }, json={ "context_uri": uri })
            else:
                requests.put("https://api.spotify.com/v1/me/player/play", headers={ "Authorization": f"Bearer {self.access_token}" }, json={ "context_uri": uri, "offset": { "uri": offset } })
        else:
            requests.put("https://api.spotify.com/v1/me/player/play", headers={ "Authorization": f"Bearer {self.access_token}" }, json={ "uris": uri })

    def pause(self):
        self._check_expiration()
        requests.put("https://api.spotify.com/v1/me/player/pause", headers={ "Authorization": f"Bearer {self.access_token}" })

    def get_playlist_tracks(self, playlist_id: str):
        self._check_expiration()
        res = requests.get(f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks", headers={ "Authorization": f"Bearer {self.access_token}" })
        data = res.json()
        
        return data['items']
