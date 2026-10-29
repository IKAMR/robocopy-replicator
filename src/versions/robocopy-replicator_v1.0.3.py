# robocopy_replicator.py
# Windows Robocopy Replicator GUI
# v1.0.3
# 2026-10-29
# IKAMR\TAA
# Python 3.10+
#
# No external packages required.


# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

APP_VERSION = "1.0.3"

DEFAULT_WIDTH = 1200
NORMAL_HEIGHT = 800
ADVANCED_HEIGHT = 800

ROBOCOPY_OK_MAX = 7


# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import json
import os
import shlex
import subprocess
import threading

from datetime import datetime
import time
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

# Optional drag & drop support
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False

# -----------------------------------------------------------------------------
# Derived constants
# -----------------------------------------------------------------------------

APP_DIR = Path(__file__).resolve().parent
APP_STEM = Path(__file__).resolve().stem

SETTINGS_FILE = APP_DIR / f"{APP_STEM}_settings.json"
PROFILES_DIR = APP_DIR / f"{APP_STEM}_profiles"
JOBS_DIR = APP_DIR / f"{APP_STEM}_jobs"
LAST_JOB_FILE = APP_DIR / f"{APP_STEM}_last_job.json"


class RobocopyReplicator:
    def __init__(self, root):
        self.root = root
        self.root.title(f"Robocopy Replicator v{APP_VERSION}")
        self.root.geometry(f"{min(DEFAULT_WIDTH, self.root.winfo_screenwidth())}x{min(NORMAL_HEIGHT, self.root.winfo_screenheight() - 100)}")

        self.sources = []
        self.current_process = None
        self.cancel_requested = False
        self.job_results = []
        self.summary_lines = []
        self.source_drag_item = None
        self.source_drag_index = None

        self.target_folder = tk.StringVar()
        self.job_name = tk.StringVar(value="robocopy-job")

        self.dry_run = tk.BooleanVar(value=False)
        self.use_timestamp = tk.BooleanVar(value=True)
        self.show_advanced = tk.BooleanVar(value=False)
        self.summary_format = tk.StringVar(value="ascii")
        self.show_exit_code = tk.BooleanVar(value=False)

        self.use_e = tk.BooleanVar(value=True)
        self.use_np = tk.BooleanVar(value=True)
        self.use_tee = tk.BooleanVar(value=True)
        self.use_j = tk.BooleanVar(value=True)
        self.use_z = tk.BooleanVar(value=False)
        self.use_mir = tk.BooleanVar(value=False)

        self.retry_count = tk.IntVar(value=3)
        self.wait_seconds = tk.IntVar(value=5)
        self.mt_count = tk.StringVar(value="")
        self.extra_options = tk.StringVar(value="")

        self.exclude_dirs = tk.StringVar(
            value='$RECYCLE.BIN Dropbox "System Volume Information"'
        )

        self.log_location = tk.StringVar(value="local")
        self.local_log_folder = tk.StringVar(value=str(APP_DIR / "robocopy_log"))

        self.status = tk.StringVar(value="Ready")
        self.progress_text = tk.StringVar(value="No job running")

        self.build_gui()
        self.load_settings()

    def build_gui(self):
        # A scrollable outer viewport keeps all controls reachable on small screens.
        viewport = ttk.Frame(self.root)
        viewport.pack(fill="both", expand=True)
        self.main_canvas = tk.Canvas(viewport, highlightthickness=0, borderwidth=0)
        main_scroll = ttk.Scrollbar(viewport, orient="vertical", command=self.main_canvas.yview)
        self.main_canvas.configure(yscrollcommand=main_scroll.set)
        main_scroll.pack(side="right", fill="y")
        self.main_canvas.pack(side="left", fill="both", expand=True)

        main = ttk.Frame(self.main_canvas, padding=10)
        self.main_canvas_window = self.main_canvas.create_window((0, 0), window=main, anchor="nw")
        main.bind("<Configure>", lambda event: self.main_canvas.configure(
            scrollregion=self.main_canvas.bbox("all")))
        self.main_canvas.bind("<Configure>", lambda event: self.main_canvas.itemconfigure(
            self.main_canvas_window, width=event.width))
        self.root.bind_all("<MouseWheel>", self._scroll_main_window, add="+")

        title = ttk.Label(
            main,
            text=f"Robocopy Replicator v{APP_VERSION}",
            font=("Segoe UI", 16, "bold"),
        )
        title.pack(anchor="w")

        ttk.Label(
            main,
            text="Simple users choose source and target. Advanced users can change robocopy parameters, logging, exclusions and profiles.",
        ).pack(anchor="w", pady=(0, 10))

        self.content_pane = ttk.PanedWindow(main, orient=tk.VERTICAL)
        self.content_pane.pack(fill="x", pady=5)
        self.content_pane.configure(height=400)

        source_frame = ttk.LabelFrame(self.content_pane, text="Sources")
        self.content_pane.add(source_frame, weight=1)

        source_buttons = ttk.Frame(source_frame)
        source_buttons.pack(fill="x", padx=5, pady=5)

        ttk.Button(source_buttons, text="Add folder", command=self.add_folder).pack(side="left", padx=3)
        ttk.Button(source_buttons, text="Add files", command=self.add_files).pack(side="left", padx=3)
        ttk.Button(source_buttons, text="Move up", command=self.move_selected_up).pack(side="left", padx=3)
        ttk.Button(source_buttons, text="Move down", command=self.move_selected_down).pack(side="left", padx=3)
        ttk.Button(source_buttons, text="Remove selected", command=self.remove_selected).pack(side="left", padx=3)
        ttk.Button(source_buttons, text="Clear", command=self.clear_sources).pack(side="left", padx=3)

        self.source_tree = ttk.Treeview(
            source_frame,
            columns=("no", "source", "type"),
            show="headings",
            # height=7,
            selectmode="extended",
        )

        self.source_tree.heading("no", text="#")
        self.source_tree.heading("source", text="Source")
        self.source_tree.heading("type", text="Type")

        self.source_tree.column("no", width=50, anchor="center", stretch=False)
        self.source_tree.column("source", width=850, anchor="w", stretch=True)
        self.source_tree.column("type", width=100, anchor="center", stretch=False)

        self.source_tree.pack(
            fill="both",
            expand=True,
            padx=5,
            pady=(0, 5),
        )

        if DND_AVAILABLE:
            self.source_tree.drop_target_register(DND_FILES)
            self.source_tree.dnd_bind("<<Drop>>", self.drop_sources)

        self.source_tree.bind("<ButtonPress-1>", self.source_drag_start)
        self.source_tree.bind("<B1-Motion>", self.source_drag_motion)
        self.source_tree.bind("<ButtonRelease-1>", self.source_drag_drop)

        target_frame = ttk.LabelFrame(main, text="Target")
        target_frame.pack(fill="x", pady=5)

        ttk.Entry(target_frame, textvariable=self.target_folder).pack(
            side="left", fill="x", expand=True, padx=5, pady=6
        )
        ttk.Button(target_frame, text="Choose target", command=self.choose_target).pack(
            side="left", padx=5
        )

        job_frame = ttk.LabelFrame(main, text="Job")
        job_frame.pack(fill="x", pady=5)

        ttk.Label(job_frame, text="Job name / log prefix:").pack(
            side="left", padx=5
        )

        ttk.Entry(
            job_frame,
            textvariable=self.job_name,
        ).pack(
            side="left",
            fill="x",
            expand=True,
            padx=5,
            pady=5,
        )

        simple_frame = ttk.LabelFrame(main, text="Simple options")
        simple_frame.pack(fill="x", pady=5)

        ttk.Checkbutton(
            simple_frame,
            text="Dry run /L - list only, do not copy",
            variable=self.dry_run,
        ).pack(anchor="w", padx=5)

        ttk.Checkbutton(
            simple_frame,
            text="Add timestamp to logfile name",
            variable=self.use_timestamp,
        ).pack(anchor="w", padx=5)

        ttk.Checkbutton(
            simple_frame,
            text="Show advanced robocopy options",
            variable=self.show_advanced,
            command=self.toggle_advanced,
        ).pack(anchor="w", padx=5)

        summary_frame = ttk.Frame(simple_frame)
        summary_frame.pack(anchor="w", padx=5, pady=3)

        ttk.Label(summary_frame, text="Summary format:").pack(side="left", padx=(0, 5))

        ttk.Radiobutton(
            summary_frame,
            text="ASCII",
            variable=self.summary_format,
            value="ascii",
        ).pack(side="left", padx=3)

        ttk.Radiobutton(
            summary_frame,
            text="Icons",
            variable=self.summary_format,
            value="icons",
        ).pack(side="left", padx=3)

        ttk.Checkbutton(
            simple_frame,
            text="Show Robocopy exit code in summary",
            variable=self.show_exit_code,
        ).pack(anchor="w", padx=5)

        self.advanced_frame = ttk.LabelFrame(main, text="Advanced options")
        self.build_advanced_options()

        self.profile_frame = ttk.LabelFrame(main, text="Profiles and command")
        self.profile_frame.pack(fill="x", pady=5)

        ttk.Button(self.profile_frame, text="Save profile", command=self.save_profile).pack(side="left", padx=4, pady=5)
        ttk.Button(self.profile_frame, text="Load profile", command=self.load_profile).pack(side="left", padx=4, pady=5)
        ttk.Button(self.profile_frame, text="Restore last job", command=self.restore_last_job).pack(side="left", padx=4, pady=5)
        ttk.Button(self.profile_frame, text="Save job", command=self.save_job).pack(side="left", padx=4, pady=5)
        ttk.Button(self.profile_frame, text="Load job", command=self.load_job).pack(side="left", padx=4, pady=5)
        ttk.Button(self.profile_frame, text="Copy command preview", command=self.copy_command_preview).pack(side="left", padx=4, pady=5)
        ttk.Button(self.profile_frame, text="Show command preview", command=self.show_command_preview).pack(side="left", padx=4, pady=5)

        run_frame = ttk.Frame(main)
        run_frame.pack(fill="x", pady=8)

        self.start_button = ttk.Button(run_frame, text="START REPLICATION", command=self.start_jobs)
        self.start_button.pack(side="left", padx=4)

        self.cancel_button = ttk.Button(run_frame, text="Cancel running job", command=self.cancel_job, state="disabled")
        self.cancel_button.pack(side="left", padx=4)

        ttk.Button(run_frame, text="Exit", command=self.on_close).pack(side="right", padx=4)

        progress_frame = ttk.LabelFrame(main, text="Status")
        progress_frame.pack(fill="x", pady=5)

        self.progress = ttk.Progressbar(
            progress_frame,
            mode="determinate",
            maximum=100,
            value=0,
        )
        self.progress.pack(fill="x", padx=5, pady=5)

        ttk.Label(progress_frame, textvariable=self.progress_text).pack(anchor="w", padx=5)
        ttk.Label(progress_frame, textvariable=self.status).pack(anchor="w", padx=5, pady=(0, 5))

        log_frame = ttk.LabelFrame(self.content_pane, text="Live robocopy output")
        self.content_pane.add(log_frame, weight=3)
        self.root.after(100, lambda: self.content_pane.sashpos(0, 330))

        self.output = scrolledtext.ScrolledText(log_frame, height=18)
        self.output.pack(fill="both", expand=True, padx=5, pady=5)
        self.output.tag_configure("summary_ok", foreground="green")
        self.output.tag_configure("summary_info", foreground="blue")
        self.output.tag_configure("summary_error", foreground="red")

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def build_advanced_options(self):
        f = self.advanced_frame

        row = 0
        flags = ttk.Frame(f)
        flags.grid(row=row, column=0, columnspan=2, sticky="w", padx=5, pady=3)

        ttk.Checkbutton(flags, text="/E", variable=self.use_e).pack(side="left", padx=4)
        ttk.Checkbutton(flags, text="/NP", variable=self.use_np).pack(side="left", padx=4)
        ttk.Checkbutton(flags, text="/TEE", variable=self.use_tee).pack(side="left", padx=4)
        ttk.Checkbutton(flags, text="/J", variable=self.use_j).pack(side="left", padx=4)
        ttk.Checkbutton(flags, text="/Z", variable=self.use_z).pack(side="left", padx=4)
        ttk.Checkbutton(flags, text="/MIR dangerous", variable=self.use_mir).pack(side="left", padx=4)

        row += 1
        ttk.Label(f, text="Retry count /R:").grid(row=row, column=0, sticky="w", padx=5, pady=3)
        ttk.Spinbox(f, from_=0, to=999, textvariable=self.retry_count, width=10).grid(row=row, column=1, sticky="w", padx=5, pady=3)

        row += 1
        ttk.Label(f, text="Wait seconds /W:").grid(row=row, column=0, sticky="w", padx=5, pady=3)
        ttk.Spinbox(f, from_=0, to=999, textvariable=self.wait_seconds, width=10).grid(row=row, column=1, sticky="w", padx=5, pady=3)

        row += 1
        ttk.Label(f, text="Multithread /MT:n blank = off:").grid(row=row, column=0, sticky="w", padx=5, pady=3)
        ttk.Entry(f, textvariable=self.mt_count, width=10).grid(row=row, column=1, sticky="w", padx=5, pady=3)

        row += 1
        ttk.Label(f, text="Exclude directories:").grid(row=row, column=0, sticky="w", padx=5, pady=3)
        ttk.Entry(f, textvariable=self.exclude_dirs).grid(row=row, column=1, sticky="ew", padx=5, pady=3)

        row += 1
        ttk.Label(f, text="Extra robocopy options:").grid(row=row, column=0, sticky="w", padx=5, pady=3)
        ttk.Entry(f, textvariable=self.extra_options).grid(row=row, column=1, sticky="ew", padx=5, pady=3)

        row += 1
        ttk.Label(f, text="Log location:").grid(row=row, column=0, sticky="w", padx=5, pady=3)

        log_frame = ttk.Frame(f)
        log_frame.grid(row=row, column=1, sticky="w", padx=5, pady=3)

        ttk.Radiobutton(log_frame, text="Local", variable=self.log_location, value="local").pack(side="left")
        ttk.Radiobutton(log_frame, text="Source", variable=self.log_location, value="source").pack(side="left")
        ttk.Radiobutton(log_frame, text="Target", variable=self.log_location, value="target").pack(side="left")

        row += 1
        ttk.Label(f, text="Local log folder:").grid(row=row, column=0, sticky="w", padx=5, pady=3)

        log_folder_frame = ttk.Frame(f)
        log_folder_frame.grid(row=row, column=1, sticky="ew", padx=5, pady=3)

        ttk.Entry(log_folder_frame, textvariable=self.local_log_folder).pack(side="left", fill="x", expand=True)
        ttk.Button(log_folder_frame, text="Choose", command=self.choose_local_log_folder).pack(side="left", padx=5)

        f.columnconfigure(1, weight=1)

    def _scroll_main_window(self, event):
        # Respect widgets that already have their own vertical scrolling.
        widget = event.widget
        while widget is not None:
            if isinstance(widget, (ttk.Treeview, tk.Text, tk.Listbox, tk.Spinbox, ttk.Spinbox)):
                return
            if widget == self.root:
                break
            widget = getattr(widget, "master", None)
        if self.main_canvas.winfo_exists():
            self.main_canvas.yview_scroll(-int(event.delta / 120) if event.delta else 0, "units")

    def toggle_advanced(self):
        if self.show_advanced.get():
            self.advanced_frame.pack(fill="x", pady=5, before=self.profile_frame)
        else:
            self.advanced_frame.pack_forget()

    def add_folder(self):
        folder = filedialog.askdirectory(title="Choose source folder")
        if folder:
            self.add_source(folder)

    def add_files(self):
        files = filedialog.askopenfilenames(title="Choose source file(s)")
        for file in files:
            self.add_source(file)

    def drop_sources(self, event):
        """
        Handle files/folders dropped from Windows Explorer into the Sources list.
        Requires tkinterdnd2.
        """
        dropped_items = self.root.tk.splitlist(event.data)

        for item in dropped_items:
            path = os.path.normpath(item)

            if os.path.exists(path):
                self.add_source(path)
            else:
                self.log(f"[SKIPPED] Dropped path does not exist: {path}")

    def add_source(self, path):
        path = os.path.normpath(path)

        if path not in self.sources:
            self.sources.append(path)
            self.refresh_source_tree()

    def remove_selected(self):
        selected_items = self.source_tree.selection()

        if not selected_items:
            return

        selected_indexes = sorted(
            [self.source_tree.index(item) for item in selected_items],
            reverse=True,
        )

        for index in selected_indexes:
            del self.sources[index]

        self.refresh_source_tree()
            
    def move_selected_up(self):
        selected_items = list(self.source_tree.selection())

        if not selected_items:
            return

        selected_indexes = sorted(
            [self.source_tree.index(item) for item in selected_items]
        )

        for index in selected_indexes:
            if index == 0:
                continue

            self.sources[index - 1], self.sources[index] = (
                self.sources[index],
                self.sources[index - 1],
            )

        new_indexes = [
            index - 1 if index > 0 else index
            for index in selected_indexes
        ]

        self.refresh_source_tree()
        self.select_source_indexes(new_indexes)

    def move_selected_down(self):
        selected_items = list(self.source_tree.selection())

        if not selected_items:
            return

        selected_indexes = sorted(
            [self.source_tree.index(item) for item in selected_items],
            reverse=True,
        )

        for index in selected_indexes:
            if index >= len(self.sources) - 1:
                continue

            self.sources[index + 1], self.sources[index] = (
                self.sources[index],
                self.sources[index + 1],
            )

        new_indexes = [
            index + 1 if index < len(self.sources) - 1 else index
            for index in reversed(selected_indexes)
        ]

        self.refresh_source_tree()
        self.select_source_indexes(new_indexes)

    def refresh_source_tree(self):
        for item in self.source_tree.get_children():
            self.source_tree.delete(item)

        for index, source in enumerate(self.sources, start=1):
            if os.path.isdir(source):
                source_type = "Folder"
            elif os.path.isfile(source):
                source_type = "File"
            else:
                source_type = "Missing"

            self.source_tree.insert(
                "",
                tk.END,
                values=(index, source, source_type),
            )

    def select_source_indexes(self, indexes):
        all_items = self.source_tree.get_children()

        self.source_tree.selection_remove(self.source_tree.selection())

        for index in indexes:
            if 0 <= index < len(all_items):
                item = all_items[index]
                self.source_tree.selection_add(item)
                self.source_tree.focus(item)
                self.source_tree.see(item)

    def source_drag_start(self, event):
        item = self.source_tree.identify_row(event.y)

        if not item:
            self.source_drag_item = None
            self.source_drag_index = None
            return

        self.source_drag_item = item
        self.source_drag_index = self.source_tree.index(item)

    def source_drag_motion(self, event):
        item = self.source_tree.identify_row(event.y)

        if item:
            self.source_tree.selection_set(item)
            self.source_tree.focus(item)

    def source_drag_drop(self, event):
        if self.source_drag_item is None or self.source_drag_index is None:
            return

        target_item = self.source_tree.identify_row(event.y)

        if not target_item:
            self.source_drag_item = None
            self.source_drag_index = None
            return

        old_index = self.source_drag_index
        new_index = self.source_tree.index(target_item)

        if old_index == new_index:
            self.source_drag_item = None
            self.source_drag_index = None
            return

        source = self.sources.pop(old_index)
        self.sources.insert(new_index, source)

        self.refresh_source_tree()
        self.select_source_indexes([new_index])

        self.source_drag_item = None
        self.source_drag_index = None

    def clear_sources(self):
        self.sources.clear()
        self.refresh_source_tree()

        self.target_folder.set("")

    def choose_target(self):
        folder = filedialog.askdirectory(title="Choose target folder")
        if folder:
            self.target_folder.set(os.path.normpath(folder))

    def choose_local_log_folder(self):
        folder = filedialog.askdirectory(title="Choose local log folder")
        if folder:
            self.local_log_folder.set(os.path.normpath(folder))

    def log(self, text=""):
        self.output.insert(tk.END, text + "\n")
        self.output.see(tk.END)
        self.root.update_idletasks()

    def log_summary_line(self, job, status, status_color_tag, status_text, exit_text):
        source_path = Path(job["source"])
        source_name = source_path.name

        if source_path.is_dir():
            source_name += "\\"

        line = (
            f'{job["job_no"]:>2}. '
            f'{status:<8} '
            f'{status_text:<45} '
            f'{exit_text}'
            f'{self.format_duration(job["duration_seconds"])}   '
            f'{source_name}'
        )

        self.summary_lines.append(line)
        self.output.insert(tk.END, line + "\n", status_color_tag)
        self.output.see(tk.END)
        self.root.update_idletasks()

    def parse_options(self, text):
        if not text.strip():
            return []
        return shlex.split(text, posix=False)

    def timestamp(self):
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def robocopy_options(self):
        opts = []

        if self.use_mir.get():
            opts.append("/MIR")
        elif self.use_e.get():
            opts.append("/E")

        if self.use_np.get():
            opts.append("/NP")

        if self.use_tee.get():
            opts.append("/TEE")

        if self.use_j.get():
            opts.append("/J")

        if self.use_z.get():
            opts.append("/Z")

        opts.append(f"/R:{self.retry_count.get()}")
        opts.append(f"/W:{self.wait_seconds.get()}")

        mt = self.mt_count.get().strip()
        if mt:
            opts.append(f"/MT:{mt}")

        if self.dry_run.get():
            opts.append("/L")

        excludes = self.parse_options(self.exclude_dirs.get())
        if excludes:
            opts.append("/XD")
            opts.extend(excludes)

        opts.extend(self.parse_options(self.extra_options.get()))

        return opts

    def get_log_file(self, source_path, target_path):
        name = self.job_name.get().strip() or "robocopy-job"

        if self.dry_run.get():
            name += "_nocopy"

        if self.use_timestamp.get():
            name += "_" + self.timestamp()

        filename = name + ".log"

        location = self.log_location.get()

        if location == "source":
            folder = source_path if source_path.is_dir() else source_path.parent
        elif location == "target":
            folder = target_path
        else:
            folder = Path(self.local_log_folder.get())

        folder.mkdir(parents=True, exist_ok=True)
        return folder / filename

    def build_command(self, source):
        source_path = Path(source)
        target_root = Path(self.target_folder.get())

        if source_path.is_dir():
            # Robocopy copies the CONTENTS of a source directory into its
            # destination directory. Never append the source folder name:
            # this also handles drive roots such as D:\\ -> E:\\.
            robocopy_source = source_path
            robocopy_target = target_root
            filename = None
        else:
            robocopy_source = source_path.parent
            robocopy_target = target_root
            filename = source_path.name

        # robocopy_target.mkdir(parents=True, exist_ok=True)

        log_file = self.get_log_file(source_path, robocopy_target)

        command = ["robocopy", str(robocopy_source), str(robocopy_target)]

        if filename:
            command.append(filename)

        command.extend(self.robocopy_options())
        command.append(f"/LOG:{log_file}")

        return command, log_file

    def format_command(self, command):
        return " ".join(f'"{x}"' if " " in x else x for x in command)

    def start_jobs(self):
        if not self.sources:
            messagebox.showerror("Missing source", "Add at least one source folder or file.")
            return

        if not self.target_folder.get().strip():
            messagebox.showerror("Missing target", "Choose target folder.")
            return

        if self.use_mir.get():
            ok = messagebox.askyesno(
                "Confirm /MIR",
                "/MIR can DELETE files and folders in the target that do not exist in the source.\n\nContinue?"
            )
            if not ok:
                return

        if self.use_j.get() and self.use_z.get():
            ok = messagebox.askyesno(
                "Confirm /J and /Z",
                "You selected both /J and /Z.\n\nUsually you should use one or the other.\n\nContinue anyway?"
            )
            if not ok:
                return

        self.save_settings()
        self.save_last_job()

        self.cancel_requested = False
        self.job_results = []
        self.summary_lines = []
        self.start_button.config(state="disabled")
        self.cancel_button.config(state="normal")
        self.progress.config(mode="indeterminate")
        self.progress["value"] = 0
        self.progress.start(35)
        self.status.set("Running")
        self.output.delete("1.0", tk.END)

        threading.Thread(target=self.run_jobs, daemon=True).start()

    def format_duration(self, seconds):
        seconds = int(seconds)
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60

        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def run_jobs(self):
        try:
            self.log(f"Robocopy Replicator v{APP_VERSION}")
            self.log("=" * 90)

            total = len(self.sources)

            for index, source in enumerate(self.sources, start=1):
                if self.cancel_requested:
                    self.log("[CANCELLED] Job cancelled before next source.")
                    break

                source_path = Path(source)

                if not source_path.exists():
                    self.log(f"[SKIPPED] Source does not exist: {source}")
                    continue

                self.progress_text.set(f"Running job {index} of {total}: {source_path.name}")

                job_start_time = time.time()
                command, log_file = self.build_command(source)

                self.log()
                self.log("=" * 90)
                self.log(f"Job {index} of {total}")
                self.log(f"Source: {source_path}")
                self.log(f"Log file: {log_file}")
                self.log("Command:")
                self.log(self.format_command(command))
                self.log()

                self.current_process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )

                for line in self.current_process.stdout:
                    self.log(line.rstrip())
                    if self.cancel_requested:
                        self.current_process.terminate()
                        self.log("[CANCELLED] Robocopy process terminated.")
                        break

                self.current_process.wait()
                code = self.current_process.returncode
                duration_seconds = int(time.time() - job_start_time)

                self.job_results.append({
                    "job_no": index,
                    "source": str(source_path),
                    "exit_code": code,
                    "duration_seconds": duration_seconds,
                    "log_file": str(log_file),
                })

                self.log()
                self.log(f"Robocopy exit code: {code}")

                if self.cancel_requested:
                    self.log("[CANCELLED] Job stopped by user.")
                    break

                if code <= ROBOCOPY_OK_MAX:
                    self.log("[OK] Finished without fatal robocopy error.")
                else:
                    self.log("[ERROR] Robocopy reported failure.")

            self.log()

            self.print_final_summary()
            self.write_summary_log_file()

            self.log()
            self.log("All jobs finished.")
            self.status.set("Finished")

        except Exception as e:
            self.log(f"[PROGRAM ERROR] {e}")
            self.status.set("Program error")
            messagebox.showerror("Program error", str(e))

        finally:
            self.current_process = None
            self.progress.stop()
            self.progress.config(mode="determinate")
            self.progress["value"] = 0
            self.progress_text.set("No job running")
            self.start_button.config(state="normal")
            self.cancel_button.config(state="disabled")

    def robocopy_status_text(self, exit_code):
        if exit_code == 0:
            return "No changes"
        if exit_code == 1:
            return "Files copied"
        if exit_code == 2:
            return "No changes (destination has extra items)"
        if exit_code == 3:
            return "Files copied (destination has extra items)"
        if exit_code == 4:
            return "Differences detected"
        if exit_code == 5:
            return "Files copied (differences detected)"
        if exit_code == 6:
            return "No changes (extra items + differences)"
        if exit_code == 7:
            return "Files copied (extra items + differences)"
        return "Copy failed"

    def robocopy_status_tag(self, exit_code):
        if exit_code <= 1:
            return "[OK]"
        if 2 <= exit_code <= 7:
            return "[INFO]"
        return "[ERROR]"

    def robocopy_status_color_tag(self, exit_code):
        if exit_code <= 1:
            return "summary_ok"
        if 2 <= exit_code <= 7:
            return "summary_info"
        return "summary_error"

    def robocopy_status_icon(self, exit_code):
        if exit_code <= 1:
            return "✔"
        if 2 <= exit_code <= 7:
            return "ℹ"
        return "✖"

    def get_summary_log_file(self):
        name = self.job_name.get().strip() or "robocopy-job"

        if self.dry_run.get():
            name += "_nocopy"

        if self.use_timestamp.get():
            name += "_" + self.timestamp()

        filename = name + "_summary.log"

        if self.log_location.get() == "target":
            folder = Path(self.target_folder.get())
        elif self.log_location.get() == "source" and self.sources:
            first_source = Path(self.sources[0])
            folder = first_source if first_source.is_dir() else first_source.parent
        else:
            folder = Path(self.local_log_folder.get())

        folder.mkdir(parents=True, exist_ok=True)
        return folder / filename
        
    def summary_log(self, text=""):
        self.summary_lines.append(text)
        self.log(text)

    def print_final_summary(self):
        self.summary_log("=" * 90)
        self.summary_log("JOB LIST")
        self.summary_log("=" * 90)
        self.summary_log(f"Target: {self.target_folder.get()}")
        self.summary_log("")

        for job in self.job_results:
            source_path = Path(job["source"])
            source_text = str(source_path)

            if source_path.is_dir():
                source_text += "\\"

            self.summary_log(f'{job["job_no"]:>2}. {source_text}')

        self.summary_log("")

        self.summary_log("=" * 90)
        self.summary_log("FINAL JOB SUMMARY")
        self.summary_log("=" * 90)

        ok_jobs = 0
        failed_jobs = 0
        total_seconds = 0

        if not self.job_results:
            self.summary_log("No job results recorded.")
            self.summary_log("=" * 90)
            return

        for job in self.job_results:
            exit_code = job["exit_code"]

            if exit_code <= ROBOCOPY_OK_MAX:
                ok_jobs += 1
            else:
                failed_jobs += 1

            total_seconds += job["duration_seconds"]

            if self.summary_format.get() == "icons":
                status = self.robocopy_status_icon(exit_code)
            else:
                status = self.robocopy_status_tag(exit_code)

            exit_text = ""
            if self.show_exit_code.get():
                exit_text = f"Exit {exit_code:<2} "

            self.log_summary_line(
                job=job,
                status=status,
                status_color_tag=self.robocopy_status_color_tag(exit_code),
                status_text=self.robocopy_status_text(exit_code),
                exit_text=exit_text,
            )

        self.summary_log("-" * 90)
        self.summary_log(f"Jobs          : {len(self.job_results)}")
        self.summary_log(f"Successful    : {ok_jobs}")
        self.summary_log(f"Failed        : {failed_jobs}")
        self.summary_log(f"Total runtime : {self.format_duration(total_seconds)}")
        self.summary_log("=" * 90)

    def write_summary_log_file(self):
        try:
            summary_file = self.get_summary_log_file()

            summary_file.write_text(
                "\n".join(self.summary_lines) + "\n",
                encoding="utf-8",
            )

            self.log()
            self.log(f"Summary log file: {summary_file}")

        except Exception as e:
            self.log(f"[WARNING] Could not write summary log file: {e}")

    def cancel_job(self):
        self.cancel_requested = True
        self.status.set("Cancelling...")
        if self.current_process:
            try:
                self.current_process.terminate()
            except Exception:
                pass

    def show_command_preview(self):
        preview = self.generate_preview()
        if preview:
            win = tk.Toplevel(self.root)
            win.title("Robocopy command preview")
            win.geometry("900x500")

            text = scrolledtext.ScrolledText(win)
            text.pack(fill="both", expand=True, padx=10, pady=10)
            text.insert(tk.END, preview)
            text.config(state="disabled")

    def copy_command_preview(self):
        preview = self.generate_preview()
        if preview:
            self.root.clipboard_clear()
            self.root.clipboard_append(preview)
            messagebox.showinfo("Copied", "Command preview copied to clipboard.")

    def generate_preview(self):
        if not self.sources:
            messagebox.showinfo("No source", "Add a source first.")
            return ""

        if not self.target_folder.get().strip():
            messagebox.showinfo("No target", "Choose target first.")
            return ""

        lines = []

        for source in self.sources:
            command, log_file = self.build_command(source)
            lines.append("=" * 90)
            lines.append(f"Source: {source}")
            lines.append(f"Log: {log_file}")
            lines.append(self.format_command(command))
            lines.append("")

        return "\n".join(lines)

    def get_config(self):
        return {
            # "sources": self.sources,
            "target_folder": self.target_folder.get(),
            "job_name": self.job_name.get(),
            "dry_run": self.dry_run.get(),
            "use_timestamp": self.use_timestamp.get(),
            "show_advanced": self.show_advanced.get(),
            "use_e": self.use_e.get(),
            "use_np": self.use_np.get(),
            "use_tee": self.use_tee.get(),
            "use_j": self.use_j.get(),
            "use_z": self.use_z.get(),
            "use_mir": self.use_mir.get(),
            "retry_count": self.retry_count.get(),
            "wait_seconds": self.wait_seconds.get(),
            "mt_count": self.mt_count.get(),
            "extra_options": self.extra_options.get(),
            "exclude_dirs": self.exclude_dirs.get(),
            "log_location": self.log_location.get(),
            "local_log_folder": self.local_log_folder.get(),
            "geometry": self.root.geometry(),
            "source_splitter": self.content_pane.sashpos(0),
            "summary_format": self.summary_format.get(),
            "show_exit_code": self.show_exit_code.get(),
        }

    def save_last_job(self):
        try:
            data = {
                "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "sources": self.sources,
                "target_folder": self.target_folder.get(),
                "job_name": self.job_name.get(),
            }

            LAST_JOB_FILE.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as e:
            self.log(f"[WARNING] Could not save last job: {e}")

    def restore_last_job(self):
        if not LAST_JOB_FILE.exists():
            messagebox.showinfo("No last job", "No last job has been saved yet.")
            return

        try:
            data = json.loads(LAST_JOB_FILE.read_text(encoding="utf-8"))

            self.sources = data.get("sources", [])
            self.target_folder.set(data.get("target_folder", ""))
            self.job_name.set(data.get("job_name", self.job_name.get()))

            self.refresh_source_tree()

            saved_at = data.get("saved_at", "unknown time")
            messagebox.showinfo("Last job restored", f"Last job restored from {saved_at}.")

        except Exception as e:
            messagebox.showerror("Restore failed", str(e))

    def save_job(self):
        if not self.sources:
            messagebox.showinfo("No sources", "Add at least one source before saving a job.")
            return

        JOBS_DIR.mkdir(exist_ok=True)

        filename = filedialog.asksaveasfilename(
            title="Save job",
            initialdir=JOBS_DIR,
            defaultextension=".json",
            filetypes=[("JSON job", "*.json")],
        )

        if not filename:
            return

        data = {
            "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "sources": self.sources,
            "target_folder": self.target_folder.get(),
            "job_name": self.job_name.get(),
        }

        Path(filename).write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        messagebox.showinfo("Job saved", "Job saved.")

    def load_job(self):
        JOBS_DIR.mkdir(exist_ok=True)

        filename = filedialog.askopenfilename(
            title="Load job",
            initialdir=JOBS_DIR,
            filetypes=[("JSON job", "*.json")],
        )

        if not filename:
            return

        data = json.loads(Path(filename).read_text(encoding="utf-8"))

        self.sources = data.get("sources", [])
        self.target_folder.set(data.get("target_folder", ""))
        self.job_name.set(data.get("job_name", self.job_name.get()))

        self.refresh_source_tree()

        saved_at = data.get("saved_at", "unknown time")
        messagebox.showinfo("Job loaded", f"Job loaded from {saved_at}.")

    def apply_config(self, cfg):
        # self.sources = cfg.get("sources", [])
        self.sources = []
        self.refresh_source_tree()

        self.target_folder.set(cfg.get("target_folder", ""))
        self.job_name.set(cfg.get("job_name", "robocopy-job"))
        self.dry_run.set(cfg.get("dry_run", False))
        self.use_timestamp.set(cfg.get("use_timestamp", True))
        self.show_advanced.set(cfg.get("show_advanced", False))

        self.summary_format.set(cfg.get("summary_format", "ascii"))
        self.show_exit_code.set(cfg.get("show_exit_code", False))

        self.use_e.set(cfg.get("use_e", True))
        self.use_np.set(cfg.get("use_np", True))
        self.use_tee.set(cfg.get("use_tee", True))
        self.use_j.set(cfg.get("use_j", True))
        self.use_z.set(cfg.get("use_z", False))
        self.use_mir.set(cfg.get("use_mir", False))

        self.retry_count.set(cfg.get("retry_count", 3))
        self.wait_seconds.set(cfg.get("wait_seconds", 5))
        self.mt_count.set(cfg.get("mt_count", ""))
        self.extra_options.set(cfg.get("extra_options", ""))
        self.exclude_dirs.set(cfg.get("exclude_dirs", '$RECYCLE.BIN Dropbox "System Volume Information"'))

        self.log_location.set(cfg.get("log_location", "local"))
        self.local_log_folder.set(cfg.get("local_log_folder", str(APP_DIR / "robocopy_log")))

        geometry = cfg.get("geometry")
        if geometry:
            try:
                # Keep saved dimensions within the current display's usable area.
                import re
                match = re.match(r"^(\d+)x(\d+)", geometry)
                if match:
                    width = min(int(match.group(1)), self.root.winfo_screenwidth())
                    height = min(int(match.group(2)), max(350, self.root.winfo_screenheight() - 100))
                    self.root.geometry(f"{width}x{height}+0+0")
            except Exception:
                pass

        self.toggle_advanced()
        splitter = cfg.get("source_splitter", 330)

        self.root.after(
            100,
            lambda: self.content_pane.sashpos(0, splitter)
        )

    def save_settings(self):
        try:
            SETTINGS_FILE.write_text(
                json.dumps(self.get_config(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            pass

    def load_settings(self):
        if SETTINGS_FILE.exists():
            try:
                cfg = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
                self.apply_config(cfg)
            except Exception:
                pass

    def save_profile(self):
        PROFILES_DIR.mkdir(exist_ok=True)

        filename = filedialog.asksaveasfilename(
            title="Save profile",
            initialdir=PROFILES_DIR,
            defaultextension=".json",
            filetypes=[("JSON profile", "*.json")],
        )

        if not filename:
            return

        Path(filename).write_text(
            json.dumps(self.get_config(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        messagebox.showinfo("Profile saved", "Profile saved.")

    def load_profile(self):
        PROFILES_DIR.mkdir(exist_ok=True)

        filename = filedialog.askopenfilename(
            title="Load profile",
            initialdir=PROFILES_DIR,
            filetypes=[("JSON profile", "*.json")],
        )

        if not filename:
            return

        cfg = json.loads(Path(filename).read_text(encoding="utf-8"))
        self.apply_config(cfg)
        messagebox.showinfo("Profile loaded", "Profile loaded.")

    def on_close(self):
        if self.current_process:
            ok = messagebox.askyesno(
                "Job running",
                "A robocopy job is running. Cancel it and exit?"
            )
            if not ok:
                return
            self.cancel_job()

        self.save_settings()
        self.root.destroy()


if __name__ == "__main__":
    if DND_AVAILABLE:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
        
    app = RobocopyReplicator(root)
    root.mainloop()