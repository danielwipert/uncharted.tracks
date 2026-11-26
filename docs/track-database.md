# Track database

One master list of every candidate song, filled in by Python so you don't have to type it.

## How it fits together

| Layer | What it is | Who edits it |
| --- | --- | --- |
| `data/master.csv` | The master data set: every fact Python can find about each song | Python only. Never edit by hand; it's refreshed on every run. |
| Your working sheet | Your own sheet built from the master: rank, essay notes, outreach, fixes | You. Rearrange it however you like. Keep the `spotify_track_id` column. |
| `songs.yaml` | What the website is built from | Python merges the master + your sheet (your sheet wins). |

`spotify_track_id` is the key that links all three.

## Where each field comes from

1. **Spotify API** (step 1, built): title, artist, featured artists, genres, album, album type, release date and month, duration, explicit, ISRC, UPC, Spotify links, cover image, which playlists, date added.
2. **MusicBrainz** (step 2, next): record label, songwriters, hometown, year formed, Bandcamp and other links.
3. **Spotify public artist page** (step 3): monthly listeners.
4. **Research agents** (step 4): whatever is still blank.

Not available anywhere automatic: followers (dropped), popularity.

---

## Step 1: Spotify app (one time, about 5 minutes)

You need a Spotify **Premium** account for this.

1. Go to <https://developer.spotify.com/dashboard> and log in with your Spotify account.
2. Click **Create app**.
3. Fill in:
   - **App name:** `Uncharted Tracks puller`
   - **App description:** `Reads my playlists for my top 50 list`
   - **Redirect URI:** `http://127.0.0.1:8888/callback` (type it exactly, then click **Add**)
   - **Which API/SDKs are you planning to use?** tick **Web API**
4. Tick the box to agree to Spotify's terms, then click **Save**.
5. On the app page, click **Settings**. Copy the **Client ID**. (You don't need the Client secret.)
6. In the repo folder, make a copy of `.env.example` and name it `.env`. Open it and paste the Client ID after `SPOTIFY_CLIENT_ID=`. Save.

## Step 1: Run it (PowerShell, in the repo folder)

```powershell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python tools/pull_spotify.py --list
```

- The first time, your browser opens and asks you to log in to Spotify and allow the app. Click **Agree**. The tab then says "Spotify login done". Close it.
- The terminal lists your playlists with their IDs.

Then pull a playlist (use its name in quotes, or its ID):

```powershell
python tools/pull_spotify.py --playlist "Your playlist name"
```

Pull several at once by repeating `--playlist`. Songs on more than one playlist appear once, with both playlist names.

The result is `data/master.csv`. Open it in Excel or import it into Google Sheets as the "Master" tab.

### If something goes wrong

| Message | What to do |
| --- | --- |
| `No SPOTIFY_CLIENT_ID found` | The `.env` file is missing or the ID isn't pasted in. See step 6. |
| Browser says `INVALID_CLIENT: Invalid redirect URI` | The Redirect URI in your Spotify app doesn't match exactly. It must be `http://127.0.0.1:8888/callback`. |
| `403 Forbidden` | The Spotify account isn't Premium, or you're not logged in with the account that made the app. |
| `No playlist called ...` | Check the spelling with `--list`, or use the ID instead. |
| Songs from a playlist are missing | Spotify only lets the app read playlists you **own** or collaborate on. Copy a followed playlist's songs into one of your own. |

To log in again from scratch, delete `.spotify_token.json` and run the script.
