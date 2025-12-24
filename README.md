# NavRoute plugin for EDMC

This [Elite Dangerous Market Connector][EDMC] plugin is designed to give you an extended view of your current NavRoute.

Once a route has been plotted, the display will indicate the remaining jumps as well as a configurable number of
interim jumps between your current position and final target.

As of version 1.3, there are now optional indicators for jump boosts (compatible with the Mk II FSD boost values),
fuel stars, and jump distances.

The EDMC window display also shows some extra info about potential route efficiency (straight vs actual distance).

If you jump to a system that is not on your route, the plugin will indicate this and suggest the nearest route location.

## Requirements
* EDMC version 6.0.0 and above

## Installation
* Download the [latest release]
* Extract the `.zip` archive that you downloaded into the EDMC `plugins` folder
  * This is accessible via the plugins tab in the EDMC settings window
* Start or restart EDMC to register the new plugin

## License

[NavRoute plugin][NavRoute] Copyright © 2025 Jeremy Rimpo

Licensed under the [GNU Public License (GPL)][GPLv2] version 2 or later.

[EDMC]: https://github.com/EDCD/EDMarketConnector/wiki
[NavRoute]: https://github.com/Silarn/EDMC-NavRoute
[latest release]: https://github.com/Silarn/EDMC-NavRoute/releases/latest
[GPLv2]: http://www.gnu.org/licenses/gpl-2.0.html
