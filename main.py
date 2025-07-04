from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
from dotenv import load_dotenv

load_dotenv()

SPOTIPY_CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
SPOTIPY_CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")
SPOTIPY_REDIRECT_URI = os.getenv("SPOTIPY_REDIRECT_URI")

SCOPE = "playlist-modify-public playlist-modify-private"

app = FastAPI()

class PlaylistRequest(BaseModel):
    playlist_name: str
    songs: list[str]

def create_spotify_client():
    return spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=SPOTIPY_CLIENT_ID,
        client_secret=SPOTIPY_CLIENT_SECRET,
        redirect_uri=SPOTIPY_REDIRECT_URI,
        scope=SCOPE,
        cache_path=".cache-spotify"
    ))

def get_existing_playlist_id(sp, playlist_name: str) -> str | None:
    """Check user's existing playlists for a match"""
    offset = 0
    limit = 50
    while True:
        playlists = sp.current_user_playlists(limit=limit, offset=offset)
        for playlist in playlists["items"]:
            if playlist["name"].lower() == playlist_name.lower():
                return playlist["id"]
        if playlists["next"]:
            offset += limit
        else:
            break
    return None

@app.post("/create-or-update-playlist")
def create_or_update_playlist(request: PlaylistRequest):
    try:
        sp = create_spotify_client()
        user_id = sp.current_user()["id"]

        # Search for all songs
        track_uris = []
        for song in request.songs:
            result = sp.search(q=song, type='track', limit=1)
            items = result['tracks']['items']
            if items:
                track_uris.append(items[0]['uri'])

        if not track_uris:
            raise HTTPException(status_code=404, detail="No valid tracks found")

        # Check if playlist exists
        playlist_id = get_existing_playlist_id(sp, request.playlist_name)

        if playlist_id:
            # Add songs to existing playlist
            sp.playlist_add_items(playlist_id, track_uris)
            playlist = sp.playlist(playlist_id)
            message = "Tracks added to existing playlist"
        else:
            # Create new playlist and add songs
            playlist = sp.user_playlist_create(user=user_id, name=request.playlist_name, public=True)
            sp.playlist_add_items(playlist['id'], track_uris)
            message = "New playlist created successfully"

        return {
            "message": message,
            "playlist_url": playlist['external_urls']['spotify']
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
