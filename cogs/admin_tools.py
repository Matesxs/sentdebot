import asyncio
import datetime
import disnake
from disnake.ext import commands
from typing import Union, List, Optional
from Levenshtein import ratio

from config import cooldowns, config
from features.base_cog import Base_Cog
from util import general_util
from database import messages_repo, users_repo, channels_repo
from static_data.strings import Strings
from util.logger import setup_custom_logger
from features.paginator import EmbedView

logger = setup_custom_logger(__name__)

class AdminTools(Base_Cog):
  def __init__(self, bot: commands.Bot):
    super(AdminTools, self).__init__(bot, __file__)

  async def delete_users_messages(self, user_id: int, guild_id: int, hours_back: float):
    delete_message_count = 0

    messages = messages_repo.get_messages_of_member(user_id, guild_id, hours_back)
    for message_it in messages:
      message = await message_it.to_object(self.bot)
      if message is None: continue

      try:
        await message.delete()
        await asyncio.sleep(0.1)
        delete_message_count += 1
      except disnake.NotFound:
        pass

    return delete_message_count

  @commands.command(brief=Strings.admin_tools_clean_raid_brief, help=Strings.admin_tools_clean_raid_help)
  @commands.check(general_util.is_mod)
  @commands.guild_only()
  async def clean_raid(self, ctx: commands.Context, first_message: Union[disnake.Message, int], last_message: Union[disnake.Message, int], hours_back: float = 1.0):
    if hours_back <= 0:
      return await general_util.generate_error_message(ctx, Strings.admin_tools_invalid_hours_back)

    if isinstance(first_message, int):
      first_message = await general_util.get_or_fetch_message(self.bot, ctx.channel, first_message)
    if isinstance(last_message, int):
      last_message = await general_util.get_or_fetch_message(self.bot, ctx.channel, last_message)

    if first_message is None or last_message is None:
      return await general_util.generate_error_message(ctx, Strings.admin_tools_clean_raid_messages_not_found)

    joined_users_items = users_repo.members_joined_in_timeframe(first_message.author.joined_at, last_message.author.joined_at, ctx.guild.id)

    statuses = []
    some_failed = False
    for user_it in joined_users_items:
      delete_message_count = await self.delete_users_messages(int(user_it.id), ctx.guild.id, hours_back)
      statuses.append(f"{user_it.nick} - Deleted {delete_message_count} messages")

    embed = disnake.Embed(title="Clean raid report", description=general_util.truncate_string("\n".join(statuses), 4000), color=disnake.Color.orange() if some_failed else disnake.Color.green())
    general_util.add_author_footer(embed, ctx.author)

    await ctx.send(embed=embed)

  @commands.command(brief=Strings.admin_tools_destroy_raid_brief, help=Strings.admin_tools_destroy_raid_help)
  @commands.check(general_util.is_mod)
  @commands.guild_only()
  async def destroy_raid(self, ctx: commands.Context, first_message: Union[disnake.Message, int], last_message: Union[disnake.Message, int], hours_back: float=1.0):
    if isinstance(first_message, int):
      first_message = await general_util.get_or_fetch_message(self.bot, ctx.channel, first_message)
    if isinstance(last_message, int):
      last_message = await general_util.get_or_fetch_message(self.bot, ctx.channel, last_message)

    if first_message is None or last_message is None:
      return await general_util.generate_error_message(ctx, Strings.admin_tools_destroy_raid_messages_not_found)

    joined_users_items = users_repo.members_joined_in_timeframe(first_message.author.joined_at, last_message.author.joined_at, ctx.guild.id)

    statuses = []
    some_failed = False
    for user_it in joined_users_items:
      delete_message_count = None
      if hours_back > 0:
        delete_message_count = await self.delete_users_messages(int(user_it.id), ctx.guild.id, hours_back)

      member = await general_util.get_or_fetch_member(ctx.guild, int(user_it.id))
      if member is None:
        statuses.append(f"{user_it.nick} not banned (not found)" + f" - Deleted {delete_message_count} messages" if delete_message_count is not None else "")
        some_failed = True
      else:
        try:
          await member.ban()
        except:
          statuses.append(f"{user_it.nick} not banned (unable)" + f" - Deleted {delete_message_count} messages" if delete_message_count is not None else "")
          some_failed = True
          continue

        statuses.append(f"{user_it.nick} banned" + f" - Deleted {delete_message_count} messages" if delete_message_count is not None else "")

    embed = disnake.Embed(title="Destroy raid report", description=general_util.truncate_string("\n".join(statuses), 4000), color=disnake.Color.orange() if some_failed else disnake.Color.green())
    general_util.add_author_footer(embed, ctx.author)

    await ctx.send(embed=embed)

  @commands.command(brief=Strings.admin_tools_clean_user_brief, help=Strings.admin_tools_clean_user_help)
  @commands.check(general_util.is_mod)
  @commands.guild_only()
  async def clean_user(self, ctx: commands.Context, user: Union[disnake.Member, disnake.User, int], hours_back: float = 1.0):
    if hours_back <= 0:
      return await general_util.generate_error_message(ctx, Strings.admin_tools_invalid_hours_back)
    delete_message_count = await self.delete_users_messages(user if isinstance(user, int) else user.id, ctx.guild.id, hours_back)
    await general_util.generate_success_message(ctx, f"User's messages cleaned\nDeleted `{delete_message_count}` messages")

  @commands.command(brief=Strings.admin_tools_destroy_user_brief, help=Strings.admin_tools_destroy_user_help)
  @commands.check(general_util.is_mod)
  @commands.guild_only()
  async def destroy_user(self, ctx: commands.Context, user: Union[disnake.Member, disnake.User, int], hours_back: float = 1.0):
    delete_message_count = None
    if hours_back > 0:
      delete_message_count = await self.delete_users_messages(user if isinstance(user, int) else user.id, ctx.guild.id, hours_back)

    await user.ban()
    await general_util.generate_success_message(ctx, "User destroyed" + (f"\nDeleted `{delete_message_count}` messages" if delete_message_count is not None else ""))

  @commands.command(brief=Strings.admin_tools_purge_brief, help=Strings.admin_tools_purge_help)
  @commands.check(general_util.is_mod)
  @commands.guild_only()
  async def purge(self, ctx: commands.Context, hours_back: float=1.0):
    threshold = datetime.datetime.utcnow() - datetime.timedelta(hours=hours_back)
    deleted_messages = await ctx.channel.purge(after=threshold)
    await general_util.generate_success_message(ctx, f"Deleted {len(deleted_messages)} message(s)")

  @commands.slash_command()
  @commands.check(general_util.is_administrator)
  async def essentials(self, inter: disnake.CommandInteraction):
    pass

  @essentials.sub_command(description=Strings.admin_tools_message_search_description)
  @cooldowns.long_cooldown
  @commands.guild_only()
  async def search_messages(self, inter: disnake.CommandInteraction,
                            search_term: str=commands.Param(description="Term to search in messages"),
                            match_with_levenshtein: bool=commands.Param(default=False, description="Use Levenshtein distance for searching"),
                            member: Optional[disnake.Member]=commands.Param(default=None, description="Filter only specific member"),
                            limit: int=commands.Param(default=100, description="Limit number of messages to retrieve")):
    await inter.response.defer(with_message=True)

    message_iterator:List[messages_repo.Message] = messages_repo.get_messages_iterator(inter.guild_id, member)

    messages = []
    number_of_messages = 0
    for message_item in message_iterator:
      if (search_term.lower() in message_item.content.lower()) \
          if not match_with_levenshtein else \
          (ratio(search_term.lower(), message_item.content.lower()) > 0.7):
        messages.append(message_item)
        number_of_messages += 1
        if number_of_messages >= limit:
          break

    if number_of_messages == 0:
      return await general_util.generate_error_message(inter, "No match found")

    pages = []
    title = f"Message search for term `{search_term}`"
    emb = disnake.Embed(title=title, colour=disnake.Color.dark_blue())
    general_util.add_author_footer(emb, inter.author)
    while messages:
      message_item = messages.pop()
      message = await message_item.to_object(self.bot)
      if message is None: continue

      field_title = f"Author: {general_util.truncate_string(message.author.display_name, 20)}"
      text = general_util.truncate_string(message.content, 800) + f"\n[Link]({message.jump_url})"
      embed_len = len(emb)
      added_length = len(field_title) + len(text)

      if embed_len + added_length > 5000:
        pages.append(emb)
        emb = disnake.Embed(title=title, colour=disnake.Color.dark_blue())
        general_util.add_author_footer(emb, inter.author)

      emb.add_field(name=field_title, value=text, inline=False)

    pages.append(emb)

    await EmbedView(inter.author, pages, perma_lock=True, timeout=600).run(inter)

  @essentials.sub_command(description=Strings.admin_tools_pull_data_description)
  @commands.max_concurrency(1, per=commands.BucketType.default)
  @cooldowns.huge_cooldown
  @commands.guild_only()
  async def pull_data(self, inter: disnake.CommandInteraction):
    async def save_messages(message_it: disnake.abc.HistoryIterator):
      retries = 0
      while True:
        try:
          async for message in message_it:
            if message.author.bot or message.author.system: continue
            messages_repo.add_if_not_existing(message, commit=False)
            await asyncio.sleep(0.2)
          break
        except disnake.Forbidden:
          return
        except disnake.HTTPException:
          retries += 1
          if retries >= 10:
            logger.warning("Limit reached 10x, skipping")
            break

          logger.warning("Limit reached, waiting")
          await asyncio.sleep(60)

    logger.info("Starting members pulling")
    await inter.send(content=Strings.admin_tools_pull_data_pulling_members, ephemeral=True)

    members = inter.guild.fetch_members(limit=None)
    async for member in members:
      users_repo.get_or_create_member_if_not_exist(member)
      await asyncio.sleep(0.2)

    logger.info("Starting channels pulling")
    message = await inter.original_message()
    if not inter.is_expired():
      await message.edit(content=Strings.admin_tools_pull_data_pulling_channels)

    channels = await inter.guild.fetch_channels()
    for channel in channels:
      if isinstance(channel, disnake.abc.Messageable):
        channels_repo.get_or_create_text_channel_if_not_exist(channel)
        await asyncio.sleep(0.2)

    channels_repo.session.commit()

    logger.info("Starting messages pulling")

    if not inter.is_expired():
      await message.edit(content=Strings.admin_tools_pull_data_pulling_messages)

    for channel in channels:
      if isinstance(channel, disnake.abc.Messageable):
        messages_it = channel.history(limit=None, oldest_first=True, after=datetime.datetime.utcnow() - datetime.timedelta(days=config.essentials.delete_messages_after_days))
        await save_messages(messages_it)
        messages_repo.session.commit()

        if hasattr(channel, "threads"):
          threads: List[disnake.Thread] = channel.threads
          for thread in threads:
            messages_it = thread.history(limit=None, oldest_first=True, after=datetime.datetime.utcnow() - datetime.timedelta(days=config.essentials.delete_messages_after_days))
            await save_messages(messages_it)

          messages_repo.session.commit()

    logger.info("Data pulling completed")

    if not inter.is_expired():
      await message.edit(content=Strings.admin_tools_pull_data_pulling_complete)

  @essentials.sub_command(description=Strings.admin_tools_purge_bot_messages_description)
  @cooldowns.default_cooldown
  @commands.guild_only()
  async def purge_bot_messages(self, inter: disnake.CommandInteraction):
    if isinstance(inter.channel, (disnake.TextChannel, disnake.Thread, disnake.VoiceChannel, disnake.StageChannel)):
      try:
        await inter.channel.purge(limit=100, check=lambda x: x.author == self.bot.user, bulk=False)
      except disnake.NotFound:
        pass
      return
    await general_util.generate_error_message(inter, Strings.admin_tools_purge_bot_messages_invalid_channel)

def setup(bot):
  bot.add_cog(AdminTools(bot))