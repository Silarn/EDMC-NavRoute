# -*- coding: utf-8 -*-
#
# Copyright (C) 2021 Jeremy Rimpo
# Copyright (C) 2017 Jonathan Harris
# 
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
# -----------------------------------------------------------
#
# Display the current navigation route
#
import tkinter as tk
from tkinter import ttk

import myNotebook as nb

import EDMCLogging
from config import config
from theme import theme
from typing import Any, MutableMapping, Mapping
from EDMCLogging import get_main_logger
from ttkHyperlinkLabel import HyperlinkLabel


class This:
    """Holds module globals."""

    def __init__(self):
        self.VERSION = "1.1.0"

        self.jump_num: tk.IntVar | None = None

        self.logger: EDMCLogging.LoggerMixin = get_main_logger()
        self.current_system: str = "Unknown"
        self.route: dict | None = None
        self.frame: tk.Frame | None = None
        self.title_label: tk.Label | None = None
        self.remain_label: tk.Label | None = None
        self.navroute_label: tk.Label | None = None
        self.search_route: bool = False
        self.remaining_jumps: int = 0


this = This()


def plugin_start3(plugin_dir: str) -> str:
    return "NavRoute"


def plugin_app(parent: tk.Frame) -> tk.Frame:
    parse_config()
    this.frame = tk.Frame(parent)
    this.frame.columnconfigure(0, weight=1)
    this.remain_label = tk.Label(this.frame, text="NavRoute: Plot a Route to Begin")
    this.remain_label.grid(row=0)
    this.navroute_label = tk.Label(this.frame, text="No NavRoute Set")
    this.navroute_label.grid(row=1)
    theme.update(this.frame)
    return this.frame


def plugin_prefs(parent: nb.Frame, cmdr: str, is_beta: bool) -> nb.Frame:
    x_padding = 10
    y_padding = 2
    frame = nb.Frame(parent)
    frame.columnconfigure(1, weight=1)

    HyperlinkLabel(frame, text='Pioneer', background=nb.Label().cget('background'),
                   url='https://github.com/Silarn/EDMC-Pioneer', underline=True) \
        .grid(row=1, padx=x_padding, sticky=tk.W)
    nb.Label(frame, text = 'Version %s' % this.VERSION).grid(row=1, column=1, padx=x_padding, sticky=tk.E)

    ttk.Separator(frame).grid(row=5, columnspan=2, pady=y_padding*2, sticky=tk.EW)

    nb.Label(
        frame,
        text="Number of Interim Jumps:",
    ).grid(row=10, padx=x_padding, sticky=tk.W)
    vcmd = (frame.register(validate_int))
    nb.Entry(
        frame,
        textvariable=this.jump_num,
        validate='all',
        validatecommand=(vcmd, '%P')
    ).grid(row=11, padx=x_padding, pady=y_padding, column=0, sticky=tk.W)

    return frame


def prefs_changed(cmdr: str, is_beta: bool) -> None:
    config.set('navroute_jumps', this.jump_num.get())
    process_jumps()


def parse_config() -> None:
    this.jump_num = tk.IntVar(value=config.get_int(key='navrout_jumps', default=1))


def validate_int(val: str) -> bool:
    if val.isdigit() or val == "":
        return True
    return False


def journal_entry(cmdr: str, is_beta: bool, system: str,
                  station: str, entry: MutableMapping[str, Any], state: Mapping[str, Any]) -> str:
    this.current_system = state['SystemName']

    match entry['event']:
        case 'FSDTarget':
            found = False
            if this.route is not None:
                for nav in this.route:
                    if nav['StarSystem'] == entry['Name']:
                        found = True
                        break
            if found:
                this.remaining_jumps = entry['RemainingJumpsInRoute']
        case 'NavRoute':
            if state['NavRoute'] is not None:
                this.route = state['NavRoute']['Route']
            else:
                this.route = entry['Route']
            this.remaining_jumps = len(this.route) - 1
            this.search_route = True
            process_jumps()
        case 'FSDJump':
            if this.route is not None:
                if entry['StarSystem'] == this.route[-1]['StarSystem']:
                    this.remain_label['text'] = "NavRoute: Route Complete!"
                    this.navroute_label['text'] = "No NavRoute Destination Set"
                    this.remaining_jumps = 0
                    this.route = None
                    this.search_route = False
                else:
                    found = False
                    for nav in this.route:
                        if nav['StarSystem'] == entry['StarSystem']:
                            found = True
                            break
                    if found:
                        process_jumps()
                    else:
                        this.remain_label['text'] = "NavRoute: Diverted From Route!"
                        index = len(this.route) - this.remaining_jumps
                        next_system = this.route[index]
                        divert_text = 'Jump to {} to Resume'.format(next_system['StarSystem'])
                        this.navroute_label['text'] = divert_text
            else:
                this.remain_label['text'] = "NavRoute: No NavRoute Set"
                this.navroute_label['text'] = "Plot a Route to Begin"

    if state['NavRoute'] is not None and this.search_route:
        if this.route != state['NavRoute']['Route']:
            this.route = state['NavRoute']['Route']
            this.search_route = False
            process_jumps()

    return ""


def process_jumps() -> None:
    remaining_route = this.route[-this.remaining_jumps:]
    last_system = this.route[-1]
    display = f"{this.current_system}"

    for i, jump in enumerate(remaining_route):
        if i >= this.jump_num.get() or i == (len(remaining_route) - 1):
            display += f" -> {last_system['StarSystem']}"
            break
        else:
            display += f" -> {jump['StarSystem']}"
            if i == (this.jump_num.get() - 1):
                display += " | + {}".format(this.remaining_jumps-this.jump_num.get()-1)

    if len(display) > 60:
        display = "\n-> ".join(display.split(" -> "))

    this.remain_label['text'] = f'NavRoute: {this.remaining_jumps} Jump{"s"[:this.remaining_jumps^1]} Remaining:'
    this.navroute_label['text'] = display
