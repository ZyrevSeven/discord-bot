import discord
from discord.ext import commands
import yt_dlp as youtube_dl
import asyncio
import os

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')


ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


ffmpeg_options = {
    'executable': 'C:/ffmpeg/bin/ffmpeg.exe', 
    'options' : '-vn'
}


ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)


class MusicQueue:
    def __init__(self):
        self.queue = []
        self.current_song = None
        self.is_playing = False

    def add_to_queue(self, song):
        self.queue.append(song)

    def get_next_song(self):
        if len(self.queue) > 0:
            return self.queue.pop(0)
        return None

music_queue = MusicQueue()

@bot.command(name='join', help='Memasukkan bot ke dalam voice channel')
async def join(ctx):
    if not ctx.message.author.voice:
        await ctx.send(f"{ctx.message.author.name} Tidak ada di dalam voice channel")
        return

    channel = ctx.message.author.voice.channel
    if ctx.voice_client is not None:
        return await ctx.voice_client.move_to(channel)

    await channel.connect()

@bot.command(name='leave', help='Keluar dari Voice Channel')
async def leave(ctx):
    if ctx.voice_client is None or not ctx.voice_client.is_connected():
        await ctx.send("Tidak dalam voice channel")
        return
    await ctx.voice_client.disconnect()


@bot.command(name='play', help='Putar lagu dari URL')
async def play(ctx, url):
    if ctx.voice_client is None:
        if ctx.author.voice is None:
            await ctx.send("Anda tidak berada di voice channel")
            return
        channel = ctx.author.voice.channel
        await channel.connect()

    async with ctx.typing():
        try:
            player = await YTDLSource.from_url(url, loop=bot.loop)
            if ctx.voice_client.is_playing():
                ctx.voice_client.stop()
            ctx.voice_client.play(player, after=lambda e: print('Player error: %s' % e) if e else None)
            await ctx.send(f"**Now playing:** {player.title}")
        except Exception as e:
            await ctx.send(f"Terjadi kesalahan: {str(e)}")

async def play_next_song(ctx):
    music_queue.is_playing = True
    music_queue.current_song = music_queue.get_next_song()
    if music_queue.current_song is None:
        music_queue.is_playing = False
        await ctx.send("Queue kosong, menghentikan playback.")
        return

    voice_channel = ctx.message.guild.voice_client
    if voice_channel is None:
        await ctx.send("Bot tidak berada di voice channel")
        return

    voice_channel.play(music_queue.current_song, after=lambda e: bot.loop.create_task(play_next_song(ctx)))

    await ctx.send(f"**Now playing:** {music_queue.current_song.title}")

@bot.command(name='skip', help='Skip musik yang sedang diputar')
async def skip(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
        voice_client.stop()
        await ctx.send("Skipped.")
    else:
        await ctx.send("Tidak ada musik yang diputar")

@bot.command(name='pause', help='Menghentikan sementara pemutaran musik')
async def pause(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
        voice_client.pause()
    else:
        await ctx.send("Tidak ada musik yang sedang diputar")

@bot.command(name='resume', help='Melanjutkan musik')
async def resume(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_paused():
        voice_client.resume()
    else:
        await ctx.send("Tidak ada musik yang diputar sebelumnya, Gunakan command Play")

@bot.command(name='stop', help='Menghentikan pemutaran musik')
async def stop(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
        voice_client.stop()
    else:
        await ctx.send("Tidak ada musik yang diputar!")

bot.run('YOUR_BOT_TOKEN_HERE')