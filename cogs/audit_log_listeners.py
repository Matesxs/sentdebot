import disnake
from disnake.ext import commands
from typing import Optional, Union

from config import config
from features.base_cog import Base_Cog
from database import audit_log_repo
from features.before_message_context import BeforeMessageContext

class AuditLogListeners(Base_Cog):
  def __init__(self, bot):
    super(AuditLogListeners, self).__init__(bot, __file__)

  @commands.Cog.listener()
  async def on_member_join(self, member: disnake.Member):
    if member.bot or member.system: return
    audit_log_repo.auditlog_member_joined(member)

  @commands.Cog.listener()
  async def on_member_remove(self, member: disnake.Member):
    if member.bot or member.system: return
    audit_log_repo.auditlog_member_left(member)

  @commands.Cog.listener()
  async def on_member_update(self, before: disnake.Member, after: disnake.Member):
    if after.bot or after.system: return
    audit_log_repo.auditlog_member_updated(before, after)

  @commands.Cog.listener()
  async def on_user_update(self, before: disnake.User, after: disnake.User):
    if after.bot or after.system: return
    audit_log_repo.auditlog_user_update(before, after)

  async def handle_message_edited(self, before: Optional[BeforeMessageContext], after: disnake.Message):
    if after.author.bot or after.author.system: return
    if after.content.startswith(config.base.command_prefix): return

    audit_log_repo.auditlog_message_edited(before, after)

  async def handle_message_deleted(self, message: Union[disnake.RawMessageDeleteEvent, BeforeMessageContext]):
    if isinstance(message, disnake.RawMessageDeleteEvent): return
    if message.author.bot or message.author.system: return
    if message.content.startswith(config.base.command_prefix): return

    audit_log_repo.auditlog_message_deleted(message)

def setup(bot):
  bot.add_cog(AuditLogListeners(bot))
