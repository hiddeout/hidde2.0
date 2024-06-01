from hiddeout import hiddeout
from hiddeout.managers import Context
import time as t
import asyncio
from hiddeout.utils import humanize, human_timedelta
from discord.ext.commands import Cog, command
from discord import Message, Embed, Member, User 
from tools.checks import Perms as utils
from datetime import datetime
import logging
import discord

log = logging.getLogger(__name__)

class Events(Cog):

    def __init__(self, bot):
        self.bot: hiddeout = bot


    @Cog.listener()
    async def on_message_delete(self, message: Message):
        if message.author.bot:
            return  # Ignore bot messages
    
        attachment_url = message.attachments[0].url if message.attachments else None
    
        try:
            # Insert the new deleted message
            await self.bot.db.execute(
                """
                INSERT INTO snipe_messages (author_id, content, attachment_url, deleted_at, channel_id)
                VALUES ($1, $2, $3, $4, $5)
                """,
                message.author.id,
                message.content,
                attachment_url,
                datetime.utcnow(),
                message.channel.id
            )
            # Delete messages older than 10 minutes
            await self.bot.db.execute(
                """
                DELETE FROM snipe_messages
                WHERE deleted_at < (NOW() - INTERVAL '10 minutes')
                """
            )
            log.info("Message deleted and recorded successfully.")
        except Exception as e:
            log.error(f"Failed to insert/delete deleted message: {e}")
    
    @Cog.listener()
    async def on_message_edit(self, before: Message, after: Message):
        if before.author.bot or before.content == after.content:
            return  # Ignore bot messages and unchanged content
    
        attachment_url = after.attachments[0].url if after.attachments else None
    
        try:
            # Insert the new edited message
            await self.bot.db.execute(
                """
                INSERT INTO edit_snipe_messages (author_id, content, attachment_url, edited_at, channel_id)
                VALUES ($1, $2, $3, $4, $5)
                """,
                before.author.id,
                after.content,
                attachment_url,
                datetime.utcnow(),
                after.channel.id
            )
            # Delete messages older than 10 minutes
            await self.bot.db.execute(
                """
                DELETE FROM edit_snipe_messages
                WHERE edited_at < (NOW() - INTERVAL '10 minutes')
                """
            )
            log.info("Edited message recorded successfully.")
        except Exception as e:
            log.error(f"Failed to insert/delete edited message: {e}")


    
    @Cog.listener()
    async def on_member_update(self, before: Member, after: Member):
        if before.display_name != after.display_name:
            try:
                async with self.bot.db.acquire() as connection:
                    await connection.execute(
                        "INSERT INTO name_changes (user_id, old_name, new_name, changed_at) VALUES ($1, $2, $3, $4)",
                        after.id, before.display_name, after.display_name, datetime.utcnow()
                    )
                log.info(f"Name change recorded: {before.display_name} to {after.display_name}")
            except Exception as e:
                log.error(f"Failed to record name change: {e}")
    
    @Cog.listener()
    async def on_member_join(self, member: Member):
        try:
            async with self.bot.db.acquire() as connection:
                role_id = await connection.fetchval("SELECT role_id FROM autoroles WHERE guild_id = $1", member.guild.id)
                if role_id:
                    role = member.guild.get_role(role_id)
                    if role:
                        await member.add_roles(role)
                        log.info(f"Assigned {role.name} to {member.display_name}.")
                    else:
                        log.warning("Role not found.")
                else:
                    log.info("No autorole set for this guild.")
        except Exception as e:
            log.error(f"Failed to assign autorole: {e}")
    
    
    

    @Cog.listener("on_message")
    async def check_afk(
        self: "Events", 
        message: Message
    ):
        if (ctx := await self.bot.get_context(message)) and ctx.command:
            return

        elif afk := await self.bot.db.fetchval(
            """
            DELETE FROM afk
            WHERE user_id = $1
            RETURNING date
            """,
            message.author.id,
        ):
            embed = Embed(
                color=0x7289da,  # You can choose an appropriate color
                description=f"👋 {ctx.author.mention}: Welcome back, You were away for **{humanize(afk, suffix=False)}**"
            )
            return await ctx.message.reply(
                embed=embed,
                mention_author=False
            )
        elif len(message.mentions) == 1 and (user := message.mentions[0]):
            if afk2 := await self.bot.db.fetchrow(
                """
                SELECT reason, date FROM afk
                WHERE user_id = $1
                """,
                user.id,
            ):
                return await ctx.warn(f"{user.mention} is AFK **{afk2['reason']}** - `{humanize(afk2['date'], suffix=False)}`")
            
async def commandhelp(self, ctx, cmd):
    try:
        command = self.bot.get_command(cmd)
        if command is None:
            await ctx.reply(f"Command `{cmd}` not found", mention_author=False)
            return

        if command.usage is None:
            usage = ""
        else:
            usage = command.usage

        # Use the clean_prefix from the context directly
        prefix = ctx.clean_prefix

        embed = discord.Embed(color=0x2f3136, title=command.name, description=command.help)
        embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar.url)
        embed.add_field(name="Category", value=command.description)
        if command.brief:
            embed.add_field(name="Commands", value=command.brief, inline=False)
        embed.add_field(name="Usage", value=f"```{prefix}{cmd} {usage}```", inline=False)
        embed.add_field(name="Aliases", value=', '.join(map(str, command.aliases)) or "none")
        await ctx.reply(embed=embed, mention_author=False)
    except Exception as e:
        await ctx.reply(f"An error occurred: {e}", mention_author=False)

async def is_blacklisted(self, entity_type, entity_id):
    async with self.bot.db.acquire() as conn:
        result = await conn.fetchrow("SELECT * FROM blacklist WHERE type = $1 AND entity_id = $2", entity_type, entity_id)
        return bool(result)  # Returns True if blacklisted, False otherwise
    

async def on_message_delete(message):
    if message.guild:
        # Log message deletions due to automod actions
        if message.author.bot:
            return  # Ignore deletions from other bots
        log_channel = discord.utils.get(message.guild.channels, name="automod-logs")
        if log_channel:
            embed = discord.Embed(title="Message Deleted (Automod)",
                                  description=f"Author: {message.author.mention}\nChannel: {message.channel.mention}\nContent: {message.content}",
                                  color=discord.Color.red())
            await log_channel.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Events(bot))

