import os
import pandas as pd
import uvicorn
from fastapi import FastAPI, UploadFile
from fastapi.responses import RedirectResponse
from motor.motor_asyncio import AsyncIOMotorClient
from config import settings
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from bson.objectid import ObjectId
from enum import Enum
import user
import json
import requests
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

DB_URL = os.environ.get("DB_CONNECTION_STRING")

# Enum
class PitchEnum(str, Enum):
    HIGH = "high",
    MODERATE = "moderate",
    LOW = "low"

# Models
class Song(BaseModel):
    song_id: str
    song_name: str
    artist_name: str
    album_name: str
    date_added: datetime

class Playlist(BaseModel):
    playlist_id: Optional[str] = None
    playlist_name: str
    songs: List[Song]
    is_deleted: bool
    date_created: datetime 

class User(BaseModel):
    name: str
    username: str
    email: str
    hash_pw: str
    to_go_playlist: Optional[str] = None
    playlists: List[Playlist]
    blacklist: List[Song]
    song_recommender: Optional[UploadFile] = None
    age: int
    pitch: PitchEnum 
    
class SpotifyAuth(BaseModel):
    redirectUri: str
    clientId: str
    clientSecret: str

# Create the FastAPP app
app = FastAPI()

origins = [
    "http://localhost",
    "http://localhost:8080",
    "http://localhost:3000",
    "https://jamz903.github.io/karaMonke"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Establish a connection to MongoDB
client = MongoClient(DB_URL)
db = client["karamonke"]

# Startup Event
@app.on_event("startup")
async def startup_db_client():
    app.mongodb_client = AsyncIOMotorClient(settings.DB_URL)
    app.mongodb = app.mongodb_client[settings.DB_NAME]

# Shutdown Event
@app.on_event("shutdown")
async def shutdown_db_client():
    app.mongodb_client.close()

# Root
@app.get("/")
async def root():
    return { "endpoints": {
        "users": "/users",
        "playlists": "/users/{user_id}/playlists",
        "songs": "/users/{user_id}/playlists/{playlist_id}/songs"
    } }
   
@app.get("/users/{user_id}")
async def get_user(user_id: str):
    try:
        collection = db["users"]
        user = collection.find_one({"_id": ObjectId(user_id)})
        if user:
            print(f"User: {user}")
            return User(**user)
        else:
            print(f"Document not found for user_id: {user_id}")
            return
    except PyMongoError as e:
        print(f"Error occurred: {str(e)}")
    return

@app.post("/users/")
async def create_user(obj: User):
    try:
        collection = db["users"]
        new_user = User(**{
            "name": obj.name,
            "username": obj.username,
            "email": obj.email,
            "hash_pw": obj.hash_pw,
            "to_go_playlist": obj.to_go_playlist,
            "playlists": [],
            "blacklist": [],
            "age": obj.age,
            "pitch": obj.pitch
        })
        res = collection.insert_one(new_user)
        user_id = res.inserted_id
        print(f"User inserted with user_id: {user_id}")
        return str(user_id)
    except PyMongoError as e:
        print(f"Error occurred: {str(e)}")
    return

@app.delete("/users/{user_id}")
async def delete_user(user_id: str):
    try:
        collection = db["users"]
        filter = {"_id": ObjectId(user_id)}
        res = collection.delete_one(filter)
        if res.deleted_count == 1:
            print(f"Successfully deleted user with user_id: {user_id}")
        else:   
            print(f"Document not found or deletion failed for user_id: {user_id}")
        return
    except PyMongoError as e:
        print(f"Error occurred: {str(e)}")
    return

# Playlists
@app.get("/users/{user_id}/playlists/{playlist_id}")
async def get_playlist(user_id, playlist_name):
    try:
        collection = db["users"]
        user = User(**collection.find_one({"_id": ObjectId(user_id)}))
        res = None
        for playlist in user.playlists:
            if playlist.playlist_name == playlist_name:
                res = playlist
        if res:
            print(f"Playlist: {res}")
            return res
        else:
            print(f"Document not found for playlist_id: {playlist_name}")
            return
    except PyMongoError as e:
        print(f"Error occurred: {str(e)}")
    return 

@app.post("/users/{user_id}/playlists/")
async def create_playlist(user_id, obj: Playlist):
    try:
        collection = db["users"]
        new_playlist = Playlist(**{
            "playlist_name": obj.playlist_name,
            "songs": [song.dict() for song in obj.songs],
            "is_deleted": obj.is_deleted,
            "date_created": obj.date_created
        })
        peek = User(**collection.find_one({"_id": ObjectId(user_id)}))
        for pl in peek.playlists:
            if pl.playlist_name == new_playlist.playlist_name:
                print(f"Please specify an unused name for your new playlist!")
                return

        res = collection.update_one(
            {"_id": ObjectId(user_id)}, 
            {"$push": {"playlists": new_playlist}},
            upsert=True
        )
        if res.modified_count > 0:
            print(f"Playlist inserted with playlist_name: {new_playlist.playlist_name}")
        else:
            print(f"Playlist insertion failed...")            
        return str(new_playlist.playlist_name)
    except PyMongoError as e:
        print(f"Error occurred: {str(e)}")
    return

@app.delete("/users/{user_id}/playlists/{playlist_id}")
async def delete_playlist(user_id, playlist_name):
    try:
        collection = db["users"]
        res = collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$pull": {"playlists": {"playlist_name": playlist_name}}}
        )
        print(f"Modified count: {res.modified_count}")
    except PyMongoError as e:
        print(f"Error occurred: {str(e)}")
    return

