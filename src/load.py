# -*- coding: utf-8 -*-
# NavRoute plugin for EDMC
# Source: https://github.com/Silarn/EDMC-NavRoute
#
# Copyright (C) 2023 Jeremy Rimpo
# Licensed under the [GNU Public License (GPL)](http://www.gnu.org/licenses/gpl-2.0.html) version 2 or later.

import json
import math
from os.path import join, expanduser
import requests
import semantic_version
import tkinter as tk
from tkinter import ttk, colorchooser as tkColorChooser

import myNotebook as nb

from navroute import const, overlay
from navroute.format_util import Formatter
from navroute.status_flags import StatusFlags2, StatusFlags

import EDMCLogging
from config import config
from theme import theme
from typing import Any, MutableMapping, Mapping
from EDMCLogging import get_plugin_logger
from ttkHyperlinkLabel import HyperlinkLabel


class This:
    """Holds module globals."""

    def __init__(self):
        self.VERSION = semantic_version.Version(const.version)
        self.NAME = const.name
        self.formatter = Formatter()

        self.jump_num: tk.IntVar | None = None

        self.logger: EDMCLogging.LoggerMixin = get_plugin_logger(self.NAME)
        self.current_system: str = "Unknown"
        self.current_system_class: str | None = None
        self.next_system_class: str | None = None
        self.route: list[dict[str, Any]] = []
        self.total_distance: float = 0
        self.straight_distance: float = 0

        self.parent: tk.Frame | None = None
        self.frame: tk.Frame | None = None
        self.title_label: tk.Label | None = None
        self.remain_label: tk.Label | None = None
        self.navroute_label: tk.Label | None = None
        self.update_button: HyperlinkLabel | None = None
        self.search_route: bool = False
        self.remaining_jumps: int = 0
        self.overcharge_boost: bool = False
        self.status: StatusFlags = StatusFlags(0)
        self.status2: StatusFlags2 = StatusFlags2(0)

        self.show_distance: tk.BooleanVar | None = None
        self.show_starclass: tk.BooleanVar | None = None
        self.show_indicators: tk.BooleanVar | None = None

        self.overlay = overlay.Overlay()
        self.use_overlay: tk.BooleanVar | None = None
        self.overlay_color: tk.StringVar | None = None
        self.overlay_size: tk.StringVar | None = None
        self.overlay_anchor_x: tk.IntVar | None = None
        self.overlay_anchor_y: tk.IntVar | None = None


this = This()


def plugin_start3(plugin_dir: str) -> str:
    return const.name


def plugin_app(parent: tk.Frame) -> tk.Frame:
    parse_config()
    this.parent = parent
    this.frame = tk.Frame(parent)
    this.frame.columnconfigure(0, weight=1)
    this.remain_label = tk.Label(this.frame, text="NavRoute: Plot a Route to Begin")
    this.remain_label.grid(row=0)
    this.navroute_label = tk.Label(this.frame, text="No NavRoute Set")
    this.navroute_label.grid(row=1)
    update = version_check()
    if update != '':
        text = f'Version {update} is now available'
        url = f'https://github.com/Silarn/EDMC-NavRoute/releases/tag/v{update}'
        this.update_button = HyperlinkLabel(this.frame, text=text, url=url)
        this.update_button.grid(row=2, sticky=tk.N)
    theme.update(this.frame)
    return this.frame


