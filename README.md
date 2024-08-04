# Spotify.nvim
A Spotify plugin for neovim

## Requirements
### Neovim
1. Neovim (Of course)
2. Python3 provider
3. Telescope

### Python
1. requests
2. pynvim
3. distutils (in case you don't have it)


## Getting Started
### Acquire Spotify API Credentials
1. Goto [Spotify Developer](https://developer.spotify.com) and log in.
2. Create a new app and name it to whatever you feel like.
3. Add `http://localhost:8080/auth` to `Redirect URIs`.
4. Select `Web API` under `Which API/SDKs are you planning to use?`.
5. Save.
6. Goto `User Management` tab of your app.
7. Add your Spotify account's email. (**Very important!** You won't be able to authenticate if you skip this)
8. Go back to `Basic Information` tab. Click on `View client secret`.
9. Record `Client ID` and `Client Secret` for the next steps

### Setup
1. Set `g:spotify_client_id` to the `Client ID` you just ~~hopefully~~ copied.
2. Set `g:spotify_client_secret` to the `Client Secret` you just copied.
3. Restart or reload your configuration.
4. Use `:SpotifyAuth` to authenticate.
5. Hopefully, now you are all set!

## Usage
This plugin currently supports the following commands:

### SpotifyPlay
resume playing, or, if you would like, pass in a Spotify URI to play the corresponding thing, or use `__liked__` to play your saved playlist.

### SpotifyPause
pause - of course

### SpotifyPlaylist
List all your playlists using Telescope. Use `<CR>` to play.
