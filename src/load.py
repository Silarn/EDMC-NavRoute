# -*- coding: utf-8 -*-
# NavRoute plugin for EDMC
# Source: https://github.com/Silarn/EDMC-NavRoute
#
# Copyright (C) 2023 Jeremy Rimpo
# Licensed under the [GNU Public License (GPL)](http://www.gnu.org/licenses/gpl-2.0.html) version 2 or later.

import tkinter as tk
from tkinter import ttk, colorchooser as tkColorChooser

import myNotebook as nb

from navroute import const, overlay

import EDMCLogging
from config import config
from theme import theme
from typing import Any, MutableMapping, Mapping
from EDMCLogging import get_main_logger
from ttkHyperlinkLabel import HyperlinkLabel


class This:
    """Holds module globals."""

    def __init__(self):
        self.jump_num: tk.IntVar | None = None

        self.logger: EDMCLogging.LoggerMixin = get_main_logger()
        self.current_system: str = "Unknown"
        self.route: dict = {}

        self.parent: tk.Frame | None = None
        self.frame: tk.Frame | None = None
        self.title_label: tk.Label | None = None
        self.remain_label: tk.Label | None = None
        self.navroute_label: tk.Label | None = None
        self.search_route: bool = False
        self.remaining_jumps: int = 0

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
    theme.update(this.frame)
    return this.frame


def plugin_prefs(parent: nb.Frame, cmdr: str, is_beta: bool) -> nb.Frame:
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
    nb.Entry(
        frame,
        textvariable=this.jump_num,
        validate='all',
        validatecommand=(vcmd, '%P')
    ).grid(row=11, padx=x_padding, pady=y_padding, column=0, sticky=tk.W)

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
    color_button = nb.ColoredButton(
        frame,
        text='Text Color',
        foreground=this.overlay_color.get(),
        background='grey4',
        command=lambda: color_chooser()
    ).grid(row=22, column=0, padx=x_button_padding, pady=y_padding, sticky=tk.W)

    anchor_frame = nb.Frame(frame)
    anchor_frame.grid(row=21, column=1, sticky=tk.NSEW)
    anchor_frame.columnconfigure(4, weight=1)

    nb.Label(anchor_frame, text='Display Anchor:') \
        .grid(row=0, column=0, sticky=tk.W)
    nb.Label(anchor_frame, text='X') \
        .grid(row=0, column=1, sticky=tk.W)
    nb.Entry(
        anchor_frame, text=this.overlay_anchor_x.get(), textvariable=this.overlay_anchor_x,
        width=8, validate='all', validatecommand=(vcmd, '%P')
    ).grid(row=0, column=2, sticky=tk.W)
    nb.Label(anchor_frame, text='Y') \
        .grid(row=0, column=3, sticky=tk.W)
    nb.Entry(
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
    config.set('navroute_overlay', this.use_overlay.get())
    config.set('navroute_overlay_color', this.overlay_color.get())
    config.set('navroute_overlay_size', this.overlay_size.get())
    config.set('navroute_overlay_anchor_x', this.overlay_anchor_x.get())
    config.set('navroute_overlay_anchor_y', this.overlay_anchor_y.get())
    process_jumps()


def parse_config() -> None:
    this.jump_num = tk.IntVar(value=config.get_int(key='navroute_jumps', default=1))
    this.use_overlay = tk.BooleanVar(value=config.get_bool(key='navroute_overlay', default=False))
    this.overlay_color = tk.StringVar(value=config.get_str(key='navroute_overlay_color', default='#ffffff'))
    this.overlay_size = tk.StringVar(value=config.get_str(key='navroute_overlay_size', default='Normal'))
    this.overlay_anchor_x = tk.IntVar(value=config.get_int(key='navroute_overlay_anchor_x', default=0))
    this.overlay_anchor_y = tk.IntVar(value=config.get_int(key='navroute_overlay_anchor_y', default=1040))


def validate_int(val: str) -> bool:
    if val.isdigit() or val == "":
        return True
    return False


def journal_entry(cmdr: str, is_beta: bool, system: str,
                  station: str, entry: MutableMapping[str, Any], state: Mapping[str, Any]) -> str:
    this.current_system = system if system is not None else ''

    match entry['event']:
        case 'FSDTarget':
            found = False
            if this.route:
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
            this.remaining_jumps = len(this.route) - 1 if this.route else 0
            this.search_route = True
            process_jumps()
        case 'NavRouteClear':
            this.remaining_jumps = 0
            this.route.clear()
            this.search_route = False
            this.remain_label['text'] = "NavRoute: NavRoute Cleared"
            this.navroute_label['text'] = "Plot a Route to Begin"
            if this.overlay.available():
                this.overlay.draw('navroute_display', 'NavRoute Cleared', this.overlay_anchor_x.get(),
                                     this.overlay_anchor_y.get(), this.overlay_color.get(),
                                     this.overlay_size.get().lower(), 10)
        case 'FSDJump':
            if len(this.route):
                if entry['StarSystem'] == this.route[-1]['StarSystem']:
                    this.remain_label['text'] = 'NavRoute: Route Complete!'
                    this.navroute_label['text'] = 'No NavRoute Destination Set'
                    this.remaining_jumps = 0
                    this.route.clear()
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
                        this.remain_label['text'] = 'NavRoute: Diverted From Route!'
                        index = len(this.route) - this.remaining_jumps
                        next_system = this.route[index]
                        divert_text = 'Jump to {} to Resume'.format(next_system['StarSystem'])
                        this.navroute_label['text'] = divert_text
                        if this.overlay.available():
                            this.overlay.display('navroute_display', divert_text, this.overlay_anchor_x.get(),
                                                 this.overlay_anchor_y.get(), this.overlay_color.get())
            else:
                this.remain_label['text'] = 'NavRoute: No NavRoute Set'
                this.navroute_label['text'] = 'Plot a Route to Begin'
                if this.overlay.available():
                    this.overlay.clear('navroute_display')

    if state['NavRoute'] is not None and this.search_route:
        if this.route != state['NavRoute']['Route']:
            this.route = state['NavRoute']['Route']
            this.search_route = False
            process_jumps()

    return ''


def process_jumps() -> None:
    if not this.route:
        this.remain_label['text'] = 'NavRoute: No NavRoute Set'
        this.navroute_label['text'] = 'Plot a Route to Begin'

        if this.overlay.available():
            this.overlay.clear('navroute_display')
        return

    remaining_route = this.route[-this.remaining_jumps:]
    last_system = this.route[-1]
    display = f'{this.current_system}'

    for i, jump in enumerate(remaining_route):
        if i >= this.jump_num.get() or i == (len(remaining_route)):
            display += f' -> {last_system['StarSystem']}'
            break
        else:
            display += f' -> {jump['StarSystem']}'
            if i == (this.jump_num.get() - 1) and i < len(remaining_route) - 2:
                display += ' | +{} Jump(s)'.format(this.remaining_jumps - this.jump_num.get() - 1)

    if len(display) > 60:
        display = '\n-> '.join(display.split(' -> '))

    this.remain_label['text'] = f'NavRoute: {this.remaining_jumps} Jump{"s"[:this.remaining_jumps ^ 1]} Remaining:'
    this.navroute_label['text'] = display

    if this.overlay.available():
        overlay_text = f'{this.remaining_jumps} Jumps: ' + display.replace('\n', ' ')
        this.overlay.display('navroute_display', overlay_text, this.overlay_anchor_x.get(),
                             this.overlay_anchor_y.get(), this.overlay_color.get(), this.overlay_size.get().lower())
