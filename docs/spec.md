# Top 50 of 2026 — Website Spec

**Version:** 0.2 · **Date:** November 8, 2026 · **Owner:** Dan Wipert
**Design canvas:** https://claude.ai/artifact/95ByXb6N3He4pCK48r9qc5
**Replaces:** v0.1 (Sept 30, 2026), which used an 80s radio-dial concept. That direction was dropped as too kitschy.

---

## 1. What this is

A website that walks through Dan's top 50 songs of 2026, designed like an indie music magazine with zine touches. It replaces the yearly Instagram / Medium post with something people explore.

**Goals**

- Easy, smooth navigation with creative spark: a zine you flip through.
- Writing and photos lead; each song gets a short magazine profile.
- Mobile first (most visitors come from Instagram on a phone), then tablet and desktop.
- Reusable every year by editing one data file.

---

## 2. Pages

| Page | What it is |
| --- | --- |
| **Home: the collage wall** | Masthead, editor's note, jump buttons, then all 50 songs as taped polaroids counting down from No. 50. |
| **Song pages (×50)** | One magazine profile per song, each with its own link (e.g. `/song/23/`). |

**Navigation**

- Countdown runs No. 50 → No. 1. "Next" moves toward No. 1.
- Every song has its own shareable link.
- A slim bar is fixed to the bottom of the screen on song pages: ← previous · All 50 · next →. When a song is playing, a mini "now playing" strip sits above it.
- A "Keep reading" block at the end of each song page repeats next / previous / all 50.

---

## 3. Visual identity

**Mood:** an indie music magazine with zine touches: newsprint paper, big condensed headlines, a magazine serif for essays, typewriter labels, tape, torn edges, and one bold spot color.

**Colors**

| Role | Hex |
| --- | --- |
| Paper (background) | `#F2EDE3` |
| Ink (text, borders) | `#161412` |
| Secondary text | `#4A453F` |
| Spot color (UI: rank stickers, tags, jump buttons, song card, buttons) | `#FF5A36` (red-orange) |
| Polaroid frame (yellowed) | `#F1E5C0` |

**Typography (Google Fonts)**

| Use | Font |
| --- | --- |
| Headlines, rank numbers, masthead | Anton |
| Essays, standfirst, song titles on song pages | Newsreader |
| Labels, metadata, buttons | Space Mono |
| Song titles written on polaroids | Permanent Marker |

**Photo treatment ("hybrid fade")**
Every song photo gets the same treatment, applied by the site (no hand editing). It is meant to look like a real print that sat out for years:

- Faded contrast, warmed with sepia.
- Orange-amber cast in shadows and midtones, a hint of yellow-green, and a light blue-violet tint.
- Lifted, brownish blacks; a pale cream haze.
- An orange light leak in the top corner and a warm dark edge.
- A worn layer on top: dust, hairline scratches, a crease, chewed edges (`static/img/wear.png`).

Photos without an image yet show a red dotted placeholder.

---

## 4. Home page: the collage wall (phone, top to bottom)

1. Masthead: "THE 2026 ISSUE · DAN WIPERT", big "TOP 50", "TAP A PHOTO" sticker.
2. **Editor's note:** a taped card with 2–3 short lines from Dan, signed "— Dan" in marker.
3. **Jump buttons:** 50–41, 40–31, 30–21, 20–11, 10–1.
4. **Polaroids, No. 50 to No. 11:** two per row, each slightly tilted, with tape, the photo, the song title handwritten in marker, the artist typed underneath, and a round red rank sticker.
5. **The Top 10:** a big "THE TOP 10" heading, then one large polaroid per row with title, artist and hometown.
6. **Spoilers:** No. 3, 2 and 1 start as blank "developing" polaroids marked "??", and fade in as the visitor scrolls to them.

**Tablet:** 3 polaroids per row. **Desktop:** 4 per row; the top 10 is 2 per row; masthead and editor's note sit side by side.

---

## 5. Song page: the magazine profile (phone, top to bottom)

1. Small header: "TOP 50 '26", "NO. 23 / 50", menu button.
2. **Magazine cover:** a tall, torn, taped photo with the genre tag, the headline (on paper strips) and a red song card (title + artist) laid over it. The rank number sits large in the top corner.
3. Photo caption and credit.
4. Standfirst (one sentence) and byline.
5. **Record sticker:** a small tilted record label showing the record label name and "FROM [HOMETOWN] · [MONTH] 2026", next to a "FILE UNDER" list (hometown, label, release month).
6. Spotify and Apple Music buttons. The real players load only when tapped.
7. **Essay:** drop cap, 2–4 short paragraphs, a pull quote in big type, and an end mark.
8. "Keep reading" block (next / previous / all 50).
9. Fixed bottom bar (see Pages).

**Desktop:** the cover photo sits on the left half and stays in place while the essay scrolls on the right.

---

## 6. Song data (`songs.yaml`)

All 50 songs live in one YAML file. Changing the list next year means editing this file, not the design.

| Field | Example |
| --- | --- |
| `rank` | 23 |
| `slug` | `something-else` (used in file names) |
| `title` | Something Else |
| `artist` | Joshua Burnside |
| `hometown` | Belfast, N. Ireland |
| `record_label` | Nettwerk |
| `release_month` | January |
| `genre_scene` | Kicker on the cover |
| `photo` | `img/photos/joshua-burnside.jpg` (optional) |
| `photo_alt` | Short description for screen readers |
| `photo_credit` | Photo: courtesy of Nettwerk |
| `headline` | Essay headline |
| `standfirst` | One-sentence hook |
| `essay` | 2–4 paragraphs (plain text, blank line between paragraphs) |
| `pull_quote` | One line of Dan's own writing |
| `spotify_url`, `apple_music_url` | Links for the players |
| `songwriters`, `duration`, `catalog_no` | Optional, for the record sticker |

---

## 7. Build and hosting

- **Build:** a Python script (`build.py`) reads `songs.yaml`, fills Jinja2 templates, and writes the finished site to `_site/`.
- **Hosting:** GitHub Pages. A GitHub Actions workflow builds the site on every push and publishes it once publishing is switched on.
- **No build step for the visitor:** plain HTML and CSS, with a small amount of JavaScript for the developing polaroids and the tap-to-load players.

---

## 8. Mobile and performance

- Phone first; every button at least 44px; body text ~18px.
- Players load only on tap; photos lazy-loaded and resized before upload.
- Animations run only on screen.

---

## 9. Content and rights

- Photos: Dan's own, or press photos artists and labels provide for coverage, always credited. Confirm credits with the label before launch.
- No lyrics, not even short lines. Headlines and pull quotes are Dan's own words.
- Audio only through official Spotify and Apple Music embeds.

---

## 10. Open items

1. Photos and essays for all 50 songs.
2. Photo credit for the Joshua Burnside press shot (ask Nettwerk).
3. "Big Feelings" (Mim Jensen) was first released as a single in Nov 2025 and is on her April 2026 EP; decide if it counts for 2026.
4. The "All 50" menu that opens from the bottom bar (not yet designed).
5. Test a very long song title.
6. Launch date and Instagram promotion.
