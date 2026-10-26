import json
import os
import random
from datetime import datetime, timedelta

import discord
from discord import app_commands

# ---------- SETTINGS ----------
DISCORD_TOKEN = "REMOVED_FOR_OBVIOUS_REASONS"

# Paste your video links here, one per line
VIDEOS = [
    "https://youtu.be/0xAHcmkayQA?si=I9m4GOHgSple-5fT",
    "https://youtu.be/aQ_oT7dQ798?si=FZAmOibAbNsFc5bM",
    "https://youtu.be/k6zYU7_QvOM?si=1eHTv0eEL5_E07Y0",
    "https://youtu.be/y6W_ZvUT3Lc?si=3ti7EBuL2qCPNHtG",
    "https://youtu.be/1gSYhfbxzfA?si=SoDo-qUiUCITLOcu",
]

WARN_FILE = "warnings.json"
# ------------------------------

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


# ---------- HELPERS ----------
def load_warns() -> dict:
    if os.path.exists(WARN_FILE):
        with open(WARN_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_warns(data: dict):
    with open(WARN_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


async def dm_user(user: discord.abc.User, text: str) -> bool:
    """Try to DM a user. Returns False if their DMs are closed."""
    try:
        await user.send(text)
        return True
    except (discord.Forbidden, discord.HTTPException):
        return False


def dm_note(sent: bool) -> str:
    return "" if sent else "\n*(I couldn't send this person a DM.)*"


async def can_moderate(interaction: discord.Interaction, member: discord.Member) -> bool:
    """Stops the action (and the DM) if it would fail anyway."""
    guild = interaction.guild
    problem = None
    if member == interaction.user:
        problem = "You can't do that to you!"
    elif member == guild.owner:
        problem = "What are you trying to do, attempting to ban the server owner? You must have 2 IQ."
    elif member.top_role >= guild.me.top_role:
        problem = "I can't do that to them (check my role position)."
    elif interaction.user != guild.owner and member.top_role >= interaction.user.top_role:
        problem = "You can't moderate someone with an equal or higher role than you."
    if problem:
        await interaction.response.send_message(problem, ephemeral=True)
        return False
    return True


# ---------- RANDOM VIDEO ----------
@tree.command(name="randomvideo", description="Get a random video from the one and only CHANNEL TECH!!!!")
async def randomvideo(interaction: discord.Interaction):
    await interaction.response.send_message(random.choice(VIDEOS))


# ---------- KICK / BAN / UNBAN ----------
@tree.command(name="kick", description="Kick a member")
@app_commands.default_permissions(kick_members=True)
@app_commands.checks.has_permissions(kick_members=True)
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason given"):
    if not await can_moderate(interaction, member):
        return
    await interaction.response.defer()

    dm_text = (
        f"You were **kicked** from **{interaction.guild.name}**. "
        f"You probably did really bad stuff there didn't you?\n"
        f"Reason: {reason}"
    )
    sent = await dm_user(member, dm_text)

    try:
        await member.kick(reason=reason)
        msg = f" Kicked {member.mention}. Reason: {reason}"
        await interaction.followup.send(msg + dm_note(sent))
    except discord.Forbidden:
        await interaction.followup.send("I can't kick that member with my HAMMER (check my role position).")


@tree.command(name="ban", description="Ban a member")
@app_commands.default_permissions(ban_members=True)
@app_commands.checks.has_permissions(ban_members=True)
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason given"):
    if not await can_moderate(interaction, member):
        return
    await interaction.response.defer()

    dm_text = f"You were **banned** from **{interaction.guild.name}**.\nReason: {reason}"
    sent = await dm_user(member, dm_text)

    try:
        await member.ban(reason=reason)
        msg = (
            f" Banned {member.mention}, they're out of here! Wooo! "
            f"And the reason is because they {reason}"
        )
        await interaction.followup.send(msg + dm_note(sent))
    except discord.Forbidden:
        await interaction.followup.send("I can't ban that person. (check my role position).")


@tree.command(name="unban", description="Unban a user by their ID")
@app_commands.default_permissions(ban_members=True)
@app_commands.checks.has_permissions(ban_members=True)
async def unban(interaction: discord.Interaction, user_id: str, reason: str = "No reason given"):
    await interaction.response.defer()
    try:
        user = await client.fetch_user(int(user_id))
        await interaction.guild.unban(user, reason=reason)
    except ValueError:
        await interaction.followup.send("That isn't a valid user ID (numbers only).")
        return
    except discord.NotFound:
        await interaction.followup.send("That user isn't banned (or doesn't exist).")
        return
    except discord.Forbidden:
        await interaction.followup.send("I don't have permission to unban.")
        return

    # Only works if they share another server with the bot
    dm_text = (
        f"You were **unbanned** from **{interaction.guild.name}**. "
        f"You better not do shit again."
    )
    sent = await dm_user(user, dm_text)

    msg = f" Unbanned **{user}**. Welcome back!"
    await interaction.followup.send(msg + dm_note(sent))


# ---------- TIMEOUT / UNTIMEOUT ----------
@tree.command(name="timeout", description="Timeout a member")
@app_commands.default_permissions(moderate_members=True)
@app_commands.checks.has_permissions(moderate_members=True)
async def timeout(
    interaction: discord.Interaction,
    member: discord.Member,
    minutes: app_commands.Range[int, 1, 40320],  # Discord's max is 28 days
    reason: str = "No reason given",
):
    if not await can_moderate(interaction, member):
        return
    await interaction.response.defer()

    try:
        await member.timeout(timedelta(minutes=minutes), reason=reason)
    except discord.Forbidden:
        await interaction.followup.send("I can't timeout that member (check my role position).")
        return

    dm_text = (
        f" You were **timed out** in **{interaction.guild.name}** "
        f"for **{minutes} minute(s)**. "
        f"I don't have to tell you to shut the fuck up anymore!\n"
        f"Reason: {reason}"
    )
    sent = await dm_user(member, dm_text)

    msg = f" {member.mention} is going to shut the fuck up for {minutes} minutes. :)"
    await interaction.followup.send(msg + dm_note(sent))


@tree.command(name="untimeout", description="Remove a member's timeout")
@app_commands.default_permissions(moderate_members=True)
@app_commands.checks.has_permissions(moderate_members=True)
async def untimeout(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason given"):
    await interaction.response.defer()
    try:
        await member.timeout(None, reason=reason)
    except discord.Forbidden:
        await interaction.followup.send("I can't do that to this member (check my role position).")
        return

    sent = await dm_user(member, f" Your timeout in **{interaction.guild.name}** was removed.")

    msg = f" {member.mention} can talk again. (hope you won't do anymore mistakes :) )"
    await interaction.followup.send(msg + dm_note(sent))


# ---------- WARN / UNWARN / WARNINGS ----------
@tree.command(name="warn", description="Warn a member")
@app_commands.default_permissions(moderate_members=True)
@app_commands.checks.has_permissions(moderate_members=True)
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason given"):
    if member.bot:
        await interaction.response.send_message("You can't warn a bot.", ephemeral=True)
        return
    if not await can_moderate(interaction, member):
        return
    await interaction.response.defer()

    data = load_warns()
    user_warns = data.setdefault(str(interaction.guild.id), {}).setdefault(str(member.id), [])
    user_warns.append({
        "reason": reason,
        "moderator": interaction.user.id,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
    })
    save_warns(data)

    dm_text = (
        f"You were **warned** in **{interaction.guild.name}**.\n"
        f"Reason: {reason}\n"
        f"Total warnings: {len(user_warns)}"
    )
    sent = await dm_user(member, dm_text)

    msg = f" Warned {member.mention} (warning #{len(user_warns)}). Reason: {reason}"
    await interaction.followup.send(msg + dm_note(sent))


@tree.command(name="warnings", description="See a member's warnings")
@app_commands.default_permissions(moderate_members=True)
@app_commands.checks.has_permissions(moderate_members=True)
async def warnings(interaction: discord.Interaction, member: discord.Member):
    user_warns = load_warns().get(str(interaction.guild.id), {}).get(str(member.id), [])
    if not user_warns:
        await interaction.response.send_message(f"{member.mention} has no warnings.", ephemeral=True)
        return
    lines = [f"**#{i}**: {w['reason']} ({w['date']})" for i, w in enumerate(user_warns, start=1)]
    text = f"Warnings for {member.mention}:\n" + "\n".join(lines)
    await interaction.response.send_message(text, ephemeral=True)


@tree.command(name="unwarn", description="Remove a warning (the latest one if no number is given)")
@app_commands.default_permissions(moderate_members=True)
@app_commands.checks.has_permissions(moderate_members=True)
async def unwarn(interaction: discord.Interaction, member: discord.Member, number: int = 0):
    data = load_warns()
    user_warns = data.get(str(interaction.guild.id), {}).get(str(member.id), [])
    if not user_warns:
        await interaction.response.send_message(f"{member.mention} has no warnings.", ephemeral=True)
        return

    index = len(user_warns) - 1 if number == 0 else number - 1
    if not 0 <= index < len(user_warns):
        text = f"Invalid number. They have {len(user_warns)} warning(s). Use /warnings to see them."
        await interaction.response.send_message(text, ephemeral=True)
        return

    await interaction.response.defer()
    removed = user_warns.pop(index)
    save_warns(data)

    dm_text = (
        f"A warning was removed in **{interaction.guild.name}**.\n"
        f"Warnings left: {len(user_warns)}"
    )
    sent = await dm_user(member, dm_text)

    msg = (
        f" Removed warning \"{removed['reason']}\" from {member.mention}. "
        f"They now have {len(user_warns)}."
    )
    await interaction.followup.send(msg + dm_note(sent))


# ---------- PURGE ----------
@tree.command(name="purge", description="Delete recent messages")
@app_commands.default_permissions(manage_messages=True)
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(interaction: discord.Interaction, amount: app_commands.Range[int, 1, 100]):
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=amount)
    await interaction.followup.send(f"Deleted {len(deleted)} messages. FUCK YOU SPAMMER", ephemeral=True)


# ---------- ERRORS + STARTUP ----------
@tree.error
async def on_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        msg = "You can't do that, you're not a Moderator, check your roles first. :)"
    else:
        raise error
    if interaction.response.is_done():
        await interaction.followup.send(msg, ephemeral=True)
    else:
        await interaction.response.send_message(msg, ephemeral=True)


@client.event
async def on_ready():
    await tree.sync()
    print(f"Logged in as {client.user}")


client.run(DISCORD_TOKEN)