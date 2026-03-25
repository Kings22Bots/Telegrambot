import os
import glob
import subprocess
import logging
import random
import asyncio
from telegram import Update, InputMediaPhoto, InputMediaVideo
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# --- CONFIGURATION ---
TOKEN = os.getenv('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
DOWNLOAD_DIR = '/tmp/downloads'
COOKIES = 'cookies.txt'

logging.basicConfig(level=logging.INFO)

# --- ANTI-DETECTION HEADERS ---
UA_STRING = 'Mozilla/5.0 (Linux; Android 14; iQOO Z9x) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36'

STEALTH_ARGS = [
    '--header', f'User-Agent: {UA_STRING}',
    '--header', 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    '--header', 'Accept-Language: en-US,en;q=0.9',
    '--header', 'Sec-Ch-Ua-Platform: "Android"',
]

async def download_media(url):
    if not os.path.exists(DOWNLOAD_DIR): os.makedirs(DOWNLOAD_DIR)
    
    # Random delay to simulate human timing
    await asyncio.sleep(random.uniform(2.0, 4.5))

    # yt-dlp Auto-Best Configuration
    # bv*+ba/b means: Best Video (any format) + Best Audio, OR Best overall single file
    # Outputting to MKV ensures 4K/HDR formats like VP9 or AV1 don't get corrupted
    y_cmd = [
        'yt-dlp', '--cookies', COOKIES, *STEALTH_ARGS,
        '-f', 'bv*+ba/b',
        '--merge-output-format', 'mkv',
        '--postprocessor-args', 'ffmpeg:-c:a aac', # Standardizes audio for mobile playback
        '-P', DOWNLOAD_DIR, '-o', 'vid_%(id)s.%(ext)s', url
    ]
    
    g_cmd = [
        'gallery-dl', '--cookies', COOKIES, 
        '--user-agent', UA_STRING, 
        '--directory', DOWNLOAD_DIR, url
    ]

    await asyncio.to_thread(subprocess.run, g_cmd, capture_output=True)
    await asyncio.to_thread(subprocess.run, y_cmd, capture_output=True)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if "instagram.com" not in url: return

    status = await update.message.reply_text("🔥 Extracting the absolute highest quality (up to 4K/HDR)...")
    
    for f in glob.glob(f'{DOWNLOAD_DIR}/*'): 
        try: os.remove(f)
        except: pass
    
    await download_media(url)

    files = sorted(glob.glob(f'{DOWNLOAD_DIR}/*'))
    media = []
    
    for path in files:
        ext = path.lower()
        if ext.endswith(('.jpg', '.jpeg', '.png', '.webp')):
            media.append(InputMediaPhoto(open(path, 'rb')))
        elif ext.endswith(('.mp4', '.mkv', '.webm', '.mov')):
            media.append(InputMediaVideo(open(path, 'rb')))

    if media:
        try:
            for i in range(0, len(media), 10):
                await update.message.reply_media_group(media[i:i+10])
            await status.delete()
        except Exception as e:
            # High-quality 4K videos easily exceed Telegram's standard bot limits
            await status.edit_text(f"❌ Upload failed. The 4K file might exceed Telegram's 50MB limit.")
    else:
        await status.edit_text("❌ Download failed. Update your cookies.txt or check if the account is blocked.")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("🚀 Auto-Best 4K Downloader is LIVE...")
    app.run_polling()

if __name__ == '__main__':
    main()
    
