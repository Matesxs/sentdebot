import disnake
from disnake.ext import commands
from requests_html import HTMLSession

from config import config
from static_data.strings import Strings
from features.base_cog import Base_Cog
from util import general_util

class Common(Base_Cog):
  def __init__(self, bot: commands.Bot):
    super(Common, self).__init__(bot, __file__)

  @commands.command(brief=Strings.common_member_count_brief)
  @commands.guild_only()
  async def member_count(self, ctx: commands.Context):
    await general_util.delete_message(self.bot, ctx)
    await ctx.send(embed=disnake.Embed(title="Member count", description=f"{ctx.guild.member_count} :monkey:", color=disnake.Color.dark_blue()))

  @commands.command(brief=Strings.common_search_brief)
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
      await general_util.generate_error_message(ctx, Strings.populate_string("common_search_nothing_found", term=search_term))

def setup(bot):
  bot.add_cog(Common(bot))