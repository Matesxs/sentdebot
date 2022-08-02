# Store for all projects

import disnake
from disnake.ext import commands

from config import cooldowns
from static_data.strings import Strings
from features.base_cog import Base_Cog
from util import general_util
from database import projects_repo

class Projects(Base_Cog):
  def __init__(self, bot):
    super(Projects, self).__init__(bot, __file__)

  @commands.slash_command(name="projects")
  async def projects(self, inter: disnake.CommandInteraction):
    pass

  @projects.sub_command(name="add", description=Strings.projects_add_project_brief)
  @commands.check(general_util.is_mod)
  async def add_project(self, inter: disnake.CommandInteraction):
    await inter.response.send_modal(modal=disnake.ui.Modal(title="Add project", custom_id="add_project",
                                                           components=
                                                           [
                                                             disnake.ui.TextInput(label="Name", custom_id="add_project:name", max_length=128, required=True),
                                                             disnake.ui.TextInput(label="Description", custom_id="add_project:description", max_length=4000, required=True, style=disnake.TextInputStyle.multi_line)
                                                           ]))

  @staticmethod
  async def projects_list_autocomplete(_, search_string: str):
    projects = projects_repo.get_all()
    project_names = [project.name for project in projects]
    if search_string is None or search_string == "":
      return project_names
    return [project_name for project_name in project_names if search_string in project_name]

  @projects.sub_command(name="remove", description=Strings.projects_remove_project_brief)
  @commands.check(general_util.is_mod)
  async def remove_project(self, inter: disnake.CommandInteraction, project_name: str = commands.Param(autocomplete=projects_list_autocomplete, description="Name of project to delete")):
    if projects_repo.remove_project(project_name):
      await general_util.generate_success_message(inter, Strings.projects_remove_project_removed(name=project_name))
    else:
      await general_util.generate_error_message(inter, Strings.projects_remove_project_failed(name=project_name))

  @projects.sub_command(name="get", description=Strings.projects_project_get_brief)
  @cooldowns.short_cooldown
  async def project_get(self, inter: disnake.CommandInteraction, project_name: str = commands.Param(autocomplete=projects_list_autocomplete, description="Name of project to show")):
    project = projects_repo.get_by_name(project_name)
    if project is None:
      return await general_util.generate_error_message(inter, Strings.projects_project_get_not_found(name=project_name))

    embed = disnake.Embed(title=project.name, description=project.description, color=disnake.Color.dark_blue())
    general_util.add_author_footer(embed, inter.author)

    await inter.send(embed=embed)

  @commands.Cog.listener()
  async def on_modal_submit(self, inter: disnake.ModalInteraction):
    if inter.custom_id == "add_project":
      project = projects_repo.add_project(project_name=inter.text_values["add_project:name"], project_description=inter.text_values["add_project:description"])
      if project is None:
        await general_util.generate_error_message(inter, Strings.projects_add_project_failed(name=inter.text_values["add_project:name"]))
      else:
        await general_util.generate_success_message(inter, Strings.projects_add_project_added(name=inter.text_values["add_project:name"]))

def setup(bot):
  bot.add_cog(Projects(bot))