# Songs
@app.get("/users/{user_id}")
async def get_song(user_id):
    return 

@app.post("/users/{user_id}/playlist/{playlist_id}/songs/")
async def create_song(user_id, playlist_name, obj: Song):
    try:
        collection = db["songs"]
        new_song = {
            "song_id": obj.song_id,
            "song_name": obj.song_name,
            "artist_name": obj.artist_name,
            "album_name": obj.album_name,
            "date_added": datetime.now()
        }
        res = collection.update_one(
            {"_id": ObjectId(user_id), "playlists.playlist_name": playlist_name},
            {"$push": {"playlists.$.songs": new_song}}
        )
        if res.modified_count > 0:
            print(f"Song inserted with song_name: {obj.song_name}")
        else:
            print(f"Song insertion failed...")  
    except PyMongoError as e:
        print(f"Error occurred: {str(e)}")
    return

@app.delete("/users/{user_id}/playlists/{playlist_id}/songs/{song_id}")
async def delete_song(user_id, playlist_id, obj):
    return 

cid = os.getenv("CLIENT_ID") 
client_secret = os.getenv("CLIENT_SECRET")
from requests import post, get
import base64
def get_token():
    auth_string = cid + ":" + client_secret
    auth_bytes = auth_string.encode("utf-8")
    auth_base64 = str(base64.b64encode(auth_bytes), "utf-8")
    
    url = 'https://accounts.spotify.com/api/token'
    headers = {
        "Authorization": "Basic " + auth_base64,
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {"grant_type": "client_credentials"}
    result = post(url, headers=headers, data=data)
    json_result = json.loads(result.content)
    token = json_result["access_token"]
    return token

def get_auth_header(token):
    return {"Authorization": "Bearer " + token}

def get_track(token, id):
    url = "https://api.spotify.com/v1/tracks/{}".format(id)
    headers = get_auth_header(token)
    result = get(url, headers=headers)
    json_result = json.loads(result.content)
    # print(json_result)
    return json_result

def get_audio_features(token, id):
    url = "https://api.spotify.com/v1/audio-features/{}".format(id)
    headers = get_auth_header(token)
    result = get(url, headers=headers)
    json_result = json.loads(result.content)
    # print(json_result)
    return json_result

@app.get("/test")
async def test():
    token = get_token()
    get_track(token, "11dFghVXANMlKmJXsNCbNl")
    get_audio_features(token, "11dFghVXANMlKmJXsNCbNl")
    return "test"

class Tracks(BaseModel):
    ids: List[str]
    
def get_df(ids):
    output_df = None
    token = get_token()
    for id in ids:
        track = get_track(token, id) # will return a dictionary
        audio_features = get_audio_features(token, id)
        
        track_dict = dict()
        track_dict['name'] = [track['name']]
        track_dict['release_date'] = [track['album']['release_date']]
        track_dict['popularity'] = [track['popularity']]
        track_dict['artists'] = [track['artists'][0]['name']]
        track_dict['explicit'] = [int(track['explicit'])]

        track_df = pd.DataFrame(track_dict)

        for keys, values in audio_features.items():
            audio_features[keys] = [values]
            audio_features_df = pd.DataFrame(data=audio_features)

        req_df = pd.concat([track_df, audio_features_df], axis=1)

        if output_df is None:
            output_df = req_df

        else:
            output_df = pd.concat([output_df, req_df], axis=0)

    return output_df 

@app.post("/users/songs/suggested")
async def get_suggested_songs(tracks: Tracks):
    ids = tracks.ids
    df = get_df(ids)
    cur_user = user.User(df)

    # Get song recommendations
    songs = cur_user.get_recommendations()
    res = json.loads(json.dumps(songs))
    return res
    # songs.to_json("songs.json")
    # f = open("songs.json")
    # json_data = json.load(f)

    # return json_data

# @app.post("/users/songs/suggested")
# async def get_suggested_songs(tracks: Tracks):
#     dataset = pd.read_csv('Test_data.csv', index_col=0)
#     ids = [44571, 94262, 90148, 573852, 75443,
#        218969, 87025, 85416, 112607, 85328,
#        88707, 357201, 112391, 112383, 85053]
#     song_infos = dataset.loc[ids]
#     cur_user = user.User(song_infos)

#     # Get song recommendations
#     songs = cur_user.get_recommendations()
#     songs.to_json("songs.json")
#     f = open("songs.json")
#     json_data = json.load(f)

#     return json_data
    
    


# Define our main function so we can easily run the server
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        reload=settings.DEBUG_MODE,
        port=settings.PORT,
    )