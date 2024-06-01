from discord import ButtonStyle, Embed, HTTPException, Interaction, Message
from discord.ext.commands import Context as DefaultContext
from discord.ui import Button, View
from asyncio import TimeoutError
from contextlib import suppress
from typing import Union
from discord.ext import commands
import discord

# Define emojis for navigation
class emoji:
    next: str = "<:right:1238691443900682322>"
    previous: str = "<:left:1238691473113874482>"
    cancel: str = "<:pageclose:1242674549514829916>"
    navigate: str = "<:navigate2:1242676587862822985>"





class EmbedBuilder:
 def ordinal(self, num: int) -> str:
   """Convert from number to ordinal (10 - 10th)""" 
   numb = str(num) 
   if numb.startswith("0"): numb = numb.strip('0')
   if numb in ["11", "12", "13"]: return numb + "th"
   if numb.endswith("1"): return numb + "st"
   elif numb.endswith("2"):  return numb + "nd"
   elif numb.endswith("3"): return numb + "rd"
   else: return numb + "th"  
   

class EmbedScript(commands.Converter): 
  async def convert(self, ctx: commands.Context, argument: str):
   x = await EmbedBuilder.to_object(EmbedBuilder.embed_replacement(ctx.author, argument))
   if x[0] or x[1]: return {"content": x[0], "embed": x[1], "view": x[2]} 
   return {"content": EmbedBuilder.embed_replacement(ctx.author, argument)}
  


class GoToModal(discord.ui.Modal, title="change the page"):
  page = discord.ui.TextInput(label="page", placeholder="change the page", max_length=3)

  async def on_submit(self, interaction: discord.Interaction) -> None:
   if int(self.page.value) > len(self.embeds): return await interaction.client.ext.send_warning(interaction, f"You can only select a page **between** 1 and {len(self.embeds)}", ephemeral=True) 
   await interaction.response.edit_message(embed=self.embeds[int(self.page.value)-1]) 
  
  async def on_error(self, interaction: discord.Interaction, error: Exception) -> None: 
    await interaction.client.ext.send_warning(interaction, "Unable to change the page", ephemeral=True)
    
# Paginator Button Class
class PaginatorButton(Button):
    def __init__(self, emoji: str, style: ButtonStyle) -> None:
        super().__init__(emoji=emoji, style=style, custom_id=emoji)
        self.disabled: bool = False

    async def callback(self, interaction: Interaction) -> None:
        await interaction.response.defer()

        if self.custom_id == emoji.previous:
            if self.view.current_page <= 0:
                self.view.current_page = len(self.view.pages) - 1
            else:
                self.view.current_page -= 1

        elif self.custom_id == emoji.next:
            if self.view.current_page >= len(self.view.pages) - 1:
                self.view.current_page = 0
            else:
                self.view.current_page += 1

        elif self.custom_id == emoji.navigate:
            for child in self.view.children:
                child.disabled = True

            await self.view.message.edit(view=self.view)
            prompt = await interaction.followup.send("What page would you like to skip to?", ephemeral=True)

            try:
                response = await self.view.ctx.bot.wait_for(
                    "message",
                    timeout=30,
                    check=lambda m: m.author.id == interaction.user.id
                            and m.channel.id == interaction.channel.id
                            and m.content.isdigit()
                            and 1 <= int(m.content) <= len(self.view.pages),
                )
            except TimeoutError:
                for child in self.view.children:
                    child.disabled = False

                await self.view.message.edit(view=self.view)
                await prompt.delete()
                return
            else:
                self.view.current_page = int(response.content) - 1
                for child in self.view.children:
                    child.disabled = False

                with suppress(HTTPException):
                    await prompt.delete()
                    await response.delete()

        elif self.custom_id == emoji.cancel:
            with suppress(HTTPException):
                await self.view.message.delete()
            return

        page = self.view.pages[self.view.current_page]
        if self.view.type == "embed":
            await self.view.message.edit(embed=page, view=self.view)
        else:
            await self.view.message.edit(content=page, view=self.view)

