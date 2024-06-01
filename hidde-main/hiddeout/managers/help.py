from discord.ext import commands
from discord.ui import Select, View, Button
import discord
from discord import Embed, Message
from .context import Context




emojis = {
    "moderation": "<:moderation:1240510532985950228>",
    "information": "<:info:1240510876876935239>",
    "configuration": "<:config:1240510620248440873>",
    "utility": "<:Utility:1240510796233048125>"
}



class HelpSelect(Select):
    def __init__(self, placeholder: str, options: list, commands: dict, emojis: dict):
        super().__init__(placeholder=placeholder, options=options)
        self.commands = commands
        self.emojis = emojis

    async def callback(self, interaction: discord.Interaction):
        cog_name = self.values[0]
        commands_list = self.commands[cog_name]
        emoji = self.emojis.get(cog_name.lower(), "")
        command_names = ", ".join([command.name for command in commands_list])
        embed = discord.Embed(
            title=f"{emoji} {cog_name}",
            description=f"```{command_names}```",
            color=0xffffff
        )
        embed.set_author(name="Hidde Command Menu", icon_url=interaction.client.user.avatar.url)

        embed.set_footer(text=f"Module: {cog_name} - Requested by {interaction.user}")
        await interaction.response.edit_message(content=None, embed=embed, view=self.view)

class HelpView(View):
    def __init__(self, commands, emojis):
        super().__init__()
        self.commands = commands
        self.emojis = emojis
        options = [
            discord.SelectOption(
                label=cog,
                description="Click to see commands in this category",
                value=cog,
                emoji=emojis.get(cog.lower(), None)
            )
            for cog in commands if cog != "No Category"
        ]
        self.add_item(HelpSelect(placeholder="Hidde Command Navigation!", options=options, commands=commands, emojis=emojis))
        
        # Add support and invite buttons
        self.add_item(Button(label="Support", url="https://discord.gg/5Mkw7YFJhj", style=discord.ButtonStyle.link))
        self.add_item(Button(label="Invite", url="https://discord.com/oauth2/authorize?client_id=1238203688741507183&permissions=8&scope=bot", style=discord.ButtonStyle.link))

class Help(commands.MinimalHelpCommand):

    context: "Context"

    def __init__(self, **options):
        super().__init__(
            command_attrs={
                "hidden": True,
                "aliases": ["h"],
            },
            **options,
        )

    async def send_bot_help(self, mapping):
        commands_by_cog = {}
        for cog, commands in mapping.items():
            if cog and cog.qualified_name in ["Owner", "Developer", "Jishaku", "Events", "Auth"]:
                continue
            filtered = await self.filter_commands(commands, sort=True)
            if filtered:
                cog_name = getattr(cog, "qualified_name", None)
                if cog_name:
                    commands_by_cog[cog_name] = filtered



        view = HelpView(commands_by_cog, emojis)
        prefix = self.context.clean_prefix  # Get the dynamic prefix from the context
        embed = discord.Embed(title="Help", description=f"Use `{prefix}help [command]` for more info on a command.", color=0xffffff)
        embed.set_author(name="Hidde Command Menu", icon_url=self.context.bot.user.avatar.url)
        embed.set_footer(text=f"some command might not work as expected, this is a beta please report any issues to the support server")
        channel = self.get_destination()
        await channel.send(embed=embed, view=view)

    async def send_command_help(self, command):
        # Define syntaxes and examples for commands
        syntaxes = {
            "ban": f"{self.context.clean_prefix}ban (user) (reason)",
            "kick": f"{self.context.clean_prefix}kick (user) (reason)",
            "prefix": f"{self.context.clean_prefix}prefix (new prefix)",
            "automod": f"{self.context.clean_prefix}automod on/off",
            "antiinvite": f"{self.context.clean_prefix}antiinvite on/off",
            # Add more syntaxes for other commands here
        }

        examples = {
            "ban": f"{self.context.clean_prefix}ban @user 1h Spamming",
            "kick": f"{self.context.clean_prefix}kick @user Breaking rules",
            "prefix": f"{self.context.clean_prefix}prefix !",
            "automod": f"{self.context.clean_prefix}automod on/off",
            "antiinvite": f"{self.context.clean_prefix}antiinvite on/off",
            # Add more examples for other commands here
        }

        # Get the syntax and example for the command, or use a default
        syntax = syntaxes.get(command.qualified_name, f"{self.context.clean_prefix}{command.qualified_name} {command.signature}")
        example = examples.get(command.qualified_name, f"{self.context.clean_prefix}{command.qualified_name} example_argument")

        # If no specific example is found, create a default one
        if example == f"{self.context.clean_prefix}{command.qualified_name} example_argument":
            example = f"{self.context.clean_prefix}{command.qualified_name} (args)"
        
        # Create the embed with the desired format
        embed = discord.Embed(
            title=f"Command: {command.qualified_name}",
            description=f"{command.help or 'No description provided.'}\n"
                        f"```Syntax: {syntax}\n"
                        f"Example: {example}```",
            color=0xffffff
        )
        embed.set_author(name="Hidde Command Menu", icon_url=self.context.bot.user.avatar.url)
        
        # Add aliases if they exist
        if command.aliases:
            aliases = ", ".join(command.aliases)
            embed.add_field(name="Aliases", value=f"```{aliases}```", inline=False)
        
        embed.set_footer(text=f"Module: {command.cog_name} - Requested by {self.context.author}")
        await self.get_destination().send(embed=embed)

    async def send_group_help(self, group):
        embed = discord.Embed(
            title=f"Command Group: {group.qualified_name}",
            description=group.help or "No description provided.",
            color=0xffffff
        )
        embed.set_author(name="Hidde Command Menu", icon_url=self.context.bot.user.avatar.url)

        # Add subcommands
        subcommands = "\n".join([f"{self.context.clean_prefix}{sub.name} - {sub.help or 'No description provided.'}" for sub in group.commands])
        embed.add_field(name="Commands", value=f"```{subcommands}```", inline=False)
    
        # Add aliases if they exist
        if group.aliases:
            aliases = ", ".join(group.aliases)
            embed.add_field(name="Aliases", value=f"```{aliases}```", inline=False)
    
        embed.set_footer(text=f"Module: {group.cog_name} - Requested by {self.context.author}")
        await self.get_destination().send(embed=embed)
