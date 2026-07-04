# 15 Günde Bir Otomatik Güncelleme Sistemi

Bu portal tamamen statik HTML olarak kalır. Kullanıcı tarafında JavaScript gerekmez. `scripts/update.py` yaklaşık 15 günde bir veri çeker, HTML dosyalarını yeniden üretir ve eski mobil tarayıcı uyumluluğunu korur.

## Güncelleme sıklığı

GitHub Actions zamanlaması:

```yaml
- cron: "10 3 1,16 * *"
```

Bu her ayın 1. ve 16. günü UTC 03:10'da çalışır. Türkiye saatiyle yaklaşık 06:10'dur. Pratikte yaklaşık 15 günde bir güncelleme yapar.

İstersen Actions sekmesinden `Run workflow` ile elle de çalıştırabilirsin.

## Veri kaynakları

- Hava ve güneş: Open-Meteo, API anahtarı gerekmez.
- Namaz vakitleri: Aladhan şehir endpoint'i, API anahtarı gerekmez.
- Döviz: Frankfurter, API anahtarı gerekmez.
- Kripto: CoinGecko public endpoint.
- Deprem: Kandilli metin listesi. Bağlantı olmazsa önbellek kullanılır.
- Tarihte bugün: Wikimedia On This Day.
- Haberler: `data/feeds.json` içindeki RSS/Atom kaynakları.
- Radyo: `data/radio_istanbul.json` dosyasından hafif tablo.
- Günlük okuma: önce Project Gutenberg kamu malı düz metinlerinden denenir; çalışmazsa `data/readings.json` içindeki hazır 15 okuma kullanılır.

## Gemini / AI yok

Bu sürümde Gemini API kullanılmaz. API anahtarı gerekmez. Özetleme veya AI metin üretimi yoktur. Site daha basit, daha ucuz ve daha güvenilir şekilde çalışır.

## Yerel çalıştırma

```bash
cd portal
python scripts/update.py
```

Bu komut şu dosyaları günceller:

```text
index.html
weather.html
earthquakes.html
crypto.html
rss.html
on-this-day.html
articles/*.html
readings/*.html
radio/istanbul.html
archive/YYYY-MM-DD.html
sitemap.xml
robots.txt
status.html
```

## GitHub Pages kurulumu

1. Zip içeriğini GitHub reposunun köküne yükle.
2. `.github/workflows/update-site.yml` dosyasının yüklendiğinden emin ol.
3. Repository Settings > Pages:
   - Source: Deploy from a branch
   - Branch: main
   - Folder: /root
4. Repository Settings > Actions bölümünden Actions açık olsun.
5. Actions sekmesinden `Update static portal` workflow'unu bir kere elle çalıştır.

## Veri kaynağı ekleme

RSS eklemek için `data/feeds.json` dosyasına yeni kaynak ekle:

```json
{"name":"Kaynak Adı", "url":"https://example.com/rss.xml"}
```

Radyo satırı eklemek için `data/radio_istanbul.json` dosyasına yeni kayıt ekle.

Hazır günlük okuma metinlerini değiştirmek için `data/readings.json` dosyasını düzenle.

## Felsefe koruması

- HTML 4.01 Transitional
- UTF-8
- Küçük CSS
- JavaScript opsiyonel
- Görsel zorunlu değil
- Framework yok
- Sayfalar statik, hızlı ve bookmark edilebilir
- Kaynak hatasında site bozulmaz; önbellek veya sade yedek metin gösterilir
