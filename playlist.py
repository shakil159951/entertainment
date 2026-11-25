from datetime import datetime
from pathlib import Path
import re
import zoneinfo
import requests

INPUT_FILE = "movies.txt"
OUTPUT_FILE = "playlist.m3u"
DEVELOPER_NAME = "FARABI"

# এখানে আপনার ২-৩টি (বা আরও বেশি) এক্সটার্নাল প্লেলিস্ট লিংক দিন
EXTERNAL_PLAYLIST_URLS = [
    "https://raw.githubusercontent.com/sm-monirulislam/SM-Movie-Hup-Auto-Update/refs/heads/main/Movie_Combined.m3u",
    "https://raw.githubusercontent.com/MRM3UK/New-try/refs/heads/main/Metflix_Playlist_1792332597030.m3u",
    "https://raw.githubusercontent.com/MRM3UK/New-try/refs/heads/main/Update%20Series.m3u",
]

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}


def get_current_time():
    try:
        tz = zoneinfo.ZoneInfo("Asia/Dhaka")
        now = datetime.now(tz)
    except Exception:
        now = datetime.now()
    return now.strftime("%d-%b-%Y %I:%M:%S %p (%Z)")


def get_resolution_score(name):
    name_lower = name.lower()
    if "4k" in name_lower or "2160p" in name_lower:
        return 4
    elif "1080p" in name_lower or "fhd" in name_lower:
        return 3
    elif "720p" in name_lower or "hd" in name_lower:
        return 2
    elif "480p" in name_lower or "360p" in name_lower:
        return 1
    return 0


def get_base_movie_name(name):
    cleaned = re.sub(
        r"(?i)\b(4k|2160p|1080p|720p|480p|360p|fhd|hd|sd|web-dl|bluray|rip|hdrip|hdts)\b",
        "",
        name,
    )
    cleaned = re.sub(r"\s+", " ", cleaned).strip().lower()
    return cleaned


def clean_title(raw_title):
    """টাইটেল পরিষ্কার করার ফাংশন"""
    title = re.sub(r"\s+", " ", raw_title).strip()
    return title


def parse_external_m3u(text_content):
    lines = [line.strip() for line in text_content.splitlines() if line.strip()]
    parsed_items = []
    i = 0
    total = len(lines)

    while i < total:
        current = lines[i]
        if current.startswith("#EXTINF:"):
            # ইমেজ/লোগো ইউআরএল হুবহু রাখা হচ্ছে, কোনো পরিবর্তন ছাড়া
            logo_match = re.search(r'tvg-logo="([^"]*)"', current)
            logo = logo_match.group(1).strip() if logo_match else ""

            category = "Others"
            match_quotes = re.search(
                r'(?i)\bgroup-title\s*=\s*(["\'])(.*?)\1', current
            )
            if match_quotes:
                category = match_quotes.group(2).strip()
            else:
                match_no_quotes = re.search(
                    r"(?i)\bgroup-title\s*=\s*([^\s,]+)", current
                )
                if match_no_quotes:
                    category = match_no_quotes.group(1).strip()

            raw_name = current.split(",")[-1].strip()
            clean_name = clean_title(raw_name)

            i += 1
            ref = None
            url = None
            while i < total and not lines[i].startswith("#EXTINF:"):
                if "http-referrer=" in lines[i]:
                    ref = (
                        lines[i]
                        .replace("#EXTVLCOPT:http-referrer=", "")
                        .replace("http-referrer=", "")
                        .strip()
                    )
                elif lines[i].startswith("http://") or lines[i].startswith("https://"):
                    url = lines[i].strip()
                    i += 1
                    break
                i += 1

            if url:
                parsed_items.append({
                    "name": clean_name,
                    "logo": logo,
                    "url": url,
                    "referrer": ref,
                    "category": category,
                    "res_score": get_resolution_score(clean_name),
                    "base_name": get_base_movie_name(clean_name),
                })
        else:
            i += 1
    return parsed_items


