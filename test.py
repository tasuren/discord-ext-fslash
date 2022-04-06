# test

from asyncio import run, sleep

from discord.ext import commands
from discord.ext.fslash import extend_force_slash, groups
import discord


GUILD_ID = 777430548951728149
GUILD = discord.Object(777430548951728149)


class MyBot(commands.Bot):
    async def setup_hook(self):
        await self.add_cog(TestCog(self))

    async def on_ready(self):
        print("sync")
        await self.tree.sync(guild=GUILD)
        print("I'm ready")


intents = discord.Intents.default()
intents.message_content = True
bot = extend_force_slash(MyBot(command_prefix="t!", intents=intents), first_groups=[
    discord.app_commands.Group(
        name="category", description="Test category", guild_ids=[GUILD_ID]
    )
])


class TestCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.describe(arg="test")
    @commands.command(guild=GUILD)
    async def cogtest(self, ctx, arg, *, arg2):
        await ctx.reply(f"Ok: {arg}, {arg2}")

    @commands.group(guild_ids=[GUILD_ID])
    async def coggroup_test(self, ctx):
        ...

    @coggroup_test.command()
    async def testcogsub(self, ctx, wow):
        await ctx.reply(f"Ok: {wow}")

    print(1)


@bot.command("sleep", guild=GUILD)
async def sleep_(ctx):
    await ctx.trigger_typing()
    await sleep(3)
    await ctx.reply("Ok")

@bot.command(guild=GUILD)
async def literal(ctx, a):
    ...
literal.__annotations__["a"] = "Literal[1,2]"

@bot.command(guild=GUILD, description="test")
async def normal(ctx):
    await ctx.reply("Ok")


@bot.command(fsparent="category")
async def category(ctx):
    await ctx.reply("Ok")


@bot.group(guild_ids=[GUILD_ID])
async def group(ctx):
    ...

@group.command(description="test")
@commands.cooldown(1, 10, commands.BucketType.user)
async def subcommand(ctx):
    await ctx.reply(f"{groups}")

class NewConverter(commands.Converter):
    async def convert(self, ctx, arg):
        print("Converter was called:", arg)
        return arg

@bot.command(guild=GUILD, description="This is the argument test.")
@discord.app_commands.describe(c="This is the test description for argument.")
@discord.app_commands.rename(a="test-rename")
@discord.app_commands.choices(a=[
    discord.app_commands.Choice(name="test", value=1),
    discord.app_commands.Choice(name="test", value=2)
])
async def test(ctx, a: discord.app_commands.Choice[int], b: int, c: bool, d: float, e: discord.Member, f: NewConverter):
    await ctx.reply(f'Ok: {"".join(map(str, (a, b, c, d, e, f)))}')


# Many nested commands
@group.group()
async def level1(ctx):
    ...

@level1.command()
async def level11(ctx):
    await ctx.reply("Ok")

@level1.group()
@commands.has_guild_permissions(administrator=True)
async def level2(ctx):
    ...

@level2.command()
async def level21(ctx):
    await ctx.reply("Ok")

@level2.command()
@commands.has_guild_permissions(administrator=True)
async def level22(ctx, test: int):
    await ctx.reply(f"Ok: {test}")

@level2.command()
async def level23(ctx, test: discord.Member):
    await ctx.reply(f"Ok: {test}")

@level2.group()
async def level3(ctx):
    ...

@level3.command()
async def level31(ctx):
    await ctx.reply("Ok")


@bot.listen()
async def on_command_error(ctx, error):
    print("Error:", ctx.args, ctx.kwargs, error)
    raise error

@bot.listen()
async def on_message(message):
    print(message.author, message.content)


with open("token.secret", "r") as f:
    TOKEN = f.read()
try: run(bot.start(TOKEN))
except KeyboardInterrupt: ...