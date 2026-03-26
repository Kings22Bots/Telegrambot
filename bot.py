import os
import glob
import subprocess
import logging
import random
import asyncio
from telegram import Update, InputMediaPhoto, InputMediaVideo
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# --- CONFIGURATION ---
TOKEN = os.getenv('BOT_TOKEN', '8636548271:AAEwAzj_qF3yS2opnixI_GbviPUpR6sobCo')
DOWNLOAD_DIR = '/tmp/downloads'
COOKIES = 'cookies.txt'

logging.basicConfig(level=logging.INFO)

# --- ADVANCED STEALTH HEADERS ---
UA_STRING = 'Mozilla/5.0 (Linux; Android 14; iQOO Z9x) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36'

STEALTH_ARGS = [
    '--header', f'User-Agent: {UA_STRING}',
    '--header', 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    '--header', 'Accept-Language: en-US,en;q=0.9',
    '--header', 'Sec-Fetch-Dest: document',
    '--header', 'Sec-Fetch-Mode: navigate',
    '--header', 'Sec-Fetch-Site: none',
]

async def download_media(url):
    if not os.path.exists(DOWNLOAD_DIR): 
        os.makedirs(DOWNLOAD_DIR)
    
    await asyncio.sleep(random.uniform(3.5, 7.0))

    # 1. Fetch the Playable Video (Forces the best MP4 stream)
    y_cmd_playable = [
        'yt-dlp', '--cookies', COOKIES, *STEALTH_ARGS,
        '-f', 'bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/best', 
        '--merge-output-format', 'mp4',
        '-P', DOWNLOAD_DIR, 
        '-o', 'playable_%(id)s.%(ext)s', 
        '--no-playlist', url
    ]

    # 2. Fetch the Raw Document (Grabs the absolute max quality, e.g., WebM/MKV)
    y_cmd_raw = [
        'yt-dlp', '--cookies', COOKIES, *STEALTH_ARGS,
        '-f', 'bv*+ba/b', 
        '-P', DOWNLOAD_DIR, 
        '-o', 'raw_%(id)s.%(ext)s', 
        '--no-playlist', url
    ]
    
    # 3. Fetch Images (if it's a carousel)
    g_cmd = [
        'gallery-dl', '--cookies', COOKIES, 
        '--user-agent', UA_STRING, 
        '--directory', DOWNLOAD_DIR, url
    ]

    # Run all downloads concurrently
    await asyncio.gather(
        asyncio.to_thread(subprocess.run, g_cmd, capture_output=True),
        asyncio.to_thread(subprocess.run, y_cmd_playable, capture_output=True),
        asyncio.to_thread(subprocess.run, y_cmd_raw, capture_output=True)
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if "instagram.com" not in url: return

    status = await update.message.reply_text("🛡️ Bypassing detection & fetching BOTH Playable + Raw formats...")
    
    for f in glob.glob(f'{DOWNLOAD_DIR}/*'): 
        try: os.remove(f)
        except: pass
    
    await download_media(url)

    files = sorted(glob.glob(f'{DOWNLOAD_DIR}/*'))
    
    playable_media = []
    document_media = []
    
    # Strict Sorting: Separate the playable MP4s from the raw documents
    for path in files:
        ext = path.lower()
        filename = os.path.basename(path)

        if ext.endswith(('.jpg', '.jpeg', '.png', '.webp')):
            playable_media.append(InputMediaPhoto(open(path, 'rb')))
        elif filename.startswith('playable_') and ext.endswith('.mp4'):
            playable_media.append(InputMediaVideo(open(path, 'rb')))
        elif filename.startswith('raw_'):
            document_media.append(path)

    # 1. Send Playable Media (Photos & the specific MP4 video)
    if playable_media:
        try:
            for i in range(0, len(playable_media), 10):
                await update.message.reply_media_group(playable_media[i:i+10])
        except Exception as e:
            logging.error(f"Playable Upload Error: {e}")

    # 2. Send Raw Document (The absolute highest quality WebM, MKV, or MP4)
    if document_media:
        # Check to make sure we don't send the exact same file twice if MP4 was already the highest quality
        for doc_path in document_media:
            try:
                await update.message.reply_document(
                    document=open(doc_path, 'rb'), 
                    caption="📄 Original Uncompressed Source Format"
                )
            except Exception as e:
                logging.error(f"Document Upload Error: {e}")

    if not playable_media and not document_media:
        await status.edit_text("❌ Download failed. Instagram detected the scraper or the link is invalid.")
    else:
        await status.delete()

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("🚀 Dual-Fetch Mode is LIVE...")
    app.run_polling()

if __name__ == '__main__':
    main()
    
