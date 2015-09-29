# Beatport Playlist Preview
Takes any Beatport.com playlist and generates a sample preview file of all the songs. 
Inspired by looking at long playlists and wondering if there was anything in them I would like, without having to scrub and skip.

#### Deploy:  
Install requirements: 
`$ pip install -r requirements.txt`  

Download and install Redis: http://redis.io/download

Run the following in 3 terminal sessions:  
1. `$ redis-server`  
2. `$ celery -A tasks.celery worker`  
3. `$ python tasks.py`

#### Options:  
- the playlist (based on the active ones on the homepage and genre pages)
- the file format (wav takes wayyy longer than mp4, so don't change that if you don't need to)
- sample start: what % into each song to start the sample (defaults to 25% in)
- sample duration: how long the sample of each track will be in the preview (default to 10 seconds)
- fade duration: how long of a crossfade between the tracks (default to 3 seconds)
- tracks to preview: if you only want to hear a preview of tracks #8 - #15, then put in those values



![Alt text](https://cloud.githubusercontent.com/assets/7770139/9838765/3c433572-5a33-11e5-9854-204d35e01ba6.png)
