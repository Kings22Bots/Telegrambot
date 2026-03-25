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

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1"
]

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

async def download_media(url):
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)
    
    await asyncio.sleep(random.uniform(2.0, 5.0))
    ua = random.choice(USER_AGENTS)

    # 1. Image Downloader
    g_cmd = [
        'gallery-dl',
        '--cookies', COOKIES,
        '--user-agent', ua,
        '--directory', DOWNLOAD_DIR,
        '--filename', 'img_{id}_{num}.{extension}',
        url
    ]
    
    # 2. Video Downloader (Optimized for Merging)
    y_cmd = [
        'yt-dlp',
        '--cookies', COOKIES,
        '--user-agent', ua,
        # Updated format string to force best quality and merge into mp4
        '-f', 'bv[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv+ba/b', 
        '--merge-output-format', 'mp4',
        '--postprocessor-args', 'ffmpeg:-c:v libx264 -c:a aac', # Ensures compatibility
        '-P', DOWNLOAD_DIR,
        '-o', 'vid_%(id)s.%(ext)s',
        '--no-playlist',
        url
    ]

    # Run gallery-dl first
    subprocess.run(g_cmd, capture_output=True)
    
    # Run yt-dlp to handle video/audio merging
    process = subprocess.run(y_cmd, capture_output=True, text=True)
    
    if process.returncode != 0:
        logging.error(f"yt-dlp Error: {process.stderr}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if "instagram.com" not in url: return

    status = await update.message.reply_text("📥 Downloading high quality...")

    # Clear old files
    for f in glob.glob(f'{DOWNLOAD_DIR}/*'):
        try: os.remove(f)
        except: pass
    
    await download_media(url)

    media_group = []
    # Get all files including the merged mp4
    downloaded_files = sorted(glob.glob(f'{DOWNLOAD_DIR}/*'))

    for path in downloaded_files:
        ext = path.lower()
        if ext.endswith(('.jpg', '.jpeg', '.png', '.webp')):
            media_group.append(InputMediaPhoto(open(path, 'rb')))
        elif ext.endswith(('.mp4', '.mov', '.m4v', '.mkv')):
            media_group.append(InputMediaVideo(open(path, 'rb')))

    if media_group:
        for i in range(0, len(media_group), 10):
            await update.message.reply_media_group(media_group[i:i+10])
    else:
        await update.message.reply_text("❌ Failed to merge audio/video. Is ffmpeg installed?")

    await status.delete()

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("🚀 Bot started. Ensure 'ffmpeg' is installed in Termux.")
    app.run_polling()

if __name__ == '__main__':
    main()
    
