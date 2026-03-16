import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from telebot import apihelper
import yt_dlp
import os
import time
import glob
import subprocess

apihelper.CONNECT_TIMEOUT = 9999
apihelper.READ_TIMEOUT = 9999

TOKEN = '8636548271:AAEaR2ihZn57PIZKfWxATk57Zha_SBENunU'
bot = telebot.TeleBot(TOKEN)

url_cache = {}

def safe_edit(text, chat_id, message_id, markup=None, parse_mode=None):
    try:
        bot.edit_message_text(
            text, chat_id=chat_id, message_id=message_id, 
            reply_markup=markup, parse_mode=parse_mode
        )
    except Exception:
        pass 

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "👋 Send a link! I will generate a format table.")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    url = message.text.strip()
    
    if not url.startswith(('http://', 'https://')):
        bot.reply_to(message, "Please send a valid URL starting with http:// or https://")
        return

    status_msg = bot.reply_to(message, "🔍 Scanning terminal formats...")

    ydl_opts = {'quiet': True, 'noplaylist': True}
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            video_id = info.get('id', str(int(time.time())))
            url_cache[video_id] = url
            
            formats = info.get('formats', [])
            markup = InlineKeyboardMarkup()
            
            terminal_text = "<b>Available Video Streams:</b>\n<pre>"
            terminal_text += f"{'ID':<4} | {'Ext':<4} | "
            terminal_text += f"{'Res':<9} | {'Size':<6} | {'Codec'}\n"
            terminal_text += "-" * 38 + "\n"
            
            added_formats = set()
            button_list = []
            
            formats.reverse() 
            
            for f in formats:
                height = f.get('height')
                vcodec = str(f.get('vcodec', '')).lower()
                ext = f.get('ext', 'unk')
                fid = f.get('format_id', 'N/A')
                
                if vcodec == 'none' or not height:
                    continue
                
                if height >= 2160: res_name = "4K"
                elif height >= 1440: res_name = "2K"
                else: res_name = f"{height}p"
                
                dynamic_range = f.get('dynamic_range', '')
                if dynamic_range and 'HDR' in str(dynamic_range).upper():
                    res_name += " HDR"
                
                unique_key = f"{res_name}_{ext}"
                
                if unique_key not in added_formats:
                    added_formats.add(unique_key)
                    
                    size_bytes = f.get('filesize') or f.get('filesize_approx')
                    if size_bytes:
                        size_mb = f"{size_bytes / (1024 * 1024):.1f}M"
                    else:
                        size_mb = "N/A"
                    
                    short_codec = vcodec.split('.')[0][:4] 
                    
                    terminal_text += f"{fid:<4} | {ext:<4} | "
                    terminal_text += f"{res_name:<9} | {size_mb:<6} | "
                    terminal_text += f"{short_codec}\n"
                    
                    cb_data = f"dl|{video_id}|{fid}|{ext}"
                    btn = InlineKeyboardButton(f"{fid} ({res_name})", callback_data=cb_data)
                    button_list.append(btn)
            
            terminal_text += "</pre>\n<i>Tap a Format ID below:</i>"
            
            row = []
            for btn in button_list:
                row.append(btn)
                if len(row) == 2:
                    markup.add(*row)
                    row = []
            if row:
                markup.add(*row)
            
            audio_btn = InlineKeyboardButton("🎵 Audio", callback_data=f"dl|{video_id}|bestaudio|m4a")
            markup.add(audio_btn)
            
            safe_edit(
                terminal_text, message.chat.id, status_msg.message_id, 
                markup=markup, parse_mode='HTML'
            )

    except Exception as e:
        safe_edit(f"❌ Failed to fetch info: {e}", message.chat.id, status_msg.message_id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('dl|'))
def handle_download(call):
    _, video_id, format_id, req_ext = call.data.split('|')
    
    url = url_cache.get(video_id)
    if not url:
        bot.answer_callback_query(call.id, "Session expired. Please send the link again.")
        return

    safe_edit(
        f"⏳ Downloading Format ID [{format_id}]...", 
        call.message.chat.id, call.message.message_id
    )
    
    if format_id == 'bestaudio':
        dl_format = 'bestaudio[ext=m4a]/bestaudio/best'
        merge_fmt = 'm4a'
    elif req_ext == 'mp4':
        dl_format = f"{format_id}+bestaudio[ext=m4a]/{format_id}+bestaudio/best"
        merge_fmt = 'mp4'
    else:
        dl_format = f"{format_id}+bestaudio[ext=webm]/{format_id}+bestaudio/best"
        merge_fmt = 'mkv'

    ydl_opts = {
        'format': dl_format,
        'outtmpl': f'downloads/{video_id}.%(ext)s',
        'quiet': True,
        'concurrent_fragment_downloads': 5,
        'merge_output_format': merge_fmt
    }

    os.makedirs('downloads', exist_ok=True)
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            
        duration = info.get('duration', 0)
        width = info.get('width', 0)
        height = info.get('height', 0)
            
        video_files = [f for f in glob.glob(f"downloads/{video_id}.*") if not f.endswith('.jpg')]
        if not video_files:
            raise Exception("Video file not found.")
        file_path = video_files[0]
        file_ext = file_path.split('.')[-1].lower()

        thumb_path = None
        
        if file_ext == 'mp4':
            thumb_path = f"downloads/{video_id}_thumb.jpg"
            safe_edit("📸 Snapping thumbnail...", call.message.chat.id, call.message.message_id)
            
            subprocess.run([
                'ffmpeg', '-y', '-i', file_path, 
                '-ss', '00:00:02.000', 
                '-vframes', '1', 
                '-vf', 'scale=320:320:force_original_aspect_ratio=decrease', 
                thumb_path
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            if not os.path.exists(thumb_path):
                thumb_path = None
        else:
            safe_edit(
                "⚡ Skipping thumbnail for WebM/HDR...", 
                call.message.chat.id, call.message.message_id
            )

        safe_edit("📤 Uploading media...", call.message.chat.id, call.message.message_id)
        
        with open(file_path, 'rb') as file:
            thumb_io = open(thumb_path, 'rb') if thumb_path else None
            
            try:
                if format_id == 'bestaudio' or file_ext in ['m4a', 'mp3']:
                    bot.send_audio(
                        chat_id=call.message.chat.id, audio=file, 
                        thumbnail=thumb_io, duration=duration, timeout=9999
                    )
                elif file_ext == 'mp4':
                    bot.send_video(
                        chat_id=call.message.chat.id, video=file, 
                        thumbnail=thumb_io, duration=duration, width=width, 
                        height=height, timeout=9999, supports_streaming=True
                    )
                else:
                    bot.send_document(
                        chat_id=call.message.chat.id, document=file, timeout=9999
                    )
            finally:
                if thumb_io:
                    thumb_io.close()
        
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        
    except Exception as e:
        safe_edit(f"❌ Error:\n\n{str(e)}", call.message.chat.id, call.message.message_id)
        
    finally:
        for f in glob.glob(f"downloads/{video_id}*"):
            try:
                os.remove(f)
            except:
                pass

print("Master Bot is running!")

while True:
    try:
        bot.infinity_polling(timeout=90, long_polling_timeout=90)
    except Exception as e:
        print(f"Network drop: {e}. Reconnecting...")
        time.sleep(5)
