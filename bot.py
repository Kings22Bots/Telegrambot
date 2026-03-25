import os
import glob
import subprocess
import logging
import random
import time
import asyncio
from telegram import Update, InputMediaPhoto, InputMediaVideo
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# --- CONFIGURATION ---
TOKEN = '8636548271:AAEwAzj_qF3yS2opnixI_GbviPUpR6sobCo'  
DOWNLOAD_DIR = 'temp_downloads'
COOKIES = 'cookies.txt'

# List of real browser User-Agents to rotate
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1"
]

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

async def download_media(url):
    """Downloads media using randomized headers and delays to mimic human behavior."""
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)
    
    # 1. Humanizing: Random delay before starting the request
    await asyncio.sleep(random.uniform(3.0, 7.0))
    
    # Select a random User-Agent
    ua = random.choice(USER_AGENTS)

    # 2. gallery-dl with custom User-Agent
    g_cmd = [
        'gallery-dl',
        '--cookies', COOKIES,
        '--user-agent', ua,
        '--directory', DOWNLOAD_DIR,
        '--filename', 'img_{id}_{num}.{extension}',
        url
    ]
    
    # 3. yt-dlp with custom User-Agent and socket timeout
    y_cmd = [
        'yt-dlp',
        '--cookies', COOKIES,
        '--user-agent', ua,
        '-f', 'bestvideo[ext=mp4]+bestaudio[m4a]/best[ext=mp4]/best',
        '--socket-timeout', '30',
        '-P', DOWNLOAD_DIR,
        '-o', 'vid_%(id)s.%(ext)s',
        '--no-playlist',
        url
    ]

    subprocess.run(g_cmd, capture_output=True)
    # Short pause between engines
    await asyncio.sleep(random.uniform(1.5, 3.5))
    subprocess.run(y_cmd, capture_output=True)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if "instagram.com" not in url:
        return

    status = await update.message.reply_text("🔍 Analyzing link safely...")

    for f in glob.glob(f'{DOWNLOAD_DIR}/*'):
        try: os.remove(f)
        except: pass
    
    await download_media(url)

    media_group = []
    downloaded_files = sorted(glob.glob(f'{DOWNLOAD_DIR}/*'))

    for path in downloaded_files:
        ext = path.lower()
        try:
            if ext.endswith(('.jpg', '.jpeg', '.png', '.webp')):
                media_group.append(InputMediaPhoto(open(path, 'rb')))
            elif ext.endswith(('.mp4', '.mov', '.m4v')):
                media_group.append(InputMediaVideo(open(path, 'rb')))
        except Exception as e:
            logging.error(f"Error opening file {path}: {e}")

    if media_group:
        # Telegram limit is 10 items per album
        for i in range(0, len(media_group), 10):
            await update.message.reply_media_group(media_group[i:i+10])
    else:
        await update.message.reply_text("❌ Session blocked. Refresh your cookies.txt and try again later.")

    await status.delete()

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("🚀 Bot is running with anti-detection...")
    app.run_polling()

if __name__ == '__main__':
    main()
