import os
import json
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

TR_TZ = timezone(timedelta(hours=3))

def fetch_url(url, timeout=10):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except Exception:
        return None

def fetch_tcmb():
    data = fetch_url("https://www.tcmb.gov.tr/kullar/today.xml")
    rates = {"USD": "---", "EUR": "---", "GBP": "---", "CHF": "---"}
    if data:
        try:
            root = ET.fromstring(data)
            for currency in root.findall('Currency'):
                code = currency.attrib.get('CurrencyCode')
                if code in rates:
                    rates[code] = currency.findtext('ForexBuying', '---')
        except Exception:
            pass
    return rates

def fetch_earthquakes():
    data = fetch_url("https://api.orhanaydogdu.com.tr/deprem/kandilli/live")
    eqs = []
    if data:
        try:
            parsed = json.loads(data.decode('utf-8'))
            for item in parsed.get('result', [])[:6]:
                eqs.append({
                    "title": item.get('title', 'Bilinmiyor'),
                    "mag": item.get('mag', '-'),
                    "depth": item.get('depth', '-'),
                    "date": item.get('date', '')
                })
        except Exception:
            pass
    return eqs

def fetch_rss_feed(url, limit=5):
    items = []
    data = fetch_url(url)
    if data:
        try:
            root = ET.fromstring(data)
            channel = root.find('channel')
            if channel is None: channel = root
            for item in channel.findall('item')[:limit]:
                title = item.findtext('title', 'Başlık Yok').strip()
                link = item.findtext('link', '#').strip()
                items.append({"title": title, "link": link})
        except Exception:
            pass
    return items

def get_daily_culture(date_str):
    seed = sum(ord(c) for c in date_str)
    
    quotes = [
        {"quote": "Hayatta en hakiki mürşit ilimdir, fendir.", "author": "Mustafa Kemal Atatürk"},
        {"quote": "Bilgi özgürleştirir, disiplin menzile ulaştırır.", "author": "Felsefe Deyişi"},
        {"quote": "Sadece bir yaşamımız var ve onu anlamlı kılmak bizim elimizde.", "author": "Doğan Cüceloğlu"},
        {"quote": "Zorluklar, başarının değerini artıran süslerdir.", "author": "Molière"}
    ]
    
    poems = [
        {"title": "Sessiz Gemi", "author": "Yahya Kemal Beyatlı", "text": "Artık demir almak günü gelmişse zamandan,\nMeçhule giden bir gemi kalkar bu limandan.\nHiç yolcusu yokmuş gibi sessizce alır yol;\nSallanmaz o kalkışta ne mendil ne de bir kol."},
        {"title": "Desem Ki", "author": "Cahit Sıtkı Tarancı", "text": "Desem ki vakitlerden bir Nisan akşamıdır,\nRüzgarların en ferahlatıcısı senden esiyor,\nSende örselenmiş ruhumun en derin yarası,\nSende başım, sende ellerim, sende ayaklarım."},
        {"title": "Anlatamıyorum", "author": "Orhan Veli Kanık", "text": "Ağlasam sesimi duyar mısınız,\nMısralarımda;\nDokunabilir misiniz,\nGözyaşlarıma, ellerinizle?"}
    ]
    
    words = [
        {"tr": "Mütefekkir", "tr_desc": "Düşünür, felsefi derinliği olan kimse.", "en": "Resilient", "en_desc": "Zorluklar karşısında çabuk toparlanan.", "latin": "Carpe Diem", "latin_desc": "Günü yakala, anı yaşa."},
        {"tr": "Gönül", "tr_desc": "Sevgi, duygu ve arzuların kaynağı olan iç dünya.", "en": "Serendipity", "en_desc": "Tesadüfen güzel bir şey bulma şansı.", "latin": "Amor Fati", "latin_desc": "Kaderini sev."},
        {"tr": "Sükûnet", "tr_desc": "Durgunluk, dinginlik, huzur hali.", "en": "Ethereal", "en_desc": "Ruhani, son derece narin ve güzel.", "latin": "Per Aspera Ad Astra", "latin_desc": "Zorluklardan yıldızlara."}
    ]
    
    wordle_pool = [
        {"word": "KALEM", "hint": "Yazı yazmaya yarayan araç"},
        {"word": "KİTAP", "hint": "Ciltli kağıt yapraklar dizisi"},
        {"word": "DENİZ", "hint": "Büyük su kütlesi"},
        {"word": "GÜNEŞ", "hint": "Isı ve ışık kaynağı yıldızımz"},
        {"word": "TOPRAK", "hint": "Yer kabuğunun üst örtüsü"}
    ]

    return {
        "quote": quotes[seed % len(quotes)],
        "poem": poems[seed % len(poems)],
        "words": words[seed % len(words)],
        "wordle": wordle_pool[seed % len(wordle_pool)]
    }

