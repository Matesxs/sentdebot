# Basic general use command

import datetime
import disnake
from disnake.ext import commands
from requests_html import HTMLSession
import time
import humanize

from config import cooldowns
from static_data.strings import Strings
from features.base_cog import Base_Cog
from util import general_util
from modals.vote_modal import VoteSetupModal

class Common(Base_Cog):
  def __init__(self, bot):
    super(Common, self).__init__(bot, __file__)

  @commands.command(name="invite", brief="Send invite link")
  @cooldowns.long_cooldown
  async def invite_link(self, ctx: commands.Context):
    await general_util.delete_message(self.bot, ctx)
    await ctx.send("https://discord.com/oauth2/authorize?client_id=998191988312657960&permissions=1567096171606&scope=bot")

  @commands.command(brief="Show uptime of bot")
  @cooldowns.default_cooldown
  async def uptime(self, ctx: commands.Context):
    await general_util.delete_message(self.bot, ctx)
    description = f"{humanize.naturaldelta(datetime.datetime.utcnow() - self.bot.start_time)}\nLast error: {humanize.naturaltime(datetime.datetime.utcnow() - self.bot.last_error) if self.bot.last_error is not None else 'Never'}"
    embed = disnake.Embed(title="Uptime", description=description, color=disnake.Color.dark_blue())
    general_util.add_author_footer(embed, ctx.author)
    await ctx.send(embed=embed)

  @commands.message_command(name="Pin message")
  @commands.check(general_util.is_mod)
  async def pin_message(self, inter: disnake.MessageCommandInteraction, message: disnake.Message):
    try:
      if message.pinned:
        await message.unpin(reason=f"{inter.author} unpinned message")
        await general_util.generate_success_message(inter, "Message pinned")
      else:
        await message.pin(reason=f"{inter.author} pinned message")
    except disnake.Forbidden:
      await general_util.generate_error_message(inter, "Bot don't have permissions to pin this message")

  @commands.command(brief=Strings.common_ping_brief)
  @cooldowns.default_cooldown
  async def ping(self, ctx: commands.Context):
    await general_util.delete_message(self.bot, ctx)

    em = disnake.Embed(color=disnake.Color.dark_blue(), title="Pong!")
    general_util.add_author_footer(em, ctx.message.author)

    start_time = time.time()
    message:disnake.Message = await ctx.channel.send(embed=em)
    end_time = time.time()

    em.description = em.description = f'Bot: {round(self.bot.latency * 1000)} ms\nAPI: {round((end_time - start_time) * 1000)}ms'
    await message.edit(embed=em)

  @commands.command(brief=Strings.common_member_count_brief)
  @cooldowns.default_cooldown
  @commands.guild_only()
  async def member_count(self, ctx: commands.Context):
    await general_util.delete_message(self.bot, ctx)
    embed = disnake.Embed(title="Member count", description=f"{ctx.guild.member_count} :monkey:", color=disnake.Color.dark_blue())
    general_util.add_author_footer(embed, ctx.author)
    await ctx.send(embed=embed)

  @commands.command(brief=Strings.common_search_brief)
  @cooldowns.default_cooldown
  async def search(self, ctx: commands.Context, *, search_term: str):
    await general_util.delete_message(self.bot, ctx)

    search_term_cleared = search_term.replace(" ", "%20")
    search_link = f"https://pythonprogramming.net/search/?q={search_term_cleared}"

    session = HTMLSession()
    r = session.get(search_link)

    specific_tutorials = [(tut.text, list(tut.links)[0]) for tut in r.html.find("a") if "collection-item" in tut.html]

    if len(specific_tutorials) > 0:
      embed = disnake.Embed(title=f"Results for '{search_term[:150]}'", description=f"More results: <{search_link}>", color=disnake.Color.dark_blue())
      for result in specific_tutorials[:5]:
        embed.add_field(name=f"{result[0]}", value=f"<https://pythonprogramming.net{result[1]}>", inline=False)
      general_util.add_author_footer(embed, ctx.author)

      await ctx.send(embed=embed)
    else:
      await general_util.generate_error_message(ctx, Strings.common_search_nothing_found(term=search_term))

  @commands.slash_command(name="vote", description=Strings.common_vote_brief)
  @cooldowns.long_cooldown
  async def vote_command(self, inter: disnake.CommandInteraction):
    await inter.response.send_modal(VoteSetupModal())

def setup(bot):
  bot.add_cog(Common(bot))
