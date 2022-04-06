# discord-ext-fslash by tasuren

from __future__ import annotations

from typing import Callable, Union, Optional, Any

from collections import defaultdict
from string import octdigits
from re import sub
import inspect

from discord.ext import commands
from discord import app_commands
import discord

from ._types import AdjustmentNameMode, BotT
from .context import Context, is_fslash


__all__ = (
    "extend_force_slash", "is_fslash", "Context", "AdjustmentNameMode",
    "groups", "exceptions"
)


VALID_COMMAND_NAME_CHARACTERS_WITHOUT_LETTERS = f"{octdigits}-_"
def adjustment_command_name(name: str, mode: AdjustmentNameMode) -> str:
    "Prepares the passed string into a string that can be used as the name of a slash command."
    sandwiched = "_" if mode == AdjustmentNameMode.SNAKE_CASE else "-"
    return "".join(
        char
        for char in sub(
            "(.[A-Z])", lambda x: f"{x.group(1)[0]}{sandwiched}{x.group(1)[1]}", name.lower()
        ).lower()
        if char in VALID_COMMAND_NAME_CHARACTERS_WITHOUT_LETTERS
    )[:32]


_bot = None


# ConverterのアノテーションをTransformerに交換するようにする。
original_evaluate_annotation = discord.utils.evaluate_annotation
def _new_evaluate_annotation(*args, **kwargs):
    annotation = original_evaluate_annotation(*args, **kwargs)
    if commands.Converter in getattr(annotation, "__mro__", ()):
        converter = annotation()
        # Converterを実行するTransformerです。
        class ConverterTransformer(app_commands.Transformer):
            @classmethod
            async def transform(cls, interaction: discord.Interaction, value: str):
                return await converter.convert(Context(interaction, {}, bot=_bot), value) # type: ignore
        annotation = app_commands.Transform[None, ConverterTransformer]
    return annotation
discord.utils.evaluate_annotation = _new_evaluate_annotation


original_atp = app_commands.transformers.annotation_to_parameter
original_signature = inspect.signature
def _replace_atp(toggle: bool, failed_annotations: Optional[dict] = None, riats: bool = False):
    # `annotation_to_parameter`の実行が失敗した際に`str`として扱うようにする関数です。
    # それと、inspectの`signature`もアノテーションがない場合は拡張します。
    if toggle:
        def new_atp(annotation, parameter):
            if riats:
                try:
                    return original_atp(annotation, parameter)
                except Exception as e:
                    # 失敗したなら`str`のアノテーションにする。
                    if failed_annotations is not None:
                        failed_annotations[annotation] = e
                    return original_atp(str, parameter)
            else:
                return original_atp(annotation, parameter)
        app_commands.transformers.annotation_to_parameter = new_atp

        def new_signature(*args, **kwargs):
            signature = original_signature(*args, **kwargs)
            ok = False
            new = []
            for name, parameter in list(signature.parameters.items()):
                if name == "ctx":
                    ok = True
                new.append(parameter)
                if ok and parameter.annotation == parameter.empty:
                    # アノテーションがない場合は`str`を設定して置く。
                    new[-1] = parameter.replace(annotation=str)
            return signature.replace(parameters=new) if ok else signature
        inspect.signature = new_signature
    else:
        app_commands.transformers.annotation_to_parameter = original_atp
        inspect.signature = original_signature


def _get(command, key, default):
    # コマンドオブジェクトの`__original_kwargs__`か`extras`から特定の値を取り出します。
    return command.__original_kwargs__.get(key, default) \
        or command.extras.get(key, default)


# `parse_arguments`で何も実行しないようにする。
_original_parse_arguments = commands.Command._parse_arguments
async def _new_parse_arguments(self, ctx):
    if is_fslash(ctx) and not getattr(ctx, "__fslash_do_original_pa__", False):
        print(1)
        ctx.args = (ctx.command.cog, ctx) if ctx.command.cog else (ctx,)
    else:
        return await _original_parse_arguments(self, ctx)
setattr(commands.Command, "_parse_arguments", _new_parse_arguments)


async def _run_command(bot, interaction, command, content, **kwargs) -> None:
    # Run command
    ctx = Context(interaction, kwargs, command, bot)
    if content is not None:
        ctx.view = type(ctx.view)(content)
        setattr(ctx, "__fslash_do_original_pa__", True)
    try:
        await command.invoke(ctx) # type: ignore
    except Exception as e:
        bot.dispatch("command_error", ctx, e)


