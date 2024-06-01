import asyncio
import asyncpg
import discord
from discord import ButtonStyle
from discord.ext import commands
from discord.ui import Button, View
from datetime import datetime
import json
import logging
from hiddeout.managers import Context
from hiddeout.managers.classes import Emojis, Colors





class Configuration(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db  # Assuming bot has an `db` attribute for asyncpg connection pool



    async def _execute_query(self, query, *args):
        async with self.db.acquire() as connection:
            return await connection.fetch(query, *args)

    async def _execute_commit(self, query, *args):
        async with self.db.acquire() as connection:
            await connection.execute(query, *args)





    @commands.command(help="Set up the jail module", description="Config")
    @commands.cooldown(1, 6, commands.BucketType.guild)
    async def setme(self, ctx: Context):
        if not ctx.author.guild_permissions.administrator:
            await ctx.warn("You do not have administrator permissions.")
            return
    
        try:
            async with self.db.acquire() as connection:
                # Check if jail module is already set
                existing_setup = await connection.fetchrow("SELECT * FROM setme WHERE guild_id = $1", ctx.guild.id)
                if existing_setup:
                    return await ctx.warn("Jail module is already set")
    
                # Create the jail role
                role = await ctx.guild.create_role(name="jail", color=0xff0000)
    
                # Create the jail channel with specific permissions
                overwrites_jail = {
                    ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    role: discord.PermissionOverwrite(read_messages=True)
                }
                jail_channel = await ctx.guild.create_text_channel('jail', overwrites=overwrites_jail)
    
                # Create the jail-log channel
                overwrites_log = {
                    ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    role: discord.PermissionOverwrite(read_messages=False)  # Jail role should not see this channel
                }
                jail_log_channel = await ctx.guild.create_text_channel('hidde-logs', overwrites=overwrites_log)
    
                # Apply role permissions to all other channels
                for channel in ctx.guild.channels:
                    if isinstance(channel, discord.TextChannel):
                        await channel.set_permissions(role, read_messages=False, read_message_history=False)
                    elif isinstance(channel, discord.VoiceChannel):
                        await channel.set_permissions(role, connect=False)
    
                # Save the role and channel IDs to the database
                await connection.execute("INSERT INTO setme (guild_id, channel_id, role_id, log_channel_id) VALUES ($1, $2, $3, $4)",
                                         ctx.guild.id, jail_channel.id, role.id, jail_log_channel.id)
                await ctx.approve("Jail module set")
    
        except Exception as e:
            await ctx.warn(f"An error occurred: {e}")
    
    @commands.command()
    @commands.cooldown(1, 6, commands.BucketType.guild)
    async def unsetme(self, ctx: commands.Context):
        if not ctx.author.guild_permissions.administrator:
            return await ctx.warn("You do not have administrator permissions.")
    
        # Check if jail module is set
        setme_check = await self._execute_query("SELECT * FROM setme WHERE guild_id = $1", ctx.guild.id)
        if not setme_check:
            return await ctx.warn("Jail module is not set")
    
        # Ensure setme_check is treated as a single dictionary
        setme_check = setme_check[0]  # Access the first row if it's a list
    
        # Get role and channel IDs from the setme table
        channel_id = setme_check["channel_id"]
        role_id = setme_check["role_id"]
        log_channel_id = setme_check["log_channel_id"]
    
        # Define interaction check
        async def interaction_check(interaction: discord.Interaction) -> bool:
            if interaction.user != ctx.author:
                embed = discord.Embed(
                    description=f"{Emojis.warning} You are not the author of this message, {interaction.user.mention}.",
                    color=0xF4DB6D
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return False
            return True
    
        # Define button callbacks
        async def confirm_button_callback(interaction: discord.Interaction):
            if not await interaction_check(interaction):
                return
    
            await interaction.response.defer()  # Defer the response to acknowledge the interaction
    
            async with self.db.acquire() as connection:
                role = ctx.guild.get_role(role_id)
                channel = ctx.guild.get_channel(channel_id)
                log_channel = ctx.guild.get_channel(log_channel_id)
    
                try:
                    if role:
                        await role.delete()
                    if channel:
                        await channel.delete()
                    if log_channel:
                        await log_channel.delete()
    
                    # Delete the setme entry from the database
                    await connection.execute("DELETE FROM setme WHERE guild_id = $1", ctx.guild.id)
    
                    embed = discord.Embed(color=Colors.green, description=f"{Emojis.check} Jail module has been cleared")
                    await interaction.edit_original_response(content="", embed=embed, view=None)
    
                except Exception as e:
                    await interaction.followup.send(content=f"An error occurred: {e}", ephemeral=True)
    
        async def cancel_button_callback(interaction: discord.Interaction):
            if not await interaction_check(interaction):
                return
    
            await interaction.response.defer()  # Defer the response to acknowledge the interaction
    
            embed = discord.Embed(color=Colors.yellow, description=f"{Emojis.warning} Operation canceled")
            await interaction.edit_original_response(content="", embed=embed, view=None)
    
        # Create buttons and embed
        confirm_button = Button(style=discord.ButtonStyle.green, label="Confirm")
        cancel_button = Button(style=discord.ButtonStyle.red, label="Cancel")
    
        confirm_button.callback = confirm_button_callback
        cancel_button.callback = cancel_button_callback
    
        embed = discord.Embed(color=Colors.yellow, description=f"{Emojis.warning} Are you sure you want to clear the jail module?")
    
        # Create a view and add buttons
        view = View()
        view.add_item(confirm_button)
        view.add_item(cancel_button)
    
        # Send message with embed and view (buttons)
        message = await ctx.send(embed=embed, view=view)
        



    @commands.command(name="autorole", help="Sets the default role for new members.")
    @commands.has_permissions(administrator=True)
    async def set_auto_role(self, ctx: Context, role: discord.Role):
        async with self.db.acquire() as connection:
            # Check if an autorole is already set
            existing_role = await connection.fetchval("SELECT role_id FROM autoroles WHERE guild_id = $1", ctx.guild.id)
            if existing_role:
                # Update the existing role
                await connection.execute("UPDATE autoroles SET role_id = $1 WHERE guild_id = $2", role.id, ctx.guild.id)
                await ctx.approve(f"Updated the autorole to {role.name}.")
            else:
                # Insert a new autorole
                await connection.execute("INSERT INTO autoroles (guild_id, role_id) VALUES ($1, $2)", ctx.guild.id, role.id)
                await ctx.approve(f"Set the autorole to {role.name}.")

















async def setup(bot):
    await bot.add_cog(Configuration(bot))







