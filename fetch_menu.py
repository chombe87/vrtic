"""
Fetches the current menu data for predskolska.rs, parses it, and writes JSON
artifacts that the front-end (index.html) can consume.

By default the script targets December 2025 assets called out in the
instructions, but month/year and source URLs are configurable via CLI flags.
"""

from __future__ import annotations

import argparse
import datetime as dt
import io
import json
import pathlib
import re
import subprocess
from typing import Dict, Iterable, List, Optional

import pdfplumber
import requests
from bs4 import BeautifulSoup

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

# WordPress uses latin, lower-case month slugs in URLs.
MONTH_SLUGS = {
    1: "januar",
    2: "februar",
    3: "mart",
    4: "april",
    5: "maj",
    6: "jun",
    7: "jul",
    8: "avgust",
    9: "septembar",
    10: "oktobar",
    11: "novembar",
    12: "decembar",
}


def serbian_month_slug(month: int) -> str:
    if month not in MONTH_SLUGS:
        raise ValueError(f"Nepoznat mesec: {month}")
    return MONTH_SLUGS[month]


def month_page_url(year: int, month: int) -> str:
    return f"https://www.predskolska.rs/jelovnik-{serbian_month_slug(month)}-{year}/"


def fetch_bytes(url: str) -> bytes:
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    resp.raise_for_status()
    return resp.content


def fetch_html(url: str) -> str:
    return fetch_bytes(url).decode("utf-8", errors="ignore")


def clean_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def normalize_for_match(text: str) -> str:
    normalized = text.lower()
    replacements = {
        "č": "c",
        "ć": "c",
        "š": "s",
        "đ": "dj",
        "ž": "z",
        "љ": "lj",
        "њ": "nj",
        "č": "c",
    }
    for src, target in replacements.items():
        normalized = normalized.replace(src, target)
    return normalized


def detect_meal_from_line(line: str) -> Optional[Dict[str, str]]:
    """
    Returns a meal dict with code/title/description if the line describes a meal.
    """
    lowered = line.lower()
    patterns = [
        ("d", ["dorucak", "doru\u010dak", "\u0434\u043e\u0440\u0443\u0447\u0430\u043a"]),
        ("u", ["uzina", "u\u017eina", "\u0443\u0436\u0438\u043d\u0430"]),
        ("r", ["rucak", "ru\u010dak", "\u0440\u0443\u0447\u0430\u043a"]),
    ]
    for code, keys in patterns:
        for key in keys:
            if lowered.startswith(key):
                parts = re.split(r"[–\-:]", line, maxsplit=1)
                desc = parts[1].strip() if len(parts) > 1 else ""
                return {"code": code, "title": parts[0].strip(), "description": desc}
    return None


def parse_menu_changes(html: str) -> Dict:
    soup = BeautifulSoup(html, "html.parser")
    container = soup.select_one("article .entry-content") or soup
    lines = [clean_spaces(t) for t in container.stripped_strings if clean_spaces(t)]

    date_re = re.compile(r"(\d{2}\.\d{2}\.\d{4})")
    entries: List[Dict] = []
    current_day: Optional[Dict] = None
    last_meal: Optional[Dict] = None

    for line in lines:
        if line.upper().startswith("IZMENA JELOVNIKA") or line.startswith("ИЗМЕНА"):
            continue

        date_match = date_re.search(line)
        if date_match:
            iso_date = dt.datetime.strptime(date_match.group(1), "%d.%m.%Y").date().isoformat()
            weekday = line[date_match.end() :].strip(" .")
            current_day = {"date": iso_date, "weekday": weekday, "meals": [], "raw": []}
            entries.append(current_day)
            last_meal = None
            continue

        if not current_day:
            continue

        meal_info = detect_meal_from_line(line)
        if meal_info:
            meal_entry = {
                "code": meal_info["code"],
                "title": meal_info["title"],
                "text": meal_info["description"],
                "affected_units": [],
                "notes": [],
                "raw": line,
            }
            current_day["meals"].append(meal_entry)
            last_meal = meal_entry
            continue

        if last_meal:
            if "," in line:
                units = [clean_spaces(part).strip(".") for part in line.split(",") if part.strip()]
                last_meal["affected_units"].extend(units)
            last_meal["notes"].append(line)
        else:
            current_day["raw"].append(line)

    return {"entries": entries}


