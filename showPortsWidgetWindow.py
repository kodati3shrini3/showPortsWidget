#!/usr/bin/env python3
# showPortsWidgetWindow.py: the window of showPortsWidget (read-only table, sortable columns, port number search)
# usage: showPortsWidgetWindow.py /path/to/showPortsWidget.sh   (the shell script supplies the rows with --rows)
import subprocess   # runs the shell script that collects the ports
import sys   # reads the command line
import threading   # reads the ports in the background so the window stays responsive
import gi   # PyGObject, the Python binding of GTK
gi.require_version("Gtk", "3.0")   # asks for GTK 3
from gi.repository import Gtk, GLib   # GTK widgets and the GLib main loop helpers

SCRIPT = sys.argv[1]   # path of showPortsWidget.sh, given by the shell script
MAX_PORT = 65535   # highest valid port number
HEADERS = ["Port", "Proto", "Reachable from", "Program", "Purpose"]   # column titles

class PortsWindow(Gtk.Window):   # the one window of the tool
    def __init__(self):   # builds the window
        super().__init__(title="Ports in use")   # window with a first title
        self.set_default_size(1150, 620)   # starting size
        self.connect("destroy", Gtk.main_quit)   # closing the window ends the program
        self.total = 0   # number of rows read
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)   # vertical layout
        box.set_border_width(10)   # space around the content
        self.add(box)   # puts the layout into the window
        info = Gtk.Label(label="Read-only list. Click a column title to sort. Type a port number to search.", xalign=0)   # instruction line
        box.pack_start(info, False, False, 0)   # adds it at the top
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)   # row for the search box
        box.pack_start(row, False, False, 0)   # adds it below the instruction
        row.pack_start(Gtk.Label(label="Port number:"), False, False, 0)   # label before the box
        self.entry = Gtk.Entry()   # the search box
        self.entry.set_max_length(5)   # a port has at most 5 digits
        self.entry.set_width_chars(8)   # small box
        self.entry.set_placeholder_text("digits only")   # hint inside the empty box
        self.entry.set_input_purpose(Gtk.InputPurpose.DIGITS)   # tells touch keyboards to show digits
        self.entry.connect("insert-text", self.on_insert)   # filters what may be typed or pasted
        self.entry.connect("changed", self.on_changed)   # re-filters the table after every change
        row.pack_start(self.entry, False, False, 0)   # adds the box to the row
        row.pack_start(Gtk.Label(label="(0 to %d; shows ports that start with these digits)" % MAX_PORT), False, False, 0)   # explains the limit
        self.store = Gtk.ListStore(int, str, str, str, str)   # the data: the port as a number, then four texts
        self.filter = self.store.filter_new()   # a view of the data that hides rows that do not match
        self.filter.set_visible_func(self.visible)   # the rule for hiding rows
        self.sorted = Gtk.TreeModelSort(model=self.filter)   # a sortable view on top of the filtered one
        self.sorted.set_sort_column_id(0, Gtk.SortType.ASCENDING)   # starts sorted by port number
        view = Gtk.TreeView(model=self.sorted)   # the table widget
        for i, title in enumerate(HEADERS):   # one column per header
            col = Gtk.TreeViewColumn(title, Gtk.CellRendererText(), text=i)   # shows model column i as text
            col.set_sort_column_id(i)   # clicking the title sorts by this column
            col.set_resizable(True)   # the user can drag the column width
            view.append_column(col)   # adds the column to the table
        scroll = Gtk.ScrolledWindow()   # makes the table scrollable
        scroll.set_vexpand(True)   # the table takes all free height
        scroll.add(view)   # puts the table inside
        box.pack_start(scroll, True, True, 0)   # adds it to the layout
        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8, homogeneous=True)   # row for the two buttons
        box.pack_start(buttons, False, False, 0)   # adds it at the bottom
        close_button = Gtk.Button(label="Close")   # Close button
        close_button.connect("clicked", lambda b: Gtk.main_quit())   # ends the program
        buttons.pack_start(close_button, True, True, 0)   # adds it
        self.refresh_button = Gtk.Button(label="Refresh")   # Refresh button
        self.refresh_button.connect("clicked", lambda b: self.load())   # reads the ports again
        buttons.pack_start(self.refresh_button, True, True, 0)   # adds it
        self.load()   # first reading

    def on_insert(self, entry, text, length, position):   # called before text is inserted into the search box
        current = entry.get_text()   # what the box holds now
        new = current[:position] + text + current[position:]   # what it would hold afterwards
        if not (text.isascii() and text.isdigit()) or int(new) > MAX_PORT:   # not only digits, or above 65535
            entry.stop_emission_by_name("insert-text")   # rejects the input

    def on_changed(self, entry):   # called after the search box changed
        self.filter.refilter()   # applies the filter again
        self.update_title()   # updates the counter in the title

    def visible(self, model, it, data):   # decides whether a row is shown
        text = self.entry.get_text()   # digits typed so far
        return text == "" or str(model[it][0]).startswith(text)   # an empty box shows all; otherwise the port must start with the digits

    def update_title(self):   # shows how many rows are listed
        if self.entry.get_text() == "":   # no search active
            self.set_title("Ports in use (%d listening)" % self.total)   # plain count
        else:   # search active
            self.set_title("Ports in use (%d of %d)" % (len(self.filter), self.total))   # shown out of total

    def load(self):   # reads the ports in the background
        self.refresh_button.set_sensitive(False)   # prevents a second reading at the same time
        self.set_title("Ports in use (reading ...)")   # tells the user to wait
        threading.Thread(target=self.read, daemon=True).start()   # starts the reading thread

    def read(self):   # runs in the background thread
        try:   # the script might fail
            out = subprocess.run([SCRIPT, "--rows"], capture_output=True, text=True, timeout=60).stdout   # asks the shell script for the rows
        except Exception:   # any failure
            out = ""   # shows an empty table
        GLib.idle_add(self.fill, out)   # hands the result to the window thread

    def fill(self, out):   # runs in the window thread
        self.store.clear()   # removes the old rows
        n = 0   # row counter
        for line in out.splitlines():   # one line per port
            f = line.split("\t")   # splits into cells
            if len(f) == 5 and f[0].isdigit():   # only complete lines with a numeric port
                self.store.append([int(f[0]), f[1], f[2], f[3], f[4]])   # adds the row
                n += 1   # counts it
        self.total = n   # remembers the total
        self.update_title()   # updates the title
        self.refresh_button.set_sensitive(True)   # allows the next refresh
        return False   # run this idle function only once

win = PortsWindow()   # creates the window
win.show_all()   # shows it
Gtk.main()   # runs until Close
