import asyncio
import asyncpg
from hiddeout import hiddeout
from hiddeout.managers import Context
from collections import defaultdict
from discord import Member, Role, Embed, utils, PermissionOverwrite, TextChannel, VoiceChannel, Forbidden, ButtonStyle, Interaction, ui, Message, User, Embed
from discord.ext.commands import Cog, command, has_permissions, group, MemberConverter, cooldown, BucketType, MemberNotFound
from datetime import datetime
from hiddeout.managers import Paginator
from hiddeout.managers.paginator import PaginatorView
from functools import partial
from hiddeout.managers.classes import Emojis, Colors
from datetime import timedelta    
import logging
import json
import pytz
from hiddeout.utils import humanize, human_timedelta
from typing import Optional


logging.basicConfig(level=logging.ERROR, format='%(asctime)s %(levelname)s:%(message)s')




class Moderation(Cog):
    def __init__(self, bot):
        self.bot: hiddeout = bot
        self.message_counts = defaultdict(lambda: defaultdict(int))
        self.reset_tasks = defaultdict(dict)
        self.log_channel_id = None
        self.db = None
        self.bot = bot
        self.db = bot.db 
    async def _execute_query(self, query, *args):
        async with self.db.acquire() as connection:
            return await connection.fetch(query, *args)

    async def _execute_commit(self, query, *args):
        async with self.db.acquire() as connection:
            await connection.execute(query, *args)


    @Cog.listener()
    async def on_member_update(self, before: Member, after: Member):
        # Check if the nickname has changed
        if before.nick != after.nick:
            # Check if the user has a forced nickname
            forced_nickname = await self.bot.db.fetchval(
                "SELECT nickname FROM forced_nicknames WHERE user_id = $1",
                after.id
            )
            if forced_nickname and after.nick != forced_nickname:
                try:
                    await after.edit(nick=forced_nickname)
                    channel = self.bot.get_channel(1240852962817867797)  # Replace with your log channel ID
                    await channel.send(f"Reverted nickname change for {after.mention} to `{forced_nickname}`")
                except Forbidden:
                    channel = self.bot.get_channel(1240852962817867797)  # Replace with your log channel ID
                    await channel.send(f"Failed to revert nickname change for {after.mention}")


    # setlimit command
    @command(
        name="setlimit",
        aliases=["setchannellimit", "channellimit"]
    )
    @has_permissions(manage_channels=True)
    async def setlimit(self, ctx: Context, limit: int, channel: TextChannel = None):
        """
        Set the message limit for a channel. Defaults to the channel where the command is used if no channel is specified.
        """
        if channel is None:
            channel = ctx.channel

        try:
            await self.bot.db.execute(
                "INSERT INTO channel_message_limits (channel_id, message_limit) VALUES ($1, $2) ON CONFLICT (channel_id) DO UPDATE SET message_limit = EXCLUDED.message_limit",
                channel.id, limit
            )
            await ctx.send(f"Message limit set to {limit} for {channel.mention}.")
        except Exception as e:
            await ctx.send(f"Failed to set message limit due to an error: {e}")
            print(f"Error setting message limit: {e}")

    @Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        channel_id = message.channel.id
        user_id = message.author.id

        # Increment message count
        self.message_counts[channel_id][user_id] += 1

        # Fetch the limit from the database
        limit = await self.bot.db.fetchval("SELECT message_limit FROM channel_message_limits WHERE channel_id = $1", channel_id)

        if limit and self.message_counts[channel_id][user_id] > limit:
            await message.delete()
            await message.channel.send(f"{message.author.mention}, you have exceeded the message limit for this channel.", delete_after=5)
        else:
            # Reset message count after the time frame
            if user_id not in self.reset_tasks[channel_id]:
                self.reset_tasks[channel_id][user_id] = self.bot.loop.create_task(self.reset_message_count(channel_id, user_id))

    async def reset_message_count(self, channel_id, user_id):
        await asyncio.sleep(3600)  # Reset after 1 hour
        self.message_counts[channel_id][user_id] = 0
        del self.reset_tasks[channel_id][user_id]

    @command(
        name="resetlimit",
        aliases=["resetchannellimit", "msgreset"]
    )
    @has_permissions(manage_channels=True)
    async def resetlimit(self, ctx: Context, channel: TextChannel = None):
        """
        Reset the message limit for a channel. Defaults to the channel where the command is used if no channel is specified.
        """
        if channel is None:
            channel = ctx.channel

        await self.bot.db.execute(
            "DELETE FROM channel_message_limits WHERE channel_id = $1",
            channel.id
        )
        self.message_counts[channel.id] = defaultdict(int)
        if channel.id in self.reset_tasks:
            for task in self.reset_tasks[channel.id].values():
                task.cancel()
            del self.reset_tasks[channel.id]
        await ctx.approve(f"Message limit reset for {channel.mention}.")

    @command(
        name="mute",
        aliases=["silence"]
    )
    @has_permissions(manage_roles=True)
    async def mute(self, ctx: Context, member: Member = None, duration: str = "0", *, reason: str = "No reason provided"):
        """
        Mute a member in the server.
        """
        if member is None:
            return await ctx.warn(f"{ctx.author.mention}: Please mention a user to mute.")
    
        mute_role_id = await self.bot.db.fetchval("SELECT role_id FROM mute_roles WHERE guild_id = $1", ctx.guild.id)
        mute_role = ctx.guild.get_role(mute_role_id) if mute_role_id else None
    
        if not mute_role:
            mute_role = await ctx.guild.create_role(name="Muted")
            await self.bot.db.execute(
                "INSERT INTO mute_roles (guild_id, role_id) VALUES ($1, $2) ON CONFLICT (guild_id) DO UPDATE SET role_id = EXCLUDED.role_id",
                ctx.guild.id, mute_role.id
            )
    
        await member.add_roles(mute_role)
        duration_display = "`permanently`" if duration == "0" else duration
        await ctx.approve(f"{member.mention} has been muted for {duration_display}. Reason: {reason}")

    @command(
        name="unmute",
        aliases=["unsilence"]
    )
    @has_permissions(manage_roles=True)
    async def unmute(self, ctx: Context, member: Member = None):
        """
        Unmute a member in the server.
        """
        if member is None:
            return await ctx.send("Please mention a user to unmute.")
    
        mute_role_id = await self.bot.db.fetchval("SELECT role_id FROM mute_roles WHERE guild_id = $1", ctx.guild.id)
        mute_role = ctx.guild.get_role(mute_role_id) if mute_role_id else None
    
        if mute_role and mute_role in member.roles:
            await member.remove_roles(mute_role)
            await ctx.approve(f"{member.display_name} has been unmuted.")
        else:
            await ctx.warn(f"{member.display_name} is not muted.")

    @command(
        name="ban",
        aliases=["deport", "banish"]
    )
    @has_permissions(ban_members=True)
    async def ban(self, ctx: Context, user: Member, *, reason: str = "No reason provided"):
        """
        Ban a member
        """
        await ctx.guild.ban(user, reason=f"{ctx.author} - {reason}")
        await ctx.approve(f"**{user}** has been banned | {reason}")

    @command(
        name="kick",
        aliases=["boot"]
    )
    @has_permissions(kick_members=True)
    async def kick(self, ctx: Context, user: Member, *, reason: str = "No reason provided"):
        """
        Kick a member
        """
        await ctx.guild.kick(user, reason=f"{ctx.author} - {reason}")
        await ctx.approve(f"**{user}** has been kicked | {reason}")

    @command(
        name="unban",
        aliases=["forgive", "pardon"]
    )
    @has_permissions(ban_members=True)
    async def unban(self, ctx: Context, user: Member):
        """
        Unban a member
        """
        try:
            await ctx.guild.unban(user)
            await ctx.approve(f"**{user}** has been unbanned")
        except:
            await ctx.warn(f"{ctx.author.mention}: {user} is not banned from the server")

    @command(
        name="slowmode",
        aliases=["slow"]
    )
    @has_permissions(manage_channels=True)
    async def slowmode(self, ctx: Context, duration: int, channel: TextChannel = None):
        """
        Set slowmode in a channel
        """
        if channel is None:
            channel = ctx.channel

        await channel.edit(slowmode_delay=duration)
        await ctx.approve(f"Slowmode set to {duration} seconds in {channel.mention}.")

    
    @command(
        name="createchannel",
        aliases=["cc"]
    )
    @has_permissions(manage_channels=True)
    async def createchannel(self, ctx: Context, name: str, category: str = None):
        """
        Create a text channel
        """
        category = utils.get(ctx.guild.categories, name=category)
        await ctx.guild.create_text_channel(name, category=category)
        await ctx.approve(f"Channel {name} has been created.")

    @command(
        name="createcategory",
        aliases=["ccat"]
    )
    @has_permissions(manage_channels=True)
    async def createcategory(self, ctx: Context, name: str):
        """
        Create a category
        """
        await ctx.guild.create_category(name=name)
        await ctx.approve(f"Category {name} has been created.")

    @command(
        name="deletechannel",
        aliases=["dc"]
    )
    @has_permissions(manage_channels=True)
    async def deletechannel(self, ctx: Context, channel: TextChannel):
        """
        Delete a channel
        """
        await channel.delete()
        await ctx.approve(f"Channel {channel.name} has been deleted.")
    
    
    @command(
        name="deletecategory",
        aliases=["dcat"]
    )
    @has_permissions(manage_channels=True)
    async def deletecategory(self, ctx: Context, category: TextChannel):
        """
        Delete a category
        """
        await category.delete()
        await ctx.approve(f"Category {category.name} has been deleted.")

    @command(
        name="renamechannel",
        aliases=["rc"]
    )
    @has_permissions(manage_channels=True)
    async def renamechannel(self, ctx: Context, channel: TextChannel, name: str):
        """
        Rename a channel
        """
        await channel.edit(name=name)
        await ctx.approve(f"Channel has been renamed to {name}.")
    


    @group(
        name="role",
        aliases=["r"],
        invoke_without_command=True
    )
    @has_permissions(manage_roles=True)
    async def role_group(self, ctx: Context):
        """
        Manage roles
        """
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @role_group.command(
        name="add"
    )
    async def add_role(self, ctx: Context, member: Member, role: Role):
        """
        Add a role to a member.
        """
        await member.add_roles(role)
        await ctx.approve(f"{role.name} role added to {member.display_name}")

    @role_group.command(
        name="remove"
    )
    async def remove_role(self, ctx: Context, member: Member, role: Role):
        """
        Remove a role from a member.
        """
        await member.remove_roles(role)
        await ctx.approve(f"{role.name} role removed from {member.display_name}")

    @role_group.command(
        name="create"
    )
    async def create_role(self, ctx: Context, name: str, color: str = None):
        """
        Create a new role.
        """
        await ctx.guild.create_role(name=name, color=color)
        await ctx.approve(f"Role {name} has been created.")

    @role_group.command(
        name="delete"
    )
    async def delete_role(self, ctx: Context, role: Role):
        """
        Delete a role.
        """
        await role.delete()
        await ctx.approve(f"Role {role.name} has been deleted.")
        

    @role_group.command(
        name="color"
    )
    async def role_color(self, ctx: Context, role: Role, color: str):
        """
        Change a role color
        """
        await role.edit(color=color)
        await ctx.approve(f"Role {role.name} has been changed to {color}.")
    
    @role_group.command(
        name="permissions"
    )
    async def role_permissions(self, ctx: Context, role: Role, permissions: str):
        """
        Change a role permissions
        """
        await role.edit(permissions=permissions)
        await ctx.approve(f"Role {role.name} has been changed to {permissions}.")
    
    @role_group.command(
        name="rename",
        aliases=["rr"]
    )
    async def rename_role(self, ctx: Context, role: Role, name: str):
        """
        Rename a role
        """
        await role.edit(name=name)
        await ctx.approve(f"Role has been renamed to {name}.")

    @role_group.command(
        name="position",
        aliases=["pos"]
    )
    async def position_role(self, ctx: Context, role: Role, position: int):
        """
        Change a role position
        """
        await role.edit(position=position)
        await ctx.approve(f"Role {role.name} has been changed to position {position}.")

    @role_group.command(
        name="clone",
        aliases=["c"]
    )
    async def clone_role(self, ctx: Context, role: Role):
        """
        Clone a role
        """
        await ctx.guild.create_role(name=role.name, color=role.color, permissions=role.permissions)
        await ctx.approve(f"Role {role.name} has been cloned.")

    @role_group.command(
        name="icon"
    )
    async def icon_role(self, ctx: Context, role: Role, icon: str):
        """
        Change a role icon
        """
        await role.edit(icon=icon)
        await ctx.approve(f"Role {role.name} has been changed to icon {icon}.")

    @role_group.command(
        name="mentionable"
    )
    async def mentionable_role(self, ctx: Context, role: Role):
        """
        Change a role mentionable
        """
        await role.edit(mentionable=True)
        await ctx.approve(f"Role {role.name} has been changed to mentionable.")
    
    @role_group.command(
        name="humans",
        aliases=["assign"]
    )
    async def humans(self, ctx: Context, role: Role):
        """
        Assign a specified role to all human members in the guild.
        """
        if not ctx.guild.me.guild_permissions.manage_roles:
            return await ctx.send("I do not have permission to manage roles in this guild.")

        if ctx.author.top_role <= role:
            return await ctx.send("You do not have the necessary permissions to assign this role.")

        members_assigned = 0
        for member in ctx.guild.members:
            if not member.bot and role not in member.roles:
                try:
                    await member.add_roles(role)
                    members_assigned += 1
                except Forbidden:
                    await ctx.warn(f"Failed to add roles for {member.display_name}. Insufficient permissions.")
                except Exception as e:
                    await ctx.warn(f"An error occurred: {str(e)}")

        await ctx.approve(f"Assigned {role.name} to {members_assigned} human members.")

    @command(
        name="timeout",
        aliases=["to"]
    )
    @has_permissions(manage_channels=True)
    async def timeout(self, ctx: Context, member: Member, duration: str):
        """
        Create a timeout for a member, specifying the duration as '15m' for minutes or '2h' for hours.
        """
        unit = duration[-1]  # Get the last character to determine the unit
        if unit not in ['m', 'h']:
            return await ctx.warn("Please specify the time unit as either 'm' for minutes or 'h' for hours.")

        try:
            time_value = int(duration[:-1])  # Extract the numerical part
        except ValueError:
            return await ctx.warn("Invalid time format. Please specify a valid number followed by 'm' or 'h'.")

        if unit == 'h':
            time_value *= 60  # Convert hours to minutes

        timeout_duration = timedelta(minutes=time_value)  # Convert minutes to timedelta

        try:
            await member.timeout(timeout_duration)
            await ctx.approve(f"{member.display_name} has been timed out for {time_value} {'minutes' if unit == 'm' else 'hours'}.")
        except Forbidden:
            await ctx.warn("I do not have permission to timeout this user.")
        except Exception as e:
            await ctx.warn(f"Failed to timeout the user: {str(e)}")

    @command(
        name="renamecategory",
        aliases=["rcat"]
    )
    @has_permissions(manage_channels=True)
    async def renamecategory(self, ctx: Context, category: TextChannel, name: str):
        """
        Rename a category
        """
        await category.edit(name=name)
        await ctx.approve(f"Category has been renamed to {name}.")

    @command(
        name="movechannel",
        aliases=["mc"]
    )
    @has_permissions(manage_channels=True)
    async def movechannel(self, ctx: Context, channel: TextChannel, category: str):
        """
        Move a channel to a category
        """
        category = utils.get(ctx.guild.categories, name=category)
        await channel.edit(category=category)
        await ctx.approve(f"Channel has been moved to {category.name}.")
    
    @command(
        name="settopic",
        aliases=["topic"]
    )
    @has_permissions(manage_channels=True)
    async def settopic(self, ctx: Context, channel: TextChannel, topic: str):
        """
        Set a channel topic
        """
        await channel.edit(topic=topic)
        await ctx.approve(f"Channel topic has been set to: {topic}.")

    @command(
        name="setnsfw",
        aliases=["nsfw"]
    )
    @has_permissions(manage_channels=True)
    async def setnsfw(self, ctx: Context, channel: TextChannel):
        """
        Set a channel as NSFW
        """
        await channel.edit(nsfw=True)
        await ctx.approve(f"Channel {channel.name} has been set as NSFW.")
    
    @command(
        name="unsetnsfw",
        aliases=["unnsfw"]
    )
    @has_permissions(manage_channels=True)
    async def unsetnsfw(self, ctx: Context, channel: TextChannel):
        """
        Unset a channel as NSFW
        """
        await channel.edit(nsfw=False)
        await ctx.approve(f"Channel {channel.name} has been unset as NSFW.")
    
    @command(
        name="setuserlimit",
        aliases=["userlimit"]
    )
    @has_permissions(manage_channels=True)
    async def setuserlimit(self, ctx: Context, channel: VoiceChannel, limit: int):
        """
        Set user limit in a voice channel
        """
        await channel.edit(user_limit=limit)
        await ctx.approve(f"User limit set to {limit} in {channel.name}.")
    
    @command(
        name="setbitrate",
        aliases=["bitrate"]
    )
    @has_permissions(manage_channels=True)
    async def setbitrate(self, ctx: Context, channel: VoiceChannel, bitrate: int):
        """
        Set bitrate in a voice channel
        """
        await channel.edit(bitrate=bitrate)
        await ctx.approve(f"Bitrate set to {bitrate} in {channel.name}.")




    @command(
        name="nickname",
        aliases=['rename', 'nick']
    )
    @has_permissions(manage_nicknames=True)
    async def nickname(
        self: "Moderation",
        ctx: Context,
        member: MemberConverter,
        *,
        nickname: str
    ):
        """
        Change a member's nickname
        """
        try:
            await member.edit(nick=nickname)
            return await ctx.approve(f"Nickname for {member.mention} changed to `{nickname}`")
        except Forbidden:
            return await ctx.warn("I do not have permission to change this user's nickname.")
        

    
    @command(name="warn")
    @has_permissions(manage_messages=True)
    async def warn(self, ctx: Context, member: MemberConverter, *, reason: str):
        """
        Warn a member, and notify the member via DM.
        """
        if not reason:
            await ctx.warn("Please provide a reason for the warning.")
            return

        # Log the warning in the database
        try:
            await self.bot.db.execute(
                "INSERT INTO warnings (guild_id, user_id, moderator_id, reason) VALUES ($1, $2, $3, $4)",
                str(ctx.guild.id), str(member.id), str(ctx.author.id), reason
            )
        except Exception as e:
            await ctx.send("Failed to log the warning in the database.")
            print(f"Database error: {e}")
            return

        # Simulate processing time with a delay
        await asyncio.sleep(0.2)  # Delay for 2 seconds

        # Attempt to send a DM to the warned user
        try:
            if not member.dm_channel:
                await member.create_dm()
            await member.dm_channel.send(
                f"You have been warned in {ctx.guild.name} for the following reason: {reason}"
            )
            await ctx.approve(f"{member.mention} has been warned for: {reason}")
        except Forbidden:
            await ctx.send(f"👍 - couldn't pm user")

    
    @command(name="clearwarns")
    @has_permissions(manage_messages=True)
    async def clearwarns(self, ctx: Context, member: MemberConverter):
        """
        Clear all warnings for a specified member.
        """
        try:
            # Execute the delete operation on the database
            await self.bot.db.execute(
                "DELETE FROM warnings WHERE guild_id = $1 AND user_id = $2",
                str(ctx.guild.id), str(member.id)
            )
            # Send a confirmation message to the guild
            await ctx.approve(f"All warnings for {member.mention} have been cleared.")
        except Exception as e:
            print(f"Error clearing warnings for member: {e}")
            await ctx.warn("Failed to clear warnings for the member.")


    @command(name="warnings", aliases=["warns"], description="Lists all warnings for the mentioned user.")
    @has_permissions(manage_messages=True)
    async def warnings(self, ctx, member: MemberConverter = None):
        """List all warnings for a member."""
        if member is None:
            await ctx.warn("Please mention a member to view warnings.")
            return

        try:
            # Fetch warnings from the database
            records = await self.bot.db.fetch(
                "SELECT reason FROM warnings WHERE guild_id = $1 AND user_id = $2",
                str(ctx.guild.id), str(member.id)
            )

            if records:
                # Extract reasons from records and format them as strings with block quote formatting
                formatted_warnings = [f"> {record['reason']}" for record in records]
                warning_list = "\n".join(formatted_warnings)
                embed = Embed(description=f"**Warnings for {member.display_name}:**\n{warning_list}")
                await ctx.send(embed=embed)
            else:
                await ctx.warn(f"No warnings found for `{member.display_name}`.")
        except Exception as e:
            print(f"Error fetching warnings: {e}")
            await ctx.warn("An error occurred while fetching warnings.")






    @group(name="purge", invoke_without_command=True)
    @has_permissions(manage_messages=True)
    async def purge_group(self, ctx: Context):
        """
        Group for purging messages
        """
        await ctx.send_help(ctx.command)

    @purge_group.command(name="all", aliases=["a"])
    async def purge_all(self, ctx: Context):
        """
        Purge all messages in the channel
        """
        await ctx.channel.purge()
        await ctx.neutral("All messages have been purged.")

    @purge_group.command(name="user")
    async def purge_user(self, ctx: Context, member: Member):
        """
        Purge all messages from a specific user
        """
        await ctx.channel.purge(check=lambda m: m.author == member)
        await ctx.neutral(f"All messages from {member.mention} have been purged.")

    @purge_group.command(name="bot")
    async def purge_bot(self, ctx: Context):
        """
        Purge all messages sent by bots
        """
        await ctx.channel.purge(check=lambda m: m.author.bot)
        await ctx.neutral("All messages from bots have been purged.")

    @purge_group.command(name="embeds")
    async def purge_embeds(self, ctx: Context):
        """
        Purge all messages containing embeds
        """
        await ctx.channel.purge(check=lambda m: len(m.embeds) > 0)
        await ctx.neutral("All messages with embeds have been purged.")

    @purge_group.command(name="contains")
    async def purge_contains(self, ctx: Context, *, text: str):
        """
        Purge all messages containing a specific text
        """
        await ctx.channel.purge(check=lambda m: text.lower() in m.content.lower())
        await ctx.neutral(f"All messages containing '{text}' have been purged.")

    @purge_group.command(name="mentions")
    async def purge_mentions(self, ctx: Context):
        """
        Purge all messages containing mentions
        """
        await ctx.channel.purge(check=lambda m: len(m.mentions) > 0)
        await ctx.neutral("All messages with mentions have been purged.")

    @purge_group.command(name="reactions")
    async def purge_reactions(self, ctx: Context):
        """
        Purge all messages containing reactions
        """
        await ctx.channel.purge(check=lambda m: len(m.reactions) > 0)
        await ctx.neutral("All messages with reactions have been purged.")




    @command(
        name="moveall",
        aliases=[
            "mall",
            "vcma"
        ]
    )
    @has_permissions(manage_channels=True)
    async def moveall(self, ctx: Context, from_vc: int, to_vc: int):
        """
        Move all members from one voice channel to another.
        """
        if not ctx.guild.me.guild_permissions.manage_channels:
            await ctx.send("I do not have permission to manage channels.")
            return
    
        from_channel = ctx.guild.get_channel(from_vc)
        to_channel = ctx.guild.get_channel(to_vc)
        if not from_channel or not to_channel:
            await ctx.send("One of the voice channels was not found.")
            return
    
        members = from_channel.members
        for member in members:
            try:
                await member.move_to(to_channel)
            except Exception as e:
                await ctx.send(f"Failed to move {member.display_name}: {str(e)}")

        await ctx.send(f"All members moved from {from_channel.name} to {to_channel.name}.")


async def setup(bot):
    await bot.add_cog(Moderation(bot))