def parse_local_txt(txt_path):
    if not txt_path.exists():
        return []

    raw_lines = txt_path.read_text(encoding="utf-8").splitlines()
    lines = [
        line.strip()
        for line in raw_lines
        if line.strip()
        and not line.startswith("##")
        and not (line.startswith("#") and not line.startswith("#EXT"))
    ]

    local_items = []
    i = 0
    total = len(lines)

    while i < total:
        current = lines[i]
        if current.startswith("#EXTINF:"):
            logo_match = re.search(r'tvg-logo="([^"]*)"', current)
            logo = logo_match.group(1).strip() if logo_match else ""

            cat_match = re.search(
                r'(?i)\bgroup-title\s*=\s*(["\'])(.*?)\1', current
            )
            cat = cat_match.group(2).strip() if cat_match else "My Collection"

            raw_name = current.split(",")[-1].strip()
            i += 1
            ref, url = None, None
            while i < total and not lines[i].startswith("#EXTINF:"):
                if "http-referrer=" in lines[i]:
                    ref = (
                        lines[i]
                        .replace("#EXTVLCOPT:http-referrer=", "")
                        .replace("http-referrer=", "")
                        .strip()
                    )
                elif lines[i].startswith("http://") or lines[i].startswith("https://"):
                    url = lines[i].strip()
                    i += 1
                    break
                i += 1

            if url:
                if "|" in raw_name:
                    parts = raw_name.split("|", 1)
                    clean_name = clean_title(parts[0])
                    cat = parts[1].strip()
                else:
                    clean_name = clean_title(raw_name)

                local_items.append({
                    "name": clean_name,
                    "logo": logo,
                    "url": url,
                    "referrer": ref,
                    "category": cat,
                    "res_score": get_resolution_score(clean_name),
                    "base_name": get_base_movie_name(clean_name),
                })

        elif (
            i + 2 < total
            and (
                lines[i + 1].startswith("http://")
                or lines[i + 1].startswith("https://")
            )
            and (
                lines[i + 2].startswith("http://")
                or lines[i + 2].startswith("https://")
            )
        ):
            raw_name = lines[i]
            logo = lines[i + 1].strip()
            url = lines[i + 2].strip()
            i += 3
            ref = None
            if i < total and "http-referrer=" in lines[i]:
                ref = (
                    lines[i]
                    .replace("http-referrer=", "")
                    .replace("#EXTVLCOPT:", "")
                    .strip()
                )
                i += 1

            if "|" in raw_name:
                parts = raw_name.split("|", 1)
                clean_name = clean_title(parts[0])
                cat = parts[1].strip()
            else:
                clean_name = clean_title(raw_name)
                cat = "My Collection"

            local_items.append({
                "name": clean_name,
                "logo": logo,
                "url": url,
                "referrer": ref,
                "category": cat,
                "res_score": get_resolution_score(clean_name),
                "base_name": get_base_movie_name(clean_name),
            })
        else:
            i += 1

    return local_items


def generate_playlist():
    local_items = parse_local_txt(Path(INPUT_FILE))
    if local_items:
        print(f"[✓] Parsed {len(local_items)} items from {INPUT_FILE}.")

    external_movies = []
    for idx, ext_url in enumerate(EXTERNAL_PLAYLIST_URLS, start=1):
        ext_url = ext_url.strip()
        if not ext_url:
            continue
        print(f"[*] Fetching external playlist #{idx}: {ext_url}")
        try:
            ext_res = requests.get(ext_url, headers=DEFAULT_HEADERS, timeout=15)
            if ext_res.status_code == 200:
                parsed_ext = parse_external_m3u(ext_res.text)
                for item in parsed_ext:
                    item["name"] = f"{item['name']} | {item['category']}"
                external_movies.extend(parsed_ext)
                print(
                    f"[✓] Fetched {len(parsed_ext)} items from playlist #{idx}."
                )
            else:
                print(
                    f"[!] Failed playlist #{idx}. HTTP {ext_res.status_code}"
                )
        except Exception as e:
            print(f"[!] Error fetching playlist #{idx}: {e}")

    final_active_items = local_items + external_movies

    # একই মুভির একাধিক রেজোলিউশন থাকলে সবচেয়ে ভালো রেজোলিউশনটি রাখা
    movie_dict = {}
    for m in final_active_items:
        b_name = m["base_name"] or m["name"].lower()
        score = m["res_score"]
        if b_name not in movie_dict or score > movie_dict[b_name]["res_score"]:
            movie_dict[b_name] = m

    final_movies = list(movie_dict.values())
    dedup_removed = len(final_active_items) - len(final_movies)

    current_time_str = get_current_time()
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        f.write("# ==========================================\n")
        f.write("# Playlist Name    : Farabi VOD Collection\n")
        f.write(f"# Developer        : {DEVELOPER_NAME}\n")
        f.write(f"# Last Updated     : {current_time_str}\n")
        f.write(f"# Total Unique VOD : {len(final_movies)}\n")
        f.write(f"# Dupes Removed    : {dedup_removed}\n")
        f.write("# ==========================================\n\n")

        for m in final_movies:
            category = m.get("category", "My Collection")
            logo_url = m.get("logo", "")

            entry_str = (
                f'#EXTINF:-1 tvg-logo="{logo_url}" '
                f'group-title="VOD;{category}", {m["name"]}\n'
            )
            if m.get("referrer"):
                entry_str += f"#EXTVLCOPT:http-referrer={m['referrer']}\n"
            entry_str += f"{m['url']}\n\n"
            f.write(entry_str)

    print("\n" + "=" * 40)
    print(f"[✓] Final Unique Playlist Count : {len(final_movies)}")
    print(f"[🔄] Lower-Res Dupes Removed     : {dedup_removed}")
    print(f"[✓] Updated: {OUTPUT_FILE}")
    print("=" * 40)


if __name__ == "__main__":
    generate_playlist()
