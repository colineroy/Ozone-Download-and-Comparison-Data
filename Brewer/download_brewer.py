"""
Brewer (EUBREWNET) — Download ozone data for Sodankyla

Site : https://eubrewnet.aemet.es/eubrewnet
Station : Sodankylä (internal ID: 18)
Brewers : #37 (MkII), #214

Requires a free account at https://eubrewnet.aemet.es/eubrewnet/default/registration

Dependencies:
    pip install requests beautifulsoup4 lxml
"""

import os
from dotenv import load_dotenv
load_dotenv()
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from datetime import datetime, timedelta
import re
import urllib.parse

# ── CONFIG ─────────────────────────────────────────────────────
EUBREWNET_USER = os.getenv("EUBREWNET_USER", "your_username")
EUBREWNET_PASS = os.getenv("EUBREWNET_PASS", "your_password")

STATION_ID = 18                # Sodankylä internal ID
BREWER_IDS = ["037", "214"]    # 3-digit format used in filenames
PRODUCT    = "ozone"           # ozone, uv, aod, so2
LEVEL      = "1.5"             # 1.5 (NRT) or 2.0 (final)

DATE_START = "2026-04-15"
DATE_END   = "2026-04-15"

OUT_DIR = Path("./brewer_data")
OUT_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = "https://eubrewnet.aemet.es/eubrewnet"


class EubrewnetSession:
    """Authenticated session for EUBREWNET."""

    def __init__(self, username, password):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36",
        })
        self.username = username
        self.password = password
        self.logged_in = False

    def _get_formkey(self, html):
        """Extract _formkey CSRF token from web2py HTML."""
        soup = BeautifulSoup(html, "lxml")
        fk = soup.find("input", {"name": "_formkey"})
        return fk["value"] if fk else None

    def login(self):
        """Authenticate to EUBREWNET."""
        print("  Logging in to EUBREWNET...")

        login_url = f"{BASE_URL}/default/user/login"
        resp = self.session.get(login_url)
        resp.raise_for_status()

        formkey = self._get_formkey(resp.text)
        if not formkey:
            raise RuntimeError("Could not find CSRF _formkey")

        data = {
            "username":   self.username,
            "password":   self.password,
            "remember_me": "on",
            "_next":      f"{BASE_URL}/default/index",
            "_formkey":   formkey,
            "_formname":  "login",
        }
        resp = self.session.post(login_url, data=data)
        resp.raise_for_status()

        if "Log in" in resp.text and "Invalid" in resp.text:
            raise RuntimeError("Login failed: check your username/password")

        self.logged_in = True
        print("  Logged in!\n")

    def get_daily_page(self, date, product=PRODUCT, level=LEVEL):
        """Fetch the data page for a given date."""
        url = (f"{BASE_URL}/station/view/{STATION_ID}"
               f"/{date.year}/{date.month:02d}/{date.day:02d}"
               f"?level={level}&product={product}")
        resp = self.session.get(url)
        resp.raise_for_status()
        return resp.text

    def extract_download_links(self, html):
        """Extract file download links from the page HTML."""
        soup = BeautifulSoup(html, "lxml")
        links = []

        for a in soup.find_all("a", href=True):
            href = a["href"]
            if any(href.endswith(f".{bid}") for bid in BREWER_IDS):
                links.append(href)
            elif href.endswith(".txt") or href.endswith(".csv"):
                links.append(href)
            if "/default/download/" in href:
                links.append(href)

        return list(set(links))

    def download_file(self, url, date):
        """Download a single file from EUBREWNET."""
        if url.startswith("/"):
            url = f"{BASE_URL}{url}"
        elif not url.startswith("http"):
            url = f"{BASE_URL}/{url}"

        filename = url.split("/")[-1].split("?")[0]
        if not filename:
            filename = f"brewer_{date.strftime('%Y%m%d')}.dat"

        date_dir = OUT_DIR / date.strftime("%Y")
        date_dir.mkdir(parents=True, exist_ok=True)
        out_path = date_dir / filename

        if out_path.exists():
            print(f"    [skip]  {filename}")
            return out_path

        print(f"    [dl]    {filename}")
        try:
            resp = self.session.get(url, stream=True)
            resp.raise_for_status()
            with open(out_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=65536):
                    f.write(chunk)
        except Exception as e:
            print(f"            [!] {e}")
            if out_path.exists():
                out_path.unlink()
            return None
        return out_path

    def download_date(self, date):
        """Download all Brewer data for a given date."""
        print(f"  [{date.strftime('%Y-%m-%d')}]")
        html = self.get_daily_page(date)
        links = self.extract_download_links(html)

        if not links:
            if "available only for Registered" in html:
                print("      No data available (not logged in?)")
            else:
                print("      No files found for this date")
            return []

        downloaded = []
        for link in links:
            out = self.download_file(link, date)
            if out:
                downloaded.append(out)
        return downloaded


def main():
    print("=== Brewer (EUBREWNET) Download — Sodankyla FMI ===\n")
    print(f"  Station  : Sodankylä (ID={STATION_ID})")
    print(f"  Product  : {PRODUCT} (Level {LEVEL})")
    print(f"  Period   : {DATE_START} -> {DATE_END}")
    print(f"  Brewers  : {', '.join(BREWER_IDS)}\n")

    session = EubrewnetSession(EUBREWNET_USER, EUBREWNET_PASS)
    session.login()

    start = datetime.strptime(DATE_START, "%Y-%m-%d")
    end   = datetime.strptime(DATE_END, "%Y-%m-%d")
    ndays = (end - start).days + 1

    all_files = []
    for i in range(ndays):
        date = start + timedelta(days=i)
        files = session.download_date(date)
        all_files.extend(files)

    print(f"\n  Done: {len(all_files)} file(s) downloaded")


if __name__ == "__main__":
    main()
