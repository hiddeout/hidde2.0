# utils/utility.py

from hiddeout import hiddeout
from hiddeout.managers import Context
import time as t
import asyncio
from hiddeout.utils import humanize, human_timedelta
from discord.ext.commands import Cog, command, hybrid_command, has_permissions, MemberConverter
from discord import Message, Embed, Member, User, Forbidden, ButtonStyle, Permissions, utils
from datetime import datetime
import logging
from features.events import is_blacklisted
from time import time
from random import choice
from hiddeout.managers import Paginator
from discord.ui import Button, View
from aiohttp import ClientSession
import aiohttp
import json
from typing import Union
import random
from hiddeout.managers.paginator import PaginatorView
from bs4 import BeautifulSoup



log = logging.getLogger(__name__)

class Utility(Cog):

    def __init__(self, bot):
        self.bot: hiddeout = bot

    @hybrid_command(
        name="prefix",
        description="Edit your guild's prefix",
        with_app_command=True,
    )
    @has_permissions(manage_guild=True)
    async def prefix(self: "Utility", ctx: Context, prefix: str): 
        if len(prefix) > 3: 
            return await ctx.warn("Uh oh! The prefix is too long")
        
        await self.bot.db.execute(
            """
            INSERT INTO prefixes (
                guild_id,
                prefix
            ) VALUES ($1, $2)
            ON CONFLICT (guild_id)
            DO UPDATE SET prefix = $2
            """,
            ctx.guild.id, 
            prefix
        )

        return await ctx.approve(f"Guild prefix changed to `{prefix}`".capitalize())

    
    @command(name="ping")
    async def ping(self, ctx: Context) -> Message:
        """
        View the bot's latency
        """
        # List of possible responses for the ping command
        ping_responses = [
            "diddys house",
            "liveleak.com",
            "a connection to the server",
            "FREE YSL",
            "911"
        ]
    
        # Measure the time it takes to send a message
        start_send = time()
        message = await ctx.send(content="ping..")
        end_send = time()
    
        # Measure the time it takes to edit the message
        start_edit = time()
        await asyncio.sleep(0.1)
        end_edit = time()
    
        # Randomly choose a response from the list
        response = choice(ping_responses)
    
        return await message.edit(
            content=f"it took `{int(self.bot.latency * 1000)}ms` to ping **{response}** (rest: `{round((end_edit - start_edit) * 1000, 2)}ms`)"
        )

    @hybrid_command(
        name="afk",
        with_app_command=True,
    )
    async def afk(self: "Utility", ctx: Context, *, reason: str = "AFK"):
        """
        Become AFK and notify members when mentioned
        """
        await self.bot.db.execute(
            """
            INSERT INTO afk (
                user_id,
                reason
            ) VALUES ($1, $2)
            ON CONFLICT (user_id) DO NOTHING;
            """,
            ctx.author.id,
            reason[:100],
        )

        await ctx.approve(f"{ctx.author.mention}: You're now AFK with the status: **{reason}**")

    @hybrid_command(
        name="snipe",
        aliases=['sn', 'snip', 's'],
        with_app_command=True,
    )
    async def snipe(self: "Utility", ctx: Context):
        """
        Snipe the last deleted message in the channel
        """

        snipe_data = await self.bot.db.fetchrow(
            """
            SELECT author_id, content, attachment_url, deleted_at FROM snipe_messages
            WHERE channel_id = $1
            ORDER BY deleted_at DESC
            LIMIT 1
            """,
            ctx.channel.id,
        )
        if not snipe_data:
            return await ctx.warn("Nothing to snipe here!")

        author = await self.bot.fetch_user(snipe_data['author_id'])
        embed = Embed(
            description=snipe_data['content']
        )
        embed.set_author(name=author.display_name, icon_url=author.avatar.url)
        if snipe_data['attachment_url']:
            embed.set_image(url=snipe_data['attachment_url'])
        embed.set_footer(text=f"Deleted {human_timedelta(snipe_data['deleted_at'])} ago • 1/1 messages")
        return await ctx.send(embed=embed)

    @hybrid_command(
        name="editsnipe",
        aliases=['esnipe', 'es'],
        with_app_command=True,
    )
    async def editsnipe(self: "Utility", ctx: Context):
        """
        Snipe the last edited message in the channel
        """
        snipe_data = await self.bot.db.fetchrow(
            """
            SELECT author_id, content, attachment_url, edited_at FROM edit_snipe_messages
            WHERE channel_id = $1
            ORDER BY edited_at DESC
            LIMIT 1
            """,
            ctx.channel.id,
        )
        
        log.info(f"Fetched snipe data: {snipe_data}")

        if not snipe_data:
            return await ctx.warn("Nothing to snipe here!")

        author = await self.bot.fetch_user(snipe_data['author_id'])
        embed = Embed(
            color=0x2B2D31,
            description=f"📨 **{author.display_name}**: {snipe_data['content']}"
        )
        if snipe_data['attachment_url']:
            embed.set_image(url=snipe_data['attachment_url'])
        embed.set_footer(text=f"Edited {human_timedelta(snipe_data['edited_at'])} ago")
        return await ctx.send(embed=embed)

    @hybrid_command(
        name="clearsnipe",
        aliases=['csnipe', 'cs'],

        with_app_command=True,
    )
    async def clearsnipe(self: "Utility", ctx: Context):
        """
        Clear snipes in the channel
        """
        await self.bot.db.execute(
            """
            DELETE FROM snipe_messages
            WHERE channel_id = $1
            """,
            ctx.channel.id,
        )
        return await ctx.approve("Snipes cleared successfully!")

    @hybrid_command(
        name="cleareditsnipe",
        aliases=['cens', 'censnipe'],

        with_app_command=True,
    )
    async def clear_editsnipe(self: "Utility", ctx: Context):
        """
        Clear edited snipes in the channel
        """
        await self.bot.db.execute(
            """
            DELETE FROM edit_snipe_messages
            WHERE channel_id = $1
            """,
            ctx.channel.id,
        )
        return await ctx.approve("Edit snipes cleared successfully!")
    

    @command(name="namehistory", aliases=["namehist"], help="Displays the name change history of a member.")
    async def name_history(self, ctx: Context, member: Member = None):
        member = member or ctx.author  # Default to the command caller if no member is specified
        async with self.bot.db.acquire() as connection:
            history_records = await connection.fetch("SELECT old_name, new_name, changed_at FROM name_changes WHERE user_id = $1 ORDER BY changed_at DESC", member.id)
            if not history_records:
                await ctx.warn(f"No name change history found for {member.display_name}.")
                return
    
            # Create pages for the paginator
            pages = []
            per_page = 5
            for i in range(0, len(history_records), per_page):
                chunk = history_records[i:i + per_page]
                history_list = "\n".join(f"`{i+1:02}` {record['old_name']} -> {record['new_name']} (Changed: {record['changed_at'].strftime('%Y-%m-%d %H:%M:%S')})" for i, record in enumerate(chunk, start=i))
                embed = Embed(title=f"Name History for {member.display_name}", description=history_list, color=0x2F3136)
                embed.set_footer(text=f"Page {i//per_page + 1}/{(len(history_records) + per_page - 1) // per_page}")
                pages.append(embed)
    
            # Initialize and start the paginator
            paginator = Paginator(ctx, pages)
            await paginator.start()
    

    @command(aliases=["support", "inv", "invt"])
    async def invite(self, ctx):
        avatar_url = self.bot.user.avatar.url
        embed = Embed(
            description="Add the bot to your server or join our support server!"
        )
        embed.set_author(name=self.bot.user.name, icon_url=f"{avatar_url}")

        # Button to invite the bot
        invite_button = Button(
            label="Invite",
            style=ButtonStyle.url,
            url=utils.oauth_url(client_id=self.bot.user.id, permissions=Permissions(administrator=True))
        )

        # Button to join the support server
        support_button = Button(
            label="Support Server",
            style=ButtonStyle.url,
            url="https://discord.gg/MjcdS9rG"
        )

        view = View()
        view.add_item(invite_button)
        view.add_item(support_button)

        await ctx.reply(embed=embed, view=view)




async def setup(bot):
    await bot.add_cog(Utility(bot))
