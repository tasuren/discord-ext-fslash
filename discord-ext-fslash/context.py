# discord-ext-fslash - Context

from __future__ import annotations

from typing import Optional

from discord.ext.commands._types import BotT
from discord.ext.commands.view import StringView

import discord


class DummyMessage:
    def __init__(
        self, state: discord.state.ConnectionState, content: Optional[str] = None
    ):
        self.content = content
        self._state = state


class Context:
    def __init__(
        self, message: DummyMessage, bot: BotT,
        view: View, prefix: Optional[str] = None
    ):
        self.message, self.bot = DummyMessage, bot
        self.view, self.prefix = view, prefix

    @classmethod
    async def from_interaction(cls, bot: BotT, interaction: discord.Interaction):
        data = interaction.data["options"][0]
        content = f"{self.bot.command_prefix[0]}{data['name']}"
        while "options" in data:
            if not data["options"]:
                break
            if "value" in data["options"][0]:
                # 引数
                length = len(data["options"])
                for count, option in enumerate(data["options"], 1):
                    if isinstance(option["value"], dict):
                        # もしユーザーが入れた引数の値が辞書の場合はIDを取る。
                        # これはこの場合は`discord.Member`等のDiscordオブジェクトのデータのためです。
                        option["value"] = str(option["value"]["id"])
                    if not isinstance(option["value"], str):
                        # もし文字列ではない状態なら文字列にする。
                        option["value"] = str(option["value"])
                    if count != length and (
                        " " in option["value"] or "\n" in option["value"]
                    ):
                        # 最後の引数ではないかつ空白または改行が含まれている場合は`"`で囲む。
                        option["value"] = f'"{option["value"]}"'

                    content += f" {option['value']}"
                break
            else:
                # サブコマンド
                data = data["options"][0]
                content += f" {data['name']}"
        return await bot.get_context(DummyMessage(interaction._state, content), cls=cls)