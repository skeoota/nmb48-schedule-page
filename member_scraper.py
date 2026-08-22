#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NMB48 Member Profile Scraper
- Scrapes member list and detail pages from NMB48 official mobile site.
- Distinguishes regular members (정규생) and research students (연구생).
- Assigns unique IDs and preserves data in member.json.
- Updates status to '졸업생' (graduated) if existing members are no longer on the site.
"""

import json
import os
import re
import sys
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

# Windows console encoding fix for multilingual characters
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://spn.nmb48.com"
MEMBER_LIST_URL = f"{BASE_URL}/feature/member"
PENLIGHT_FILE_PATH = "penlight.json"
DATA_FILE_PATH = "member.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ja,ko-KR;q=0.9,ko;q=0.8,en-US;q=0.7,en;q=0.6",
}

COLOR_MAP_KO = {
    "흰색": "#FFFFFF", "화이트": "#FFFFFF", "빨강": "#FF0000", "레드": "#FF0000",
    "오렌지": "#EDA900", "주황": "#EDA900", "노랑": "#FFD700", "옐로우": "#FFD700",
    "보라": "#7B4DA0", "퍼플": "#7B4DA0", "연보라": "#926EAE", "라벤더": "#926EAE",
    "연한 보라": "#926EAE", "연한보라": "#926EAE",
    "초록": "#00C800", "그린": "#00C800", "에메랄드그린": "#009473", "에메랄드": "#009473",
    "레몬 옐로우": "#FFF44F", "레몬": "#FFF44F", "레몬옐로우": "#FFF44F",
    "라이트 블루": "#87CEEB", "소라": "#87CEEB", "하늘": "#87CEEB", "하늘색": "#87CEEB", "물색": "#87CEEB",
    "블루": "#0066CC", "파랑": "#0066CC",
    "딥핑크": "#FF1493", "진한 핑크": "#FF1493", "진한핑크": "#FF1493", "핫핑크": "#FF69B4",
    "연핑크": "#FFB6C1", "연한 핑크": "#FFB6C1", "연한핑크": "#FFB6C1", "라이트 핑크": "#FFB6C1",
    "핑크": "#FFC0CB", "연두": "#A4E468", "검정": "#222222", "블랙": "#222222"
}

COLOR_MAP_JA = {
    "白": "#FFFFFF", "ホワイト": "#FFFFFF", "赤": "#FF0000", "レッド": "#FF0000",
    "オレンジ": "#EDA900", "黄": "#FFD700", "イエロー": "#FFD700",
    "紫": "#7B4DA0", "パープル": "#7B4DA0", "薄紫": "#926EAE", "ラベンダー": "#926EAE",
    "緑": "#00C800", "グリーン": "#00C800", "エメラルドグリーン": "#009473",
    "レモンイエロー": "#FFF44F", "水色": "#87CEEB", "ライトブルー": "#87CEEB",
    "青": "#0066CC", "ブルー": "#0066CC", "濃いピンク": "#FF1493", "ホットピンク": "#FF69B4",
    "薄ピンク": "#FFB6C1", "ライトピンク": "#FFB6C1", "ピンク": "#FFC0CB",
    "黄緑": "#A4E468", "黒": "#222222", "ブラック": "#222222"
}

COLOR_MAP_EN = {
    "white": "#FFFFFF", "red": "#FF0000", "orange": "#EDA900", "yellow": "#FFD700",
    "purple": "#7B4DA0", "light purple": "#926EAE", "lavender": "#926EAE",
    "green": "#00C800", "emerald green": "#009473", "lemon yellow": "#FFF44F",
    "light blue": "#87CEEB", "blue": "#0066CC", "deep pink": "#FF1493", "dark pink": "#FF1493",
    "hot pink": "#FF69B4", "light pink": "#FFB6C1", "pink": "#FFC0CB",
    "light green": "#A4E468", "black": "#222222"
}


def resolve_color_hex(color_name: str) -> str:
    """Resolve HEX code from color name in KO, JA, or EN."""
    c = color_name.strip()
    if c.startswith("#"):
        return c.upper()
    if c in COLOR_MAP_KO:
        return COLOR_MAP_KO[c]
    if c in COLOR_MAP_JA:
        return COLOR_MAP_JA[c]
    c_lower = c.lower()
    if c_lower in COLOR_MAP_EN:
        return COLOR_MAP_EN[c_lower]
    # Fuzzy match
    for k, v in COLOR_MAP_KO.items():
        if k in c:
            return v
    for k, v in COLOR_MAP_JA.items():
        if k in c:
            return v
    return "#FFFFFF"


def load_penlight_json_data(file_path: str = PENLIGHT_FILE_PATH) -> Dict[str, Dict[str, Any]]:
    """
    Load and parse NMB48 member lightstick colors from penlight.json.
    Returns lookup map keyed by normalized Japanese member name, Korean name, and English name.
    """
    print(f"[*] 팬라이트(펜라이트) 데이터 로드 중: {file_path}")
    lightstick_map: Dict[str, Dict[str, Any]] = {}

    if not os.path.exists(file_path):
        print(f"[!] '{file_path}' 파일이 존재하지 않습니다.")
        return lightstick_map

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        nmb_groups = data.get("NMB48", {})
        total_members_found = 0

        for gen_name, members in nmb_groups.items():
            if not isinstance(members, list):
                continue
            for m in members:
                name_info = m.get("name", {})
                name_ja = name_info.get("ja", "").strip()
                name_ko = name_info.get("ko", "").strip()
                name_en = name_info.get("en", "").strip()

                penlight_info = m.get("penlight", {})
                ja_colors = penlight_info.get("ja", [])
                ko_colors = penlight_info.get("ko", [])
                en_colors = penlight_info.get("en", [])

                # Derive HEX colors
                hex_colors = []
                for idx, c_ja in enumerate(ja_colors):
                    hex_code = resolve_color_hex(c_ja)
                    if hex_code == "#FFFFFF" and idx < len(ko_colors):
                        hex_code = resolve_color_hex(ko_colors[idx])
                    hex_colors.append(hex_code)

                lightstick_record = {
                    "colors": hex_colors,
                    "color_names": {
                        "ko": ko_colors,
                        "ja": ja_colors,
                        "en": en_colors,
                    },
                    "color_str": {
                        "ko": " × ".join(ko_colors),
                        "ja": " × ".join(ja_colors),
                        "en": " × ".join(en_colors),
                    },
                }

                if name_ja:
                    clean_ja = re.sub(r"\s+", "", name_ja)
                    lightstick_map[clean_ja] = lightstick_record

                if name_ko:
                    clean_ko = re.sub(r"\s+", "", name_ko)
                    lightstick_map[clean_ko] = lightstick_record

                if name_en:
                    clean_en = re.sub(r"[^a-z0-9]+", "", name_en.lower())
                    lightstick_map[clean_en] = lightstick_record

                total_members_found += 1

        print(f"[*] 'penlight.json'에서 NMB48 멤버 {total_members_found}명의 펜라이트 데이터를 성공적으로 로드했습니다.")

    except Exception as e:
        print(f"[!] 'penlight.json' 로드 중 오류 발생: {e}")

    return lightstick_map


def create_session() -> requests.Session:
    """Create requests session with custom headers."""
    session = requests.Session()
    session.headers.update(HEADERS)
    return session


def load_existing_members(file_path: str = DATA_FILE_PATH) -> Dict[str, Dict[str, Any]]:
    """Load existing member data if member.json exists."""
    if not os.path.exists(file_path):
        print(f"[*] '{file_path}' 파일이 존재하지 않아 새로 생성합니다.")
        return {}

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        member_map: Dict[str, Dict[str, Any]] = {}
        if isinstance(data, list):
            for item in data:
                m_id = item.get("id")
                if m_id:
                    member_map[m_id] = item
        elif isinstance(data, dict):
            # If stored as {"members": [...]} or dict of ids
            if "members" in data and isinstance(data["members"], list):
                for item in data["members"]:
                    m_id = item.get("id")
                    if m_id:
                        member_map[m_id] = item
            else:
                member_map = data

        print(f"[*] 기존 '{file_path}'에서 {len(member_map)}명의 멤버 데이터를 불러왔습니다.")
        return member_map
    except Exception as e:
        print(f"[!] '{file_path}' 로드 중 오류 발생: {e}")
        return {}


def extract_image_url(element: Any) -> Optional[str]:
    """Extract background-image url from style attribute or src."""
    if not element:
        return None

    img_tag = element.find("img")
    if img_tag:
        # Check style="background-image :url(...)"
        style_attr = img_tag.get("style", "")
        bg_match = re.search(r"url\((['\"]?)(.*?)\1\)", style_attr)
        if bg_match:
            img_url = bg_match.group(2)
            return urljoin(BASE_URL, img_url)

        src = img_tag.get("src")
        if src and "cover_member.png" not in src:
            return urljoin(BASE_URL, src)

    return None


def parse_member_detail(session: requests.Session, detail_url: str) -> Dict[str, Any]:
    """
    Fetch and parse member detail page.
    Reads list items under 'section.section--detail.page--member ul.list--data li'.
    """
    detail_data: Dict[str, Any] = {
        "profile": {},
        "sns": [],
        "image_url": None,
    }

    try:
        response = session.get(detail_url, timeout=15)
        response.raise_for_status()
        response.encoding = response.apparent_encoding or "utf-8"
        soup = BeautifulSoup(response.text, "lxml")

        # Extract main detail profile image
        ph_fig = soup.select_one("section.section--detail.page--member div.left figure.ph")
        if ph_fig:
            img_url = extract_image_url(ph_fig)
            if img_url:
                detail_data["image_url"] = img_url

        # Profile details: section.section--detail.page--member ul.list--data li
        data_items = soup.select("section.section--detail.page--member ul.list--data li")
        for li in data_items:
            data_span = li.select_one("span.data")
            if data_span:
                key = data_span.get_text(strip=True)
                # Remove the span from li text to get the actual value
                data_span.decompose()
                value = li.get_text(strip=True)
                detail_data["profile"][key] = value
            else:
                text = li.get_text(strip=True)
                if text:
                    detail_data["profile"][f"item_{len(detail_data['profile'])+1}"] = text

        # SNS Links (Bonus enrichment)
        sns_links = soup.select("section.section--detail.page--member ul.list--sns li a")
        for a_tag in sns_links:
            href = a_tag.get("href")
            name = a_tag.get_text(strip=True)
            if href:
                detail_data["sns"].append({
                    "name": name,
                    "url": href,
                })

    except Exception as e:
        print(f"    [!] 상세 페이지({detail_url}) 파싱 실패: {e}")

    return detail_data


import hashlib
import uuid


def generate_unique_id(detail_url: str, href: str, yomi: str) -> str:
    """
    Generate a truly unique and deterministic ID for each member.
    Combines readable slug with URL-based deterministic UUID hash to avoid collisions (e.g. same names).
    Example: 'aobara_yuka_a3f81c9b'
    """
    # 1. Base slug from href or yomi
    slug = ""
    if href:
        clean_href = href.strip("/").split("/")[-1]
        slug = clean_href.replace("member_", "").strip()

    if not slug and yomi:
        slug = re.sub(r"[^a-zA-Z0-9]+", "_", yomi.strip().lower()).strip("_")

    if not slug:
        slug = "member"

    # 2. Deterministic short hash from detail_url or full URL (always unique per URL)
    target_for_hash = detail_url if detail_url else href
    url_uuid = uuid.uuid5(uuid.NAMESPACE_URL, target_for_hash)
    short_hash = url_uuid.hex[:8]

    return f"{slug}_{short_hash}"


def scrape_and_update(output_file: str = DATA_FILE_PATH, delay: float = 0.3) -> List[Dict[str, Any]]:
    """Main scraping and incremental update workflow."""
    print("==================================================")
    print("         NMB48 Member Profile Scraper             ")
    print("==================================================")

    # 1. Load existing data
    existing_members = load_existing_members(output_file)

    session = create_session()

    # 2. Load Lightstick colors database from penlight.json
    lightstick_db = load_penlight_json_data(PENLIGHT_FILE_PATH)

    print(f"\n[*] 멤버 목록 페이지 요청 중: {MEMBER_LIST_URL}")

    try:
        response = session.get(MEMBER_LIST_URL, timeout=15)
        response.raise_for_status()
        response.encoding = response.apparent_encoding or "utf-8"
    except Exception as e:
        print(f"[!] 멤버 목록 페이지 요청 실패: {e}")
        sys.exit(1)

    soup = BeautifulSoup(response.text, "lxml")

    # 3. Select member list elements: section.section--detail.page--member ul.list--profile li
    member_elements = soup.select("section.section--detail.page--member ul.list--profile li")
    print(f"[*] {len(member_elements)}개의 멤버 항목을 발견했습니다.")

    current_scraped_ids = set()
    updated_members: Dict[str, Dict[str, Any]] = {}

    for idx, li in enumerate(member_elements, 1):
        a_tag = li.select_one("a")
        if not a_tag:
            continue

        href = a_tag.get("href", "").strip()
        if not href:
            continue
        detail_url = urljoin(BASE_URL, href)

        # Name extraction
        name_tag = a_tag.select_one("p.name")
        raw_name = name_tag.get_text(strip=True) if name_tag else ""

        # Member type distinction (연구생 vs 정규생)
        # Check for both full-width （研究生） and half-width (研究生)
        is_kenkyusei = "研究生" in raw_name
        member_type = "연구생" if is_kenkyusei else "정규생"
        status_category = "研究生" if is_kenkyusei else "正規生"

        # Clean name by removing （研究生） / (研究生)
        cleaned_name = re.sub(r"[（\(]\s*研究生\s*[）\)]", "", raw_name).strip()

        # Yomi (English name)
        yomi_tag = a_tag.select_one("span.yomi")
        yomi = yomi_tag.get_text(strip=True) if yomi_tag else ""

        # Unique ID & UUID
        member_id = generate_unique_id(detail_url, href, yomi)
        member_uuid = str(uuid.uuid5(uuid.NAMESPACE_URL, detail_url))
        current_scraped_ids.add(member_id)

        # Thumbnail image
        thumb_img_url = extract_image_url(a_tag)

        # Match lightstick color data
        clean_name_key = re.sub(r"\s+", "", cleaned_name)
        clean_yomi_key = re.sub(r"[^a-z0-9]+", "", yomi.lower())
        lightstick_info = (
            lightstick_db.get(clean_name_key)
            or lightstick_db.get(clean_yomi_key)
            or None
        )

        lightstick_display = (
            f" [팬라이트: {lightstick_info['color_str']['ko']}]"
            if lightstick_info
            else ""
        )

        print(f"[{idx:02d}/{len(member_elements):02d}] 파싱 중: {cleaned_name} ({yomi}) - 구분: {member_type}{lightstick_display} [ID: {member_id}]")

        # 4. Fetch detail page
        detail_info = parse_member_detail(session, detail_url)

        # Merge with any existing custom data
        existing_info = existing_members.get(member_id, {})

        member_record: Dict[str, Any] = {
            "id": member_id,
            "uuid": member_uuid,
            "name": cleaned_name,
            "raw_name": raw_name,
            "yomi": yomi,
            "member_type": member_type,
            "status": status_category,
            "is_graduated": False,
            "detail_url": detail_url,
            "thumbnail_url": thumb_img_url,
            "image_url": detail_info.get("image_url") or thumb_img_url,
            "lightstick": lightstick_info,
            "profile": detail_info.get("profile", {}),
            "sns": detail_info.get("sns", []),
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        # Preserve any past graduation notes or custom fields if existed
        for k, v in existing_info.items():
            if k not in member_record:
                member_record[k] = v

        updated_members[member_id] = member_record

        # Polite crawling delay
        time.sleep(delay)

    # 4. Handle graduated members (졸업생 처리)
    # Any member that existed in member.json previously but is NOT in current scraping
    graduated_count = 0
    for old_id, old_member in existing_members.items():
        if old_id not in current_scraped_ids:
            graduated_count += 1
            print(f"[!] 웹페이지 목록에서 누락된 멤버 -> 졸업생으로 업데이트: {old_member.get('name')} (ID: {old_id})")
            old_member["is_graduated"] = True
            old_member["status"] = "졸업생"
            old_member["member_type"] = "졸업생"
            old_member["graduated_detected_at"] = old_member.get(
                "graduated_detected_at", time.strftime("%Y-%m-%d %H:%M:%S")
            )
            updated_members[old_id] = old_member

    # Convert map to ordered list
    final_list = list(updated_members.values())

    # 5. Save to member.json
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(final_list, f, ensure_ascii=False, indent=2)

    print("==================================================")
    print(f"[✓] 작업 완료!")
    print(f"    - 현재 활동 멤버: {len(current_scraped_ids)}명")
    print(f"    - 졸업생 멤버: {graduated_count}명")
    print(f"    - 총 저장 멤버 수: {len(final_list)}명")
    print(f"    - 저장 위치: {os.path.abspath(output_file)}")
    print("==================================================")

    return final_list


if __name__ == "__main__":
    scrape_and_update()
