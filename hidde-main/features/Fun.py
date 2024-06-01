import discord
from discord.ext import commands
import instaloader
import re
import aiohttp
import aiofiles
import os
import asyncio
from hiddeout.managers import Context


class Fun(commands.Cog, name="Social Media Commands"):
    def __init__(self, bot):
        self.bot = bot
        self.loader = instaloader.Instaloader()



    @commands.command(name="ig")
    async def ig(self, ctx: Context, *, username: str):
        try:
            profile = instaloader.Profile.from_username(self.loader.context, username)
            profile_pic_url = profile.profile_pic_url
            followers = profile.followers
            following = profile.followees
            posts = profile.mediacount
            bio = profile.biography
            external_url = profile.external_url
            profile_url = f"https://www.instagram.com/{username}/"

            embed = discord.Embed(title=f"@{username}", description=bio, url=profile_url)
            embed.set_thumbnail(url=profile_pic_url)
            embed.add_field(name="Followers", value=followers, inline=True)
            embed.add_field(name="Following", value=following, inline=True)
            embed.add_field(name="Posts", value=posts, inline=True)
            if external_url:
                embed.add_field(name="External Link", value=external_url, inline=False)

            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.warn(f"Failed to retrieve the Instagram profile: {str(e)}")
        finally:
            # Close the Instaloader context
            self.loader.close()






async def setup(bot):
    await bot.add_cog(Fun(bot))