groups = []
exceptions = defaultdict[str, dict[Any, Exception]](dict)
__patched = False
def extend_force_slash(
    bot: BotT, *,
    check: Optional[Callable[[Union[commands.Command, commands.Group]], bool]] = None,
    adjustment_name: Optional[AdjustmentNameMode] = None,
    replace_invalid_annotation_to_str: bool = False,
    default_description: str = "...", first_groups: Optional[list[app_commands.Group]] = None
) -> BotT:
    """This class forces commands in the command framework bot to be registered even if they are slash commands.
    """
    global _bot, groups, exceptions
    _bot = bot
    if first_groups is not None: groups = first_groups

    global __patched
    assert not __patched, "This can only be called once."
    __patched = True

    # コマンドが作られた際にそのコマンドを呼び出すコマンドをtreeに登録する。
    def make_command_new_init(original):
        def command_new_init(command: commands.Command, func, /, **kwargs):
            original(command, func, **kwargs)

            # もしNestしすぎたグループコマンドのコマンドの場合はパスする。この`__fslash_*_*__`は下で作られます。
            if command.parent is not None and getattr(
                command.parent, "__fslash_max_parent__", False
            ):
                print(-10, command.name)
                setattr(command, "__fslash_max_parent__", True)
                return

            # コマンドを実装するかのチェックをする。
            if check is not None and not check(command): return

            _replace_atp(
                True, exceptions["replace_invalid_annotation_to_str"],
                replace_invalid_annotation_to_str
            )

            # もし親のグループが指定されているのならそれを探し出す。
            parent = None
            fsparent = _get(command, "fsparent", None)
            for group in groups:
                if fsparent == group.name:
                    parent = group
                    break
            else:
                assert fsparent is None, f"A group command that has not yet been registered as a parent command in `{command}` has been specified."
            # もしコマンドフレームワークのグループコマンドのサブコマンドの場合は、親コマンドのスラッシュのグループコマンドを、スラッシュでも親コマンドとする。
            if parent is None and command.parent is not None:
                parent = getattr(command.parent, "__fslash__")
            # スラッシュコマンドを作る。
            name = command.name if adjustment_name is None \
                else adjustment_command_name(command.name, adjustment_name)
            if isinstance(command, commands.Group):
                try:
                    groups.append(app_commands.Group(
                        name=name,
                        description=command.description or default_description,
                        parent=parent, guild_ids=_get(command, "guild_ids", None)
                    ))
                except ValueError:
                    # もしNestしすぎたグループコマンドがある場合は、コマンドの文を受け取るコマンドを代わりに作る。
                    assert isinstance(parent, app_commands.Group)
                    @parent.command(
                        name=name, description=command.description or default_description
                    )
                    async def alternative_for_nested(
                        interaction: discord.Interaction, content: str
                    ):
                        await _run_command(bot, interaction, command, content)
                    setattr(command, "__fslash_max_parent__", True)
                setattr(command, "__fslash__", groups[-1])
                print(0, command, parent)
            else:
                # `describe`等で付けられたデータを`callback`にも適用させる。
                for name, value in filter(
                    lambda x: x[0].startswith("__discord_app_commands"),
                    command.__dict__.items()
                ):
                    setattr(command.callback, name, value)
                # スラッシュコマンドを作る。
                app_command: app_commands.Command = (bot.tree.command if parent is None else parent.command)(
                    name=name, description=command.description or default_description,
                    **(dict(
                        guild=_get(command, "guild", discord.utils.MISSING), guilds=_get(
                            command, "guilds", discord.utils.MISSING
                        )
                    ) if parent is None else {})
                )(command.callback) # type: ignore
                setattr(command, "__fslash__", app_command)

                # 実行される関数を用意する。
                async def inner_function(interaction: discord.Interaction, **kwargs): # type: ignore
                    await _run_command(bot, interaction, command, None, **kwargs)
                setattr(app_command, "_callback", inner_function)

                print(1, command, parent)

            _replace_atp(False, None, replace_invalid_annotation_to_str)
        return command_new_init
    setattr(commands.Command, "__init__", make_command_new_init(commands.Command.__init__))

    # コマンドが削除された時はスラッシュコマンドも削除する。
    def command_new_del(command: commands.Command):
        slash: Optional[app_commands.Command] = getattr(command, "__fslash__", None);
        if slash is not None:
            if slash.parent is None:
                bot.tree.remove_command(slash) # type: ignore
                print(-1, slash)
            else:
                slash.parent.remove_command(slash) # type: ignore
                print(-2, slash.parent)
    setattr(commands.Command, "__del__", command_new_del)

    # `sync`が実行された際に`groups`にあるものを追加するようにする。
    original_sync = app_commands.CommandTree.sync
    async def new_sync(self, *, guild=None):
        for group in groups:
            if not getattr(group, "__synced__", False) \
                    and group.parent is None:
                bot.tree.add_command(group)
                print(group._children)
                setattr(group, "__synced__", True)
        print(groups)
        return await original_sync(self, guild=guild)
    app_commands.CommandTree.sync = new_sync

    return bot