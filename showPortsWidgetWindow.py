#!/usr/bin/env python3
# showPortsWidgetWindow.py: the window of showPortsWidget (read-only tables, sortable columns, port number search, two tabs)
# usage: showPortsWidgetWindow.py /path/to/showPortsWidget.sh   (the shell script supplies the rows with --rows and --k8s-rows)
import subprocess   # runs the shell script that collects the ports
import sys   # reads the command line
import threading   # reads the data in the background so the window stays responsive
import gi   # PyGObject, the Python binding of GTK
gi.require_version("Gtk", "3.0")   # asks for GTK 3
from gi.repository import Gtk, GLib   # GTK widgets and the GLib main loop helpers

SCRIPT = sys.argv[1]   # path of showPortsWidget.sh, given by the shell script
MAX_PORT = 65535   # highest valid port number
HEADERS = ["Port", "Proto", "Reachable from", "Program", "Purpose"]   # column titles of tab 1
K8S_HEADERS = ["Namespace", "Service", "Address", "Ports", "Ready backends"]   # column titles of tab 2
TIPS = [   # plain-language explanation of each column of tab 1
    "The door number a program listens on. Like a room number in a hotel.",   # Port
    "The kind of connection. tcp is a phone call (a steady, checked connection). udp is a postcard (quick, no confirmation).",   # Proto
    "Who can knock on this door: this machine only, the Tailscale network only, or all networks (anyone who can reach this computer).",   # Reachable from
    "The program that has opened this door. hidden (needs admin) means Linux shows the name only to an administrator.",   # Program
    "What the door is used for: a Docker container, a Kubernetes service, a well-known service or your own note.",   # Purpose
]   # end of the tab 1 explanations
K8S_TIPS = [   # plain-language explanation of each column of tab 2
    "A folder inside Kubernetes that groups related things, for example monitoring or one model.",   # Namespace
    "The name that other programs inside Kubernetes use to reach an app, like an entry in an address book.",   # Service
    "The private number of the service. It works only inside Kubernetes. headless (no address) means there is no single number; callers find the individual pods directly.",   # Address
    "The doors of the service, written as number/type, for example 80/TCP.",   # Ports
    "How many running copies of the app (pods) are ready to answer. 0 means nobody is behind this service, for example when a model is stopped.",   # Ready backends
]   # end of the tab 2 explanations
TAB_TIPS = [   # explanation of the two tab names and the search box
    "Real ports this system is listening on, from Docker, Kubernetes (k3s), Tailscale and the operating system. The Reachable from column shows who can connect.",   # tab 1
    "Services that exist only inside Kubernetes. Each has a private (virtual) address and ports, but no real port is opened on this system, so nothing outside the cluster can reach them.",   # tab 2
    "Type a port number. Only digits are accepted, from 0 to 65535. Both tabs show only ports that start with these digits.",   # search box
]   # end of the other explanations

