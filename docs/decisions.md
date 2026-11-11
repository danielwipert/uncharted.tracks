# Decision log

| Date | Decision | Why | Where it lives |
| --- | --- | --- | --- |
| 2026-09-30 | Custom website instead of Instagram / Medium | More expressive; built to explore | spec §1 |
| 2026-09-30 | Mobile first | Most visitors arrive from Instagram on a phone | spec §8 |
| 2026-09-30 | Players load on tap (Spotify + Apple Music) | Keeps pages fast | spec §5 |
| 2026-11-08 | Drop the radio-dial concept | Felt too kitschy | spec §1 |
| 2026-11-08 | Indie music magazine with zine touches | Smooth UX plus creative spark | spec §3 |
| 2026-11-08 | Own look, not the Social Studio design system | This site has its own identity | spec §3 |
| 2026-11-08 | Keep the record label as a small tilted sticker | Holds the must-have info (label, hometown) on-theme | spec §5 |
| 2026-11-08 | Song page opens like a magazine cover (headline on the photo) | Visitors see the song and headline right away | spec §5 |
| 2026-11-08 | Fixed bottom bar for prev / all / next | Always in thumb reach on a phone | spec §2 |
| 2026-11-08 | Home page is a polaroid collage wall | Most zine-like; picked from three mocked directions | spec §4 |
| 2026-11-08 | Song titles handwritten in marker, artist typed | Real-polaroid feel that stays readable | spec §4 |
| 2026-11-08 | Even two-column grid; top 10 one per row | Easy to scan; the top 10 gets more weight | spec §4 |
| 2026-11-08 | Compact masthead plus a short editor's note | Adds Dan's voice without pushing the wall down | spec §4 |
| 2026-11-08 | Top 3 start as blank "developing" polaroids | On-theme spoiler protection | spec §4 |
| 2026-11-08 | Tablet/desktop: same pieces, more room | Keeps the design; mobile stays the priority | spec §4–5 |
| 2026-11-08 | Red spot color for the UI; photos get their own treatment | Red works for numbers and tags, not on photos | spec §3 |
| 2026-11-08 | Photo treatment: hybrid fade + light blue-violet tint, worn texture | Looks like a real print aged for years; based on how real prints fade | spec §3 |
| 2026-11-08 | Build with Python + Jinja2 | Dan's language; matches other projects | spec §7 |
| 2026-11-08 | Song data in one YAML file | Easiest to write essays by hand | spec §6 |
| 2026-11-08 | GitHub Actions builds and publishes automatically | Matches other projects; no manual builds | spec §7 |
| 2026-11-08 | Photo look baked into images by Python, not applied live in the browser | Fast on every phone, same in every browser, tweakable in Python | photos.py |
| 2026-11-08 | Publish as a hidden preview (GitHub Pages, kept out of search) | Check it on a real phone before launch | songs.yaml `hidden_preview` |
| 2026-11-08 | Up to five listening links: Bandcamp, Spotify, Apple Music, YouTube, YouTube Music | Cover every audience; Bandcamp pays artists best | spec §5 |
| 2026-11-08 | Listening links shown as a cassette insert, Bandcamp first | Most zine-like; puts Bandcamp at the top | spec §5 |
| 2026-11-08 | Magazine extras (Listen for, File next to, segue) as taped notes | Matches the tape and polaroids on the page | spec §5 |
| 2026-11-08 | Replace "Listen for" and "File next to" with one "In their own words" artist quote | Too much information on the page; the artist's voice adds more | spec §5 |
| 2026-11-11 | Songwriters move off the record into the FILE UNDER list | Long credits didn't fit on the record label | templates/song.html |
| 2026-11-11 | Cover shows only rank, photo and song card; genre tag and headline removed (replaces the 2026-11-08 "headline on the photo" decision) | Cleaner cover; Dan's writing leads | templates/song.html |
| 2026-11-11 | Essay moves up to where the standfirst was, above the record; standfirst dropped | Writing first, at the top of the right column on desktop | templates/song.html |
| 2026-11-11 | Keep Reading cards show the artist under each song title | Easier to tell songs apart | templates/song.html |
| 2026-11-11 | Uncharted Tracks is the publication; the Top 50 is this year's issue. Black "UNCHARTED TRACKS" nameplate above TOP 50 / OF 2026 on the home page; small "UNCHARTED TRACKS" label over "TOP 50 '26" on song pages; brand in every page title and footer | Builds the brand that will own the URL, and carries over to future years | songs.yaml `site.brand`; templates |
| 2026-11-11 | Spot red softened a smidge: #FF5A36 → #F46F52 (less saturated, slightly lighter) | Full-strength red felt a bit loud across the page | static/css/site.css `--spot` |
