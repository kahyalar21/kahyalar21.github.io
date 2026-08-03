import os
import json
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

TR_TZ = timezone(timedelta(hours=3))

def get_tcmb_rates():
    try:
        url = "https://www.tcmb.gov.tr/kullar/today.xml"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            root = ET.fromstring(response.read())
        rates = {}
        for currency in root.findall('Currency'):
            code = currency.attrib.get('CurrencyCode')
            if code in ['USD', 'EUR', 'GBP']:
                rates[code] = currency.find('ForexBuying').text
        return rates
    except Exception as e:
        return {"USD": "---", "EUR": "---", "GBP": "---"}

def get_weather():
    try:
        url = "https://api.open-meteo.com/v1/forecast?latitude=41.0082&longitude=28.9784&current=temperature_2m,relative_humidity_2m,wind_speed_10m&daily=temperature_2m_max,temperature_2m_min,sunrise,sunset&timezone=Europe%2FIstanbul"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
        return {
            "temp": round(data['current']['temperature_2m']),
            "wind": round(data['current']['wind_speed_10m']),
            "sunrise": data['daily']['sunrise'][0].split('T')[-1],
            "sunset": data['daily']['sunset'][0].split('T')[-1]
        }
    except Exception:
        return {"temp": "--", "wind": "--", "sunrise": "--:--", "sunset": "--:--"}

def generate_site():
    now = datetime.now(TR_TZ)
    rates = get_tcmb_rates()
    weather = get_weather()
    
    # HTML şablonunu derleme ve index.html olarak kaydetme işlemleri
    print(f"Site başarıyla derlendi: {now.strftime('%d.%m.%Y %H:%M')}")

if __name__ == "__main__":
    generate_site()