import os
from pathlib import Path
from typing import List, Optional

import httpx
import click
from PyInquirer import prompt
from cookiecutter.main import cookiecutter

from ._pip import _call_pip_install, _call_pip_update
from nb_cli.utils import Plugin, list_style, print_package_results


def create_plugin(name: Optional[str] = None, plugin_dir: Optional[str] = None):
    if not name:
        question = [{
            "type": "input",
            "name": "plugin_name",
            "message": "Plugin Name:",
            "validate": lambda x: len(x) > 0
        }]
        answers = prompt(question, qmark="[?]", style=list_style)
        if "plugin_name" not in answers:
            click.secho(f"Error Input!", fg="red")
            return
        name = answers["plugin_name"]

    if not plugin_dir:
        detected = [
            *filter(lambda x: x.is_dir(),
                    Path(".").glob("**/plugins/")), "Other"
        ]
        question = [{
            "type": "list",
            "name": "plugin_dir",
            "message": "Where to store the plugin?",
            "choices": list(map(str, detected)),
        }]
        answers = prompt(question, qmark="[?]", style=list_style)
        if "plugin_dir" not in answers:
            click.secho(f"Error Input!", fg="red")
            return
        plugin_dir = answers["plugin_dir"]
        if plugin_dir == "Other":
            question = [{
                "type": "input",
                "name": "plugin_dir",
                "message": "Plugin Dir:",
                "validate": lambda x: len(x) > 0 and Path(x).is_dir()
            }]
            answers = prompt(question, qmark="[?]", style=list_style)
            if "plugin_dir" not in answers:
                click.secho(f"Error Input!", fg="red")
                return
            plugin_dir = answers["plugin_dir"]
    elif not Path(plugin_dir).is_dir():
        click.secho(f"Plugin Dir is not a directory!", fg="yellow")
        question = [{
            "type": "input",
            "name": "plugin_dir",
            "message": "Plugin Dir:",
            "validate": lambda x: len(x) > 0 and Path(x).is_dir()
        }]
        answers = prompt(question, qmark="[?]", style=list_style)
        if "plugin_dir" not in answers:
            click.secho(f"Error Input!", fg="red")
            return
        plugin_dir = answers["plugin_dir"]

    question = [{
        "type": "confirm",
        "name": "sub_plugin",
        "message": "Do you want to load sub plugins in current plugin?",
        "default": False
    }]
    answers = prompt(question, qmark="[?]", style=list_style)
    if not answers or "sub_plugin" not in answers:
        click.secho(f"Error Input! Missing 'sub_plugin'", fg="red")
        return
    cookiecutter(str((Path(__file__).parent.parent / "plugin").resolve()),
                 no_input=True,
                 output_dir=plugin_dir,
                 extra_context={
                     "plugin_name": name,
                     "sub_plugin": answers["sub_plugin"]
                 })


def search_plugin(package: Optional[str] = None):
    _package: str
    if package is None:
        question = [{
            "type": "input",
            "name": "package",
            "message": "Plugin name you want to search?"
        }]
        answers = prompt(question, qmark="[?]", style=list_style)
        if not answers or "package" not in answers:
            click.secho("Error Input! Missing 'package'", fg="red")
            return
        _package = answers["package"]
    else:
        _package = package
    plugins = _get_plugins()
    plugins = list(
        filter(lambda x: any(_package in value for value in x.dict().values()),
               plugins))
    print_package_results(plugins)


def install_plugin(package: Optional[str] = None,
                   file: str = "bot.py",
                   index: Optional[str] = None):
    _package: str
    if package is None:
        question = [{
            "type": "input",
            "name": "package",
            "message": "Plugin name you want to search?"
        }]
        answers = prompt(question, qmark="[?]", style=list_style)
        if not answers or "package" not in answers:
            click.secho("Error Input! Missing 'package'", fg="red")
            return
        _package = answers["package"]
    else:
        _package = package
    plugins = _get_plugins()
    plugin_exact = list(
        filter(lambda x: _package == x.id or _package == x.name, plugins))
    if not plugin_exact:
        plugin = list(
            filter(lambda x: _package in x.id or _package in x.name, plugins))
        if len(plugin) > 1:
            print_package_results(plugin)
            return
        elif len(plugin) != 1:
            click.secho("Package not found!", fg="red")
            return
        else:
            plugin = plugin[0]
    else:
        plugin = plugin_exact[0]
    status = _call_pip_install(plugin.link, index)
    if status == 0 and os.path.isfile(file):  # SUCCESS
        with open(file, "r") as f:
            lines = f.readlines()
        insert_index = len(lines) - list(
            map(
                lambda x: x.startswith("nonebot.load") or x.startswith(
                    "nonebot.init"), lines[::-1])).index(True)
        lines.insert(insert_index, f"nonebot.load_plugin(\"{plugin.id}\")\n")
        with open(file, "w") as f:
            f.writelines(lines)
    elif status == 0:
        click.secho(f"Cannot find {file} in current folder!", fg="red")


def update_plugin(package: Optional[str] = None, index: Optional[str] = None):
    _package: str
    if package is None:
        question = [{
            "type": "input",
            "name": "package",
            "message": "Plugin name you want to search?"
        }]
        answers = prompt(question, qmark="[?]", style=list_style)
        if not answers or "package" not in answers:
            click.secho("Error Input! Missing 'package'", fg="red")
            return
        _package = answers["package"]
    else:
        _package = package
    plugins = _get_plugins()
    plugin_exact = list(
        filter(lambda x: _package == x.id or _package == x.name, plugins))
    if not plugin_exact:
        plugin = list(
            filter(lambda x: _package in x.id or _package in x.name, plugins))
        if len(plugin) > 1:
            print_package_results(plugin)
            return
        elif len(plugin) != 1:
            click.secho("Package not found!", fg="red")
            return
        else:
            plugin = plugin[0]
    else:
        plugin = plugin_exact[0]
    return _call_pip_update(plugin.link, index)


def _get_plugins() -> List[Plugin]:
    res = httpx.get("https://v2.nonebot.dev/plugins.json")
    plugins = res.json()
    return list(map(lambda x: Plugin(**x), plugins))