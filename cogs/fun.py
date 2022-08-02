import disnake
from disnake.ext import commands
import cachetools
import requests
import io
from PIL import Image, ImageDraw

from config import cooldowns
from features.base_cog import Base_Cog
from static_data.strings import Strings

class Fun(Base_Cog):
  def __init__(self, bot):
    super(Fun, self).__init__(bot, __file__)

    self.pet_cache = cachetools.LRUCache(maxsize=20)

  @commands.slash_command(name="pet", description=Strings.common_pet_brief)
  @cooldowns.short_cooldown
  async def pet(self, inter: disnake.CommandInteraction, user: disnake.Member = commands.Param(default=None, description="User to pet")):
    if user is None:
      user = inter.author

    if user.id in self.pet_cache.keys():
      image_binary = self.pet_cache.get(user.id)
    else:
      if not user.avatar:
        url = user.display_avatar.with_format('png').url
      else:
        url = user.display_avatar.with_format('jpg').url
      response = requests.get(url, timeout=10)
      avatarFull = Image.open(io.BytesIO(response.content))

      if not user.avatar:
        avatarFull = avatarFull.convert("RGB")

      frames = []
      deformWidth = [-1, -2, 1, 2, 1]
      deformHeight = [4, 3, 1, 1, -4]
      width = 80
      height = 80

      for i in range(5):
        frame = Image.new('RGBA', (112, 112), (255, 255, 255, 1))
        hand = Image.open(f"static_data/pet/{i}.png")
        width = width - deformWidth[i]
        height = height - deformHeight[i]
        avatar = avatarFull.resize((width, height))
        avatarMask = Image.new('1', avatar.size, 0)
        draw = ImageDraw.Draw(avatarMask)
        draw.ellipse((0, 0) + avatar.size, fill=255)
        avatar.putalpha(avatarMask)

        frame.paste(avatar, (112 - width, 112 - height), avatar)
        frame.paste(hand, (0, 0), hand)
        frames.append(frame)

      image_binary = io.BytesIO()
      frames[0].save(image_binary, format='GIF', save_all=True,
                     append_images=frames[1:], duration=40,
                     loop=0, transparency=0, disposal=2, optimize=False)
      self.pet_cache[user.id] = image_binary

    image_binary.seek(0)
    await inter.response.send_message(file=disnake.File(fp=image_binary, filename="pet.gif"))

  @pet.error
  async def pet_error(self, inter: disnake.CommandInteraction, error):
    if isinstance(error, commands.MemberNotFound):
      await inter.response.send_message(Strings.common_pet_user_not_found)
      return True

def setup(bot):
  bot.add_cog(Fun(bot))
