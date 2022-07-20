import asyncio
import datetime
import disnake
from disnake.ext import commands, tasks
from typing import Dict, Optional, List

from config import config
from static_data.strings import Strings
from features.base_cog import Base_Cog
from util.logger import setup_custom_logger

logger = setup_custom_logger(__name__)

def generate_nick_string(members: List[disnake.Member]):
  if len(members) > 1:
    output = ", ".join([member.name for member in members[:-1]])
    return f"{output} and {members[-1].name}"
  return f"{members[0].name}"

class VoiceChannelNotifier(Base_Cog):
  def __init__(self, bot: commands.Bot):
    super(VoiceChannelNotifier, self).__init__(bot, __file__)

    self.voice_channel_ids = [channel.id for channel in config.voice_channel_notifier.channels]
    self.annouce_thresholds = {channel.id: channel.user_threshold for channel in config.voice_channel_notifier.channels}
    self.annouce_channel_ids = {channel.id: channel.announce_channel_id for channel in config.voice_channel_notifier.channels}

    self.initialised = False
    self.voice_channel_members: Dict[int, Dict[int, datetime.datetime]] = {}
    self.member_counts: Dict[int, int] = {}
    self.last_announcements:Dict[int, Optional[datetime.datetime]] = {}

    if self.bot.is_ready():
      loop = asyncio.get_running_loop()
      asyncio.ensure_future(self.async_init(), loop=loop)

  @commands.Cog.listener()
  async def on_ready(self):
    await self.async_init()

  def cog_unload(self) -> None:
    if self.announcement_task.is_running():
      self.announcement_task.cancel()

  def __del__(self):
    if self.announcement_task.is_running():
      self.announcement_task.cancel()

  async def async_init(self):
    self.voice_channel_members = {channel_id:{} for channel_id in self.voice_channel_ids}
    self.member_counts = {channel_id:0 for channel_id in self.voice_channel_ids}
    self.last_announcements = {channel_id:None for channel_id in self.voice_channel_ids}

    update_time = datetime.datetime.utcnow()

    for channel_id in self.voice_channel_ids:
      channel = self.bot.get_channel(channel_id)

      if channel is None:
        channel = await self.bot.fetch_channel(channel_id)

      if channel is None or not isinstance(channel, disnake.VoiceChannel):
        continue

      for member in channel.members:
        self.voice_channel_members[channel.id][member.id] = update_time

    self.initialised = True
    if not self.announcement_task.is_running():
      self.announcement_task.start()

  def get_number_of_users_in_channel(self, channel_id: int) -> int:
    channel_members = self.voice_channel_members[channel_id]

    number_of_members = 0

    current_time = datetime.datetime.utcnow()
    for _, join_time in channel_members.items():
      if current_time - join_time > datetime.timedelta(minutes=config.voice_channel_notifier.stay_threshold_minutes):
        number_of_members += 1

    # logger.info(f"Members in channel `{channel_id}`: {number_of_members}")

    return number_of_members

  async def get_n_oldest_members(self, channel: disnake.VoiceChannel, number_of_members: int) -> List[disnake.Member]:
    list_of_members = list(self.voice_channel_members[channel.id].items())
    list_of_members.sort(key=lambda tup: tup[1])

    oldest_members_ids = [mem[0] for mem in list_of_members[:number_of_members]]
    members = []
    for member_id in oldest_members_ids:
      member = channel.guild.get_member(member_id)
      if member is None:
        member = await channel.guild.fetch_member(member_id)

      if member is not None:
        members.append(member)
    return members

  def get_number_of_users(self) -> Dict[int, int]:
    members = {}
    for channel_id in self.voice_channel_members.keys():
      members[channel_id] = self.get_number_of_users_in_channel(channel_id)
    return members

  @tasks.loop(minutes=config.voice_channel_notifier.update_every_minutes)
  async def announcement_task(self):
    new_member_counts = self.get_number_of_users()

    current_time = datetime.datetime.utcnow()

    for channel_id in self.voice_channel_ids:
      member_threshold = self.annouce_thresholds[channel_id]
      if member_threshold <= 0:
        logger.warning(f"Invalid member threshold for channel id `{channel_id}`, threshold can't be lower than 1")
        continue

      time_since_announcement = (current_time - self.last_announcements[channel_id]) if self.last_announcements[channel_id] is not None else None

      if new_member_counts[channel_id] >= member_threshold > self.member_counts[channel_id] and \
         (time_since_announcement is None or time_since_announcement >= datetime.timedelta(minutes=config.voice_channel_notifier.delay_between_announcements_minutes)):
        announce_channel = self.bot.get_channel(self.annouce_channel_ids[channel_id])

        if announce_channel is None:
          announce_channel = await self.bot.fetch_channel(self.annouce_channel_ids[channel_id])

        if announce_channel is None:
          logger.warning(f"Failed to find announce channel with id `{self.annouce_channel_ids[channel_id]}` for voice channel with id `{channel_id}`")
          continue

        voice_channel = self.bot.get_channel(channel_id)
        if voice_channel is None:
          voice_channel = await self.bot.fetch_channel(channel_id)

        if voice_channel is None:
          logger.warning(f"Failed to find voice channel with id `{channel_id}` for announcement")
          continue

        oldest_members = await self.get_n_oldest_members(voice_channel, member_threshold)
        if not oldest_members:
          continue

        nicks = generate_nick_string(oldest_members)

        if len(oldest_members) == 1:
          await announce_channel.send(Strings.voice_channel_notifier_single_user(nick=nicks, channel=voice_channel.mention))
        else:
          await announce_channel.send(Strings.voice_channel_notifier_multiple_users(nicks=nicks, channel=voice_channel.mention))

        logger.info(f"Event in `{voice_channel.name}`")
        self.last_announcements[channel_id] = current_time
    self.member_counts = new_member_counts

  @commands.Cog.listener()
  async def on_voice_state_update(self, member: disnake.Member, before: disnake.VoiceState, after: disnake.VoiceState):
    if not self.initialised: return

    if (before.channel is not None and after.channel is not None and before.channel == after.channel) or (before.channel is None and after.channel is None):
        return

    if before.channel is not None and before.channel.id in self.voice_channel_ids:
      del self.voice_channel_members[before.channel.id][member.id]

    if after.channel is not None and after.channel.id in self.voice_channel_ids:
      self.voice_channel_members[after.channel.id][member.id] = datetime.datetime.utcnow()

def setup(bot):
  bot.add_cog(VoiceChannelNotifier(bot))
