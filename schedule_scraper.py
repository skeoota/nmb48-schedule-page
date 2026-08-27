#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NMB48 Ameba Blog RSS Theater Schedule & FANY Ticket Scraper
- Filters RSS entries by theme_id (10033701523 or 10039020167) from Ameba Blog API.
- Parses theater performance schedules, times, titles, and member lineups.
- Calculates exact performance year based on pubDate (advancing to next year if month < pub_month).
- Links performing members with member.json unique IDs.
- Fetches official FANY Ticket search API to integrate accurate ticket application periods and links.
- Outputs monthly schedule JSON files into the schedules/ directory.
"""

import email.utils
import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin

# Windows console encoding fix
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import requests
from bs4 import BeautifulSoup

RSS_URL = "https://rssblog.ameba.jp/nmb48/rss20.xml"
BLOG_API_URL = "https://ameblo.jp/_api/blogEntries;amebaId=nmb48;blogId=10014580212;limit=20;offset=0;page=1?returnMeta=true"
FANY_SEARCH_URL = "https://ticket.fany.lol/search/event_more?keywords=NMB48%E5%8A%87%E5%A0%B4&search_type=search_string&offset={offset}"

MEMBER_FILE_PATH = "member.json"
SCHEDULE_OUTPUT_DIR = "schedules"

# Valid theme IDs for theater notices and schedules
ALLOWED_THEME_IDS = {"10033701523", "10039020167"}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ja,ko-KR;q=0.9,ko;q=0.8,en-US;q=0.7,en;q=0.6",
    "Cache-Control": "no-cache, no-store, must-revalidate",
    "Pragma": "no-cache",
    "Expires": "0",
}


def clean_html_text(raw_html: str) -> str:
    """Remove HTML tags and normalize whitespace."""
    if not raw_html:
        return ""
    text = re.sub(r"<[^>]+>", "", raw_html)
    return re.sub(r"\s+", " ", text).strip()


def load_member_database(file_path: str = MEMBER_FILE_PATH) -> Dict[str, Dict[str, Any]]:
    """Load member.json and build lookup maps by clean name."""
    if not os.path.exists(file_path):
        print(f"[!] '{file_path}' 파일이 없습니다. 고유 ID 매칭 없이 진행합니다.")
        return {}

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        name_map = {}
        for m in data:
            raw_name = m.get("name", "")
            clean_name = re.sub(r"\s+", "", raw_name)
            if clean_name:
                name_map[clean_name] = m

            full_raw = m.get("raw_name", "")
            clean_raw = re.sub(r"[（\(].*?[）\)]", "", full_raw)
            clean_raw = re.sub(r"\s+", "", clean_raw)
            if clean_raw and clean_raw not in name_map:
                name_map[clean_raw] = m

        print(f"[*] '{file_path}'에서 {len(name_map)}명의 멤버 색인을 생성했습니다.")
        return name_map
    except Exception as e:
        print(f"[!] '{file_path}' 로드 실패: {e}")
        return {}


def load_existing_monthly_schedules(
    schedule_dir: str = SCHEDULE_OUTPUT_DIR,
) -> Dict[str, Dict[Tuple[str, str], Dict[str, Any]]]:
    """
    Load existing schedule JSON files from schedules/ directory.
    Returns map: { "YYYY-MM": { (date, time): show_dict, ... }, ... }
    """
    if not os.path.exists(schedule_dir):
        return {}

    existing_data: Dict[str, Dict[Tuple[str, str], Dict[str, Any]]] = defaultdict(dict)
    for filename in os.listdir(schedule_dir):
        if filename.startswith("schedule_") and filename.endswith(".json"):
            ym_match = re.search(r"schedule_(\d{4}-\d{2})\.json", filename)
            if not ym_match:
                continue
            ym = ym_match.group(1)
            filepath = os.path.join(schedule_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    shows = json.load(f)
                if isinstance(shows, list):
                    for show in shows:
                        date_val = show.get("date")
                        time_val = show.get("time")
                        if date_val and time_val:
                            existing_data[ym][(date_val, time_val)] = show
                print(f"[*] 기존 스케줄 로드: {filename} ({len(existing_data[ym])}개 공연)")
            except Exception as e:
                print(f"[!] '{filename}' 로드 실패: {e}")

    return existing_data


def get_allowed_entry_ids(session: requests.Session) -> Dict[str, Dict[str, Any]]:
    """Fetch recent blog entries metadata from Ameba API and filter by theme_id."""
    api_url = f"{BLOG_API_URL}&_t={int(time.time())}"
    print(f"[*] Ameba Blog API 요청 중: {api_url}")
    allowed_entries: Dict[str, Dict[str, Any]] = {}

    try:
        response = session.get(api_url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        data = response.json()

        entry_map = (
            data.get("data", {})
            .get("entities", {})
            .get("entryMap", {})
        )

        for entry_id_str, entry_data in entry_map.items():
            theme_id_str = str(entry_data.get("theme_id", ""))
            if theme_id_str in ALLOWED_THEME_IDS:
                allowed_entries[str(entry_id_str)] = entry_data

        print(f"[*] 극장 공지 테마(theme_id in {ALLOWED_THEME_IDS}) 글 {len(allowed_entries)}건 필터링 완료.")
        for eid, edata in allowed_entries.items():
            print(f"    - [{eid}] {edata.get('entry_title')} (Theme: {edata.get('theme_name')})")

    except Exception as e:
        print(f"[!] Ameba Blog API 요청 중 오류 발생: {e}")

    return allowed_entries


def fetch_fany_ticket_data(session: requests.Session) -> Dict[Tuple[str, str], Dict[str, Any]]:
    """
    Fetch all active NMB48 theater performance ticket info from FANY Ticket Search API.
    Returns a lookup map keyed by (YYYY-MM-DD, HH:MM).
    """
    print(f"[*] FANY 티켓 검색 API 수집 시작...")
    fany_shows: Dict[Tuple[str, str], Dict[str, Any]] = {}
    offset = 0
    total_fetched = 0

    while True:
        url = FANY_SEARCH_URL.format(offset=offset) + f"&_t={int(time.time())}"
        try:
            res = session.get(url, headers=HEADERS, timeout=15)
            res.raise_for_status()
            data = res.json()
        except Exception as e:
            print(f"    [!] FANY API 요청 실패 (offset={offset}): {e}")
            break

        performances = data.get("performances", [])
        if not performances:
            break

        for p in performances:
            total_fetched += 1
            perf_id = p.get("id")
            name = p.get("name", "")
            perf_date_raw = p.get("performance_date", "")
            start_time_raw = p.get("start_time", "")

            # Extract YYYY-MM-DD
            d_match = re.search(r"(\d{4})/(\d{2})/(\d{2})", perf_date_raw)
            if not d_match:
                continue
            date_iso = f"{d_match.group(1)}-{d_match.group(2)}-{d_match.group(3)}"

            # Extract HH:MM
            start_time = ""
            if len(start_time_raw) >= 4:
                start_time = f"{start_time_raw[:2]}:{start_time_raw[2:4]}"

            # Parse sales
            sales_list = []
            for s in p.get("performance_sales", []):
                sales_name = clean_html_text(s.get("sales_name", ""))
                start_dt = clean_html_text(s.get("sales_start_datetime", ""))
                end_dt = clean_html_text(s.get("sales_end_datetime", ""))
                status = clean_html_text(s.get("display_sales_status", ""))
                dest_url = s.get("destination_url", "")

                sales_list.append({
                    "sales_id": s.get("sales_id"),
                    "sales_name": sales_name,
                    "period_start": start_dt,
                    "period_end": end_dt,
                    "status": status,
                    "url": dest_url,
                })

            key = (date_iso, start_time)
            fany_shows[key] = {
                "fany_performance_id": perf_id,
                "fany_event_name": name,
                "fany_date": date_iso,
                "fany_time": start_time,
                "sales": sales_list,
            }

        offset += len(performances)
        if len(performances) < 10:
            break

    print(f"[*] FANY 티켓에서 총 {total_fetched}개 공연 티켓 정보 수집 완료.")
    return fany_shows


def fetch_entry_html(session: requests.Session, entry_url: str) -> Optional[str]:
    """Directly fetch the live Ameba blog entry page to bypass RSS caching/delays."""
    try:
        url_with_cachebust = f"{entry_url}?_t={int(time.time())}"
        resp = session.get(url_with_cachebust, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        resp.encoding = "utf-8"
        soup = BeautifulSoup(resp.text, "html.parser")
        body = (
            soup.find("div", {"id": "entryBody"})
            or soup.find("div", class_=lambda c: c and "skin-entryBody" in c)
            or soup.find("div", class_="articleText")
            or soup.find("article")
        )
        if body:
            return str(body)
    except Exception as e:
        print(f"    [!] 원본 블로그 페이지 직접 수집 실패 ({entry_url}): {e}")
    return None


def parse_schedule_description(
    description_html: str,
    pub_datetime: email.utils.datetime.datetime,
    member_db: Dict[str, Dict[str, Any]],
    fany_ticket_db: Dict[Tuple[str, str], Dict[str, Any]],
    entry_id: str,
    entry_title: str,
    entry_url: str,
) -> List[Dict[str, Any]]:
    """Parse theater schedules from item description HTML."""
    soup = BeautifulSoup(description_html, "lxml")

    # Replace breaks and paragraphs with newlines
    for tag in soup.find_all(["p", "div", "br", "article", "li"]):
        tag.insert_after("\n")

    text = soup.get_text()
    raw_lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    lines = [line for line in raw_lines if line]

    schedules: List[Dict[str, Any]] = []

    pub_year = pub_datetime.year
    pub_month = pub_datetime.month

    current_date_info: Optional[Dict[str, Any]] = None
    current_date_shows: List[Dict[str, Any]] = []

    date_pattern = re.compile(r"^(?:本日)?\s*(\d{1,2})月(\d{1,2})日(?:\(([^)]+)\))?")
    time_show_pattern = re.compile(r"^[・\-\s]*(\d{1,2}:\d{2})\s*(?:開演)?\s*(.*)")
    title_pattern = re.compile(r"「(.*?)」\s*公演(?:\s*【(.*?)】)?")

    def flush_date_shows():
        nonlocal current_date_shows
        for show in current_date_shows:
            # If no member line was assigned and members is empty, mark undecided
            if not show["members"] and not show["members_raw"]:
                show["is_members_undecided"] = True
                show["members_raw"] = "※出演メンバーは決まり次第お知らせいたします。"

            # Match official FANY ticket info by (date, time)
            show_key = (show["date"], show["time"])
            fany_match = fany_ticket_db.get(show_key)

            if fany_match:
                show["fany_performance_id"] = fany_match.get("fany_performance_id")
                show["ticket_sales"] = fany_match.get("sales", [])
            else:
                show["fany_performance_id"] = None
                show["ticket_sales"] = []

            schedules.append(show)
        current_date_shows.clear()

    for line in lines:
        # Check if line is a Date line: e.g. 8月31日(月) or 9月1日(火)
        date_match = date_pattern.match(line)
        if date_match and not line.startswith("申込期間") and not line.startswith("当落発表") and "開演" not in line:
            flush_date_shows()
            month = int(date_match.group(1))
            day = int(date_match.group(2))
            day_of_week = date_match.group(3) or ""

            # Year calculation rule: if performance month < pubDate month, it's next year
            year = pub_year + 1 if month < pub_month else pub_year

            iso_date = f"{year:04d}-{month:02d}-{day:02d}"
            date_display = f"{year}年{month}月{day}日" + (f"({day_of_week})" if day_of_week else "")
            year_month = f"{year:04d}-{month:02d}"

            current_date_info = {
                "year": year,
                "month": month,
                "day": day,
                "day_of_week": day_of_week,
                "iso_date": iso_date,
                "date_display": date_display,
                "year_month": year_month,
                "date_raw": line,
            }
            continue

        # Check if line is a Performance line: e.g. ・18:30開演「青春！恋のDestination」公演【田中美空 生誕祭】
        show_match = time_show_pattern.match(line)
        if show_match and current_date_info:
            start_time = show_match.group(1)
            raw_title_str = show_match.group(2).strip()

            # Parse title and event tags
            t_match = title_pattern.search(raw_title_str)
            if t_match:
                title = t_match.group(1).strip()
                event_tag = t_match.group(2) or ""
            else:
                title = raw_title_str.replace("公演", "").strip()
                event_tag = ""

            all_tags = re.findall(r"【(.*?)】", raw_title_str)
            if not event_tag and all_tags:
                event_tag = " / ".join(all_tags)

            show_id = f"show_{current_date_info['iso_date']}_{start_time.replace(':', '')}_{len(schedules) + len(current_date_shows) + 1}"

            new_show = {
                "id": show_id,
                "entry_id": entry_id,
                "entry_title": entry_title,
                "entry_url": entry_url,
                "pub_date": email.utils.format_datetime(pub_datetime),
                "date": current_date_info["iso_date"],
                "year_month": current_date_info["year_month"],
                "date_display": current_date_info["date_display"],
                "day_of_week": current_date_info["day_of_week"],
                "time": start_time,
                "title": title,
                "full_title": raw_title_str,
                "event_type": event_tag,
                "is_members_undecided": False,
                "members_raw": "",
                "members": [],
                "special_notes": [],
                "fany_performance_id": None,
                "ticket_sales": [],
            }
            current_date_shows.append(new_show)
            continue

        # Check if line contains Performing Members (出演：...)
        if current_date_shows and (line.startswith("出演：") or line.startswith("出演:") or line.startswith("出演メンバー：")):
            raw_members_text = re.sub(r"^出演(メンバー)?\s*[:：]\s*", "", line).strip()

            # Split by japanese comma, comma, or spaces
            member_names = [m.strip() for m in re.split(r"[,、\s]+", raw_members_text) if m.strip()]
            member_ids = []

            for name in member_names:
                clean_name = re.sub(r"\s+", "", name)
                member_info = member_db.get(clean_name)
                if member_info and member_info.get("id"):
                    member_ids.append(member_info["id"])
                else:
                    member_ids.append(name)

            # Assign this member lineup to all shows on this date that don't have members yet
            for s in current_date_shows:
                if not s["members"]:
                    s["members_raw"] = raw_members_text
                    s["members"] = list(member_ids)
                    s["is_members_undecided"] = False
            continue

        # Check if line indicates undecided members
        if current_date_shows and "出演メンバーは決まり次第" in line:
            for s in current_date_shows:
                if not s["members"]:
                    s["is_members_undecided"] = True
                    s["members_raw"] = line
                    s["members"] = []
            continue

        # Additional special notes on performance
        if current_date_shows and (line.startswith("※") or line.startswith("💡")):
            if "決まり次第" not in line:
                for s in current_date_shows:
                    if not s.get("special_notes") or line not in s["special_notes"]:
                        s["special_notes"].append(line)

    flush_date_shows()
    return schedules


def run_schedule_scraper() -> Dict[str, List[Dict[str, Any]]]:
    """Execute complete schedule scraping, FANY ticket merging, and monthly saving workflow."""
    print("==================================================")
    print("  NMB48 Ameba Schedule & FANY Ticket Scraper      ")
    print("==================================================")

    # 1. Load member.json database
    member_db = load_member_database(MEMBER_FILE_PATH)

    session = requests.Session()
    session.headers.update(HEADERS)

    # 2. Get allowed entry IDs from Ameba Blog API
    allowed_entries = get_allowed_entry_ids(session)

    # 3. Fetch official FANY ticket information
    fany_ticket_db = fetch_fany_ticket_data(session)

    # 4. Fetch and parse RSS feed with cache-busting
    rss_url = f"{RSS_URL}?_t={int(time.time())}"
    print(f"\n[*] RSS 피드 요청 중: {rss_url}")
    try:
        response = session.get(rss_url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        response.encoding = "utf-8"
    except Exception as e:
        print(f"[!] RSS 피드 다운로드 실패: {e}")
        sys.exit(1)

    root = ET.fromstring(response.content)
    items = root.findall("./channel/item")
    print(f"[*] RSS 피드에서 총 {len(items)}개의 아이템을 읽었습니다.")

    all_schedules: List[Dict[str, Any]] = []

    for item in items:
        title_tag = item.find("title")
        link_tag = item.find("link")
        desc_tag = item.find("description")
        pubdate_tag = item.find("pubDate")

        title = title_tag.text.strip() if title_tag is not None and title_tag.text else ""
        link = link_tag.text.strip() if link_tag is not None and link_tag.text else ""
        description = desc_tag.text if desc_tag is not None and desc_tag.text else ""
        pubdate_str = pubdate_tag.text.strip() if pubdate_tag is not None and pubdate_tag.text else ""

        entry_id_match = re.search(r"entry-(\d+)\.html", link)
        if not entry_id_match:
            continue

        entry_id = entry_id_match.group(1)

        # Filter by allowed theme_ids
        if allowed_entries and entry_id not in allowed_entries:
            continue

        try:
            pub_dt = email.utils.parsedate_to_datetime(pubdate_str)
        except Exception:
            pub_dt = email.utils.datetime.datetime.now(email.utils.timezone.utc)

        print(f"\n[+] 극장 스케줄 글 파싱: [{entry_id}] {title}")
        print(f"    - 링크: {link}")
        print(f"    - 작성일(pubDate): {pubdate_str} (기준연도: {pub_dt.year}, 기준월: {pub_dt.month})")

        parsed_shows = parse_schedule_description(
            description_html=description,
            pub_datetime=pub_dt,
            member_db=member_db,
            fany_ticket_db=fany_ticket_db,
            entry_id=entry_id,
            entry_title=title,
            entry_url=link,
        )

        # Fallback to direct live blog page HTML if any members are undecided or parsing returned 0 shows
        has_undecided = any(show.get("is_members_undecided") for show in parsed_shows)
        if has_undecided or not parsed_shows:
            print(f"    [*] 멤버 미정 또는 상세 확인 필요 -> 원본 블로그 페이지 직접 요청 ({link})")
            live_html = fetch_entry_html(session, link)
            if live_html:
                live_shows = parse_schedule_description(
                    description_html=live_html,
                    pub_datetime=pub_dt,
                    member_db=member_db,
                    fany_ticket_db=fany_ticket_db,
                    entry_id=entry_id,
                    entry_title=title,
                    entry_url=link,
                )
                if live_shows:
                    live_undecided = sum(1 for s in live_shows if s.get("is_members_undecided"))
                    orig_undecided = sum(1 for s in parsed_shows if s.get("is_members_undecided"))
                    if live_undecided < orig_undecided or not parsed_shows:
                        print(f"    [✓] 원본 블로그 직접 조회로 최신 멤버 정보 반영 완료! (미정 {orig_undecided}건 -> {live_undecided}건)")
                        parsed_shows = live_shows

        print(f"    -> {len(parsed_shows)}개의 공연 일정을 추출했습니다.")
        for show in parsed_shows:
            member_count_str = (
                f"{len(show['members'])}명" if not show["is_members_undecided"] else "미정"
            )
            ticket_str = f"티켓 정보 {len(show['ticket_sales'])}건" if show["ticket_sales"] else "티켓 정보 없음"
            print(f"       • {show['date_display']} {show['time']} - {show['title']} (출연: {member_count_str}, {ticket_str})")

        all_schedules.extend(parsed_shows)

    # 5. Deduplicate and merge shows for the same date & time (Latest pubDate wins)
    merged_schedules_map: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for show in all_schedules:
        key = (show["date"], show["time"])
        if key not in merged_schedules_map:
            merged_schedules_map[key] = show
        else:
            existing = merged_schedules_map[key]
            existing_dt = email.utils.parsedate_to_datetime(existing["pub_date"])
            current_dt = email.utils.parsedate_to_datetime(show["pub_date"])
            if current_dt >= existing_dt:
                combined_notes = list(set(existing.get("special_notes", []) + show.get("special_notes", [])))
                show["special_notes"] = combined_notes
                # Preserve ticket sales if current lacks it
                if not show.get("ticket_sales") and existing.get("ticket_sales"):
                    show["ticket_sales"] = existing["ticket_sales"]
                    show["fany_performance_id"] = existing.get("fany_performance_id")
                merged_schedules_map[key] = show

    unique_schedules = list(merged_schedules_map.values())
    print(f"\n[*] 중복 및 멤버 변경 공지 병합 완료: 총 {len(all_schedules)}개 -> 고유 {len(unique_schedules)}개 공연")

    # Ensure output directory exists
    os.makedirs(SCHEDULE_OUTPUT_DIR, exist_ok=True)

    # 1. Load existing monthly schedule data
    existing_monthly_data = load_existing_monthly_schedules(SCHEDULE_OUTPUT_DIR)

    # 2. Group newly scraped schedules by Year-Month
    scraped_by_month: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for show in unique_schedules:
        ym = show.get("year_month", "unknown")
        scraped_by_month[ym].append(show)

    print("\n==================================================")
    print("           월별 스케줄 데이터 병합 및 저장       ")
    print("==================================================")

    # All target months from existing files + newly scraped shows
    all_target_months = set(list(existing_monthly_data.keys()) + list(scraped_by_month.keys()))

    final_monthly_schedules: Dict[str, List[Dict[str, Any]]] = {}

    for ym in sorted(all_target_months):
        month_map = existing_monthly_data.get(ym, {})
        new_shows = scraped_by_month.get(ym, [])

        updated_count = 0
        added_count = 0

        for new_show in new_shows:
            key = (new_show["date"], new_show["time"])
            if key in month_map:
                # Update existing performance with latest info
                old_show = month_map[key]
                old_show.update(new_show)
                month_map[key] = old_show
                updated_count += 1
            else:
                # Add newly discovered performance
                month_map[key] = new_show
                added_count += 1

        final_shows = list(month_map.values())
        final_shows.sort(key=lambda s: (s.get("date", ""), s.get("time", "")))
        final_monthly_schedules[ym] = final_shows

        month_file_path = os.path.join(SCHEDULE_OUTPUT_DIR, f"schedule_{ym}.json")
        with open(month_file_path, "w", encoding="utf-8") as f:
            json.dump(final_shows, f, ensure_ascii=False, indent=2)

        print(f"[✓] {ym} 스케줄 저장: {month_file_path} (총 {len(final_shows)}개 공연 | 갱신: {updated_count}개, 신규: {added_count}개)")

    print("==================================================")
    return final_monthly_schedules


if __name__ == "__main__":
    run_schedule_scraper()