def plugin_prefs(parent: ttk.Notebook, cmdr: str, is_beta: bool) -> nb.Frame:
    color_button = None

    def color_chooser() -> None:
        (_, color) = tkColorChooser.askcolor(
            this.overlay_color.get(), title='Overlay Color', parent=this.parent
        )

        if color:
            this.overlay_color.set(color)
            if color_button is not None:
                color_button['foreground'] = color

    x_padding = 10
    x_button_padding = 12
    y_padding = 2
    frame = nb.Frame(parent)
    frame.columnconfigure(1, weight=1)

    HyperlinkLabel(frame, text=const.name, background=nb.Label().cget('background'),
                   url='https://github.com/Silarn/EDMC-NavRoute', underline=True) \
        .grid(row=1, padx=x_padding, sticky=tk.W)
    nb.Label(frame, text='Version %s' % const.version).grid(row=1, column=1, padx=x_padding, sticky=tk.E)

    ttk.Separator(frame).grid(row=5, columnspan=2, pady=y_padding * 2, sticky=tk.EW)

    nb.Label(
        frame,
        text="Number of Interim Jumps:",
    ).grid(row=10, padx=x_padding, sticky=tk.W)
    vcmd = (frame.register(validate_int))
    nb.EntryMenu(
        frame,
        textvariable=this.jump_num,
        validate='all',
        validatecommand=(vcmd, '%P')
    ).grid(row=11, padx=x_padding, pady=y_padding, column=0, sticky=tk.W)
    nb.Checkbutton(
        frame,
        text='Show jump distance',
        variable=this.show_distance,
        command=lambda: indicator_check.config(state=tk.DISABLED if not this.show_starclass.get() else tk.NORMAL)
    ).grid(row=11, padx=x_padding, pady=y_padding, column=1, sticky=tk.W)
    indicator_check = nb.Checkbutton(
        frame,
        text='Show fuel / boost indicators (requires star class)',
        variable=this.show_indicators,
        state=tk.DISABLED if not this.show_starclass.get() else tk.NORMAL,
    )
    indicator_check.grid(row=12, padx=x_padding, pady=y_padding, column=1, sticky=tk.W)
    nb.Checkbutton(
        frame,
        text='Show star class',
        variable=this.show_starclass,
        command=lambda: indicator_check.config(state=tk.DISABLED if not this.show_starclass.get() else tk.NORMAL)
    ).grid(row=12, padx=x_padding, pady=y_padding, column=0, sticky=tk.W)

    # Overlay settings
    ttk.Separator(frame).grid(row=15, columnspan=3, pady=y_padding * 2, sticky=tk.EW)

    nb.Label(frame,
             text='EDMC Overlay Integration',
             justify=tk.LEFT) \
        .grid(row=20, column=0, padx=x_padding, sticky=tk.NW)
    nb.Checkbutton(
        frame,
        text='Enable overlay',
        variable=this.use_overlay
    ).grid(row=21, column=0, padx=x_button_padding, pady=0, sticky=tk.W)
    color_button = tk.Button(
        frame,
        text='Text Color',
        foreground=this.overlay_color.get(),
        background='grey4',
        command=lambda: color_chooser()
    )
    color_button.grid(row=22, column=0, padx=x_button_padding, pady=y_padding, sticky=tk.W)

    anchor_frame = nb.Frame(frame)
    anchor_frame.grid(row=21, column=1, sticky=tk.NSEW)
    anchor_frame.columnconfigure(4, weight=1)

    nb.Label(anchor_frame, text='Display Anchor:') \
        .grid(row=0, column=0, sticky=tk.W)
    nb.Label(anchor_frame, text='X') \
        .grid(row=0, column=1, sticky=tk.W)
    nb.EntryMenu(
        anchor_frame, text=this.overlay_anchor_x.get(), textvariable=this.overlay_anchor_x,
        width=8, validate='all', validatecommand=(vcmd, '%P')
    ).grid(row=0, column=2, sticky=tk.W)
    nb.Label(anchor_frame, text='Y') \
        .grid(row=0, column=3, sticky=tk.W)
    nb.EntryMenu(
        anchor_frame, text=this.overlay_anchor_y.get(), textvariable=this.overlay_anchor_y,
        width=8, validate='all', validatecommand=(vcmd, '%P')
    ).grid(row=0, column=4, sticky=tk.W)

    nb.Label(
        frame,
        text='Text Size:',
    ).grid(row=23, padx=x_padding, sticky=tk.W)
    size_options = [
        'Normal',
        'Large'
    ]
    nb.OptionMenu(
        frame,
        this.overlay_size,
        this.overlay_size.get(),
        *size_options
    ).grid(row=24, padx=x_padding, pady=y_padding, column=0, sticky=tk.W)

    return frame


def prefs_changed(cmdr: str, is_beta: bool) -> None:
    config.set('navroute_jumps', this.jump_num.get())
    config.set('navroute_distance', this.show_distance.get())
    config.set('navroute_starclass', this.show_starclass.get())
    config.set('navroute_indicators', this.show_indicators.get())
    config.set('navroute_overlay', this.use_overlay.get())
    config.set('navroute_overlay_color', this.overlay_color.get())
    config.set('navroute_overlay_size', this.overlay_size.get())
    config.set('navroute_overlay_anchor_x', this.overlay_anchor_x.get())
    config.set('navroute_overlay_anchor_y', this.overlay_anchor_y.get())
    this.formatter.set_locale(config.get_str('language'))
    process_jumps()


