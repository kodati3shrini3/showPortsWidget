#!/bin/bash
# install.sh: creates the desktop icon and menu entry of showPortsWidget (this tool's own launcher only)
# usage: install.sh [--dry-run] [--no-desktop] [--remove]

ROOT="$(dirname "$(readlink -f "$0")")"   # folder of this tool, wherever it was cloned
NAME="ShowPortsWidget.desktop"   # file name of the launcher
APPDIR="$HOME/.local/share/applications"   # where the application menu looks for launchers
DESKTOPDIR="$(xdg-user-dir DESKTOP 2>/dev/null)"   # the user's Desktop folder, if the system knows it
{ [ -z "$DESKTOPDIR" ] || [ "$DESKTOPDIR" = "$HOME" ]; } && DESKTOPDIR="$HOME/Desktop"   # falls back to ~/Desktop when unknown
BACKUPS="${XDG_STATE_HOME:-$HOME/.local/state}/showPortsWidget/launcherBackups"   # where a different existing launcher is saved before it is replaced
DRY=0; DESK=1; REMOVE=0   # option flags: dry run, desktop icon wanted, removal mode
for A in "$@"; do   # reads the options one by one
  case "$A" in --dry-run) DRY=1;; --no-desktop) DESK=0;; --remove) REMOVE=1;; *) echo "unknown option: $A" >&2; exit 1;; esac   # sets a flag or stops on an unknown option
done   # end of the option loop

launcher_text() {   # prints the content of the launcher file
  printf '[Desktop Entry]\nType=Application\nName=Show Ports\nComment=List all ports in use, who can reach them and what they are for\nExec="%s"\nIcon=%s\nTerminal=false\nCategories=System;Network;\n' "$ROOT/showPortsWidget.sh" "$ROOT/showPortsWidgetIcon.svg"   # fixed content with this tool's own paths
}   # end of launcher_text

TARGETS=("$APPDIR/$NAME")   # the menu entry is always handled
[ "$DESK" = 1 ] && [ -d "$DESKTOPDIR" ] && TARGETS+=("$DESKTOPDIR/$NAME")   # the Desktop icon only when a Desktop folder exists

if [ "$REMOVE" = 1 ]; then   # removal mode: only this tool's own launchers
  for T in "${TARGETS[@]}"; do   # each launcher of this tool
    if [ -f "$T" ]; then   # only when it exists
      echo "remove: $T"   # tells what is removed
      [ "$DRY" = 1 ] || { gio trash "$T" 2>/dev/null || rm -f "$T"; }   # moves it to the Trash, or deletes it when there is no Trash
    fi   # end of the exists check
  done   # end of the removal loop
  echo "done."; exit 0   # finished
fi   # end of removal mode

for TOOL in ss awk sort; do   # software the widget always needs
  if ! command -v "$TOOL" >/dev/null 2>&1; then echo "skipped: showPortsWidget needs '$TOOL', which is not installed (Ubuntu: sudo apt install iproute2 gawk coreutils)"; exit 0; fi   # nothing is created without its software
done   # end of the software check
if ! { python3 -c 'import gi; gi.require_version("Gtk","3.0"); from gi.repository import Gtk' >/dev/null 2>&1 || command -v zenity >/dev/null 2>&1; }; then echo "skipped: showPortsWidget needs a window program: python3-gi with GTK 3 (Ubuntu: sudo apt install python3-gi gir1.2-gtk-3.0) or zenity"; exit 0; fi   # needs at least one window program

[ "$DRY" = 1 ] && echo "DRY RUN: nothing will be changed"   # reminds that a dry run changes nothing
[ "$DRY" = 1 ] || mkdir -p "$APPDIR"   # makes sure the menu folder exists
for T in "${TARGETS[@]}"; do   # each launcher to create
  if [ -f "$T" ] && [ "$(launcher_text)" = "$(cat "$T")" ]; then echo "unchanged: $T"; continue; fi   # already correct, nothing to do
  if [ -f "$T" ]; then   # a different launcher exists
    echo "replace: $T (the old one is saved in $BACKUPS)"   # tells what happens
    [ "$DRY" = 1 ] || { mkdir -p "$BACKUPS"; cp "$T" "$BACKUPS/$(basename "$(dirname "$T")")-$NAME.$(date +%Y%m%d%H%M%S)"; }   # saves the old one; the folder name keeps the menu and Desktop copies apart
  else echo "create: $T"; fi   # a new launcher
  if [ "$DRY" = 0 ]; then   # real run only
    launcher_text > "$T"; chmod +x "$T"   # writes the launcher and makes it executable
    case "$T" in "$DESKTOPDIR"/*) gio set "$T" metadata::trusted true 2>/dev/null;; esac   # lets the Desktop icon start without a warning
  fi   # end of the real-run part
done   # end of the launcher loop
echo "done."   # finished
