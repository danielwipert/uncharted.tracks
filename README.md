# Top 50 of 2026

Dan Wipert's top 50 songs of the year, as a zine-style website: a polaroid collage wall that opens into a magazine profile for each song.

- **Spec:** [docs/spec.md](docs/spec.md)
- **Decisions so far:** [docs/decisions.md](docs/decisions.md)

## How it works

| File / folder | What it is |
| --- | --- |
| `songs.yaml` | All the content: every song, its details and its essay. This is the file you edit most. |
| `build.py` | The Python script that turns `songs.yaml` into web pages. |
| `templates/` | The page layouts (HTML with blanks that `build.py` fills in). |
| `static/` | CSS, the worn-photo texture, and song photos (`static/img/photos/`). |
| `_site/` | The finished website. Created by `build.py`; not saved in git. |
| `.github/workflows/site.yml` | Tells GitHub to build (and later publish) the site on every push. |

## Run it on your computer (Windows, PowerShell)

One-time setup, inside this folder:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Every time you want to see your changes:

```powershell
.venv\Scripts\Activate.ps1
python build.py
python -m http.server 8000 --directory _site
```

Then open http://localhost:8000 in your browser. Press `Ctrl+C` in PowerShell to stop the preview.

## Adding a song photo

1. Save the photo into `static/img/photos/` with a simple name, like `armlock.jpg`.
2. In `songs.yaml`, add to that song:
   ```yaml
   photo: "img/photos/armlock.jpg"
   photo_alt: "Short description of the photo"
   photo_credit: "Photo: [photographer or source]"
   ```
3. The site applies the faded-polaroid treatment automatically. Never edit photos by hand.
