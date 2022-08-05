import disnake
from disnake.ext import commands, tasks
from typing import Union

from util.logger import setup_custom_logger
from config import config
from database import messages_repo, users_repo, user_metrics_repo, guilds_repo, channels_repo
from features.base_cog import Base_Cog
from features import before_message_context

logger = setup_custom_logger(__name__)

class DataCollection(Base_Cog):
  def __init__(self, bot):
    super(DataCollection, self).__init__(bot, __file__)

    if not self.cleanup_taks.is_running():
      self.cleanup_taks.start()

    if self.bot.is_ready():
      if not self.user_stats_task.is_running():
        self.user_stats_task.start()

      if not self.user_update_task.is_running():
        self.user_update_task.start()

  @commands.Cog.listener()
  async def on_ready(self):
    if not self.user_stats_task.is_running():
      self.user_stats_task.start()

    if not self.user_update_task.is_running():
      self.user_update_task.start()

  def cog_unload(self) -> None:
    if self.cleanup_taks.is_running():
      self.cleanup_taks.cancel()

    if self.user_stats_task.is_running():
      self.user_stats_task.cancel()

    if self.user_update_task.is_running():
      self.user_update_task.start()

  @tasks.loop(minutes=5)
  async def user_stats_task(self):
    guilds = self.bot.guilds
    for guild in guilds:
      user_metrics_repo.add_user_metrics(guild)
    user_metrics_repo.session.commit()

  @commands.Cog.listener()
  async def on_raw_thread_update(self, after: disnake.Thread):
    thread_it = channels_repo.get_thread(after.id)
    if thread_it is not None:
      thread_it.archived = after.archived
      thread_it.locked = after.locked
      channels_repo.session.commit()

  @commands.Cog.listener()
  async def on_thread_create(self, thread: disnake.Thread):
    channels_repo.get_or_create_text_thread(thread)

  @commands.Cog.listener()
  async def on_raw_thread_delete(self, payload: disnake.RawThreadDeleteEvent):
    channels_repo.remove_thread(payload.thread_id)

  @commands.Cog.listener()
  async def on_guild_channel_create(self, channel: disnake.abc.GuildChannel):
    if isinstance(channel, (disnake.TextChannel, disnake.VoiceChannel, disnake.StageChannel, disnake.ForumChannel)):
      channels_repo.get_or_create_text_channel_if_not_exist(channel)

  @commands.Cog.listener()
  async def on_guild_channel_delete(self, channel: disnake.abc.GuildChannel):
    if isinstance(channel, (disnake.TextChannel, disnake.VoiceChannel, disnake.StageChannel, disnake.ForumChannel)):
      channels_repo.remove_channel(channel.id)

  @commands.Cog.listener()
  async def on_message(self, message: disnake.Message):
    if message.guild is None: return
    if message.author.bot or message.author.system: return
    if message.content.startswith(config.base.command_prefix): return

    messages_repo.add_or_set_message(message, commit=True)

  async def handle_message_edited(self, _, after: disnake.Message):
    if after.guild is None: return
    if after.author.bot or after.author.system: return
    if after.content.startswith(config.base.command_prefix): return

    if not users_repo.can_collect_data(after.author.id, after.guild.id):
      return

    messages_repo.add_or_set_message(after)

  async def handle_message_deleted(self, message: Union[disnake.RawMessageDeleteEvent, before_message_context.BeforeMessageContext]):
    message_id = message.message_id if isinstance(message, disnake.RawMessageDeleteEvent) else message.id
    messages_repo.delete_message(message_id, commit=True)

  @commands.Cog.listener()
  async def on_member_update(self, _, after: disnake.Member):
    user_it = users_repo.get_or_create_member_if_not_exist(after)
    user_it.nick = after.display_name
    user_it.icon_url = after.display_avatar.url
    user_it.premium = after.premium_since is not None
    users_repo.session.commit()

  @commands.Cog.listener()
  async def on_user_update(self, _, after: disnake.User):
    user_it = users_repo.get_or_create_user_if_not_exist(after)
    user_it.name = after.name
    users_repo.session.commit()

  @commands.Cog.listener()
  async def on_member_join(self, member: disnake.Member):
    users_repo.get_or_create_member_if_not_exist(member)

  @commands.Cog.listener()
  async def on_member_remove(self, member: disnake.Member):
    users_repo.set_member_left(member)

  @commands.Cog.listener()
  async def on_guild_join(self, guild: disnake.Guild):
    guilds_repo.get_or_create_guild_if_not_exist(guild)
    for member in guild.members:
      users_repo.get_or_create_member_if_not_exist(member)

  @commands.Cog.listener()
  async def on_guild_remove(self, guild: disnake.Guild):
    guilds_repo.remove_guild(guild.id)

  @tasks.loop(hours=24)
  async def cleanup_taks(self):
    logger.info("Starting cleanup")
    if config.essentials.delete_left_users_after_days > 0:
      users_repo.delete_left_members(config.essentials.delete_left_users_after_days, commit=False)
    if config.essentials.delete_messages_after_days > 0:
      messages_repo.delete_old_messages(config.essentials.delete_messages_after_days, commit=False)

    user_iterator = users_repo.get_all_users_iterator()
    for user_it in user_iterator:
      if len(user_it.members) == 0:
        users_repo.session.delete(user_it)

    users_repo.session.commit()
    logger.info("Cleanup finished")

  @tasks.loop(hours=1)
  async def user_update_task(self):
    members = self.bot.get_all_members()
    updated_users = []

    for member in members:
      if member.id not in updated_users:
        updated_users.append(member.id)

        user_it = users_repo.get_user(member.id)
        if user_it is None:
          users_repo.get_or_create_user_if_not_exist(member)
          continue

        user_it.status = member.status

    users_repo.session.commit()

def setup(bot):
  bot.add_cog(DataCollection(bot))
