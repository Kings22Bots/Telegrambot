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
DOWNLOAD_DIR = '/tmp/downloads'
COOKIES = 'cookies.txt'

logging.basicConfig(level=logging.INFO)

# --- STEALTH HEADERS ---
# Cleaned up to prevent CDN blocks. Only User-Agent and Cookies are needed.
UA_STRING = 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36'

async def download_media(url):
    if not os.path.exists(DOWNLOAD_DIR): 
        os.makedirs(DOWNLOAD_DIR)
    
    await asyncio.sleep(random.uniform(2.5, 4.5))

    # 1. yt-dlp: Fetch the Playable Video 
    y_cmd_playable = [
        'yt-dlp', '--cookies', COOKIES, 
        '--user-agent', UA_STRING,
        '-f', 'bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/best', 
        '--merge-output-format', 'mp4',
        '-P', DOWNLOAD_DIR, 
        '-o', 'playable_%(id)s.%(ext)s', 
        '--no-playlist', url
    ]

    # 2. yt-dlp: Fetch the Raw Document (Max Quality)
    y_cmd_raw = [
        'yt-dlp', '--cookies', COOKIES, 
        '--user-agent', UA_STRING,
        '-f', 'bv*+ba/b', 
        '-P', DOWNLOAD_DIR, 
        '-o', 'raw_%(id)s.%(ext)s', 
        '--no-playlist', url
    ]
    
    # 3. gallery-dl: Fetches Images AND acts as a bulletproof video fallback
    g_cmd = [
        'gallery-dl', '--cookies', COOKIES, 
        '--user-agent', UA_STRING, 
        '--directory', DOWNLOAD_DIR, url
    ]

    # Run all 3 concurrently
    await asyncio.gather(
        asyncio.to_thread(subprocess.run, g_cmd, capture_output=True),
        asyncio.to_thread(subprocess.run, y_cmd_playable, capture_output=True),
        asyncio.to_thread(subprocess.run, y_cmd_raw, capture_output=True)
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if "instagram.com" not in url: return

    status = await update.message.reply_text("🛡️ Fetching Dual Formats (with gallery-dl fallback)...")
    
    for f in glob.glob(f'{DOWNLOAD_DIR}/*'): 
        try: os.remove(f)
        except: pass
    
    await download_media(url)

    files = sorted(glob.glob(f'{DOWNLOAD_DIR}/*'))
    
    playable_media = []
    document_media = []
    
    # --- SMART SORTING & FALLBACK LOGIC ---
    for path in files:
        ext = path.lower()
        filename = os.path.basename(path)

        # 1. Handle Images
        if ext.endswith(('.jpg', '.jpeg', '.png', '.webp')):
            playable_media.append(InputMediaPhoto(open(path, 'rb')))
            
        # 2. Handle yt-dlp Playable Video
        elif filename.startswith('playable_') and ext.endswith('.mp4'):
            playable_media.append(InputMediaVideo(open(path, 'rb')))
            
        # 3. Handle yt-dlp Raw Document
        elif filename.startswith('raw_'):
            document_media.append(path)
            
        # 4. THE BACKUP: If yt-dlp failed, but gallery-dl got the video, send it to BOTH!
        elif ext.endswith(('.mp4', '.mov', '.webm', '.mkv')):
            if not any(f.startswith('playable_') for f in os.listdir(DOWNLOAD_DIR)):
                playable_media.append(InputMediaVideo(open(path, 'rb')))
            if not any(f.startswith('raw_') for f in os.listdir(DOWNLOAD_DIR)):
                document_media.append(path)

    # Send Playable Media
    if playable_media:
        try:
            for i in range(0, len(playable_media), 10):
                await update.message.reply_media_group(playable_media[i:i+10])
        except Exception as e:
            logging.error(f"Playable Upload Error: {e}")

    # Send Raw Document
    if document_media:
        for doc_path in document_media:
            try:
                await update.message.reply_document(
                    document=open(doc_path, 'rb'), 
                    caption="📄 Original Source Format"
                )
            except Exception as e:
                logging.error(f"Document Upload Error: {e}")

    if not playable_media and not document_media:
        await status.edit_text("❌ Total failure. Cookie might be expired.")
    else:
        await status.delete()

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("🚀 Bot is LIVE with Smart Fallback...")
    app.run_polling()

if __name__ == '__main__':
    main()
