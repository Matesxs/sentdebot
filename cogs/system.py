import disnake as discord
from disnake.ext import commands
import asyncio
import math

from config import config
from features.base_cog import Base_Cog
from util import general_util
from util.logger import setup_custom_logger
from static_data.strings import Strings
from features.paginator import PaginatorSession

logger = setup_custom_logger(__name__)

class System(Base_Cog):
  def __init__(self, bot: commands.Bot):
    super(System, self).__init__(bot, __file__)

  @commands.command(brief=Strings.system_load_brief, help=Strings.system_load_help)
  @commands.check(general_util.is_administrator)
  @commands.guild_only()
  async def load(self, ctx: commands.Context, extension_name: str):
    await general_util.delete_message(self.bot, ctx)

    loaded_cogs = [cog.file for cog in self.bot.cogs.values()]
    cogs_in_folder = general_util.get_cogs_in_folder()

    if extension_name.lower() == "all":
      final_embed = discord.Embed(title="Extensions loaded", color=discord.Color.green(), description="Failed extensions:")

      for cog in cogs_in_folder:
        if str(cog) not in loaded_cogs:
          try:
            self.bot.load_extension(f"cogs.{str(cog)}")
            logger.info(f"{str(cog)} loaded")
            await asyncio.sleep(0)
          except Exception as e:
            final_embed.description += f"\n{str(cog)}"
            final_embed.colour = discord.Color.orange()

            await general_util.generate_error_message(ctx, Strings.populate_string("system_unable_to_load_cog", cog=str(cog), e=e))

      await ctx.send(embed=final_embed, delete_after=config.success_duration)
    else:
      try:
        self.bot.load_extension(f"cogs.{extension_name}")
        logger.info(f"{extension_name} loaded")

        await general_util.generate_success_message(ctx, Strings.populate_string("system_cog_loaded", extension=extension_name))
      except Exception as e:
        await general_util.generate_error_message(ctx, Strings.populate_string("system_unable_to_load_cog", cog=extension_name, e=e))

  @commands.command(brief=Strings.system_unload_brief, help=Strings.system_unload_help)
  @commands.check(general_util.is_administrator)
  @commands.guild_only()
  async def unload(self, ctx: commands.Context, extension_name: str):
    await general_util.delete_message(self.bot, ctx)

    loaded_cogs = [cog.file for cog in self.bot.cogs.values()]

    if extension_name in config.protected_cogs:
      return await general_util.generate_error_message(ctx, Strings.populate_string("system_unload_protected_cog", extension=extension_name))

    if extension_name.lower() == "all":
      final_embed = discord.Embed(title="Extensions unload", color=discord.Color.green(), description="Failed extensions:")

      for cog in loaded_cogs:
        if cog not in config.protected_cogs:
          try:
            self.bot.unload_extension(f"cogs.{cog}")
            logger.info(f'{cog} unloaded')
            await asyncio.sleep(0)
          except Exception as e:
            final_embed.description += f"\n{str(cog)}"
            final_embed.colour = discord.Color.orange()

            await general_util.generate_error_message(ctx, Strings.populate_string("system_unable_to_unload_cog", cog=cog, e=e))

      await ctx.send(embed=final_embed, delete_after=config.success_duration)
    else:
      try:
        self.bot.unload_extension(f"cogs.{extension_name}")
        logger.info(f'{extension_name} unloaded')
        await general_util.generate_success_message(ctx, Strings.populate_string("system_cog_unloaded", extension=extension_name))
      except Exception as e:
        await general_util.generate_error_message(ctx, Strings.populate_string("system_unable_to_unload_cog", cog=extension_name, e=e))

  @commands.command(brief=Strings.system_reload_brief, help=Strings.system_reload_help)
  @commands.check(general_util.is_administrator)
  @commands.guild_only()
  async def reload(self, ctx: commands.Context, extension_name: str):
    await general_util.delete_message(self.bot, ctx)

    loaded_cogs = [cog.file for cog in self.bot.cogs.values()]

    if extension_name.lower() == "all":
      final_embed = discord.Embed(title="Extensions reloaded", color=discord.Color.green(), description="Failed extensions:")

      for cog in loaded_cogs:
        try:
          self.bot.reload_extension(f"cogs.{cog}")
          logger.info(f"{cog} reloaded")
          await asyncio.sleep(0)
        except Exception as e:
          final_embed.description += f"\n{str(cog)}"
          final_embed.colour = discord.Color.orange()

          await general_util.generate_error_message(ctx, Strings.populate_string("system_unable_to_reload_cog", cog=cog, e=e))

      await ctx.send(embed=final_embed, delete_after=config.success_duration)
    else:
      try:
        self.bot.reload_extension(f"cogs.{extension_name}")
        logger.info(f"{extension_name} reloaded")

        await general_util.generate_success_message(ctx, Strings.populate_string("system_cog_reloaded", extension=extension_name))
      except Exception as e:
        await general_util.generate_error_message(ctx, Strings.populate_string("system_unable_to_reload_cog", cog=extension_name, e=e))

  @commands.command(brief=Strings.system_cogs_brief, aliases=["extensions"])
  @commands.check(general_util.is_administrator)
  @commands.guild_only()
  async def cogs(self, ctx: commands.Context):
    await general_util.delete_message(self.bot, ctx)

    cogs_in_folder = general_util.get_cogs_in_folder()
    loaded_cogs = [cog.file for cog in self.bot.cogs.values()]

    number_of_batches = math.ceil(len(cogs_in_folder) / 21)
    cogs_in_folder_batches = [cogs_in_folder[i * 21: i * 21 + 21] for i in range(number_of_batches)]

    pages = []
    for batch in cogs_in_folder_batches:
      embed = discord.Embed(title="Cogs", description="List of all loaded and unloaded cogs", color=discord.Color.dark_magenta())

      for idx, cog in enumerate(batch):
        status = "🔒 *protected*" if cog in config.protected_cogs else ("✅ **loaded**" if cog in loaded_cogs else "❌ **unloaded**")
        embed.add_field(name=cog, value=status)

      pages.append(embed)

    p_session = PaginatorSession(self.bot, ctx, pages=pages)
    await p_session.run()

def setup(bot):
  bot.add_cog(System(bot))