def build_site():
    now = datetime.now(TR_TZ)
    date_str = now.strftime("%d.%m.%Y")
    time_str = now.strftime("%H:%M")

    tcmb = fetch_tcmb()
    eqs = fetch_earthquakes()
    culture = get_daily_culture(date_str)

    # Canlı RSS Akışları
    news_tr = fetch_rss_feed("https://www.trthaber.com/sondakika_articles.rss", 5)
    news_world = fetch_rss_feed("https://feeds.bbci.co.uk/turkce/rss.xml", 5)
    news_tech = fetch_rss_feed("https://www.webtekno.com/rss.xml", 5)

    html_content = f"""<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Günlük Portal | {date_str}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace; background: #121212; color: #e0e0e0; margin: 0; padding: 20px; line-height: 1.6; }}
        a {{ color: #64b5f6; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        .header {{ border-bottom: 2px solid #333; padding-bottom: 10px; margin-bottom: 25px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; }}
        .header h1 {{ margin: 0; font-size: 1.6em; color: #fff; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 20px; }}
        .card {{ background: #1e1e1e; border: 1px solid #333; border-radius: 6px; padding: 18px; }}
        .card-full {{ grid-column: 1 / -1; }}
        h2 {{ margin-top: 0; color: #ffb74d; font-size: 1.15em; border-bottom: 1px solid #333; padding-bottom: 8px; font-weight: 600; }}
        ul {{ padding-left: 18px; margin: 8px 0; }}
        li {{ margin-bottom: 8px; }}
        .badge {{ background: #333; color: #ffb74d; padding: 2px 6px; border-radius: 3px; font-size: 0.8em; margin-right: 6px; }}
        button {{ background: #ffb74d; color: #121212; border: none; padding: 6px 12px; font-weight: bold; cursor: pointer; border-radius: 4px; }}
        input[type="text"], textarea {{ background: #2a2a2a; color: #fff; border: 1px solid #444; padding: 8px; border-radius: 4px; width: 100%; box-sizing: border-box; }}
        .poem-box {{ background: #181818; padding: 12px; border-left: 3px solid #ffb74d; white-space: pre-line; font-style: italic; }}
    </style>
</head>
<body>

    <div class="header">
        <div>
            <h1>🇹🇷 Türkiye Günlük Metin Portalı</h1>
            <small style="color: #888;">Otomatik Güncelleme: {date_str} - {time_str} (TSİ)</small>
        </div>
        <div>
            <button onclick="toggleTheme()">🌓 Tema</button>
        </div>
    </div>

    <div class="grid">

        <!-- 1. PİYASALAR VE EKONOMİ -->
        <div class="card">
            <h2>📊 Finans & Kurlar (TCMB)</h2>
            <p><span class="badge">USD</span> {tcmb.get('USD', '---')} ₺</p>
            <p><span class="badge">EUR</span> {tcmb.get('EUR', '---')} ₺</p>
            <p><span class="badge">GBP</span> {tcmb.get('GBP', '---')} ₺</p>
            <p><span class="badge">CHF</span> {tcmb.get('CHF', '---')} ₺</p>
        </div>

        <!-- 2. GÜNÜN KELİME OYUNU -->
        <div class="card">
            <h2>🎯 Günün Kelime Oyunu (Wordle)</h2>
            <p>İpucu: <em>{culture['wordle']['hint']}</em></p>
            <div style="display:flex; gap:8px;">
                <input type="text" id="guessInput" maxlength="5" placeholder="5 Harfli Kelime">
                <button onclick="checkGuess()">Dene</button>
            </div>
            <p id="gameResult" style="margin-top:10px; font-weight:bold;"></p>
        </div>

        <!-- 3. KİŞİSEL NOTLAR & TO-DO -->
        <div class="card">
            <h2>📝 Günlük Not Defterim (Yerel)</h2>
            <textarea id="userNotes" rows="3" placeholder="Notlarınızı buraya yazın (Otomatik saklanır)..."></textarea>
            <button onclick="saveNotes()" style="margin-top:6px;">Kaydet</button>
        </div>

        <!-- 4. TÜRKİYE GÜNDEM HABERLERİ -->
        <div class="card">
            <h2>🇹🇷 Türkiye Gündemi</h2>
            <ul>
"""
    for n in news_tr:
        html_content += f'                <li><a href="{n["link"]}" target="_blank">{n["title"]}</a></li>\n'

    html_content += """            </ul>
        </div>

        <!-- 5. DÜNYA & DİŞ HABERLER -->
        <div class="card">
            <h2>🌍 Dünya & Avrupa</h2>
            <ul>
"""
    for n in news_world:
        html_content += f'                <li><a href="{n["link"]}" target="_blank">{n["title"]}</a></li>\n'

    html_content += """            </ul>
        </div>

        <!-- 6. BİLİM VE TEKNOLOJİ -->
        <div class="card">
            <h2>💻 Bilim & Teknoloji</h2>
            <ul>
"""
    for n in news_tech:
        html_content += f'                <li><a href="{n["link"]}" target="_blank">{n["title"]}</a></li>\n'

    html_content += f"""            </ul>
        </div>

        <!-- 7. KÜLTÜR & GÜNÜN KELİMELERİ -->
        <div class="card">
            <h2>📚 Günün Sözcükleri & Dil</h2>
            <p><strong>Türkçe:</strong> <span class="badge">{culture['words']['tr']}</span> {culture['words']['tr_desc']}</p>
            <p><strong>İngilizce:</strong> <span class="badge">{culture['words']['en']}</span> {culture['words']['en_desc']}</p>
            <p><strong>Latince Deyim:</strong> <span class="badge">{culture['words']['latin']}</span> {culture['words']['latin_desc']}</p>
        </div>

        <!-- 8. GÜNÜN ŞİİRİ -->
        <div class="card">
            <h2>🎭 Günün Şiiri</h2>
            <p><strong>{culture['poem']['title']}</strong> - <em>{culture['poem']['author']}</em></p>
            <div class="poem-box">{culture['poem']['text']}</div>
        </div>

        <!-- 9. ÖZLÜ SÖZ VE DÜŞÜNCE -->
        <div class="card">
            <h2>💡 Günün Düşüncesi</h2>
            <blockquote style="margin:0; font-style:italic;">"{culture['quote']['quote']}"</blockquote>
            <p style="text-align:right; margin-top:5px;">— <strong>{culture['quote']['author']}</strong></p>
        </div>

        <!-- 10. SON DEPREMLER -->
        <div class="card card-full">
            <h2>⚠️ Son Depremler (Kandilli Rasathanesi)</h2>
            <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap:10px;">
"""
    for eq in eqs:
        html_content += f'                <div style="background:#252525; padding:8px; border-radius:4px;"><span class="badge" style="background:#d32f2f; color:#fff;">M {eq["mag"]}</span> <strong>{eq["title"]}</strong><br><small style="color:#aaa;">{eq["date"]} - Derinlik: {eq["depth"]} km</small></div>\n'

    html_content += """            </div>
        </div>

        <!-- 11. POMODORO SAYAÇ & RADYO -->
        <div class="card">
            <h2>⏱️ Odaklanma Zamanlayıcısı</h2>
            <p id="timerDisplay" style="font-size:1.6em; font-weight:bold; margin:5px 0;">25:00</p>
            <button onclick="startTimer()">Başlat</button>
            <button onclick="resetTimer()">Sıfırla</button>
        </div>

        <div class="card">
            <h2>📻 Canlı Metin Radyoları</h2>
            <p>TRT Radyo 1, TRT FM ve haber yayınları için tıklayın:</p>
            <p><a href="https://www.trtdinle.com/" target="_blank">▶️ TRT Canlı Radyo Yayınını Aç</a></p>
        </div>

    </div>

    <script>
        // Kelime Oyunu
        const targetWord = '""" + culture['wordle']['word'] + """';
        function checkGuess() {
            const input = document.getElementById('guessInput').value.toUpperCase();
            const res = document.getElementById('gameResult');
            if(input.length !== 5) { res.innerText = 'Lütfen 5 harfli kelime girin.'; return; }
            if(input === targetWord) { res.innerText = '🎉 Tebrikler! Doğru bildiniz.'; }
            else { res.innerText = '❌ Yanlış tahmin, tekrar deneyin.'; }
        }

        // Not Saklama
        document.getElementById('userNotes').value = localStorage.getItem('portal_notes') || '';
        function saveNotes() {
            localStorage.setItem('portal_notes', document.getElementById('userNotes').value);
            alert('Notlarınız tarayıcınıza kaydedildi.');
        }

        // Pomodoro
        let timer, seconds = 1500;
        function startTimer() {
            clearInterval(timer);
            timer = setInterval(() => {
                if(seconds <= 0) { clearInterval(timer); alert('Süre doldu!'); return; }
                seconds--;
                let m = Math.floor(seconds / 60), s = seconds % 60;
                document.getElementById('timerDisplay').innerText = (m<10?'0':'')+m + ':' + (s<10?'0':'')+s;
            }, 1000);
        }
        function resetTimer() { clearInterval(timer); seconds = 1500; document.getElementById('timerDisplay').innerText = '25:00'; }

        // Tema Geçişi
        function toggleTheme() {
            document.body.style.background = document.body.style.background === 'rgb(245, 245, 245)' ? '#121212' : '#f5f5f5';
            document.body.style.color = document.body.style.color === 'rgb(18, 18, 18)' ? '#e0e0e0' : '#121212';
        }
    </script>
</body>
</html>
"""
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)

if __name__ == "__main__":
    build_site()