def parse_config() -> None:
    this.jump_num = tk.IntVar(value=config.get_int(key='navroute_jumps', default=1))
    this.show_distance = tk.BooleanVar(value=config.get_bool(key='navroute_distance', default=True))
    this.show_starclass = tk.BooleanVar(value=config.get_bool(key='navroute_starclass', default=True))
    this.show_indicators = tk.BooleanVar(value=config.get_bool(key='navroute_indicators', default=True))
    this.use_overlay = tk.BooleanVar(value=config.get_bool(key='navroute_overlay', default=False))
    this.overlay_color = tk.StringVar(value=config.get_str(key='navroute_overlay_color', default='#ffffff'))
    this.overlay_size = tk.StringVar(value=config.get_str(key='navroute_overlay_size', default='Normal'))
    this.overlay_anchor_x = tk.IntVar(value=config.get_int(key='navroute_overlay_anchor_x', default=0))
    this.overlay_anchor_y = tk.IntVar(value=config.get_int(key='navroute_overlay_anchor_y', default=1040))
    this.formatter.set_locale(config.get_str('language'))


def version_check() -> str:
    """
    Parse latest GitHub release version

    :return: The latest version string if it's newer than ours
    """

    try:
        req = requests.get(url='https://api.github.com/repos/Silarn/EDMC-NavRoute/releases/latest')
        data = req.json()
        if req.status_code != requests.codes.ok:
            raise requests.RequestException
    except (requests.RequestException, requests.JSONDecodeError) as ex:
        this.logger.error('Failed to parse GitHub release info', exc_info=ex)
        return ''

    version = semantic_version.Version(data['tag_name'][1:])
    if version > this.VERSION:
        return str(version)
    return ''


def validate_int(val: str) -> bool:
    if val.isdigit() or val == "":
        return True
    return False


def parse_navroute():
    journal_dir = config.get_str('journaldir', default=config.default_journal_dir)
    logdir = expanduser(journal_dir)
    try:
        with open(join(logdir, 'NavRoute.json')) as f:
            raw = f.read()

        try:
            data = json.loads(raw)
            if data is not None:
                this.route = data['Route']
                this.remaining_jumps = len(this.route) - 1
                this.search_route = True
                parse_total_distance()

        except json.JSONDecodeError as e:
            this.logger.exception('Failed to decode NavRoute.json', exc_info=e)
    except OSError as e:
        this.logger.exception(f'Could not open navroute file.', exc_info=e)


def can_display_overlay(status: StatusFlags | None = None) -> bool:
    if status is None:
        status = this.status
    if ((StatusFlags.IN_SHIP in status) and not (StatusFlags.DOCKED in status)
            and not (StatusFlags.LANDED in status)):
        return True
    return False


