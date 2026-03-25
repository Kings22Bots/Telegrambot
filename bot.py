import os
import glob
import subprocess
import logging
import random
import asyncio
from telegram import Update, InputMediaPhoto, InputMediaVideo
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# --- CONFIGURATION ---
TOKEN = '8636548271:AAEwAzj_qF3yS2opnixI_GbviPUpR6sobCo'  
DOWNLOAD_DIR = 'temp_downloads'
COOKIES = 'cookies.txt'

# --- ANTI-DETECTION HEADERS ---
# Spoofing a standard mobile device
UA_STRING = 'Mozilla/5.0 (Linux; Android 14; iQOO Z9x) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36'

STEALTH_ARGS = [
    '--header', f'User-Agent: {UA_STRING}',
    '--header', 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    '--header', 'Accept-Language: en-US,en;q=0.9',
    '--header', 'Sec-Ch-Ua-Platform: "Android"',
    '--header', 'Sec-Fetch-Mode: navigate'
]

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

async def download_media(url):
    """Downloads highest quality media using dual engines."""
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)
        
    # Anti-Detection: Random delay to mimic human behavior
    await asyncio.sleep(random.uniform(2.5, 5.5))
    
    # 1. gallery-dl: Focuses on original image quality
    g_cmd = [
        'gallery-dl',
        '--cookies', COOKIES,
        '--user-agent', UA_STRING, # Added stealth User-Agent
        '--directory', DOWNLOAD_DIR,
        '--filename', 'img_{id}_{num}.{extension}',
        url
    ]
    
    # 2. yt-dlp: Focuses on Best Video/Audio (MP4 preferred for Telegram compatibility)
    y_cmd = [
        'yt-dlp',
        '--cookies', COOKIES,
        *STEALTH_ARGS, # Added stealth headers
        # YOUR UNTOUCHED VIDEO SETTINGS BELOW:
        '-f', 'bestvideo[ext=mp4]+bestaudio[m4a]/best[ext=mp4]/best',
        '-P', DOWNLOAD_DIR,
        '-o', 'vid_%(id)s.%(ext)s',
        '--no-playlist',
        url
    ]

    # Execute both using to_thread to prevent the bot from freezing
    await asyncio.to_thread(subprocess.run, g_cmd, capture_output=True)
    await asyncio.to_thread(subprocess.run, y_cmd, capture_output=True)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if "instagram.com" not in url:
        return

    # Inform the user
    status = await update.message.reply_text("🔍 Extracting high-quality media safely...")

    # Wipe previous downloads to prevent mixing posts
    for f in glob.glob(f'{DOWNLOAD_DIR}/*'):
        try: os.remove(f)
        except: pass
    
    # Run downloaders
    await download_media(url)

    # Gather files
    media_group = []
    # Sort to keep carousel order as much as possible
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

    # Send grouped media
    if media_group:
        # Telegram limit is 10 items per album
        for i in range(0, len(media_group), 10):
            await update.message.reply_media_group(media_group[i:i+10])
    else:
        await update.message.reply_text("❌ Failed to grab media. Ensure your cookies.txt is valid and the post is public.")

    await status.delete()

def main():
    # Increase connect_timeout for large video uploads
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("🚀 Bot is running with anti-detection...")
    app.run_polling()

if __name__ == '__main__':
    main()
    
