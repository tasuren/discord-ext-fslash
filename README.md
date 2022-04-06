[![PyPI](https://img.shields.io/pypi/v/discord-ext-fslash)](https://pypi.org/project/discord-ext-fslash/) ![PyPI - Python Version](https://img.shields.io/pypi/pyversions/discord-ext-fslash) ![PyPI - Downloads](https://img.shields.io/pypi/dm/discord-ext-fslash) ![PyPI - License](https://img.shields.io/pypi/l/discord-ext-fslash) [![Documentation Status](https://tasuren.github.io/discord-ext-fslash)](https://img.shields.io/github/workflow/status/tasuren/discord-ext-fslash/github-pages/gh-pages?label=docs) [![Discord](https://img.shields.io/discord/777430548951728149?label=chat&logo=discord)](https://discord.gg/kfMwZUyGFG) [![Buy Me a Coffee](https://img.shields.io/badge/-tasuren-E9EEF3?label=Buy%20Me%20a%20Coffee&logo=buymeacoffee)](https://www.buymeacoffee.com/tasuren)
# discord-ext-fslash
This library registers commands from the discord.py command framework as slash commands in discord.py 2.0 as well by doing a monkey patch.  
**WARNING** Once again, the way this library works is a monkey patch and not without the possibility of unexpected behavior.

## Features
It will support both the cooldown and other decorators of the command framework and the `describe` decorator of the app command to work.
Also, the converter will automatically replace to the `Transformer` of slash version.
Even if you have too many commands and reach the maximum number of can be registered slash commands, we have a way to deal with it. (An example is below)

## Installation
`pip install discord-ext-fslash`

## Example
### Normal
The following is an example of creating a command called `ping` that works with both slash and message commands.
```python
from discord.ext.fslash import extend_force_slash

# ...

bot = extend_force_slash(commands.Bot(command_prefix="fs!", intents=intents))

@bot.command()
async def ping(ctx):
    await ctx.reply("pong")
```
### Split Commands by Categories
Even if there are too many commands in the command framework to register in the slash, it provides a way to implement them all by making only the commands in the slash subcommands of the group command.  
The following example creates the group commands `server-tool` and `entertainment` and sets up the commands in the command framework as subcommands of those commands.
```python
from discord.ext.fslash import extend_force_slash

# ...

bot = extend_force_slash(
    commands.Bot(command_prefix="fs!", intents=intents),
    first_groups=(
        discord.app_commands.Group(name="server-tool"),
        discord.app_commands.Group(name="entertainment")
    )
)

@bot.command(description="Ban member", fsparent="server-tool")
@commands.has_guild_permissions(ban_members=True)
@commands.cooldown(1, 10, commands.BucketType.guild)
@discord.app_commands.describe(member="Member to be banned")
async def ban(ctx, *, member: discord.Member):
    # `/server-tool ban member: ...` or `fs!ban ...` to run this command.
    await ctx.trigger_typing()
    await member.ban()
    await ctx.reply("pong")

@bot.command(description="Make wow", fsparent="entertainment")
async def wow(ctx):
    # `/entertainment wow` or `fs!wow` to run this command.
    await ctx.reply("wow")
```

## Documentation
There are features to improve compatibility for greater convenience.  
See the [documentation](https://tasuren.github.io/discord-ext-fslash) for details.  

## Contributing
Issues and PullRequests should be brief in content.  
The code should be similar in style to the current code.  
Please limit all text to 100 characters per line if possible, except for comments.  
For comments, please limit to 200 characters per line if possible.

## License
MIT