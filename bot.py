import os
import discord
import sqlite3
from discord.ext import commands

TOKEN = os.getenv("TOKEN")

# STORAGE CHANNEL IDS (PUT YOUR CHANNEL IDS HERE)
RENDERS_CHANNEL_ID = 1480048829297328228
THEMES_CHANNEL_ID = 1480048843310497924
RBXM_CHANNEL_ID = 1480048869734744184

DB_FILE = "database.db"
MAX_FILE_SIZE = 8 * 1024 * 1024  # 8MB limit

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)


# ---------------- DATABASE ---------------- #

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS assets (
            server_id TEXT,
            name TEXT,
            render_msg_id TEXT,
            theme_msg_id TEXT,
            rbxm_msg_id TEXT,
            PRIMARY KEY (server_id, name)
        )
        """)
        conn.commit()


# ---------------- READY ---------------- #

@bot.event
async def on_ready():
    init_db()
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")


# ---------------- SAVE HELPER ---------------- #

async def save_asset(interaction, name, attachment, channel_id, column):
    if attachment.size > MAX_FILE_SIZE:
        await interaction.response.send_message("File too large (8MB max).", ephemeral=True)
        return

    storage_channel = bot.get_channel(channel_id)
    if not storage_channel:
        await interaction.response.send_message("Storage channel not found.", ephemeral=True)
        return

    msg = await storage_channel.send(file=await attachment.to_file())

    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("""
        INSERT INTO assets (server_id, name, render_msg_id, theme_msg_id, rbxm_msg_id)
        VALUES (?, ?, NULL, NULL, NULL)
        ON CONFLICT(server_id, name) DO NOTHING
        """, (interaction.guild_id, name.lower()))

        conn.execute(f"""
        UPDATE assets
        SET {column} = ?
        WHERE server_id = ? AND name = ?
        """, (msg.id, interaction.guild_id, name.lower()))

        conn.commit()

    await interaction.response.send_message(f"Saved under `{name}`.")


# ---------------- COMMANDS ---------------- #

@bot.tree.command(name="addrender", description="Upload a render image")
async def addrender(interaction: discord.Interaction, name: str, image: discord.Attachment):
    await save_asset(interaction, name, image, RENDERS_CHANNEL_ID, "render_msg_id")


@bot.tree.command(name="addtheme", description="Upload a theme audio")
async def addtheme(interaction: discord.Interaction, name: str, audio: discord.Attachment):
    await save_asset(interaction, name, audio, THEMES_CHANNEL_ID, "theme_msg_id")


@bot.tree.command(name="addrbxm", description="Upload an RBXM file")
async def addrbxm(interaction: discord.Interaction, name: str, file: discord.Attachment):
    await save_asset(interaction, name, file, RBXM_CHANNEL_ID, "rbxm_msg_id")


@bot.tree.command(name="getall", description="Get all assets under a name")
async def getall(interaction: discord.Interaction, name: str):
    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.execute("""
        SELECT render_msg_id, theme_msg_id, rbxm_msg_id
        FROM assets
        WHERE server_id = ? AND name = ?
        """, (interaction.guild_id, name.lower()))

        row = cur.fetchone()

    if not row:
        await interaction.response.send_message("Nothing found.", ephemeral=True)
        return

    files = []

    for msg_id, channel_id in zip(
        row,
        [RENDERS_CHANNEL_ID, THEMES_CHANNEL_ID, RBXM_CHANNEL_ID]
    ):
        if msg_id:
            channel = bot.get_channel(channel_id)
            try:
                msg = await channel.fetch_message(int(msg_id))
                if msg.attachments:
                    files.append(await msg.attachments[0].to_file())
            except:
                pass

    if not files:
        await interaction.response.send_message("No files stored.", ephemeral=True)
        return

    await interaction.response.send_message(files=files)


bot.run(TOKEN)