# Paginator Class
class Paginator(View):
    def __init__(self, ctx: DefaultContext, pages: list[Union[Embed, str]]) -> None:
        super().__init__(timeout=180)
        self.ctx = ctx
        self.pages = pages
        self.current_page = 0
        self.message = None
        self.add_initial_buttons()

    def add_initial_buttons(self):
        for button in (
            PaginatorButton(emoji=emoji.previous, style=ButtonStyle.blurple),
            PaginatorButton(emoji=emoji.next, style=ButtonStyle.blurple),
            PaginatorButton(emoji=emoji.navigate, style=ButtonStyle.grey),
            PaginatorButton(emoji=emoji.cancel, style=ButtonStyle.red),
        ):
            self.add_item(button)

    @property
    def type(self) -> str:
        return "embed" if isinstance(self.pages[0], Embed) else "text"

    async def send(self, content: Union[Embed, str], **kwargs) -> Message:
        if self.type == "embed":
            return await self.ctx.send(embed=content, **kwargs)
        else:
            return await self.ctx.send(content=content, **kwargs)

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("You're not the author of this embed!", ephemeral=True)
            return False
        return True

    async def on_timeout(self) -> None:
        for child in self.children:
            child.disabled = True
        if self.message:
            await self.message.edit(view=self)

    async def start(self) -> Message:
        if len(self.pages) == 1:
            self.message = await self.send(self.pages[0])
        else:
            self.message = await self.send(self.pages[self.current_page], view=self)
        return self.message


class PaginatorView(discord.ui.View): 
    def __init__(self, ctx: commands.Context, embeds: list): 
      super().__init__()  
      self.embeds = embeds
      self.ctx = ctx
      self.i = 0

    @discord.ui.button(emoji="<:left:1238691473113874482>", style=discord.ButtonStyle.blurple)
    async def left(self, interaction: discord.Interaction, button: discord.ui.Button): 
      if interaction.user.id != self.ctx.author.id: return await interaction.client.ext.send_warning(interaction, "You are not the author of this embed")          
      if self.i == 0: 
        await interaction.response.edit_message(embed=self.embeds[-1])
        self.i = len(self.embeds)-1
        return
      self.i = self.i-1
      return await interaction.response.edit_message(embed=self.embeds[self.i])

    @discord.ui.button(emoji="<:right:1238691443900682322>", style=discord.ButtonStyle.blurple)
    async def right(self, interaction: discord.Interaction, button: discord.ui.Button): 
      if interaction.user.id != self.ctx.author.id: return await interaction.client.ext.send_warning(interaction, "You are not the author of this embed")     
      if self.i == len(self.embeds)-1: 
        await interaction.response.edit_message(embed=self.embeds[0])
        self.i = 0
        return 
      self.i = self.i + 1  
      return await interaction.response.edit_message(embed=self.embeds[self.i])   
 
    @discord.ui.button(emoji="<:navigate2:1242676587862822985>")
    async def goto(self, interaction: discord.Interaction, button: discord.ui.Button): 
     if interaction.user.id != self.ctx.author.id: return await interaction.client.ext.send_warning(interaction, "You are not the author of this embed")     
     modal = GoToModal()
     modal.embeds = self.embeds
     await interaction.response.send_modal(modal)
     await modal.wait()
     try:
      self.i = int(modal.page.value)-1
     except: pass 
    
    @discord.ui.button(emoji="<:deny:1229815132553744565>", style=discord.ButtonStyle.danger)
    async def delete(self, interaction: discord.Interaction, button: discord.ui.Button): 
      if interaction.user.id != self.ctx.author.id: return await interaction.client.ext.send_warning(interaction, "You are not the author of this embed")     
      await interaction.message.delete()

    async def on_timeout(self) -> None: 
        mes = await self.message.channel.fetch_message(self.message.id)
        if mes is None: return
        if len(mes.components) == 0: return
        for item in self.children:
            item.disabled = True

        try: await self.message.edit(view=self)   
        except: pass