import nest_asyncio
nest_asyncio.apply()

import asyncio
import logging
import requests
import json
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from bs4 import BeautifulSoup
from flask import Flask
from threading import Thread
from flask import Flask
from threading import Thread

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot aktif!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)


# --- Flask Web Server ---
app = Flask('')

@app.route('/')
def home():
    return "Zara Stok Botu Çalışıyor!"

@app.route('/ping')
def ping():
    return "pong"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

# --- CONFIG ---
BOT_TOKEN = "8190673290:AAE7-xcfdZjvhMfguGYvOrmMxqreZ1C0xIc"
CHAT_ID = "1207180714"

URUN_DOSYA = "urunler.json"

if os.path.exists(URUN_DOSYA):
    with open(URUN_DOSYA, "r", encoding="utf-8") as f:
        urunler = json.load(f)
else:
    urunler = [
        {"name": "Suni Kürk Ceket", "url": "https://www.zara.com/tr/tr/suni-kurk-ceket-p06318033.html?v1=413909490"},
        {"name": "Kruvaze Kısa Ceket", "url": "https://www.zara.com/tr/tr/kruvaze-kisa-ceket-p03046066.html?v1=450363820"},
        {"name": "Çift Yüzlü Süslü Düğmeli Ceket", "url": "https://www.zara.com/tr/tr/cift-yuzlu-suslu-dugmeli-ceket-p06318032.html?v1=433418533"},
        {"name": "Pullu Mini Etek", "url": "https://www.zara.com/tr/tr/pullu-mini-etek-p03920721.html?v1=446546074"},
    ]
    with open(URUN_DOSYA, "w", encoding="utf-8") as f:
        json.dump(urunler, f, ensure_ascii=False, indent=2)

stok_durum = {}

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Stok kontrol fonksiyonu ---
def urun_stokta_mi(urun_url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0"
        }
        response = requests.get(urun_url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        return not soup.find(string=lambda text: "Tükendi" in text)
    except Exception as e:
        logger.error(f"Stok kontrol hatası: {e}")
        return False

async def stok_kontrol_job(application):
    global stok_durum, urunler
    for urun in urunler:
        stokta = urun_stokta_mi(urun["url"])
        onceki_durum = stok_durum.get(urun["url"], None)
        if onceki_durum != stokta:
            stok_durum[urun["url"]] = stokta
            if stokta:
                mesaj = f"🔥 {urun['name']} stoklara girdi!\nLink: {urun['url']}"
                await application.bot.send_message(chat_id=CHAT_ID, text=mesaj)

# --- Komutlar ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Zara Stok Takip Botuna Hoşgeldiniz!\n/yardim ile komutları görebilirsiniz.")

async def yardim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Komutlar:\n"
        "/start - Başlat\n"
        "/liste - Ürünleri göster\n"
        "/ekle <Ad> <Link> - Ürün ekle\n"
        "/sil <Link> - Ürün sil\n"
        "/yardim - Yardım menüsü"
    )

async def liste(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not urunler:
        await update.message.reply_text("Takip edilen ürün yok.")
        return
    mesaj = "Takip edilen ürünler:\n"
    for u in urunler:
        mesaj += f"- {u['name']}: {u['url']}\n"
    await update.message.reply_text(mesaj)

async def ekle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global urunler
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Kullanım: /ekle <Ad> <Link>")
        return
    ad = args[0]
    link = args[1]
    for u in urunler:
        if u["url"] == link:
            await update.message.reply_text("Bu ürün zaten takipte.")
            return
    urunler.append({"name": ad, "url": link})
    with open(URUN_DOSYA, "w", encoding="utf-8") as f:
        json.dump(urunler, f, ensure_ascii=False, indent=2)
    await update.message.reply_text(f"{ad} eklendi.")

async def sil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global urunler
    args = context.args
    if not args:
        await update.message.reply_text("Kullanım: /sil <Link>")
        return
    link = args[0]
    yeni_liste = [u for u in urunler if u["url"] != link]
    if len(yeni_liste) == len(urunler):
        await update.message.reply_text("Bu ürün listede yok.")
        return
    urunler = yeni_liste
    with open(URUN_DOSYA, "w", encoding="utf-8") as f:
        json.dump(urunler, f, ensure_ascii=False, indent=2)
    await update.message.reply_text("Ürün silindi.")

# --- Ping (self-ping) fonksiyonu ---
def ping_self():
    try:
        requests.get("http://127.0.0.1:8080/")
        logger.info("Ping atıldı.")
    except Exception as e:
        logger.error(f"Ping hatası: {e}")

# --- Main ---
async def main():
    # Flask sunucusunu başlat
    Thread(target=run_flask).start()

    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("yardim", yardim))
    application.add_handler(CommandHandler("liste", liste))
    application.add_handler(CommandHandler("ekle", ekle))
    application.add_handler(CommandHandler("sil", sil))

    scheduler = AsyncIOScheduler()
    scheduler.add_job(lambda: asyncio.create_task(stok_kontrol_job(application)), "interval", minutes=2)
    scheduler.add_job(ping_self, "interval", minutes=5)
    scheduler.start()

    await application.run_polling()

if __name__ == "__main__":
    asyncio.run(main())

