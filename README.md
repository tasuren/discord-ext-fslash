# discord-ext-fslash
Force the discord.py command framework to correspond to the slashes.

## Example
The command framework can be diverted without modification.
```python
@bot.command()
async def ping(ctx):
    await ctx.reply("pong")
```