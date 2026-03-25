import os
import glob
import subprocess
import logging
import random
import asyncio
from telegram import Update, InputMediaPhoto, InputMediaVideo
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# Use Environment Variables for the Token on Railway
TOKEN = os.getenv('BOT_TOKEN', '8636548271:AAEwAzj_qF3yS2opnixI_GbviPUpR6sobCo')
DOWNLOAD_DIR = '/tmp/downloads'
COOKIES = 'cookies.txt'

logging.basicConfig(level=logging.INFO)

# 1. Anti-Detection: Mimic a real mobile device
UA_STRING = 'Mozilla/5.0 (Linux; Android 14; iQOO Z9x) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36'

STEALTH_ARGS = [
    '--header', f'User-Agent: {UA_STRING}',
    '--header', 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    '--header', 'Accept-Language: en-US,en;q=0.9',
    '--header', 'Sec-Ch-Ua-Platform: "Android"',
]

async def download_media(url):
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)
    
    # 2. Anti-Detection: Random delay to prevent "Automated Behavior" flag
    await asyncio.sleep(random.uniform(2.5, 5.5))

    # Video Downloader - The "Bulletproof" Merge Version
    y_cmd = [
        'yt-dlp',
        '--cookies', COOKIES,
        *STEALTH_ARGS, # Inject stealth headers
        '-f', 'bv[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/best',
        '--merge-output-format', 'mp4',
        '--recode-video', 'mp4',
        '--postprocessor-args', 'ffmpeg:-c:v libx264 -c:a aac',
        '-P', DOWNLOAD_DIR,
        '-o', 'vid_%(id)s.%(ext)s',
        '--no-playlist',
        url
    ]

    # Gallery-dl for images
    g_cmd = [
        'gallery-dl', 
        '--cookies', COOKIES, 
        '--user-agent', UA_STRING, # Spoof user-agent here as well
        '--directory', DOWNLOAD_DIR, 
        url
    ]

    # 3. Concurrency: Use to_thread so the bot doesn't freeze while downloading
    await asyncio.to_thread(subprocess.run, g_cmd, capture_output=True)
    await asyncio.to_thread(subprocess.run, y_cmd, capture_output=True)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if "instagram.com" not in url: return

    status = await update.message.reply_text("⚡ Processing high-quality media safely...")

    # Clear temp folder to avoid sending previous downloads
    for f in glob.glob(f'{DOWNLOAD_DIR}/*'):
        try: os.remove(f)
        except: pass
    
    await download_media(url)

    media_group = []
    files = sorted(glob.glob(f'{DOWNLOAD_DIR}/*'))

    for path in files:
        ext = path.lower()
        if ext.endswith(('.jpg', '.jpeg', '.png', '.webp')):
            media_group.append(InputMediaPhoto(open(path, 'rb')))
        elif ext.endswith(('.mp4', '.mkv', '.mov')):
            media_group.append(InputMediaVideo(open(path, 'rb')))

    if media_group:
        # Telegram limit is 10 items per album
        for i in range(0, len(media_group), 10):
            await update.message.reply_media_group(media_group[i:i+10])
    else:
        await update.message.reply_text("❌ Media extraction failed. The link might be private, or cookies need updating.")

    await status.delete()

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("🚀 Bot is running with anti-detection active...")
    app.run_polling()

if __name__ == '__main__':
    main()
    
