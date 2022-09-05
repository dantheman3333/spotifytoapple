
from argparse import ArgumentParser
import json
from json.tool import main
import urllib.parse
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


USER_DATA_DIR = "userdata"

def login(page):
    page.goto("https://music.apple.com/login")
    page.wait_for_url("https://music.apple.com/us/listen-now", timeout=5*60*1000) # 5min

def create_new_playlist(page, name):
    print("create new playlist")
    page.locator(".context-menu").locator("text=Add to playlist").nth(0).hover()
    page.locator(".context-menu").locator("text=New Playlist").click(delay=300)
    page.locator(".editable-textfield").click()
    for _ in range(200):
        page.keyboard.press("ArrowRight")
    for _ in range(200):
        page.keyboard.press("Backspace")
    page.keyboard.type(name)
    page.keyboard.press("Enter")

    page.wait_for_timeout(10*1000)

def add_to_playlist(page, name):
    if not click_top_hit(page):
        return False
    try:    
        page.locator(".context-menu").locator("text=Add to playlist").nth(0).hover()
    except PlaywrightTimeoutError:
        return False
    page.locator(".context-menu").locator("text=Add to playlist").nth(0).click(delay=350)
    if page.locator(".context-menu").locator("text={}".format(name)).nth(0).count() == 0:
        create_new_playlist(page, name)
    else:
        page.locator(".context-menu").locator("text=New Playlist").nth(0).hover()
        page.locator(".context-menu").locator("text={}".format(name)).nth(0).hover()
        page.locator(".context-menu").locator("text={}".format(name)).nth(0).click(delay=320)
    page.wait_for_timeout(4*1000)
    return True

def search(page, text):
    txt = ' '.join(text.split())
    encoded = urllib.parse.quote(txt)
    url = "https://music.apple.com/us/search?term={}".format(encoded)
    page.goto(url)
    page.wait_for_timeout(3*1000)
    if page.locator(".search__no-results").count() == 0:
        return True
    return False

def click_top_hit(page):
    top_hits = page.locator('div.search__search-hits')
    menu = top_hits.locator('div.context-menu__overflow')
    if menu.count() == 0:
        print("no top hit")
        return False
    menu.nth(0).hover()
    menu.nth(0).click(delay=211)
    return True

def _replace_whitespace(text):
    return " ".join(text.split())

def load_playlist_file(file_path):
    def get_first_artist(track_entry):
        for artist_entry in track_entry["artists"]:
            if artist_entry.get("type") != "artist":
                continue
            return artist_entry["name"]
        return ""
    playlists = {}

    with open(file_path) as f:
        d = json.load(f)

    for playlist_entry in d:
        tracks = []
        for entry in playlist_entry["tracks"]:
            if "track" not in entry:
                continue
            track_entry = entry["track"]
            if track_entry.get("type") != "track":
                continue
            name = "{} {}".format(track_entry["name"], get_first_artist(track_entry))
            tracks.append(_replace_whitespace(name))

        playlists[_replace_whitespace(playlist_entry["name"])] = tracks

    return playlists

def main():
    parser = ArgumentParser()
    parser.add_argument("-f", "--file", required=True, help="Path to a json playlist file")
    args = parser.parse_args()

    playlists = load_playlist_file(args.file)

    with sync_playwright() as p:
        browser = p.firefox.launch_persistent_context(USER_DATA_DIR, headless=False)
        page = browser.new_page()

        login(page)

        unknown_tracks = []

        for playlist, tracks in playlists.items():
            for track in tracks:
                if search(page, track):
                    if not add_to_playlist(page, playlist):
                        unknown_tracks.append(track)
                else:
                    unknown_tracks.append(track)

        print("Couldn't find: {}".format("\n".join(unknown_tracks)))
        page.wait_for_timeout(100*60*1000)


if __name__ == "__main__":
    main()