def extract_pdf_lines(pdf_bytes: bytes) -> List[str]:
    lines: List[str] = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            for raw in text.splitlines():
                line = clean_spaces(raw)
                if line:
                    lines.append(line)
    return lines


def map_meal_code(ch: str) -> Optional[str]:
    first = ch.lower()
    if first in {"d", "\u0434"}:
        return "d"
    if first in {"u", "\u0443"}:
        return "u"
    if first in {"r", "\u0440"}:
        return "r"
    return None


def strip_calories(text: str) -> (str, List[float]):
    calorie_pattern = re.compile(
        r"(?:[-–]?\s*)?((?:\d+[.,]?\d*)\s*(?:kcal|kal)(?:\s*/\s*\d+[.,]?\d*\s*(?:kcal|kal))*)",
        flags=re.IGNORECASE,
    )
    calories: List[float] = []
    match = calorie_pattern.search(text)
    cleaned = text
    if match:
        numbers = re.findall(r"\d+[.,]?\d*", match.group(1))
        calories = [float(num.replace(",", ".")) for num in numbers]
        cleaned = (text[: match.start()] + text[match.end() :]).strip(" -/;:,")
    return cleaned, calories


def clean_pdf_meal_text(text: str) -> str:
    t = clean_spaces(text)
    # Remove known boilerplate / contact info
    contact_patterns = [
        r"kontakt telefoni centralne kuhinje.*",
        r"контакт телефони централне кухиње.*",
    ]
    for pat in contact_patterns:
        t = re.sub(pat, "", t, flags=re.IGNORECASE)
    # Strip trailing meal labels
    tail_patterns = [
        r"(doručak|dorucak|доручак)$",
        r"(užina|uzina|ужина)$",
        r"(ručak|rucak|ручак)$",
    ]
    for pat in tail_patterns:
        t = re.sub(rf"[\s,.\-–]*{pat}", "", t, flags=re.IGNORECASE)
    return t.strip(" ,.-–")


def parse_monthly_menu(pdf_bytes: bytes) -> Dict:
    lines = extract_pdf_lines(pdf_bytes)
    date_re = re.compile(r"(\d{2}\.\d{2}\.\d{4})")
    days: List[Dict] = []
    current: Optional[Dict] = None
    last_meal: Optional[Dict] = None

    for line in lines:
        if re.search(r"kontakt telefoni centralne kuhinje", line, re.IGNORECASE) or re.search(
            r"контакт телефони централне кухиње", line, re.IGNORECASE
        ):
            continue

        date_match = date_re.search(line)
        if date_match and (not line.strip().startswith(("-", "Д-", "У-", "Р-", "D-", "U-", "R-"))):
            if current:
                days.append(current)
            iso_date = dt.datetime.strptime(date_match.group(1), "%d.%m.%Y").date().isoformat()
            weekday = line[date_match.end() :].strip(" .")
            current = {"date": iso_date, "weekday": weekday, "meals": []}
            last_meal = None
            continue

        if not current:
            continue

        meal_match = re.match(r"^([A-Za-z\u0410-\u042f\u0430-\u044f])[-–]\s*(.+)", line)
        if meal_match:
            code = map_meal_code(meal_match.group(1))
            if not code:
                continue
            text_body = meal_match.group(2).strip()
            description, calories = strip_calories(text_body)
            description = clean_pdf_meal_text(description)
            meal_entry = {
                "code": code,
                "text": description,
                "calories": calories,
                "raw": line,
            }
            current["meals"].append(meal_entry)
            last_meal = meal_entry
            continue

        if last_meal:
            last_meal["text"] = clean_pdf_meal_text(f"{last_meal['text']} {line}".strip())

    if current:
        days.append(current)

    return {"days": days}


def parse_ingredients(pdf_bytes: bytes) -> Dict:
    lines = extract_pdf_lines(pdf_bytes)
    items: List[Dict] = []
    current_item: Optional[Dict] = None
    current_category = ""

    for line in lines:
        if line.isupper() and ":" not in line and len(line) < 40:
            current_category = line
            continue

        if ":" in line:
            name_part, ingredients_part = line.split(":", 1)
            if current_item:
                items.append(current_item)
            current_item = {
                "name": clean_spaces(name_part),
                "ingredients_raw": ingredients_part.strip(),
                "ingredients": [],
                "category": current_category,
            }
        elif current_item:
            current_item["ingredients_raw"] = f"{current_item['ingredients_raw']} {line}".strip()

    if current_item:
        items.append(current_item)

    for item in items:
        raw = item["ingredients_raw"]
        split_ingredients = [clean_spaces(p) for p in re.split(r",|;", raw) if clean_spaces(p)]
        item["ingredients"] = split_ingredients

    return {"items": items}


