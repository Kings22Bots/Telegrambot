import os
import yt_dlp
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = "8731814924:AAGx2vfmMc00ywb0erHTFq3KsbmHBiOjHBM"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Send command:\n\n"
        "/yt <link> - download best quality\n"
        "/yt720 <link> - download 720p\n"
        "/yt360 <link> - download 360p"
    )

async def download(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if len(context.args) == 0:
        await update.message.reply_text("Send link after command")
        return

    url = context.args[0]

    quality = "best"
    if update.message.text.startswith("/yt720"):
        quality = "bestvideo[height<=720]+bestaudio/best[height<=720]"
    elif update.message.text.startswith("/yt360"):
        quality = "bestvideo[height<=360]+bestaudio/best[height<=360]"

    await update.message.reply_text("Downloading...")

    ydl_opts = {
        "format": quality,
        "outtmpl": "video.%(ext)s",
        "merge_output_format": "mp4"
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    for file in os.listdir():
        if file.startswith("video"):
            await update.message.reply_video(video=open(file, "rb"))
            os.remove(file)

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("yt", download))
app.add_handler(CommandHandler("yt720", download))
app.add_handler(CommandHandler("yt360", download))

app.run_polling()