# Beatport Playlist Preview
Takes any Beatport.com playlist and generates a sample preview file of all the songs. 
Inspired by looking at long playlists and wondering if there was anything in them I would like, without having to scrub and skip.

#### Options:
- the playlist (based on the active ones on the homepage and genre pages)
- the file format (wav takes wayyy longer than mp4, so don't change that if you don't need to)
- sample start: what % into each song to start the sample (defaults to 25% in)
- sample duration: how long the sample of each track will be in the preview (default to 10 seconds)
- fade duration: how long of a crossfade between the tracks (default to 3 seconds)
- tracks to preview: if you only want to hear a preview of tracks #8 - #15, then put in those values

#### Deploy locally
Install dependencies in requirements.txt and redis, then run the following in 3 terminal sessions:  

1. `$ redis-server`  
2. `$ celery -A tasks.celery worker`  
3. `$ python tasks.py`