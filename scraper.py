import requests
from bs4 import BeautifulSoup
import csv
from datetime import datetime, timedelta
import os
import re
from collections import defaultdict

# Config
BASE_URL = ""
SEARCH_URL = BASE_URL + ""
CSV_FILE = "laptops.csv"
HTML_CACHE = "cache"
BOT_TOKEN = "YOUR_BOT_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"
TARGET_GPU = "AMD Radeon 890M"
TARGET_CPU = ""
MAX_PRICE = 2000.0
HEADERS = {"User-Agent": "Mozilla/5.0"}

os.makedirs(HTML_CACHE, exist_ok=True)

def clean_text(text):
    return re.sub(r'["'"'´¨\n\r]', '', text)

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg}
    requests.post(url, data=payload)

def fetch_page(page_number):
    cache_file = os.path.join(HTML_CACHE, f"page_{page_number}.html")
    if os.path.exists(cache_file):
        last_modified = datetime.fromtimestamp(os.path.getmtime(cache_file))
        if datetime.now() - last_modified < timedelta(hours=1):
            with open(cache_file, 'r', encoding='utf-8') as file:
                return file.read()
    response = requests.get(SEARCH_URL.format(page_number), headers=HEADERS)
    if response.url.strip("/") == BASE_URL.strip("/"):
        return None
    with open(cache_file, 'w', encoding='utf-8') as file:
        file.write(response.text)
    return response.text

def parse_product(card):
    try:
        name_tag = card.select_one("div.p-y-10 h3 a")
        if not name_tag:
            return None
        name = name_tag.get("title").strip()
        link = BASE_URL.rstrip("/") + name_tag.get("href").strip()
        specs = [clean_text(li.get_text(strip=True)) for li in card.select("ul.specs li")]
        if len(specs) < 7:
            return None
        cpu, gpu = specs[3], specs[4]
        if TARGET_GPU and TARGET_GPU not in gpu:
            return None
        if TARGET_CPU and TARGET_CPU not in cpu:
            return None
        price_tag = card.select_one("a.btn-success.price")
        if not price_tag:
            return None
        price_text = price_tag.get_text(strip=True)
        price_clean = price_text.replace("€", "").replace(",", ".").replace(" ", "")
        price = float(price_clean)
        if price > MAX_PRICE:
            return None
        return {
            "name": clean_text(name),
            "link": link,
            "screen": specs[0],
            "resolution": specs[1],
            "os": specs[2],
            "cpu": cpu,
            "gpu": gpu,
            "ram": specs[5],
            "storage": specs[6],
            "price": price,
            "date": datetime.now().strftime("%Y-%m-%d")
        }
    except:
        return None

def scrape_all():
    page = 1
    results = []
    while True:
        html = fetch_page(page)
        if html is None:
            break
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select("div.card.product")
        if not cards:
            break
        for card in cards:
            product = parse_product(card)
            if product:
                results.append(product)
        page += 1
    return results

def save_csv(data, filename):
    if not data:
        return
    fields = ["name", "link", "screen", "resolution", "os", "cpu", "gpu", "ram", "storage", "price", "date"]
    existing = set()
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing.add((row["link"], row["price"], row["date"]))
    new_entries = []
    for item in data:
        key = (item["link"], str(item["price"]), item["date"])
        if key not in existing:
            for k in ["name", "screen", "resolution", "os", "cpu", "gpu", "ram", "storage"]:
                item[k] = clean_text(item[k])
            new_entries.append(item)
    if not new_entries:
        return
    write_header = not os.path.exists(filename)
    with open(filename, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        if write_header:
            writer.writeheader()
        writer.writerows(new_entries)

def summarize_and_notify(laptops):
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    total_today = len(laptops)
    existing = defaultdict(list)
    if os.path.exists(CSV_FILE):
        with open(CSV_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing[row["link"]].append({"price": float(row["price"]), "date": row["date"]})
    new_since_yesterday = 0
    new_ever = 0
    best_price_today = min((l["price"] for l in laptops), default=None)
    all_prices = [entry["price"] for history in existing.values() for entry in history]
    prices_yesterday = [entry["price"] for history in existing.values() for entry in history if entry["date"] == yesterday]
    best_price_yesterday = min(prices_yesterday, default=None)
    best_price_ever = min(all_prices, default=None)
    for laptop in laptops:
        link = laptop["link"]
        if link not in existing:
            new_ever += 1
            new_since_yesterday += 1
        else:
            dates = [entry["date"] for entry in existing[link]]
            if yesterday not in dates:
                new_since_yesterday += 1
    msg = (
        f"Laptop Prices Summary:\n\n"
        f"{total_today} laptops found today.\n"
        f"{new_since_yesterday} not present yesterday.\n"
        f"{new_ever} not present ever.\n\n"
        f"Best price today: {'{:.2f}€'.format(best_price_today) if best_price_today else 'N/A'}\n"
        f"Best price yesterday: {'{:.2f}€'.format(best_price_yesterday) if best_price_yesterday else 'N/A'}\n"
        f"Best price ever: {'{:.2f}€'.format(best_price_ever) if best_price_ever else 'N/A'}"
    )
    send_telegram(msg)

if __name__ == "__main__":
    laptops = scrape_all()
    save_csv(laptops, CSV_FILE)
    summarize_and_notify(laptops)