def journal_entry(cmdr: str, is_beta: bool, system: str,
                  station: str, entry: MutableMapping[str, Any], state: Mapping[str, Any]) -> str:
    if this.current_system is None:
        parse_navroute()
    if system != this.current_system:
        this.current_system = system if system is not None else ''
        this.current_system_class = None
    if state['NavRoute'] is not None and state['NavRoute']['Route'] != this.route:
        this.route = state['NavRoute']['Route']
        this.remaining_jumps = 0
        this.search_route = True
        parse_total_distance()

    this.overcharge_boost = False
    if 'FrameShiftDrive' in state['Modules']:
        if state['Modules']['FrameShiftDrive']['Item'] == 'int_hyperdrive_overcharge_size8_class5_overchargebooster_mkii':
            this.overcharge_boost = True

    if entry['event'] == 'FSDTarget':
        found = False
        if this.route:
            for nav in this.route:
                if nav['StarSystem'] == entry['Name']:
                    found = True
                    break
        if found:
            this.remaining_jumps = entry['RemainingJumpsInRoute']
        else:
            parse_navroute()

    if this.route and this.search_route:
        for i, nav in enumerate(this.route):
            if nav['StarSystem'] == this.current_system:
                this.current_system_class = nav['StarClass']
                this.remaining_jumps = len(this.route) - (i + 1)
                break

    match entry['event']:
        case 'NavRoute':
            if state['NavRoute'] is not None:
                this.route = state['NavRoute']['Route']
            else:
                this.route = entry['Route']
            this.remaining_jumps = len(this.route) - 1 if this.route else 0
            this.search_route = True
            parse_total_distance()
            process_jumps()
        case 'NavRouteClear':
            if StatusFlags.FSD_JUMP_IN_PROGRESS not in this.status:
                this.remaining_jumps = 0
                this.route.clear()
                this.search_route = False
                this.remain_label['text'] = "NavRoute: NavRoute Cleared"
                this.navroute_label['text'] = "Plot a Route to Begin"
                this.total_distance = 0
                if this.overlay.available() and can_display_overlay():
                    this.overlay.draw('navroute_display', 'NavRoute Cleared', this.overlay_anchor_x.get(),
                                      this.overlay_anchor_y.get(), this.overlay_color.get(),
                                      this.overlay_size.get().lower(), 10)
        case 'StartJump':
            this.next_system_class = entry['StarClass']
        case 'FSDJump':
            if this.next_system_class:
                this.current_system_class = this.next_system_class
                this.next_system_class = None
            if len(this.route):
                if entry['StarSystem'] == this.route[-1]['StarSystem']:
                    this.remain_label['text'] = 'NavRoute: Route Complete!'
                    this.navroute_label['text'] = 'No NavRoute Destination Set'
                    this.remaining_jumps = 0
                    this.route.clear()
                    this.search_route = False
                    this.total_distance = 0
                    if this.overlay.available() and can_display_overlay():
                        this.overlay.draw('navroute_display', 'NavRoute Complete!',
                                          this.overlay_anchor_x.get(), this.overlay_anchor_y.get(),
                                          this.overlay_color.get(), this.overlay_size.get().lower(), 10)
                else:
                    found = False
                    for nav in this.route:
                        if nav['StarSystem'] == entry['StarSystem']:
                            found = True
                            break
                    if found:
                        process_jumps()
                    else:
                        this.remain_label['text'] = 'NavRoute: Diverted From Route!'
                        nearest_system = ('', -1)
                        for nav in this.route:
                            distance = get_distance(entry['StarPos'], nav['StarPos'])
                            if nearest_system[1] == -1 or distance < nearest_system[1]:
                                nearest_system = (nav['StarSystem'], distance)
                        divert_text = f'Recalculate or Jump\n{nearest_system[0]} to Resume\n({this.formatter.format_distance(nearest_system[1], 'ly', False)})'
                        this.navroute_label['text'] = divert_text
                        if this.overlay.available() and can_display_overlay():
                            this.overlay.display('navroute_display', divert_text.replace('\n', ' '), this.overlay_anchor_x.get(),
                                                 this.overlay_anchor_y.get(), this.overlay_color.get())
            else:
                this.remain_label['text'] = 'NavRoute: No NavRoute Set'
                this.navroute_label['text'] = 'Plot a Route to Begin'
                if this.overlay.available() and can_display_overlay():
                    this.overlay.clear('navroute_display')

    if this.search_route:
        this.search_route = False
        process_jumps()

    return ''


def get_distance(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2)


def parse_total_distance() -> None:
    this.straight_distance = get_distance(this.route[0]['StarPos'], this.route[-1]['StarPos'])
    total_distance = 0
    last_pos = this.route[0]['StarPos']
    for i, nav in enumerate(this.route[1:]):
        total_distance += get_distance(nav['StarPos'], last_pos)
        last_pos = nav['StarPos']
    this.total_distance = total_distance


def dashboard_entry(cmdr: str, is_beta: bool, entry: dict[str, any]) -> str:
    """
    EDMC dashboard entry hook. Parses updates to the Status.json.
    Used to determine planetary location data. Used by waypoints, organic scans, and display focus.

    :param cmdr: Commander name (unused)
    :param is_beta: Beta status (unused)
    :param entry: Dictionary of status file data
    :return: Result string. Empty means success.
    """

    old_status = this.status
    this.status = StatusFlags(entry['Flags'])
    this.status2 = StatusFlags2(0)
    if 'Flags2' in entry:
        this.status2 = StatusFlags2(entry['Flags2'])

    if can_display_overlay(old_status) != can_display_overlay():
        process_jumps()

    return ''