class PortsWindow(Gtk.Window):   # the one window of the tool
    def __init__(self):   # builds the window
        super().__init__(title="Ports in use")   # window with a first title
        self.set_default_size(1280, 620)   # starting size, wide enough for all column titles
        self.connect("destroy", Gtk.main_quit)   # closing the window ends the program
        self.total = 0   # number of port rows read (tab 1)
        self.total_k8s = 0   # number of Kubernetes service rows read (tab 2)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)   # vertical layout
        box.set_border_width(10)   # space around the content
        self.add(box)   # puts the layout into the window
        info = Gtk.Label(label="Read-only lists. Click a column title to sort. Type a port number to search (both tabs).", xalign=0)   # instruction line
        box.pack_start(info, False, False, 0)   # adds it at the top
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)   # row for the search box
        box.pack_start(row, False, False, 0)   # adds it below the instruction
        row.pack_start(Gtk.Label(label="Port number:"), False, False, 0)   # label before the box
        self.entry = Gtk.Entry()   # the search box
        self.entry.set_max_length(5)   # a port has at most 5 digits
        self.entry.set_width_chars(8)   # small box
        self.entry.set_tooltip_text(TAB_TIPS[2])   # explains what the box accepts
        self.entry.set_placeholder_text("digits only")   # hint inside the empty box
        self.entry.set_input_purpose(Gtk.InputPurpose.DIGITS)   # tells touch keyboards to show digits
        self.entry.connect("insert-text", self.on_insert)   # filters what may be typed or pasted
        self.entry.connect("changed", self.on_changed)   # re-filters the tables after every change
        row.pack_start(self.entry, False, False, 0)   # adds the box to the row
        row.pack_start(Gtk.Label(label="(0 to %d; shows ports that start with these digits)" % MAX_PORT), False, False, 0)   # explains the limit
        self.notebook = Gtk.Notebook()   # the two tabs
        box.pack_start(self.notebook, True, True, 0)   # the tabs take all free space
        self.store = Gtk.ListStore(int, str, str, str, str)   # tab 1 data: the port as a number, then four texts
        self.filter, page1 = self.make_table(self.store, HEADERS, [0, 1, 2, 3, 4], self.visible, TIPS)   # tab 1 table, sort by the shown columns
        tab1 = Gtk.Label(label="Listening ports on this system")   # title of tab 1
        tab1.set_tooltip_text(TAB_TIPS[0])   # explains tab 1
        self.notebook.append_page(page1, tab1)   # first tab
        self.kstore = Gtk.ListStore(str, str, str, str, str, int, bool)   # tab 2 data: five texts, the ready count as a number (for sorting), a flag for the notice row
        self.kfilter, page2 = self.make_table(self.kstore, K8S_HEADERS, [0, 1, 2, 3, 5], self.visible_k8s, K8S_TIPS)   # tab 2 table; the last column sorts by the number
        tab2 = Gtk.Label(label="Kubernetes-only services (virtual ports)")   # title of tab 2
        tab2.set_tooltip_text(TAB_TIPS[1])   # explains tab 2
        self.notebook.append_page(page2, tab2)   # second tab
        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8, homogeneous=True)   # row for the two buttons
        box.pack_start(buttons, False, False, 0)   # adds it at the bottom
        close_button = Gtk.Button(label="Close")   # Close button
        close_button.connect("clicked", lambda b: Gtk.main_quit())   # ends the program
        buttons.pack_start(close_button, True, True, 0)   # adds it
        self.refresh_button = Gtk.Button(label="Refresh")   # Refresh button
        self.refresh_button.connect("clicked", lambda b: self.load())   # reads everything again
        buttons.pack_start(self.refresh_button, True, True, 0)   # adds it
        self.load()   # first reading

    def make_table(self, store, headers, sort_ids, vis_func, tips):   # builds one filtered, sortable table; returns the filter and the scrollable widget
        flt = store.filter_new()   # a view of the data that hides rows that do not match
        flt.set_visible_func(vis_func)   # the rule for hiding rows
        srt = Gtk.TreeModelSort(model=flt)   # a sortable view on top of the filtered one
        srt.set_sort_column_id(sort_ids[0], Gtk.SortType.ASCENDING)   # starts sorted by the first column
        view = Gtk.TreeView(model=srt)   # the table widget
        view.set_grid_lines(Gtk.TreeViewGridLines.HORIZONTAL)   # thin lines between rows
        for i, title in enumerate(headers):   # one column per header
            col = Gtk.TreeViewColumn(title, Gtk.CellRendererText(), text=i)   # shows model column i as text
            col.set_sort_column_id(sort_ids[i])   # clicking the title sorts by this model column
            col.set_resizable(True)   # the user can drag the column width
            label = Gtk.Label(label=title)   # the visible column title
            label.set_tooltip_text(tips[i])   # the explanation shown when the mouse rests on the title
            label.show()   # makes the title visible
            col.set_widget(label)   # uses the label as the column header (clicking it still sorts)
            col.set_min_width(90)   # no column becomes too narrow
            col.set_expand(i == len(headers) - 1)   # the last column takes the spare width so its title is never cut off
            view.append_column(col)   # adds the column to the table
        scroll = Gtk.ScrolledWindow()   # makes the table scrollable
        scroll.set_vexpand(True)   # the table takes all free height
        scroll.add(view)   # puts the table inside
        return flt, scroll   # hands both back

    def on_insert(self, entry, text, length, position):   # called before text is inserted into the search box
        current = entry.get_text()   # what the box holds now
        new = current[:position] + text + current[position:]   # what it would hold afterwards
        if not (text.isascii() and text.isdigit()) or int(new) > MAX_PORT:   # not only digits, or above 65535
            entry.stop_emission_by_name("insert-text")   # rejects the input

    def on_changed(self, entry):   # called after the search box changed
        self.filter.refilter()   # applies the filter to tab 1
        self.kfilter.refilter()   # applies the filter to tab 2
        self.update_title()   # updates the counters in the title

    def visible(self, model, it, data):   # tab 1: decides whether a row is shown
        text = self.entry.get_text()   # digits typed so far
        return text == "" or str(model[it][0]).startswith(text)   # an empty box shows all; otherwise the port must start with the digits

    def visible_k8s(self, model, it, data):   # tab 2: decides whether a service row is shown
        text = self.entry.get_text()   # digits typed so far
        if text == "" or model[it][6]:   # an empty box shows all, and the notice row is always shown
            return True   # visible
        return any(p.split("/")[0].startswith(text) for p in model[it][3].split(",") if p)   # a service matches when one of its ports starts with the digits

    def update_title(self):   # shows how many rows are listed in each tab
        if self.entry.get_text() == "":   # no search active
            self.set_title("Ports in use (%d listening, %d inside Kubernetes)" % (self.total, self.total_k8s))   # plain counts
        else:   # search active
            shown_k = sum(1 for r in self.kfilter if not r[6])   # matching service rows (the notice row is not counted)
            self.set_title("Ports in use (%d of %d, %d of %d inside Kubernetes)" % (len(self.filter), self.total, shown_k, self.total_k8s))   # shown out of total

    def load(self):   # reads the data in the background
        self.refresh_button.set_sensitive(False)   # prevents a second reading at the same time
        self.set_title("Ports in use (reading ...)")   # tells the user to wait
        threading.Thread(target=self.read, daemon=True).start()   # starts the reading thread

    def read(self):   # runs in the background thread
        try:   # the script might fail
            out = subprocess.run([SCRIPT, "--rows"], capture_output=True, text=True, timeout=60).stdout   # asks the shell script for the port rows
        except Exception:   # any failure
            out = ""   # shows an empty table
        try:   # kubectl might be slow or missing
            kout = subprocess.run([SCRIPT, "--k8s-rows"], capture_output=True, text=True, timeout=40).stdout   # asks the shell script for the Kubernetes rows
        except Exception:   # any failure
            kout = ""   # shows an empty table
        GLib.idle_add(self.fill, out, kout)   # hands the results to the window thread

    def fill(self, out, kout):   # runs in the window thread
        self.store.clear()   # removes the old port rows
        n = 0   # port row counter
        for line in out.splitlines():   # one line per port
            f = line.split("\t")   # splits into cells
            if len(f) == 5 and f[0].isdigit():   # only complete lines with a numeric port
                self.store.append([int(f[0]), f[1], f[2], f[3], f[4]])   # adds the row
                n += 1   # counts it
        self.total = n   # remembers the total
        self.kstore.clear()   # removes the old Kubernetes rows
        k = 0   # service row counter
        for line in kout.splitlines():   # one line per service
            f = line.split("\t")   # splits into cells
            if f[0] == "NOTE" and len(f) >= 2:   # a notice such as "Kubernetes is not running"
                self.kstore.append(["-", f[1], "", "", "", -1, True])   # shows the notice in the Service column
            elif len(f) == 5:   # a complete service line
                self.kstore.append([f[0], f[1], f[2], f[3], f[4], int(f[4]) if f[4].isdigit() else -1, False])   # adds the row; the count is also kept as a number for sorting
                k += 1   # counts it
        self.total_k8s = k   # remembers the total
        self.update_title()   # updates the title
        self.refresh_button.set_sensitive(True)   # allows the next refresh
        return False   # run this idle function only once

win = PortsWindow()   # creates the window
win.show_all()   # shows it
Gtk.main()   # runs until Close
