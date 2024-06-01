import datetime
import asyncio
import sys
import discord_ios
from asyncpg import create_pool
from hiddeout.patches import interaction
import json
from hiddeout.setup import logging
from hiddeout.managers.context import Context
from hiddeout.managers.help import Help
from config import owner_ids, token
import os
import subprocess

from datetime import timedelta, datetime
from hiddeout.managers.classes import Colors
from discord.ext import commands
from loguru import logger
from discord import Embed, Forbidden, HTTPException

from discord.ext.commands import (
    AutoShardedBot,
    CooldownMapping, 
    BucketType,
    CommandOnCooldown, 
    CommandError,
    CheckFailure,
    CommandNotFound,
    DisabledCommand,
    NotOwner,
    UserInputError,
    MissingRequiredArgument,
    MissingPermissions,
    when_mentioned_or,
    ExtensionNotFound,
    ExtensionNotLoaded,
    NoEntryPointError
)
from discord import Intents, AllowedMentions, Message, Guild

from pathlib import Path
from discord.utils import utcnow
from datetime import datetime
from typing import Any
log = logging.getLogger(__name__)

logger.remove()
logger.add(sys.stderr, level="INFO")

class hiddeout(AutoShardedBot):
    def __init__(self: "hiddeout"):
        super().__init__(
            auto_update=False,
            intents=Intents.all(),
            help_command=Help(),
            command_prefix=self.get_prefix,
            case_insensitive=True,
            owner_ids=owner_ids,
            allowed_mentions=AllowedMentions(
                replied_user=False,
                everyone=False,
                roles=False,
                users=True,
            ),
        )
        self.uptime: datetime = utcnow()
        self.run(
            token,
            log_handler=None,
        )

    @property
    def members(self):
        return list(self.get_all_members())

    @property
    def channels(self):
        return list(self.get_all_channels())

    @property
    def commandss(self):
        return set(self.walk_commands())

    async def setup_hook(self: "hiddeout"):
        try:
            self.db = await create_pool(
                port="5432", 
                database="postgres", 
                user="postgres", 
                host="HOST",
                password="PASSWORD",
            )
            log.info("Database connection successfully established.")
        except Exception as e:
            log.error(f"Failed to establish database connection: {e}")
    
        await self.load_extension("jishaku")
        for file in Path("features").rglob("*.py"):
            await self.load_extension(f"{'.'.join(file.parts[:-1])}.{file.stem}")

    async def get_context(self: "hiddeout", message: Message, *, cls=Context) -> Context:
        return await super().get_context(message, cls=cls)

    async def get_prefix(self, message: Message) -> Any:
        prefix = (
            await self.db.fetchval(
                """
            SELECT prefix FROM prefixes
            WHERE guild_id = $1
            """,
                message.guild.id,
            )
            or ';'
        )

        return when_mentioned_or(prefix)(self, message)
    
    async def process_commands(self: "hiddeout", message: Message):
        if not message.guild: 
            return
        
        ctx = await self.get_context(message)
        await super().process_commands(message)

    async def on_message(self, message: Message):
        if not message.guild or not self.is_ready():
            return
        
        ctx = await self.get_context(message)
        
        if message.content == f"<@{message.guild.me.id}>" or message.content == f"<@!{message.guild.me.id}>":
            prefix = (
                await self.db.fetchval(
                    """
                    SELECT prefix FROM prefixes
                    WHERE guild_id = $1
                    """,
                    message.guild.id,
                )
                or ';'
            )
            if ctx.command is None:
                await ctx.neutral(f"prefix for server  `{prefix}`")
        
        await self.process_commands(message)
        

    async def on_command_error(self: "hiddeout", ctx: Context, exception: CommandError):
        if isinstance(exception, CommandOnCooldown):
            await ctx.send(f"Command is on cooldown. Try again in {exception.retry_after:.2f}s.")
        elif isinstance(exception, commands.MissingPermissions): 
            await ctx.warn(f"You're missing the **{', '.join(exception.missing_permissions)}** permissions necessary to run this command.")
        elif isinstance(exception, MissingRequiredArgument):
            await ctx.send_help(ctx.command)
        elif isinstance(exception, commands.BotMissingPermissions): 
            await ctx.warn(f"I'm missing the **{', '.join(exception.missing_permissions)}** permissions necessary to run this command.")
        else:
            print(exception)  # Log other exceptions for debugging
    async def on_guild_join(self: "hiddeout", guild: Guild):
        channel = await self.fetch_channel(1241597404340551805)
        await channel.send(f"Joined {guild} ({guild.id}) owned by {guild.owner}")

    async def on_guild_remove(self: "hiddeout", guild: Guild):
        channel = await self.fetch_channel(1241597404340551805)
        await channel.send(f"Left {guild} ({guild.id}) owned by {guild.owner}")
    
    async def on_ready(self):
        log.info(f"Bot is online and ready. Logged in as {self.user} (ID: {self.user.id})")
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print('------')
    
        # Send a message indicating the bot is online
        message_channel = self.get_channel(1241597404340551805)
        if message_channel:
            await message_channel.send("> Bot is online")
        else:
            log.warning("Failed to find message channel with ID 1241597404340551805")
    
        # Check for the restart_info.json file and send the message if it exists
        if os.path.exists("restart_info.json"):
            log.info("Found restart_info.json file.")
            with open("restart_info.json", "r") as f:
                try:
                    data = json.load(f)
                    log.info(f"Loaded data from restart_info.json: {data}")
                    channel_id = data.get("channel_id")
                    message = data.get("message")
                    
                    # Retrieve the channel object from ID
                    channel = self.get_channel(channel_id)
                    if channel:
                        await channel.send(message)
                        log.info(f"Sent message to channel {channel_id}: {message}")
                    else:
                        log.warning(f"Failed to find channel with ID {channel_id}")
                except Exception as e:
                    log.error(f"Error loading or sending restart info: {e}")
            os.remove("restart_info.json")
            log.info("Removed restart_info.json file.")
        else:
            log.info("No restart_info.json found")







            
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())