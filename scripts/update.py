#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Static daily builder for the ultra-light portal.
No external Python packages. Designed to run on GitHub Actions, Cloudflare build,
or a small VPS/cron job. If a remote source fails, previous cached data is used.
"""
import datetime as dt
import email.utils
import html
import json
import os
import random
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CACHE_FILE = DATA / "cache.json"
UA = "LitePortalTR/1.0 (+static daily portal; contact: admin@example.com)"
IST_LAT, IST_LON = 41.0082, 28.9784


def now_istanbul():
    if ZoneInfo:
        return dt.datetime.now(ZoneInfo("Europe/Istanbul"))
    return dt.datetime.utcnow() + dt.timedelta(hours=3)


def esc(x):
    return html.escape(str(x or ""), quote=True)


def fetch_text(url, timeout=14, encoding=None):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read(800000)  # hard cap per source
        enc = encoding or r.headers.get_content_charset() or "utf-8"
        return raw.decode(enc, errors="replace")


def fetch_json(url, timeout=14):
    return json.loads(fetch_text(url, timeout=timeout))


def load_cache():
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text("utf-8"))
        except Exception:
            return {}
    return {}


def save_cache(cache):
    DATA.mkdir(exist_ok=True)
    CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), "utf-8")


def cached(cache, key, func, default):
    try:
        val = func()
        cache[key] = {"ts": int(time.time()), "value": val}
        return val
    except Exception as e:
        print("WARN", key, e, file=sys.stderr)
        if key in cache and "value" in cache[key]:
            return cache[key]["value"]
        return default


def page(title, body, rel=""):
    css = rel + "style.css"
    home = rel + "index.html"
    return f'''<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html lang="tr">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)}</title>
<link rel="stylesheet" type="text/css" href="{css}">
</head>
<body>
<a class="skip" href="#content">İçeriğe geç</a>
<div id="top"><div class="wrap"><a href="{home}">Ana sayfa</a> | {esc(title)}</div></div>
<div class="wrap" id="content">
{body}
<div class="foot small"><a href="{home}">Ana sayfa</a> | Güncelleme: {esc(now_istanbul().strftime('%Y-%m-%d %H:%M'))}</div>
</div>
</body>
</html>
'''


def write(path, content):
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, "utf-8")


def parse_rss(xml_text, limit=6):
    items = []
    try:
        root = ET.fromstring(xml_text.strip().encode("utf-8"))
    except Exception:
        return items
    # RSS item or Atom entry
    candidates = root.findall(".//item")
    if not candidates:
        candidates = root.findall(".//{http://www.w3.org/2005/Atom}entry")
    for it in candidates[:limit]:
        def find_text(names):
            for name in names:
                el = it.find(name)
                if el is not None and el.text:
                    return el.text.strip()
            return ""
        title = find_text(["title", "{http://www.w3.org/2005/Atom}title"])
        link = find_text(["link"])
        if not link:
            atom_link = it.find("{http://www.w3.org/2005/Atom}link")
            if atom_link is not None:
                link = atom_link.attrib.get("href", "")
        desc = find_text(["description", "summary", "{http://www.w3.org/2005/Atom}summary"])
        desc = re.sub("<[^>]+>", " ", desc)
        desc = re.sub(r"\s+", " ", desc).strip()
        pub = find_text(["pubDate", "published", "updated", "{http://www.w3.org/2005/Atom}updated"])
        if title:
            items.append({"title": title[:180], "link": link, "summary": desc[:260], "pub": pub})
    return items


def read_json(path, default):
    try:
        return json.loads((DATA / path).read_text("utf-8"))
    except Exception:
        return default


def read_lines(path):
    try:
        return [x.strip() for x in (DATA / path).read_text("utf-8").splitlines() if x.strip()]
    except Exception:
        return []


def get_weather():
    url = ("https://api.open-meteo.com/v1/forecast?latitude=41.0082&longitude=28.9784"
           "&current=temperature_2m,weather_code,wind_speed_10m"
           "&daily=temperature_2m_max,temperature_2m_min,sunrise,sunset,precipitation_probability_max"
           "&timezone=Europe%2FIstanbul&forecast_days=3")
    j = fetch_json(url)
    cur = j.get("current", {})
    daily = j.get("daily", {})
    return {
        "temp": cur.get("temperature_2m"),
        "wind": cur.get("wind_speed_10m"),
        "code": cur.get("weather_code"),
        "sunrise": (daily.get("sunrise") or [""])[0][-5:],
        "sunset": (daily.get("sunset") or [""])[0][-5:],
        "days": [
            {"date": d, "max": mx, "min": mn, "rain": rp}
            for d, mx, mn, rp in zip(daily.get("time", []), daily.get("temperature_2m_max", []), daily.get("temperature_2m_min", []), daily.get("precipitation_probability_max", []))
        ]
    }


def get_prayer(today):
    url = "https://api.aladhan.com/v1/timingsByCity/{}?city=Istanbul&country=Turkey&method=13".format(today.strftime("%d-%m-%Y"))
    j = fetch_json(url)
    t = j.get("data", {}).get("timings", {})
    return {k: t.get(k, "--") for k in ["Fajr", "Sunrise", "Dhuhr", "Asr", "Maghrib", "Isha"]}


def get_rates():
    j = fetch_json("https://api.frankfurter.app/latest?from=EUR&to=TRY,USD,GBP")
    r = j.get("rates", {})
    eur_try = float(r.get("TRY", 0) or 0)
    eur_usd = float(r.get("USD", 0) or 0)
    eur_gbp = float(r.get("GBP", 0) or 0)
    return {
        "EURTRY": round(eur_try, 4) if eur_try else "--",
        "USDTRY": round(eur_try / eur_usd, 4) if eur_try and eur_usd else "--",
        "GBPTRY": round(eur_try / eur_gbp, 4) if eur_try and eur_gbp else "--"
    }


def get_crypto():
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,tether&vs_currencies=usd,try&include_24hr_change=true"
    j = fetch_json(url)
    return j


def get_earthquakes():
    # Kandilli Observatory text list. If blocked, cache/fallback keeps page alive.
    txt = fetch_text("http://www.koeri.boun.edu.tr/scripts/lst0.asp", encoding="iso-8859-9")
    rows = []
    for line in txt.splitlines():
        if re.match(r"\d{4}\.\d{2}\.\d{2}", line):
            parts = line.split()
            if len(parts) >= 9:
                rows.append({"date": parts[0], "time": parts[1], "lat": parts[2], "lon": parts[3], "mag": parts[6], "place": " ".join(parts[8:])[:80]})
        if len(rows) >= 12:
            break
    return rows


def get_onthisday(today):
    url = "https://api.wikimedia.org/feed/v1/wikipedia/tr/onthisday/all/{:02d}/{:02d}".format(today.month, today.day)
    j = fetch_json(url)
    def collect(name):
        out=[]
        for x in j.get(name, [])[:5]:
            year = x.get("year", "")
            text = x.get("text", "")
            out.append({"year": year, "text": text[:220]})
        return out
    return {"events": collect("events"), "births": collect("births"), "deaths": collect("deaths")}


def get_rss_groups(cache):
    feeds = read_json("feeds.json", {})
    groups = {}
    for group, arr in feeds.items():
        items=[]
        for feed in arr:
            key = "rss:" + feed.get("url", "")
            xml = cached(cache, key, lambda url=feed["url"]: fetch_text(url), "")
            for item in parse_rss(xml, limit=4):
                item["source"] = feed.get("name", "")
                items.append(item)
        # crude de-duplicate by title
        seen=set(); dedup=[]
        for it in items:
            t=it["title"].lower()
            if t not in seen:
                seen.add(t); dedup.append(it)
            if len(dedup) >= 8:
                break
        groups[group]=dedup
    return groups


def render_news_page(slug, title, items, rel="../"):
    body = [f"<h1>{esc(title)}</h1>", "<p class=\"small muted\">RSS kaynaklarından otomatik derlenmiştir. Başlıklar kaynak sitelere bağlanır.</p>"]
    body.append("<ul>")
    for it in items:
        link = it.get("link") or "#"
        body.append(f"<li><a href=\"{esc(link)}\">{esc(it.get('title'))}</a> <span class=\"small muted\">{esc(it.get('source'))}</span><br>{esc(it.get('summary'))}</li>")
    if not items:
        body.append("<li>Bugün kaynaklardan veri alınamadı. Önceki arşivi kontrol edin.</li>")
    body.append("</ul>")
    write(f"articles/{slug}.html", page(title, "\n".join(body), rel=rel))


def render_weather(weather):
    rows = "".join(f"<tr><td>{esc(d['date'])}</td><td>{esc(d['min'])} / {esc(d['max'])} °C</td><td>{esc(d['rain'])}%</td></tr>" for d in weather.get("days", []))
    body = f"<h1>Hava durumu - İstanbul</h1><p>Şu an: <b>{esc(weather.get('temp','--'))} °C</b>, rüzgar {esc(weather.get('wind','--'))} km/sa.</p><p>Güneş: doğuş {esc(weather.get('sunrise','--'))}, batış {esc(weather.get('sunset','--'))}.</p><table class=\"grid\"><tr><th>Gün</th><th>Min / Maks</th><th>Yağış olasılığı</th></tr>{rows}</table>"
    write("weather.html", page("Hava durumu", body))


def render_earthquakes(rows):
    trs = "".join(f"<tr><td>{esc(x['date'])} {esc(x['time'])}</td><td>{esc(x['mag'])}</td><td>{esc(x['place'])}</td></tr>" for x in rows)
    body = f"<h1>Son depremler</h1><table class=\"grid\"><tr><th>Saat</th><th>Büyüklük</th><th>Yer</th></tr>{trs}</table><p class=\"small muted\">Kaynak: Kandilli listesi; bağlantı yoksa önbellek kullanılır.</p>"
    write("earthquakes.html", page("Son depremler", body))


def render_crypto(c):
    names = [("bitcoin", "BTC"), ("ethereum", "ETH"), ("tether", "USDT")]
    rows=[]
    for key,name in names:
        x=c.get(key,{}) if isinstance(c,dict) else {}
        rows.append(f"<tr><td>{name}</td><td>{esc(x.get('usd','--'))}</td><td>{esc(x.get('try','--'))}</td><td>{esc(round(x.get('usd_24h_change',0),2) if x.get('usd_24h_change') is not None else '--')}%</td></tr>")
    body="<h1>Kripto para özeti</h1><table class=\"grid\"><tr><th>Varlık</th><th>USD</th><th>TRY</th><th>24s</th></tr>{}</table>".format("".join(rows))
    write("crypto.html", page("Kripto", body))


def render_onthisday(otd):
    def sec(name, arr):
        s=[f"<h2>{name}</h2><ul>"]
        for x in arr:
            s.append(f"<li><b>{esc(x.get('year'))}</b> - {esc(x.get('text'))}</li>")
        s.append("</ul>")
        return "\n".join(s)
    body = "<h1>Tarihte bugün</h1>" + sec("Olaylar", otd.get("events", [])) + sec("Doğumlar", otd.get("births", [])) + sec("Ölümler", otd.get("deaths", []))
    write("on-this-day.html", page("Tarihte bugün", body))


def render_radio():
    arr = read_json("radio_istanbul.json", [])
    rows = "".join(f"<tr><td>{esc(x['station'])}</td><td>{esc(x['morning'])}</td><td>{esc(x['day'])}</td><td>{esc(x['evening'])}</td></tr>" for x in arr)
    body = f"<h1>İstanbul radyo akışları</h1><p class=\"small muted\">Bu tablo veri dosyasından otomatik üretilir. Resmi yayıncı akış URL'leri eklendiğinde betik genişletilebilir.</p><table class=\"grid\"><tr><th>İstasyon</th><th>Sabah</th><th>Gün</th><th>Akşam</th></tr>{rows}</table>"
    write("radio/istanbul.html", page("İstanbul radyo", body, rel="../"))


def render_static_service_pages(rates):
    write("fuel.html", page("Akaryakıt", "<h1>Akaryakıt fiyatları</h1><p>Ücretsiz ve güvenilir resmi API bulunmadığında bu sayfa son bilinen veri veya manuel veri dosyası ile güncellenir. İl bazlı kaynak eklendiğinde otomatik tablo üretilebilir.</p>"))
    write("traffic.html", page("Trafik", "<h1>Trafik özeti</h1><p>Canlı trafik için genellikle API anahtarı gerekir. Bu hafif sürümde metin özetleri server-side eklenir; harita ve ağır script kullanılmaz.</p>"))
    write("tv.html", page("TV yayın akışı", "<h1>TV yayın akışı</h1><p>Yayıncıların resmi RSS/XML kaynakları eklendiğinde günlük akış otomatik üretilir.</p>"))
    body = f"<h1>Para ve emtia</h1><table class=\"grid\"><tr><td>USD/TRY</td><td>{esc(rates.get('USDTRY'))}</td></tr><tr><td>EUR/TRY</td><td>{esc(rates.get('EURTRY'))}</td></tr><tr><td>GBP/TRY</td><td>{esc(rates.get('GBPTRY'))}</td></tr></table>"
    write("newspapers.html", page("Gazete manşetleri", "<h1>Gazete manşetleri</h1><p>RSS kaynakları veya elle doğrulanmış başlık listesi ile güncellenir. Telifli kapak görselleri kullanılmaz.</p>"))
    write("markets.html", page("Piyasalar", body))



def clean_plain_text(txt):
    txt = txt.replace("\r\n", "\n").replace("\r", "\n")
    txt = re.sub(r"\n{3,}", "\n\n", txt)
    return txt.strip()


def get_online_reading(today):
    """Try to fetch a public-domain excerpt. Fallback is local readings.
    Sources are plain text, no API key. This keeps the portal static for users.
    """
    sources = [
        {"title": "Alice's Adventures in Wonderland", "url": "https://www.gutenberg.org/cache/epub/11/pg11.txt"},
        {"title": "The Adventures of Sherlock Holmes", "url": "https://www.gutenberg.org/cache/epub/1661/pg1661.txt"},
        {"title": "A Tale of Two Cities", "url": "https://www.gutenberg.org/cache/epub/98/pg98.txt"}
    ]
    src = sources[today.toordinal() % len(sources)]
    txt = fetch_text(src["url"], timeout=18)
    # Remove Gutenberg boilerplate when markers exist.
    m = re.search(r"\*\*\* START OF (?:THE|THIS) PROJECT GUTENBERG EBOOK.*?\*\*\*", txt, re.I | re.S)
    if m:
        txt = txt[m.end():]
    m = re.search(r"\*\*\* END OF (?:THE|THIS) PROJECT GUTENBERG EBOOK", txt, re.I)
    if m:
        txt = txt[:m.start()]
    txt = clean_plain_text(txt)
    paras = [re.sub(r"\s+", " ", x).strip() for x in txt.split("\n\n")]
    paras = [x for x in paras if 80 <= len(x) <= 1200]
    if len(paras) < 12:
        raise RuntimeError("not enough public-domain paragraphs")
    start = (today.toordinal() * 5) % max(1, len(paras) - 12)
    chosen = paras[start:start+12]
    return {"title": src["title"], "source": src["url"], "paragraphs": chosen, "online": True}


def get_local_reading(today):
    arr = read_json("readings.json", [])
    if not arr:
        return {"title":"Günlük okuma", "paragraphs":["Okuma verisi bulunamadı."], "online": False}
    item = arr[today.toordinal() % len(arr)]
    item["online"] = False
    return item


def render_daily_reading(today, online_reading=None):
    local = get_local_reading(today)
    reading = online_reading if online_reading and online_reading.get("paragraphs") else local
    source_note = ""
    if reading.get("online"):
        source_note = "<p class=\"small muted\">Kaynak: kamu malı metin, Project Gutenberg. Bağlantı çalışmazsa yerel 15 günlük okuma arşivi kullanılır.</p>"
    else:
        source_note = "<p class=\"small muted\">Kaynak: yerel 15 günlük okuma arşivi. İsterseniz data/readings.json dosyasından elle güncellenebilir.</p>"
    paras = "".join("<p>{}</p>".format(esc(x)) for x in reading.get("paragraphs", []))
    body = "<h1>{}</h1><p class=\"small muted\">Okuma süresi: yaklaşık 10-15 dk.</p>{}{}".format(esc(reading.get("title", "Günlük okuma")), source_note, paras)
    write("articles/daily-reading.html", page("Günlük okuma", body, rel="../"))

    # Also publish the prepared 15 local readings as bookmarkable pages.
    arr = read_json("readings.json", [])
    links = ["<h1>15 günlük okuma arşivi</h1><p>Bu sayfalar dış kaynaklar çalışmasa bile hazırdır.</p><ol>"]
    for item in arr:
        rid = item.get("id", "reading")
        title = item.get("title", rid)
        links.append('<li><a href="{}.html">{}</a></li>'.format(esc(rid), esc(title)))
        ibody = "<h1>{}</h1><p class=\"small muted\">Okuma süresi: yaklaşık {} dk.</p>{}".format(
            esc(title), esc(item.get("minutes", 10)), "".join("<p>{}</p>".format(esc(x)) for x in item.get("paragraphs", []))
        )
        write("readings/{}.html".format(rid), page(title, ibody, rel="../"))
    links.append("</ol>")
    write("readings/index.html", page("Okuma arşivi", "\n".join(links), rel="../"))


def render_rss_page(groups):
    b=["<h1>RSS başlıkları</h1>"]
    for g, items in groups.items():
        b.append(f"<h2>{esc(g.title())}</h2><ul>")
        for it in items[:8]:
            b.append(f"<li><a href=\"{esc(it.get('link','#'))}\">{esc(it.get('title'))}</a> <span class=\"small muted\">{esc(it.get('source'))}</span></li>")
        b.append("</ul>")
    write("rss.html", page("RSS başlıkları", "\n".join(b)))


def render_index(today, weather, prayer, rates, groups, crypto):
    quotes = read_lines("quotes.txt") or ["Bilgi, paylaşıldıkça çoğalır."]
    facts = read_lines("facts.txt") or ["Düz metin dayanıklıdır."]
    words = read_json("words.json", [{"tr":"sebat","en":"lucid","la":"aqua"}])
    seed = int(today.strftime("%Y%m%d"))
    random.seed(seed)
    quote = random.choice(quotes)
    fact = random.choice(facts)
    word = words[seed % len(words)]
    def list_items(group, n=3):
        s=[]
        for it in groups.get(group, [])[:n]:
            s.append(f"<li><a href=\"{esc(it.get('link','#'))}\">{esc(it.get('title'))}</a> <span class=\"small muted\">{esc(it.get('source'))}</span></li>")
        return "\n".join(s) or "<li>Veri bekleniyor.</li>"
    btc = crypto.get("bitcoin", {}).get("usd", "--") if isinstance(crypto, dict) else "--"
    body = f'''<a class="skip" href="#content">İçeriğe geç</a>
<div id="top"><div class="wrap"><b>Günlük Portal</b> | {esc(today.strftime('%d.%m.%Y'))} | <a href="search.html">Ara</a> | <a href="bookmarks.html">Yer imleri</a></div></div>
<div class="wrap">
<div class="nav"><a href="#summary">Özet</a><a href="#news">Haber</a><a href="#markets">Piyasa</a><a href="#read">Okuma</a><a href="#puzzle">Bulmaca</a><a href="#radio">Radyo</a><a href="archive/{esc(today.strftime('%Y-%m-%d'))}.html">Arşiv</a></div>
<h1 id="content">Türkiye için günlük metin portalı</h1>
<p class="small muted">Otomatik statik üretim. JavaScript gerekmez. Son güncelleme: {esc(today.strftime('%Y-%m-%d %H:%M'))}</p>
<h2 id="summary">Bugünün özeti</h2>
<table class="grid" summary="Bugünün kısa bilgileri">
<tr><th>Başlık</th><th>Bilgi</th></tr>
<tr><td>Tarih</td><td>{esc(today.strftime('%A, %d.%m.%Y'))}</td></tr>
<tr><td>Hava</td><td>İstanbul: {esc(weather.get('temp','--'))} °C, rüzgar {esc(weather.get('wind','--'))} km/sa. <a href="weather.html">Tahmin</a></td></tr>
<tr><td>Güneş</td><td>Doğuş {esc(weather.get('sunrise','--'))}, batış {esc(weather.get('sunset','--'))}</td></tr>
<tr><td>Namaz</td><td>İmsak {esc(prayer.get('Fajr','--'))}, Güneş {esc(prayer.get('Sunrise','--'))}, Öğle {esc(prayer.get('Dhuhr','--'))}, İkindi {esc(prayer.get('Asr','--'))}, Akşam {esc(prayer.get('Maghrib','--'))}, Yatsı {esc(prayer.get('Isha','--'))}</td></tr>
<tr><td>Döviz</td><td>USD/TRY {esc(rates.get('USDTRY','--'))}, EUR/TRY {esc(rates.get('EURTRY','--'))}, GBP/TRY {esc(rates.get('GBPTRY','--'))}</td></tr>
<tr><td>Kripto</td><td>BTC {esc(btc)} USD. <a href="crypto.html">Kripto özeti</a></td></tr>
</table>
<h2 id="news">Haberler</h2>
<h3>Türkiye</h3><ul>{list_items('turkiye')}</ul><p class="more"><a href="articles/turkiye-gundem.html">Türkiye haberleri</a></p>
<h3>Avrupa</h3><ul>{list_items('europe')}</ul>
<h3>Dünya</h3><ul>{list_items('world')}</ul>
<h3>Bilim, teknoloji, ekonomi, spor</h3><ul><li><a href="articles/science.html">Bilim</a></li><li><a href="articles/technology.html">Teknoloji</a></li><li><a href="articles/economy.html">Ekonomi</a></li><li><a href="articles/sports.html">Spor</a></li></ul>
<h2 id="markets">Piyasa, şehir ve servis</h2>
<table class="grid two"><tr><td><b>Deprem</b><br><a href="earthquakes.html">Son depremler</a></td><td><b>Trafik</b><br><a href="traffic.html">Trafik özeti</a></td></tr><tr><td><b>Akaryakıt</b><br><a href="fuel.html">Fiyatlar</a></td><td><b>TV</b><br><a href="tv.html">Yayın akışı</a></td></tr><tr><td><b>Gazete</b><br><a href="newspapers.html">Manşetler</a></td><td><b>RSS</b><br><a href="rss.html">Başlıklar</a></td></tr></table>
<h2>Kültür ve bilgi</h2>
<table class="grid"><tr><th>Alan</th><th>Bugünün içeriği</th></tr><tr><td>Tarihte bugün</td><td><a href="on-this-day.html">Olaylar, doğumlar, ölümler</a></td></tr><tr><td>Kelime</td><td>Türkçe: <b>{esc(word.get('tr'))}</b>; English: <b>{esc(word.get('en'))}</b>; Latin: <b>{esc(word.get('la'))}</b></td></tr><tr><td>Alıntı</td><td class="quote">{esc(quote)}</td></tr><tr><td>İlginç gerçek</td><td>{esc(fact)}</td></tr></table>
<h2 id="read">Günlük okuma</h2><p class="lite"><b>10-15 dakikalık okuma:</b> <a href="articles/daily-reading.html">Günün uzun okuması</a> | <a href="readings/index.html">15 günlük hazır arşiv</a></p><p><a href="books/index.html">Kamu malı kitaplık</a> | <a href="poetry.html">Şiir</a> | <a href="ascii.html">ASCII</a></p>
<h2 id="puzzle">Günün bulmacası</h2><ul><li><a href="puzzles/sudoku.html">Sudoku</a></li><li><a href="puzzles/chess.html">Satranç problemi</a></li><li><a href="puzzles/crossword.html">Mini çengel</a></li></ul>
<h2 id="radio">Radyo</h2><p><a href="radio/istanbul.html">İstanbul radyo akışları</a></p>
<div class="foot small"><p>Statik HTML. CSS küçük. JavaScript şart değildir. 15 günde bir otomatik güncellenir. <a href="#top">Başa dön</a> | <a href="about.html">Hakkında</a> | <a href="status.html">Durum</a></p></div>
</div>'''
    full = '''<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html lang="tr"><head><meta http-equiv="Content-Type" content="text/html; charset=UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Günlük Hafif Portal - Türkiye</title><link rel="stylesheet" type="text/css" href="style.css"></head><body>''' + body + '<script type="text/javascript" src="bookmarks.js"></script></body></html>\n'
    write("index.html", full)
    # Archive page: keep it lightweight and make links correct from archive/.
    archive_body = f'''<h1>{esc(today.strftime('%d.%m.%Y'))} arşivi</h1>
<p>Bu günün otomatik üretilen ana bağlantıları.</p>
<ul>
<li><a href="../index.html">Günün ana sayfası</a></li>
<li><a href="../weather.html">Hava durumu</a></li>
<li><a href="../earthquakes.html">Son depremler</a></li>
<li><a href="../rss.html">RSS başlıkları</a></li>
<li><a href="../on-this-day.html">Tarihte bugün</a></li>
<li><a href="../articles/daily-reading.html">Günlük okuma</a></li>
</ul>'''
    write(f"archive/{today.strftime('%Y-%m-%d')}.html", page(today.strftime('%Y-%m-%d') + " arşivi", archive_body, rel="../"))



def render_support_files(today):
    pages = []
    for path in ROOT.rglob("*.html"):
        if any(part.startswith(".") for part in path.relative_to(ROOT).parts):
            continue
        rel = path.relative_to(ROOT).as_posix()
        pages.append(rel)
    pages = sorted(set(pages))
    sitemap = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for rel in pages:
        sitemap.append('<url><loc>/{}</loc><lastmod>{}</lastmod></url>'.format(esc(rel), today.strftime('%Y-%m-%d')))
    sitemap.append('</urlset>')
    write("sitemap.xml", "\n".join(sitemap) + "\n")
    write("robots.txt", "User-agent: *\nAllow: /\nSitemap: /sitemap.xml\n")
    status_body = "<h1>Sistem durumu</h1><table class=\"grid\"><tr><th>Öğe</th><th>Durum</th></tr><tr><td>Son üretim</td><td>{}</td></tr><tr><td>Güncelleme sıklığı</td><td>Her ay 1 ve 16. gün</td></tr><tr><td>HTML sayfa sayısı</td><td>{}</td></tr><tr><td>JavaScript zorunlu mu?</td><td>Hayır</td></tr><tr><td>AI/Gemini</td><td>Kullanılmıyor</td></tr></table>".format(esc(today.strftime('%Y-%m-%d %H:%M')), len(pages))
    write("status.html", page("Sistem durumu", status_body))


def main():
    today = now_istanbul()
    cache = load_cache()
    weather = cached(cache, "weather", get_weather, {"temp":"--","wind":"--","sunrise":"--","sunset":"--","days":[]})
    prayer = cached(cache, "prayer:" + today.strftime("%Y%m%d"), lambda: get_prayer(today), {})
    rates = cached(cache, "rates", get_rates, {})
    crypto = cached(cache, "crypto", get_crypto, {})
    quakes = cached(cache, "earthquakes", get_earthquakes, [])
    otd = cached(cache, "onthisday:" + today.strftime("%m%d"), lambda: get_onthisday(today), {"events":[],"births":[],"deaths":[]})
    groups = get_rss_groups(cache)
    online_reading = cached(cache, "online_reading:" + today.strftime("%Y%m%d"), lambda: get_online_reading(today), {})
    save_cache(cache)

    render_weather(weather)
    render_earthquakes(quakes)
    render_crypto(crypto)
    render_onthisday(otd)
    render_radio()
    render_static_service_pages(rates)
    render_rss_page(groups)
    titles = {"turkiye":"Türkiye haberleri", "europe":"Avrupa haberleri", "world":"Dünya haberleri", "science":"Bilim", "technology":"Teknoloji", "economy":"Ekonomi", "sports":"Spor"}
    for slug, title in titles.items():
        render_news_page("turkiye-gundem" if slug == "turkiye" else slug, title, groups.get(slug, []))
    render_daily_reading(today, online_reading)
    render_index(today, weather, prayer, rates, groups, crypto)
    render_support_files(today)
    print("OK generated", today.isoformat())

if __name__ == "__main__":
    main()