def write_json(path: pathlib.Path, data: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preuzimanje i parsiranje jelovnika.")
    parser.add_argument("--year", type=int, default=2026, help="Godina jelovnika (default 2026).")
    parser.add_argument("--month", type=int, default=1, help="Mesec jelovnika (default 1).")
    parser.add_argument(
        "--menu-pdf-url",
        default="https://www.predskolska.rs/wp-content/uploads/2025/12/%D0%88%D0%95%D0%9B%D0%9E%D0%92%D0%9D%D0%98%D0%9A-%D0%97%D0%90-%D0%88%D0%90%D0%9D%D0%A3%D0%90%D0%A0-2026.pdf",
        help="URL PDF-a sa mesečnim jelovnikom.",
    )
    parser.add_argument(
        "--ingredients-pdf-url",
        default="https://www.predskolska.rs/wp-content/uploads/2024/12/%D0%A1%D0%90%D0%A1%D0%A2%D0%90%D0%92-%D0%9D%D0%90%D0%9C%D0%98%D0%A0%D0%9D%D0%98%D0%A6%D0%90-%D0%A3-%D0%88%D0%95%D0%9B%D0%98%D0%9C%D0%90-13.12.2024.pdf",
        help="URL PDF-a sa sastavom namirnica.",
    )
    parser.add_argument("--output-dir", default="data", help="Direktorijum za JSON izlaz.")
    parser.add_argument(
        "--git-push",
        action="store_true",
        help='Na kraju pokreni "git commit -am" sa timestamp porukom i "git push".',
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = pathlib.Path(args.output_dir)

    page_url = month_page_url(args.year, args.month)
    print(f"[1/4] Preuzimam izmenu jelovnika sa {page_url}")
    menu_changes_html = fetch_html(page_url)
    menu_changes = parse_menu_changes(menu_changes_html)
    menu_changes.update({"source": page_url, "year": args.year, "month": args.month})
    write_json(output_dir / "menu_changes.json", menu_changes)

    print(f"[2/4] Preuzimam PDF jelovnika sa {args.menu_pdf_url}")
    monthly_pdf_bytes = fetch_bytes(args.menu_pdf_url)
    monthly_menu = parse_monthly_menu(monthly_pdf_bytes)
    monthly_menu.update(
        {"source": args.menu_pdf_url, "year": args.year, "month": args.month}
    )
    write_json(output_dir / "monthly_menu.json", monthly_menu)

    print(f"[3/4] Preuzimam PDF sastava namirnica sa {args.ingredients_pdf_url}")
    ingredients_pdf_bytes = fetch_bytes(args.ingredients_pdf_url)
    ingredients = parse_ingredients(ingredients_pdf_bytes)
    ingredients.update({"source": args.ingredients_pdf_url})
    write_json(output_dir / "ingredients.json", ingredients)

    meta = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "month": args.month,
        "year": args.year,
        "sources": {
            "page": page_url,
            "menu_pdf": args.menu_pdf_url,
            "ingredients_pdf": args.ingredients_pdf_url,
        },
    }
    write_json(output_dir / "metadata.json", meta)
    print(f"[4/4] Završeno. JSON fajlovi su u {output_dir.resolve()}")

    if args.git_push:
        try:
            status = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                check=False,
            ).stdout.strip().splitlines()
            changed_files = {line.strip().split(maxsplit=1)[-1] for line in status if line.strip()}
            if not changed_files:
                print("[git] Nema izmena za commit.")
                return
            only_meta = changed_files == {"data/metadata.json"} or changed_files == {"metadata.json"}
            if only_meta:
                #subprocess.run(["git", "reset", "--hard"], check=False)
                print("[git] Samo metadata izmena, ne radim ništa")
                return
            ts = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
            msg = f"json refresh {ts}"
            subprocess.run(["git", "add", "."], check=False)
            subprocess.run(["git", "commit", "-am", msg], check=False)
            subprocess.run(["git", "push"], check=False)
            print("[git] commit/push odrađen.")
        except Exception as exc:
            print(f"[git] Greška pri commit/push: {exc}")


if __name__ == "__main__":
    main()
