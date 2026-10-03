import base64
import json
import os
import re
from pathlib import Path
from typing import Any
from uuid import uuid4

import requests
import streamlit as st

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"
WATCHLIST_PATH = DATA_DIR / "watchlist.json"


def ensure_watchlist_file() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not WATCHLIST_PATH.exists():
        WATCHLIST_PATH.write_text("[]", encoding="utf-8")


def load_watchlist() -> list[dict[str, Any]]:
    ensure_watchlist_file()
    try:
        raw = json.loads(WATCHLIST_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if isinstance(raw, list):
        return raw
    return []


def save_watchlist(entries: list[dict[str, Any]]) -> None:
    ensure_watchlist_file()
    temp_path = WATCHLIST_PATH.with_suffix(".tmp")
    temp_path.write_text(
        json.dumps(entries, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    temp_path.replace(WATCHLIST_PATH)


def publish_watchlist(entries: list[dict[str, Any]]) -> str:
    try:
        secret_token = st.secrets.get("GITHUB_TOKEN", "")
    except Exception:
        secret_token = ""
    token = os.environ.get("GITHUB_TOKEN", str(secret_token)).strip()
    if not token:
        raise RuntimeError(
            "เพิ่ม GITHUB_TOKEN ใน .streamlit/secrets.toml ก่อนเผยแพร่"
        )

    api_url = "https://api.github.com/repos/affranphanjampee-art/kuroya/contents/data/watchlist.json"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    current_file = requests.get(
        api_url, headers=headers, params={"ref": "main"}, timeout=20
    )
    current_file.raise_for_status()
    encoded_content = base64.b64encode(
        json.dumps(entries, indent=2, ensure_ascii=False).encode("utf-8")
    ).decode("ascii")
    result = requests.put(
        api_url,
        headers=headers,
        json={
            "message": "Update public anime watchlist",
            "content": encoded_content,
            "sha": current_file.json()["sha"],
            "branch": "main",
        },
        timeout=20,
    )
    result.raise_for_status()
    return result.json().get("commit", {}).get("html_url", "")


def split_total_annotation(value: str) -> tuple[str, str]:
    match = re.fullmatch(r"(.*?)\s*\(([^()]*)\)", value.strip())
    if match:
        annotation = match.group(2)
        return match.group(1), "" if annotation.endswith("%") else annotation
    return value, ""


def parse_episode_counts(value: str) -> tuple[int, int] | None:
    match = re.match(r"\s*(\d+)\s*/\s*(\d+)", value)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def estimate_watch_time(episode_count: int) -> str:
    total_minutes = episode_count * 24
    hours, minutes = divmod(total_minutes, 60)
    return f"{hours:02d}:{minutes:02d}:00"


st.set_page_config(page_title="Anime Notebook", page_icon="📚", layout="wide")

try:
    secret_read_only = st.secrets.get("ANIME_NOTEBOOK_READ_ONLY", "")
except Exception:
    secret_read_only = ""
READ_ONLY_MODE = str(
    os.environ.get("ANIME_NOTEBOOK_READ_ONLY", secret_read_only)
).casefold() in {"1", "true", "yes"}

st.markdown(
    """
    <style>
    :root {
        --vermilion: #bd4636;
        --moss: #52746b;
    }
    .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"] {
        font-family: "Yu Gothic UI", "Noto Sans Thai", "Meiryo", sans-serif;
    }
    [data-testid="stHeader"] { background: transparent !important; }
    [data-testid="stSidebar"] {
        border-right: 1px solid color-mix(in srgb, currentColor 16%, transparent);
    }
    .block-container {
        max-width: 1160px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }
    h1 {
        font-weight: 650 !important;
        letter-spacing: 0 !important;
        border-left: 4px solid var(--vermilion);
        padding-left: 14px;
    }
    .jp-kicker {
        color: var(--vermilion) !important;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        margin: 0 0 0.35rem 1.1rem;
    }
    [data-testid="stMetric"] {
        background: transparent;
        border-left: 2px solid color-mix(in srgb, currentColor 16%, transparent);
        padding: 0.25rem 0.8rem;
    }
    [data-testid="stExpander"] {
        border: 1px solid color-mix(in srgb, currentColor 18%, transparent);
        border-radius: 4px;
        margin-bottom: 0.55rem;
    }
    [data-testid="stExpander"] details summary:hover { color: var(--vermilion); }
    [data-testid="stTextInput"] input,
    [data-testid="stNumberInput"] input,
    [data-testid="stTextArea"] textarea,
    [data-baseweb="select"] > div { border-radius: 4px !important; }
    [data-testid="stButton"] button,
    [data-testid="stFormSubmitButton"] button {
        border-radius: 4px;
        transition: background-color 120ms ease, border-color 120ms ease;
    }
    [data-testid="stButton"] button:hover,
    [data-testid="stFormSubmitButton"] button:hover {
        border-color: var(--moss);
    }
    [data-baseweb="tab-list"] { border-bottom: 1px solid var(--line); }
    [data-baseweb="tab"][aria-selected="true"] {
        color: var(--vermilion) !important;
        border-bottom-color: var(--vermilion) !important;
    }
    [data-testid="stProgressBar"] > div { border-radius: 2px; }
    [data-testid="stProgressBar"] > div > div {
        background: var(--vermilion);
        border-radius: 2px;
    }
    [data-testid="stDialog"] {
        background: rgba(32, 40, 37, 0.28) !important;
    }
    [data-testid="stDialog"] section[role="dialog"] {
        border: 1px solid color-mix(in srgb, currentColor 18%, transparent);
        border-radius: 6px;
    }
    @media (max-width: 700px) {
        .block-container { padding-top: 1.2rem; }
        h1 { font-size: 1.8rem !important; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)
if READ_ONLY_MODE:
    st.markdown(
        "<style>[data-testid='stForm'] { display: none !important; }</style>",
        unsafe_allow_html=True,
    )

watchlist = load_watchlist()
anime_items = [item for item in watchlist if item.get("kind") == "anime"]
manga_items = [item for item in watchlist if item.get("kind") == "manga"]
categories = sorted({item["category"] for item in watchlist if item.get("category")})
annotation_options = sorted(
    {
        annotation
        for item in watchlist
        for _, annotation in [split_total_annotation(item.get("total", ""))]
        if annotation and not annotation.endswith("%")
    }
    | {"กำลังดู", "กำลังฉาย", "กำลังสร้าง", "ยังไม่ฉาย", "จบแล้ว"}
)
annotation_options = ["ไม่มี", *annotation_options]

@st.dialog("เพิ่มอนิเมะเรื่องใหม่")
def add_anime_dialog() -> None:
    default_category = "แฟนตาซี & ผจญภัย"
    if default_category not in categories and categories:
        default_category = categories[0]

    with st.form("add_anime_form"):
        title = st.text_input("ชื่อเรื่อง", placeholder="ชื่ออนิเมะ")
        category = st.text_input("หมวด", value=default_category)
        info_cols = st.columns(2)
        year = info_cols[0].number_input(
            "ปีที่เริ่มฉาย", min_value=1900, max_value=2099, value=2026, step=1
        )
        parts = info_cols[1].text_input("จำนวนภาค", value="1 ภาค")
        progress_text = st.text_area(
            "ความคืบหน้า (หนึ่งรายการต่อบรรทัด)", value="SS1: 0/--", height=100
        )
        total_cols = st.columns(2)
        total_value = total_cols[0].text_input("รวมทั้งเรื่อง", value="0/--")
        annotation = total_cols[1].selectbox("สถานะ", annotation_options)
        rating = st.text_input("คะแนน", value="-")
        cover_image = st.text_input(
            "URL รูปปก (ไม่บังคับ)", placeholder="https://..."
        )
        submitted = st.form_submit_button(
            "เพิ่มลงในรายการ", type="primary", use_container_width=True
        )

    if not submitted:
        return
    cleaned_title = title.strip()
    if not cleaned_title:
        st.error("กรุณาใส่ชื่อเรื่อง")
        return
    if cover_image.strip() and not cover_image.strip().startswith(("https://", "http://")):
        st.error("URL รูปปกต้องขึ้นต้นด้วย http:// หรือ https://")
        return
    if any(item["title"].casefold() == cleaned_title.casefold() for item in watchlist):
        st.error("มีชื่อเรื่องนี้ในรายการแล้ว")
        return

    item_id = re.sub(r"[^a-z0-9]+", "-", cleaned_title.casefold()).strip("-")
    if not item_id or any(item.get("id") == item_id for item in watchlist):
        item_id = f"anime-{uuid4().hex[:10]}"
    status_suffix = f" ({annotation})" if annotation != "ไม่มี" else ""
    watchlist.append(
        {
            "id": item_id,
            "title": cleaned_title,
            "kind": "anime",
            "category": category.strip() or default_category,
            "year": int(year),
            "parts": parts.strip() or "1 ภาค",
            "progress": [line.strip() for line in progress_text.splitlines() if line.strip()],
            "total": f"{total_value.strip()}{status_suffix}",
            "rating": rating.strip() or "-",
            "cover_image": cover_image.strip(),
        }
    )
    save_watchlist(watchlist)
    st.success(f"เพิ่ม {cleaned_title} แล้ว")
    st.rerun()


st.title("Anime Notebook")
st.markdown('<div class="jp-kicker">アニメ記録 · ANIME NOTEBOOK</div>', unsafe_allow_html=True)
st.caption("บันทึกอนิเมะและมังงะ พร้อมความคืบหน้าของแต่ละเรื่อง")
if READ_ONLY_MODE:
    st.info("โหมดแชร์: ดูข้อมูลได้อย่างเดียว")

overview_cols = st.columns(3)
overview_cols[0].metric("ทั้งหมด", len(watchlist))
overview_cols[1].metric("อนิเมะ", len(anime_items))
overview_cols[2].metric("มังงะ", len(manga_items))

if not READ_ONLY_MODE:
    action_cols = st.columns([1, 1])
    with action_cols[0]:
        if st.button("เผยแพร่รายการล่าสุด", use_container_width=True):
            try:
                commit_url = publish_watchlist(watchlist)
                st.success("อัปเดตเว็บสาธารณะแล้ว")
                if commit_url:
                    st.link_button("ดู commit บน GitHub", commit_url)
            except RuntimeError as error:
                st.error(str(error))
            except requests.HTTPError as error:
                status_code = error.response.status_code if error.response else "?"
                st.error(
                    f"GitHub ปฏิเสธการอัปเดต (HTTP {status_code}) "
                    "ตรวจสิทธิ์ Contents: Read and write ของ token"
                )
            except requests.RequestException:
                st.error("เชื่อมต่อ GitHub ไม่สำเร็จ ลองใหม่อีกครั้ง")
    with action_cols[1]:
        if st.button(
            "＋ เพิ่มอนิเมะเรื่องใหม่", type="primary", use_container_width=True
        ):
            add_anime_dialog()

with st.sidebar:
    st.header("ค้นหาและกรอง")
    search_query = st.text_input("ค้นหาชื่อเรื่อง", placeholder="พิมพ์ชื่อเรื่อง")
    selected_category = st.selectbox("หมวด", ["ทั้งหมด", *categories])
    selected_kind = st.selectbox("ประเภท", ["ทั้งหมด", "อนิเมะ", "มังงะ"])

list_tab, summary_tab = st.tabs(["รายการของฉัน", "สรุป"])

with list_tab:
    filtered_items = [
        item
        for item in watchlist
        if (not search_query or search_query.casefold() in item["title"].casefold())
        and (selected_category == "ทั้งหมด" or item.get("category") == selected_category)
        and (
            selected_kind == "ทั้งหมด"
            or item.get("kind") == ("anime" if selected_kind == "อนิเมะ" else "manga")
        )
    ]

    st.caption(f"แสดง {len(filtered_items)} จาก {len(watchlist)} เรื่อง")
    if not filtered_items:
        st.info("ไม่พบเรื่องที่ตรงกับตัวกรอง")
    else:
        for item in filtered_items:
            year = f" [{item['year']}]" if item.get("year") else ""
            title = f"{item['title']}{year}"
            rating = item.get("rating", "-")
            with st.expander(f"{title}  ·  {rating}/10"):
                detail_cols = st.columns([1, 2])
                with detail_cols[0]:
                    if item.get("cover_image"):
                        st.image(item["cover_image"], width=150)
                    st.caption(item.get("category", item.get("kind", "")))
                    if item.get("parts"):
                        st.write(item["parts"])
                    st.write(f"คะแนน: {rating}/10")
                    counts = parse_episode_counts(item.get("total", ""))
                    if item.get("kind") == "anime" and counts is not None:
                        st.write(
                            "เวลาประมาณ: "
                            f"{estimate_watch_time(counts[0])} (24 นาที/ตอน)"
                        )
                with detail_cols[1]:
                    total_base, annotation = split_total_annotation(
                        item.get("total", "")
                    )
                    if total_base:
                        st.markdown(f"**รวมทั้งเรื่อง:** {total_base}")
                    if counts is not None and counts[1] > 0:
                        percent = round(counts[0] / counts[1] * 100)
                        st.progress(percent, text=f"ดูแล้ว {percent}%")
                    if annotation:
                        st.caption(annotation)
                    for progress_line in item.get("progress", []):
                        st.write(progress_line)

                with st.form(key=f"edit_{item['id']}"):
                    current_total, current_annotation = split_total_annotation(
                        item.get("total", "")
                    )
                    progress_text = st.text_area(
                        "ความคืบหน้า (หนึ่งรายการต่อบรรทัด)",
                        value="\n".join(item.get("progress", [])),
                        height=140,
                        disabled=READ_ONLY_MODE,
                    )
                    edit_cols = st.columns(2)
                    total_value = edit_cols[0].text_input(
                        "รวมทั้งเรื่อง",
                        value=current_total,
                        disabled=READ_ONLY_MODE,
                    )
                    selected_annotation = edit_cols[1].selectbox(
                        "สถานะ/เปอร์เซ็นต์ในวงเล็บ",
                        annotation_options,
                        index=(
                            annotation_options.index(current_annotation)
                            if current_annotation in annotation_options
                            else 0
                        ),
                        key=f"annotation_{item['id']}",
                        disabled=READ_ONLY_MODE,
                    )
                    edit_cols = st.columns(2)
                    rating_value = edit_cols[0].text_input(
                        "คะแนน",
                        value=str(item.get("rating", "-")),
                        disabled=READ_ONLY_MODE,
                    )
                    cover_image_value = st.text_input(
                        "URL รูปปก (ไม่บังคับ)",
                        value=item.get("cover_image", ""),
                        key=f"cover_{item['id']}",
                        placeholder="https://...",
                        disabled=READ_ONLY_MODE,
                    )
                    current_counts = parse_episode_counts(current_total)
                    if item.get("kind") == "anime" and current_counts is not None:
                        edit_cols[1].caption(
                            "เวลาประมาณ (คำนวณอัตโนมัติ): "
                            f"{estimate_watch_time(current_counts[0])}"
                        )
                    if st.form_submit_button(
                        "บันทึกความคืบหน้า", disabled=READ_ONLY_MODE
                    ):
                        if cover_image_value.strip() and not cover_image_value.strip().startswith(
                            ("https://", "http://")
                        ):
                            st.error("URL รูปปกต้องขึ้นต้นด้วย http:// หรือ https://")
                            st.stop()
                        item["progress"] = [
                            line.strip()
                            for line in progress_text.splitlines()
                            if line.strip()
                        ]
                        annotation_suffix = (
                            f" ({selected_annotation})"
                            if selected_annotation != "ไม่มี"
                            else ""
                        )
                        item["total"] = f"{total_value.strip()}{annotation_suffix}"
                        item["rating"] = rating_value.strip() or "-"
                        if cover_image_value.strip():
                            item["cover_image"] = cover_image_value.strip()
                        else:
                            item.pop("cover_image", None)
                        item.pop("watch_time", None)
                        save_watchlist(watchlist)
                        st.success(f"บันทึก {item['title']} แล้ว")
                        st.rerun()

with summary_tab:
    st.subheader("จำนวนรายการที่นำเข้า")
    st.write(
        f"มี {len(anime_items)} เรื่องอนิเมะ และ {len(manga_items)} เรื่องมังงะ "
        f"รวม {len(watchlist)} รายการ"
    )
    st.caption(
        "สรุปท้ายข้อความต้นฉบับระบุ 43 เรื่อง (อนิเมะ 42 + มังงะ 1) "
        "แต่เมื่อนับรายการรายเรื่องที่ส่งมาพบอนิเมะ 43 เรื่อง บวกมังงะ 1 เรื่อง"
    )

    st.subheader("สรุปตามต้นฉบับที่ส่งมา")
    summary_cols = st.columns(3)
    summary_cols[0].metric("เรื่องจบแล้ว", "18")
    summary_cols[1].metric("กำลังดู/อ่าน", "22")
    summary_cols[2].metric("ยังไม่เริ่ม", "3")
    summary_cols = st.columns(2)
    watched_episodes = sum(
        counts[0]
        for item in anime_items
        if (counts := parse_episode_counts(item.get("total", ""))) is not None
    )
    total_watch_minutes = watched_episodes * 24
    total_watch_hours, remaining_minutes = divmod(total_watch_minutes, 60)
    summary_cols[0].metric(
        "เวลาที่ดูโดยประมาณ",
        f"{total_watch_hours} ชั่วโมง {remaining_minutes} นาที",
    )
    summary_cols[1].metric("คะแนนเฉลี่ย", "7.83/10")

st.caption("ข้อมูล watchlist จัดเก็บไว้ในเครื่องนี้ที่ data/watchlist.json")
