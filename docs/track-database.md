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
2. **MusicBrainz** (step 2, built): record label, songwriters, hometown, year formed, Bandcamp and other links.
   **Genius** (step 2b, built): songwriters, producers, credits, studio, Apple Music and YouTube links.
3. **Spotify public artist page** (step 3): monthly listeners.
4. **Research agents** (step 4): whatever is still blank.

Not available anywhere automatic: followers (dropped), popularity.

Everything runs in the cloud (GitHub Actions). Nothing runs on your computer.

---

## Step 1: Add your Spotify keys to GitHub (one time)

You need your Spotify app's **Client ID** and **Client Secret** (developer.spotify.com/dashboard → your app → **Settings**).

1. Open <https://github.com/danielwipert/uncharted.tracks/settings/secrets/actions> in a browser. (On a phone, use the browser, not the GitHub app, and switch to "Desktop site" if the page looks cut off.)
2. Click **New repository secret**.
3. **Name:** `SPOTIFY_CLIENT_ID` · **Secret:** paste your Client ID · click **Add secret**.
4. Click **New repository secret** again.
5. **Name:** `SPOTIFY_CLIENT_SECRET` · **Secret:** paste your Client Secret · click **Add secret**.

Secrets are hidden: nobody (including you) can read them back, and they never show in the run logs.

## Step 1: Run the test

1. Open the **Actions** tab: <https://github.com/danielwipert/uncharted.tracks/actions>
2. Click **Pull from Spotify** on the left.
3. Click **Run workflow**. In the box, paste a playlist link (in Spotify: playlist → ⋯ → Share → Copy link). Several links: separate with commas.
4. Click the green **Run workflow** button. Wait about a minute, then click the run to see the result.

**What the result means**

- ✅ Green, with songs listed: the key-only login works. `data/master.csv` is saved to the repo automatically.
- ❌ Red, "no songs came back with the key-only login": Spotify hides playlist songs without your personal login. Next step is the one-time phone login (step 1b, to be added).

### If something goes wrong

| Message | What to do |
| --- | --- |
| `No SPOTIFY_CLIENT_ID found` | The secret is missing or misnamed. Names must match exactly. |
| `Spotify refused the Client ID / Client Secret` | A typo or extra space in a secret. Delete it and add it again. |
| `Spotify refused to open this playlist` | The link is wrong, or the playlist is private. |
| `names only work with your Spotify login` | Paste the playlist link, not its name. |

---

## Step 2: Fill from MusicBrainz

No setup or secrets needed. MusicBrainz is free.

1. Open the **Actions** tab → **Fill from MusicBrainz** → **Run workflow** → green **Run workflow**.
2. It takes about 5 seconds per song (MusicBrainz allows one request per second), so roughly 7 minutes for 80 songs.
3. The run page shows how many songs were found and how many got a label, hometown, songwriters, year formed and Bandcamp link.

It only checks songs it hasn't checked before, so after pulling new songs from Spotify, run it again and it does just the new ones. Tick **Re-check songs that were already checked** to redo everything (for example, a few months later, when volunteers have added more).

**What `mb_match` means**

| Value | Meaning |
| --- | --- |
| `isrc` | Song found: label, songwriters, producers and artist details filled where MusicBrainz has them |
| `spotify-artist-link` | Song not in MusicBrainz, but the artist is: hometown, formed, links only |
| `not found` | Nothing in MusicBrainz yet. These go to the research agents (step 4). |

---

## Step 2b: Fill from Genius

Needs one GitHub secret: `GENIUS_ACCESS_TOKEN` (genius.com/api-clients → your client → **Generate Access Token**). The Client ID and Client Secret are not needed.

Run it the same way: **Actions** → **Fill from Genius** → **Run workflow**. Takes a few minutes. Like MusicBrainz, it only checks new songs unless you tick **Re-check**.

**What it adds**

| Column | What it is |
| --- | --- |
| `genius_songwriters`, `genius_producers` | Song credits |
| `genius_label`, `genius_credits`, `genius_recorded_at` | Label (when Genius lists it), other credits like mixing and mastering, and the studio |
| `apple_music_url`, `youtube_url`, `soundcloud_url` | Listening links for the song page |
| `genius_relationships` | Samples, covers, remixes |
| `genius_description`, `genius_artist_bio` | **Background reading only.** Written by Genius users or the artist, so it stays off the site. |
| `genius_instagram`, `genius_twitter` | Artist socials |

A song only counts as found when both the artist and the title match closely, so a different song with the same name is skipped rather than filled in wrong. Lyrics are not collected.
