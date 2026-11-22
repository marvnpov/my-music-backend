from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from ytmusicapi import YTMusic
import yt_dlp
import httpx

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ytm = YTMusic()

@app.get("/")
def health_check():
    return {"status": "online"}

@app.get("/api/home")
def get_home():
    charts = ytm.get_charts(country="ZZ")
    moods = ytm.get_mood_categories()
    return {
        "top_songs": charts.get("songs", {}).get("items", [])[:15],
        "moods": moods
    }

@app.get("/api/search")
def search_songs(q: str):
    results = ytm.search(q, filter="songs", limit=20)
    formatted = []
    for item in results:
        thumbnails = item.get("thumbnails", [])
        cover = thumbnails[-1]["url"] if thumbnails else ""
        if "w120-h120" in cover:
            cover = cover.replace("w120-h120", "w544-h544")
            
        artists = ", ".join([a["name"] for a in item.get("artists", [])])
        formatted.append({
            "videoId": item.get("videoId"),
            "title": item.get("title"),
            "artist": artists,
            "album": item.get("album", {}).get("name") if item.get("album") else "Single",
            "duration": item.get("duration", "0:00"),
            "cover": cover
        })
    return {"results": formatted}

@app.get("/api/stream/{video_id}")
def get_audio_stream(video_id: str):
    url = f"https://music.youtube.com/watch?v={video_id}"
    ydl_opts = {
        "format": "bestaudio[ext=m4a]/bestaudio",
        "quiet": True,
        "no_warnings": True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                "audioUrl": info["url"],
                "duration": info.get("duration", 0)
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/lyrics")
async def get_synced_lyrics(title: str, artist: str):
    async with httpx.AsyncClient() as client:
        res = await client.get(
            "https://lrclib.net/api/get",
            params={"track_name": title, "artist_name": artist}
        )
        if res.status_code == 200:
            data = res.json()
            return {
                "syncedLyrics": data.get("syncedLyrics"),
                "plainLyrics": data.get("plainLyrics")
            }
        return {"syncedLyrics": None, "plainLyrics": "Lyrics not found."}
