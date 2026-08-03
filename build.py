import os
import json
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

TR_TZ = timezone(timedelta(hours=3))

def fetch_tcmb():
    """TCMB Canlı Döviz Kurlarını Çeker"""
    try:
        url = "https://www.tcmb.gov.tr/kullar/today.xml"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            root = ET.fromstring(resp.read())
        rates = {}
        for currency in root.findall('Currency'):
            code = currency.attrib.get('CurrencyCode')
            if code in ['USD', 'EUR', 'GBP']:
                rates[code] = currency.findtext('ForexBuying', '---')
        return rates
    except Exception:
        return {"USD": "---", "EUR": "---", "GBP": "---"}

def fetch_rss_news():
    """Canlı Son Dakika Haber Başlıklarını Çeker"""
    feeds = [
        ("TRT Haber", "https://www.trthaber.com/sondakika_articles.rss"),
        ("BBC Türkçe", "https://feeds.bbci.co.uk/turkce/rss.xml")
    ]
    all_news = []
    for source, url in feeds:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as resp:
                root = ET.fromstring(resp.read())
            channel = root.find('channel')
            if channel is not None:
                for item in channel.findall('item')[:5]:
                    title = item.findtext('title', 'Başlık Yok')
                    link = item.findtext('link', '#')
                    all_news.append({"source": source, "title": title, "link": link})
        except Exception as e:
            print(f"Haber çekme hatası ({source}): {e}")
    return all_news

def get_word_of_the_day(date_str):
    """Günün Kelime Oyunu Hedefini Belirler"""
    words = [
        {"word": "KALEM", "hint": "Yazı yazmaya yarayan araç"},
        {"word": "KİTAP", "hint": "Ciltli veya ciltsiz kağıt yapraklar dizisi"},
        {"word": "DENİZ", "hint": "Yer kabuğunun çukur bölümlerini kaplayan büyük su kütlesi"},
        {"word": "GÜNEŞ", "hint": "Dünyamıza ısı ve ışık veren yıldız"},
        {"word": "TOPRAK", "hint": "Yer kabuğunun en üstünde bulunan örtü"},
        {"word": "ZAMAN", "hint": "Bir işin, bir oluşun içinde geçtiği süre"}
    ]
    idx = sum(ord(c) for c in date_str) % len(words)
    return words[idx]

def build_site():
    now = datetime.now(TR_TZ)
    date_str = now.strftime("%d.%m.%Y")
    time_str = now.strftime("%H:%M")
    
    tcmb = fetch_tcmb()
    news = fetch_rss_news()
    word_info = get_word_of_the_day(date_str)
    
    html_content = f"""<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Günlük Portal | {date_str}</title>
    <style>
        body {{ font-family: monospace, sans-serif; background: #121212; color: #e0e0e0; margin: 0; padding: 15px; line-height: 1.5; }}
        a {{ color: #4da6ff; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        .header {{ border-bottom: 2px solid #333; padding-bottom: 10px; margin-bottom: 20px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 15px; }}
        .card {{ background: #1e1e1e; border: 1px solid #333; padding: 15px; border-radius: 4px; }}
        h2 {{ margin-top: 0; color: #ff9800; font-size: 1.2em; border-bottom: 1px dashed #444; padding-bottom: 5px; }}
        ul {{ padding-left: 20px; margin: 5px 0; }}
        li {{ margin-bottom: 8px; }}
        button {{ background: #ff9800; color: #000; border: none; padding: 6px 12px; cursor: pointer; font-weight: bold; border-radius: 3px; }}
        input[type="text"] {{ padding: 6px; background: #222; color: #fff; border: 1px solid #444; width: 60%; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🇹🇷 Günlük Metin Portalı</h1>
        <p>Son Otomatik Güncelleme: <strong>{date_str} - {time_str}</strong></p>
    </div>

    <div class="grid">
        <div class="card">
            <h2>📊 Piyasalar (TCMB)</h2>
            <p><strong>USD/TRY:</strong> {tcmb.get('USD', '---')} ₺</p>
            <p><strong>EUR/TRY:</strong> {tcmb.get('EUR', '---')} ₺</p>
            <p><strong>GBP/TRY:</strong> {tcmb.get('GBP', '---')} ₺</p>
        </div>

        <div class="card">
            <h2>🎯 Günün Kelime Oyunu (5 Harf)</h2>
            <p>İpucu: <em>{word_info['hint']}</em></p>
            <input type="text" id="guessInput" maxlength="5" placeholder="Tahmininiz...">
            <button onclick="checkGuess()">Tahmin Et</button>
            <p id="gameResult"></p>
        </div>

        <div class="card">
            <h2>⏱️ Pomodoro Odaklanma Sayacı</h2>
            <p id="timerDisplay" style="font-size: 1.5em; font-weight: bold;">25:00</p>
            <button onclick="startTimer()">Başlat</button>
            <button onclick="resetTimer()">Sıfırla</button>
        </div>

        <div class="card" style="grid-column: 1 / -1;">
            <h2>📰 Canlı Son Dakika Haber Başlıkları</h2>
            <ul>
"""
    for item in news:
        html_content += f'                <li>[{item["source"]}] <a href="{item["link"]}" target="_blank">{item["title"]}</a></li>\n'
    
    html_content += f"""            </ul>
        </div>
    </div>

    <script>
        const targetWord = '{word_info["word"]}';
        function checkGuess() {{
            const input = document.getElementById('guessInput').value.toUpperCase();
            const res = document.getElementById('gameResult');
            if(input.length !== 5) {{ res.innerText = 'Lütfen 5 harfli kelime girin.'; return; }}
            if(input === targetWord) {{ res.innerText = '🎉 Tebrikler! Doğru Bildiniz!'; }}
            else {{ res.innerText = '❌ Yanlış tahmin, tekrar deneyin!'; }}
        }}

        let timer;
        let seconds = 1500;
        function startTimer() {{
            clearInterval(timer);
            timer = setInterval(() => {{
                if(seconds <= 0) {{ clearInterval(timer); alert('Süre doldu!'); return; }}
                seconds--;
                let m = Math.floor(seconds / 60);
                let s = seconds % 60;
                document.getElementById('timerDisplay').innerText = (m<10?'0':'')+m + ':' + (s<10?'0':'')+s;
            }}, 1000);
        }}
        function resetTimer() {{ clearInterval(timer); seconds = 1500; document.getElementById('timerDisplay').innerText = '25:00'; }}
    </script>
</body>
</html>
"""
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)

if __name__ == "__main__":
    build_site()
