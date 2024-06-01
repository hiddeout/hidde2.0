import time as t
import asyncio
from hiddeout import hiddeout
from hiddeout.utils import humanize, human_timedelta
from hiddeout.managers import Context
from typing import Union
from aiohttp import ClientSession
from discord import Message, Embed, Member, User, Permissions, Role
from discord.utils import format_dt
from discord.ext.commands import Cog, command, Author, has_permissions, RoleNotFound
from hiddeout.managers.paginator import PaginatorView
from hiddeout.managers import Paginator
from discord.ui import Button, View
from jishaku.features.root_command import *
from datetime import datetime, timezone
import aiohttp
import random


class Information(Cog):

    def __init__(self, bot):
        self.bot: hiddeout = bot


    async def avatar(self, ctx: Context, *, member: Union[Member, User] = None):
        """
        Sends the avatar of the specified user or the command invoker in an embed with a download button.
        """
        if not member:
            member = ctx.author  # Default to the command invoker if no member is specified

        avatar_url = member.display_avatar.url
        embed = discord.Embed(
            title=f"{member}'s Avatar",
        )
        embed.set_image(url=avatar_url)
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)

        # Button to download the avatar
        download_button = Button(
            label="Download Avatar",
            style=discord.ButtonStyle.url,
            url=avatar_url
        )

        view = View()
        view.add_item(download_button)

        await ctx.send(embed=embed, view=view)

    @command(
        name="userinfo",
        aliases=[
            "whois", 
            "ui", 
            "user"
        ]
    )
    async def userinfo(
        self: "Information", 
        ctx: Context, 
        *, 
        member: Union[Member, User] = Author
    ):
        await ctx.typing()

        e = Embed()  
        if isinstance(member, Member): 
            e.set_author(
                name=f"{member}", 
                icon_url=member.display_avatar.url
            )
            e.add_field(
                name="Dates", 
                value=(
                    f"**Joined:** {format_dt(member.joined_at)} ({human_timedelta(member.joined_at, accuracy=1)})\n"
                    f"**Created:** {format_dt(member.created_at)} ({human_timedelta(member.created_at, accuracy=1)})\n"
                    f"{'**Boosted:** ' + format_dt(member.premium_since) + ' (' + human_timedelta(member.premium_since, accuracy=1) + ')' if member.premium_since else ''}"
                ),
                inline=False
            )

            roles = member.roles[1:][::-1]  # Skip @everyone role and reverse list
            
            if roles:
                e.add_field(
                    name=f"Roles ({len(roles)})", 
                    value=' '.join([r.mention for r in roles]) 
                    if len(roles) < 5 
                    else ' '.join([r.mention for r in roles[:4]]) 
                    + f" ... and {len(roles)-4} more"
                )
            e.set_footer(text='ID: ' + str(member.id) + f" | {len(member.mutual_guilds)} mutual server(s)")

        elif isinstance(member, User):  # Handle User objects separately
            e.set_author(
                name=f"{member}", 
                icon_url=member.display_avatar.url
            )
            e.add_field(
                name="Created", 
                value=f"**Created:** {format_dt(member.created_at)} ({human_timedelta(member.created_at, accuracy=1)})",
                inline=False
            )
            e.set_footer(text='ID: ' + str(member.id))

        e.set_thumbnail(url=member.display_avatar.url)
        await ctx.send(embed=e)






    @command(
        name="botinfo",
        aliases=[
            'about',
            'bi'
        ]
    )
    async def botinfo(
        self: "Information",
        ctx: Context
    ):
        """
        Get info on bot
        """

        summary = [
            f"Bot created and maintained by <@971464344749629512>\n"
            f"> Bot was started `{human_timedelta(self.bot.uptime, suffix=False)} ago`\n"
            ""
        ]

        if psutil:
            try:
                proc = psutil.Process()

                with proc.oneshot():
                    try:
                        mem = proc.memory_full_info()
                        summary.append(f"Using `{natural_size(mem.rss)} physical memory` and "
                                       f"`{natural_size(mem.vms)} virtual memory`, "
                                       f"`{natural_size(mem.uss)}` of which unique to this process.")
                    except psutil.AccessDenied:
                        pass

                    try:

                        summary.append(f"Utilizing `{len(self.bot.commandss)} command(s)`.")
                    except psutil.AccessDenied:
                        pass

                    summary.append("")  # blank line
            except psutil.AccessDenied:
                summary.append(
                    "psutil is installed, but this process does not have high enough access rights "
                    "to query process information."
                )
                summary.append("")  # blank line

        cache_summary = f"`{len(self.bot.guilds):,} guild(s)` and `{len(self.bot.users):,} user(s)`"

        shard_ids = ', '.join(str(i) for i in self.bot.shards.keys())
        summary.append(
            f"This bot is sharded (Shards {shard_ids} of {self.bot.shard_count})"
            f" and can see {cache_summary}."
        )

        summary.append(f"**Average websocket latency: {round(self.bot.latency * 1000, 2)}ms**")

        e = Embed(
            description="\n".join(summary)
        ).set_thumbnail(url=self.bot.user.avatar.url)
        await ctx.send(embed=e)





    @command(
        name="avatar",
        aliases=[
            "av",
            "pfp"
        ]
    )
    async def avatar(self, ctx: Context, *, member: Union[Member, User] = None):
        """
        Sends the avatar of the specified user or the command invoker in an embed with a download button.
        """
        if not member:
            member = ctx.author  # Default to the command invoker if no member is specified

        avatar_url = member.display_avatar.url
        embed = discord.Embed(
            title=f"{member}'s Avatar",
        )
        embed.set_image(url=avatar_url)
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)

        # Button to download the avatar
        download_button = Button(
            label="Download Avatar",
            style=discord.ButtonStyle.url,
            url=avatar_url
        )

        view = View()
        view.add_item(download_button)

        await ctx.send(embed=embed, view=view)




    @command(
        name="banner",
        description="returns the banner of a user or the bot owner if no user is specified",
        usage="[user]",
        brief="returns the banner of a user"
    )
    async def banner(self, ctx: Context, user: discord.User = None):
        if not user:
            app_info = await self.bot.application_info()  # Fetches the bot's application info
            user = app_info.owner  # Gets the owner from the application info
        if user.banner:
            return await ctx.send(file=await user.banner.to_file(filename=f"{user.name}.png"))
        return await ctx.warn(f"{ctx.author.mention}: This user does not have a banner")
    
    


    @command(
        name="serverbanner",
        aliases=["sb"],
        brief="returns the server banner"
    )
    async def serverbanner(self, ctx: Context):
        return await ctx.send(file=await ctx.guild.banner.to_file(filename=f"{ctx.guild.name}.png"))


    @command(
        name="servericon",
        brief="returns the server icon"
    )
    async def servericon(self, ctx: Context):
        return await ctx.send(file=await ctx.guild.icon.to_file(filename=f"{ctx.guild.name}.png"))
    




async def setup(bot):
    await bot.add_cog(Information(bot))