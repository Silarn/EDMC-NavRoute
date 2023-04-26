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
from theme import theme
from typing import List, Optional, Dict, Any
from EDMCLogging import get_main_logger

logger = get_main_logger()

current_system: str = "Unknown"
route: Optional[Dict] = None
frame: Optional[tk.Frame] = None
title_label: Optional[tk.Label] = None
remain_label: Optional[tk.Label] = None
navroute_label: Optional[tk.Label] = None
search_route: bool = False
remaining_jumps: int = 0


def plugin_start3(plugin_dir):
    return "NavRoute"


def plugin_app(parent: tk.Frame) -> tk.Frame:
    global frame, title_label, remain_label, navroute_label
    frame = tk.Frame(parent)
    frame.columnconfigure(0, weight=1)
    remain_label = tk.Label(frame, text="NavRoute: Plot a Route to Begin")
    remain_label.grid(row=0)
    navroute_label = tk.Label(frame, text="No NavRoute Set")
    navroute_label.grid(row=1)
    theme.update(frame)
    return frame


def journal_entry(cmdr: Optional[str], is_beta: bool, system: Optional[str],
                  station: Optional[str], entry: Dict[str, Any], state: Dict[str, Any]):
    global route, remaining_jumps, current_system, search_route
    current_system = system
    if entry['event'] == 'FSDTarget':
        found = False
        if route is not None:
            for nav in route:
                if nav['StarSystem'] == entry['Name']:
                    found = True
                    break
        if found:
            remaining_jumps = entry['RemainingJumpsInRoute']
    if entry['event'] == 'NavRoute':
        if state['NavRoute'] is not None:
            route = state['NavRoute']['Route']
        else:
            route = entry['Route']
        remaining_jumps = len(route) - 1
        search_route = True
        process_jumps()
    if entry['event'] == 'FSDJump':
        if route is not None:
            if entry['StarSystem'] == route[-1]['StarSystem']:
                remain_label['text'] = "NavRoute: Route Complete!"
                navroute_label['text'] = "No NavRoute Destination Set"
                remaining_jumps = 0
                route = None
                search_route = False
            else:
                found = False
                for nav in route:
                    if nav['StarSystem'] == entry['StarSystem']:
                        found = True
                        break
                if found:
                    process_jumps()
                else:
                    remain_label['text'] = "NavRoute: Diverted From Route!"
                    index = len(route) - remaining_jumps
                    next_system = route[index]
                    divert_text = 'Jump to {} to Resume'.format(next_system['StarSystem'])
                    navroute_label['text'] = divert_text
        else:
            remain_label['text'] = "NavRoute: No NavRoute Set"
            navroute_label['text'] = "Plot a Route to Begin"

    if state['NavRoute'] is not None and search_route:
        if route != state['NavRoute']['Route']:
            route = state['NavRoute']['Route']
            search_route = False
            process_jumps()


def process_jumps():
    next_system = route[0 - remaining_jumps]
    last_system = route[-1]
    if remaining_jumps > 1:
        next_label = '{}{}'.format(
            next_system['StarSystem'],
            (' | +' + (remaining_jumps - 2).__str__()) if remaining_jumps > 2 else ""
        )
        remaining_string = 'NavRoute: {} Jumps Remaining:'.format(remaining_jumps)
        navroute_string = '{} -> {} -> {}'.format(current_system, next_label, last_system['StarSystem'])
        if len(navroute_string) > 60:
            navroute_string = '{}\n-> {}\n-> {}'.format(current_system, next_label, last_system['StarSystem'])
        remain_label['text'] = remaining_string
        navroute_label['text'] = navroute_string
    else:
        remain_label['text'] = "NavRoute: 1 Jump Remaining"
        navroute_label['text'] = "{} -> {}".format(current_system, last_system['StarSystem'])