import os
import glob
import subprocess
import logging
import json
import random
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, InputMediaVideo
from telegram.ext import Application, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# --- CONFIGURATION ---
TOKEN = os.getenv('BOT_TOKEN', '8636548271:AAEwAzj_qF3yS2opnixI_GbviPUpR6sobCo')
DOWNLOAD_DIR = '/tmp/downloads'
COOKIES = 'cookies.txt'

logging.basicConfig(level=logging.INFO)

# Helper to get available formats
def get_formats(url):
    cmd = [
        'yt-dlp',
        '--cookies', COOKIES,
        '--dump-json',
        '--no-playlist',
        url
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return None
    
    data = json.loads(result.stdout)
    formats = []
    
    # Filter for video formats that have a known resolution
    for f in data.get('formats', []):
        if f.get('vcodec') != 'none' and f.get('height'):
            resolution = f"{f['height']}p"
            ext = f['ext']
            format_id = f['format_id']
            # We store a label for the button and the ID to download
            formats.append({
                'label': f"{resolution} ({ext})",
                'id': format_id
            })
    
    # Remove duplicates and sort by height
    unique_formats = {f['label']: f for f in formats}.values()
    return sorted(unique_formats, key=lambda x: x['label'], reverse=True)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if "instagram.com" not in url: return

    wait_msg = await update.message.reply_text("🔎 Fetching available qualities...")
    
    formats = await asyncio.to_thread(get_formats, url)
    
    if not formats:
        await wait_msg.edit_text("❌ Could not find video formats. It might be a private post or an image carousel.")
        # Fallback: Just try gallery-dl for images
        return

    # Create buttons
    keyboard = []
    for f in formats:
        # Callback data format: "dl|[format_id]|[url]"
        # Note: Telegram has a 64-byte limit for callback_data. 
        # For long URLs, we store the URL in context.user_data instead.
        context.user_data[f['id']] = url
        keyboard.append([InlineKeyboardButton(f"Download {f['label']}", callback_data=f"dl|{f['id']}")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await wait_msg.edit_text("✅ Choose your preferred quality:", reply_markup=reply_markup)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data.split('|')
    format_id = data[1]
    url = context.user_data.get(format_id)

    if not url:
        await query.edit_message_text("❌ Session expired. Please send the link again.")
        return

    await query.edit_message_text(f"🚀 Downloading {format_id} quality... please wait.")

    # 1. Clear temp folder
    if not os.path.exists(DOWNLOAD_DIR): os.makedirs(DOWNLOAD_DIR)
    for f in glob.glob(f'{DOWNLOAD_DIR}/*'): os.remove(f)

    # 2. Download specific format + best audio
    # Using 'f' flag to combine the selected video with the best available audio
    y_cmd = [
        'yt-dlp',
        '--cookies', COOKIES,
        '-f', f"{format_id}+bestaudio/best",
        '--merge-output-format', 'mp4',
        '--recode-video', 'mp4',
        '-P', DOWNLOAD_DIR,
        '-o', 'vid_%(id)s.%(ext)s',
        url
    ]
    
    await asyncio.to_thread(subprocess.run, y_cmd, capture_output=True)

    # 3. Send to user
    files = glob.glob(f'{DOWNLOAD_DIR}/*.mp4')
    if files:
        await query.message.reply_video(video=open(files[0], 'rb'), caption="✅ Here is your video!")
    else:
        await query.message.reply_text("❌ Failed to process video/audio merge.")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_callback))
    print("🚀 Bot is running with Quality Selection...")
    app.run_polling()

if __name__ == '__main__':
    main()