def star_display(star_class: str | None, indicators: bool = True) -> str:
    if star_class is None:
        return ''

    if indicators:
        match star_class:
            case 'M' | 'K' | 'G' | 'F' | 'A' | 'B' | 'O':
                return f'\N{FUEL PUMP}{star_class}'
            case 'N':
                return '\N{HIGH VOLTAGE SIGN}{}N'.format('×6 ' if this.overcharge_boost else '×4 ')

        if star_class.startswith('D'):
            return '\N{HIGH VOLTAGE SIGN}{}{}'.format('×3 ' if this.overcharge_boost else '×1.5 ', star_class)

    return star_class


def process_jumps() -> None:
    if not this.route:
        this.remain_label['text'] = 'NavRoute: No NavRoute Set'
        this.navroute_label['text'] = 'Plot a Route to Begin'

        if this.overlay.available() and can_display_overlay():
            this.overlay.clear('navroute_display')
        return

    remaining_route = this.route[-this.remaining_jumps:]
    route_from_here = this.route[-(this.remaining_jumps+1):]
    last_system = this.route[-1]
    display = '{}{}'.format(this.current_system, f' [{star_display(this.current_system_class, this.show_indicators.get())}]')
    remaining_distance = 0

    for i, jump in enumerate(remaining_route):
        if i >= this.jump_num.get() or i == (len(remaining_route)):
            remainder_distance = 0
            for j, jump_remainder in enumerate(remaining_route[i:]):
                remainder_distance += get_distance(jump_remainder['StarPos'], remaining_route[i-1:][j]['StarPos'])
            remaining_distance += remainder_distance
            display += ((f' - {this.formatter.format_distance(remainder_distance, 'ly', False)} -> ' if this.show_distance.get() else ' -> ') +
                        f'{last_system["StarSystem"]} [{star_display(last_system["StarClass"], this.show_indicators.get())}]') if this.show_starclass.get() \
                else f' - {this.formatter.format_distance(remainder_distance, 'ly', False)} -> {last_system["StarSystem"]}'
            break
        else:
            distance = get_distance(jump['StarPos'], route_from_here[i]['StarPos'])
            remaining_distance += distance
            display += ((f' - {this.formatter.format_distance(distance, 'ly', False)} -> ' if this.show_distance.get() else ' -> ') +
                        f'{jump["StarSystem"]}' + f' [{star_display(jump["StarClass"], this.show_indicators.get())}]') if this.show_starclass.get() \
                else f' - {this.formatter.format_distance(distance, 'ly', False)} -> {jump["StarSystem"]}' if this.show_distance.get() else f'{jump["StarSystem"]}'
            if i == (this.jump_num.get() - 1) and i < len(remaining_route) - 2:
                display += f' | +{this.remaining_jumps - this.jump_num.get() - 1} Jump{"s"[:this.remaining_jumps ^ 1]}'

    if len(display) > 60:
        display = '\n-> '.join(display.split(' -> '))

    distance_ratio = f'{this.formatter.format_distance(remaining_distance, '', False)}/{this.formatter.format_distance(this.total_distance, 'ly', False)}'
    this.remain_label['text'] = (f'NavRoute ({this.formatter.format_distance(this.straight_distance, 'ly', False)},'
                                 f' {(this.straight_distance/this.total_distance*100):.1f}% efficiency)\n '
                                 f'{this.remaining_jumps} Jump{"s"[:this.remaining_jumps ^ 1]} Remaining ({distance_ratio})')
    this.navroute_label['text'] = display

    if this.overlay.available():
        if can_display_overlay():
            overlay_text = f'{this.remaining_jumps} Jump{"s"[:this.remaining_jumps ^ 1]} ({distance_ratio}): ' + display.replace('\n', ' ')
            this.overlay.display('navroute_display', overlay_text, this.overlay_anchor_x.get(),
                                 this.overlay_anchor_y.get(), this.overlay_color.get(), this.overlay_size.get().lower())
        else:
            this.overlay.clear('navroute_display')
