# utils/developer.py

import time
import asyncpg
import asyncio
from hiddeout import hiddeout
from hiddeout.managers import Context
from discord import Embed, User, Forbidden, HTTPException, Message
from discord.ext.commands import Cog, hybrid_command
from aiohttp import ClientSession
from discord.ext import commands
import subprocess
from jishaku.functools import executor_function
import json
import os
import logging
from copy import deepcopy  # Ensure copy is imported correctly
from io import StringIO
from contextlib import redirect_stdout, redirect_stderr

log = logging.getLogger(__name__)







class Developer(Cog):
    def __init__(self, bot):
        self.bot: hiddeout = bot
        self.db = None
        self.blacklisted_users: set[int] = set()

    async def cog_check(self, ctx):
        # Check if the author of the command is the bot owner
        return await self.bot.is_owner(ctx.author)
    
    @commands.command(name="reload", aliases=['rl'], description="Reload all functions")
    async def reload(self, ctx: Context):
        reloaded = []
        
        # Loop through all loaded extensions (cogs)
        for extension_name in list(self.bot.extensions):
            try:
                await self.bot.reload_extension(extension_name)  # Correctly await the coroutine
                reloaded.append(extension_name)
            except Exception as e:
                # Log the error for debugging purposes
                print(f"Failed to reload {extension_name}: {e}")
                await ctx.warn(f"Failed to reload `{extension_name}`!")
        
        await ctx.approve(f"Successfully reloaded `{len(reloaded)}` features!")





    @commands.command(name="restart", aliases=['rs'], description="Restarts the bot")
    async def restart(self, ctx):
        try:
            # Store the message and channel information in a file
            restart_info = {"channel_id": 1241597404340551805, "message": "Bot has restarted successfully!"}
            with open("restart_info.json", "w") as f:
                json.dump(restart_info, f)
            log.info(f"Created restart_info.json with data: {restart_info}")

            # Use jishaku to run the pm2 command and capture the output
            prefix = (await self.bot.get_prefix(ctx.message))[0]  # Get the command prefix
            command_string = f"{prefix}jsk sh pm2 restart hidde"
            new_message = ctx.message
            new_message.content = command_string
            new_ctx = await self.bot.get_context(new_message)

            # Capture the output of the command
            f = StringIO()
            with redirect_stdout(f), redirect_stderr(f):
                await self.bot.invoke(new_ctx)
            output = f.getvalue()

            # Send the captured output as a message
            formatted_output = f"```\n{output}\n```"
            await ctx.send(formatted_output)
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")
            log.error(f"An error occurred during restart: {str(e)}")












    @commands.command(name="globalban", aliases=['gban'], description="Bans a user globally from all guilds the bot is in")
    async def globalban(self: "Developer", ctx: Context, user_id: int):
        user = await self.bot.fetch_user(user_id)
        if not user:
            return await ctx.send("User not found.")

        banned_guilds = 0
        for guild in self.bot.guilds:
            if guild.me.guild_permissions.ban_members:
                try:
                    await guild.ban(user, reason="Global ban executed.")
                    banned_guilds += 1
                except Forbidden:
                    await ctx.send(f"Failed to ban in {guild.name} (insufficient permissions).")
                except HTTPException:
                    await ctx.send(f"Failed to ban in {guild.name} (HTTP error).")

        await ctx.send(f"User {user} has been banned from {banned_guilds} guilds.")

    @commands.command(name="botavatar", aliases=['ba', 'setpfp', 'botpfp'], description="Sets bot's profile picture")
    async def botavatar(self: "Developer", ctx: Context, image: str = None):
        if not image:
            image = ctx.message.attachments[0].url

        async with ClientSession() as session:
            async with session.get(image) as response:
                if response.status != 200:
                    raise ValueError("Image unreadable.")

                img = await response.read()

        await self.bot.user.edit(avatar=img)

        embed = Embed(description=f"{self.bot.user.name} Avatar changed to")
        embed.set_image(url=image)
        await ctx.reply(embed=embed)

    @commands.command(name="botname", aliases=["bn", "changename"], description="Changes bot's name")
    async def botname(self: "Developer", ctx: Context, new_name: str):
        await ctx.guild.me.edit(nick=new_name)
        await ctx.approve(f"Changed my display name to `{new_name}`")

    @commands.command(name="selfpurge", aliases=["self", "clean"], description="Self purges the owner's messages")
    async def selfpurge(self: "Developer", ctx: Context, limit: int = 100):
        deleted = await ctx.message.channel.purge(limit=limit, check=lambda msg: msg.author == ctx.author)
        m = await ctx.approve(f"> Deleted `{len(deleted)}` messages from {ctx.author.mention}.")
        time.sleep(0.2)
        await m.delete()

    @commands.command(name="eval", aliases=['evaluate', 'ev'], description="Evaluates code")
    async def eval(self: "Developer", ctx: Context, code: str):
        await ctx.reply(f"```{eval(code)}```")

    @commands.command(name="exec", aliases=['ex'], description="Executes code")
    async def exec(self: "Developer", ctx: Context, code: str):
        await ctx.reply(f"```{exec(code)}```")

    @commands.command(name="shutdown", aliases=['sd'], description="Shuts down the bot")
    async def shutdown(self: "Developer", ctx: Context):
        await ctx.reply(f"```{self.bot.logout()}```")


    @commands.command(name="leave", aliases=['lv'], description="Leaves the guild")
    async def leave(self: "Developer", ctx: Context):
        await ctx.guild.leave()
        await ctx.approve("Successfully left the guild")

    @commands.command(name="join", aliases=['jn'], description="Generates an invite link for the bot")
    async def join(self: "Developer", ctx: Context):
        try:
            invite_link = f"https://discord.com/api/oauth2/authorize?client_id={self.bot.user.id}&permissions=8&scope=bot"
            await ctx.send(f"Use this link to invite the bot to a server: {invite_link}")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")
    
    @commands.command(name="guilds", aliases=['gs'], description="Lists guilds")
    async def guilds(self: "Developer", ctx: Context):
        embed = Embed(title="Guilds", color=0x2B2D31)
        for guild in self.bot.guilds:
            embed.add_field(name=guild.name, value=f"```{guild.id}```", inline=False)
        await ctx.reply(embed=embed)

    @commands.command(name="sync", aliases=['slash'], description="Sync slash commands with Discord")
    async def sync(self: "Developer", ctx: Context):
        await self.bot.tree.sync()
        await ctx.reply("Slash commands have been synchronized with Discord.")




    
    @commands.group(invoke_without_command=True)
    @commands.is_owner()
    async def blacklist(self, ctx):
        return await ctx.send_help(self.blacklist)
    
    @blacklist.command(name="user", help="Blacklist a user", brief="Bot owner")
    async def blacklist_user(self, ctx, member: User):
        if member.id in self.bot.owner_ids:
            return await ctx.warn("You can't blacklist a bot owner.")
    
        async with self.bot.db.acquire() as conn:
            async with conn.transaction():
                # Check if user is already blacklisted
                check = await conn.fetchrow("SELECT * FROM blacklist WHERE type = 'user' AND entity_id = $1", member.id)
                if check:
                    await conn.execute("DELETE FROM blacklist WHERE type = 'user' AND entity_id = $1", member.id)
                    await ctx.approve(f"{member.mention} is no longer blacklisted.")
                else:
                    # Insert into blacklist table
                    await conn.execute("INSERT INTO blacklist (type, entity_id, added_by) VALUES ('user', $1, $2)",
                                       member.id, ctx.author.id)
                    await ctx.approve(f"{member.mention} is now blacklisted.")
    
    @blacklist.command(name="guild", help="Blacklist a guild", brief="Bot owner")
    async def blacklist_guild(self, ctx, *, guildid: int):
        if guildid in self.bot.main_guilds:
            return await ctx.warn("You can't blacklist this guild.")
    
        async with self.bot.db.acquire() as conn:
            async with conn.transaction():
                # Check if guild is already blacklisted
                check = await conn.fetchrow("SELECT * FROM blacklist WHERE type = 'guild' AND entity_id = $1", guildid)
                if check:
                    await conn.execute("DELETE FROM blacklist WHERE type = 'guild' AND entity_id = $1", guildid)
                    await ctx.approve(f"{guildid} is no longer blacklisted.")
                else:
                    # Insert into blacklist table
                    await conn.execute("INSERT INTO blacklist (type, entity_id, added_by) VALUES ('guild', $1, $2)",
                                       guildid, ctx.author.id)
                    await ctx.approve(f"{guildid} is now blacklisted.")
        




    @commands.command(name="getinvite", aliases=['gi'], description="Generates an invite link for a specific guild by ID")
    async def getinvite(self: "Developer", ctx: Context, guild_id: int):
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return await ctx.send("Guild not found.")
    
        # Check if the bot has the necessary permissions to create an invite
        if not guild.me.guild_permissions.create_instant_invite:
            return await ctx.send("I do not have permissions to create invites in this guild.")
    
        # Try to create an invite from the first available channel
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).create_instant_invite:
                invite = await channel.create_invite(max_age=3600, reason=f"Requested by {ctx.author}")
                return await ctx.send(f"Here is an invite link: {invite.url}")
    
        await ctx.send("No suitable channel found to create an invite.")




async def setup(bot):
    await bot.add_cog(Developer(bot))
