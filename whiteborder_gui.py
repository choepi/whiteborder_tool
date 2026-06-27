"""
whiteborder_gui — graphical interface for the White Border Tool.

Run with: python whiteborder_gui.py
Requires: Pillow (and optionally exifread) — no extra GUI dependencies.
"""

import queue
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import whiteborder as wb

_BRANDS = list(wb.SUPPORTED_BRANDS.keys())
_BRAND_LABELS = {k: v[0] for k, v in wb.SUPPORTED_BRANDS.items()}


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("White Border Tool")
        self.resizable(False, False)
        self._queue = queue.Queue()

        self._input = tk.StringVar(value=str(Path.cwd() / "input"))
        self._output = tk.StringVar(value=str(Path.cwd() / "output"))
        self._size = tk.IntVar(value=2160)
        self._show_brand = tk.BooleanVar(value=True)
        self._brand_vars = {b: tk.BooleanVar(value=True) for b in _BRANDS}

        self._apply_theme()
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _apply_theme(self):
        style = ttk.Style(self)
        if sys.platform == "win32":
            try:
                style.theme_use("vista")
            except tk.TclError:
                style.theme_use("winnative")
        elif sys.platform == "linux":
            style.theme_use("clam")

    def _build_ui(self):
        p = {"padx": 10, "pady": 5}
        f = ttk.Frame(self, padding=18)
        f.grid(sticky="nsew")

        # ── folders ───────────────────────────────────────────────────────
        ttk.Label(f, text="Input folder").grid(row=0, column=0, sticky="w", **p)
        ttk.Entry(f, textvariable=self._input, width=46).grid(row=0, column=1, **p)
        ttk.Button(f, text="Browse…", command=self._pick_input).grid(row=0, column=2, **p)

        ttk.Label(f, text="Output folder").grid(row=1, column=0, sticky="w", **p)
        ttk.Entry(f, textvariable=self._output, width=46).grid(row=1, column=1, **p)
        ttk.Button(f, text="Browse…", command=self._pick_output).grid(row=1, column=2, **p)

        ttk.Separator(f, orient="horizontal").grid(
            row=2, column=0, columnspan=3, sticky="ew", pady=10
        )

        # ── output size ───────────────────────────────────────────────────
        ttk.Label(f, text="Output size").grid(row=3, column=0, sticky="w", **p)
        size_row = ttk.Frame(f)
        size_row.grid(row=3, column=1, sticky="w", **p)
        for label, val in (("1080 px", 1080), ("2160 px", 2160)):
            ttk.Radiobutton(size_row, text=label, variable=self._size, value=val).pack(
                side="left", padx=10
            )

        ttk.Separator(f, orient="horizontal").grid(
            row=4, column=0, columnspan=3, sticky="ew", pady=10
        )

        # ── brand marks ───────────────────────────────────────────────────
        brand_header = ttk.Frame(f)
        brand_header.grid(row=5, column=0, columnspan=3, sticky="w", **p)
        ttk.Checkbutton(
            brand_header,
            text="Show brand marks",
            variable=self._show_brand,
            command=self._toggle_brands,
        ).pack(side="left")

        brand_row = ttk.Frame(f)
        brand_row.grid(row=6, column=0, columnspan=3, sticky="w", padx=22, pady=2)
        self._brand_checks = {}
        for b in _BRANDS:
            cb = ttk.Checkbutton(brand_row, text=_BRAND_LABELS[b], variable=self._brand_vars[b])
            cb.pack(side="left", padx=6)
            self._brand_checks[b] = cb

        ttk.Separator(f, orient="horizontal").grid(
            row=7, column=0, columnspan=3, sticky="ew", pady=10
        )

        # ── run button ────────────────────────────────────────────────────
        self._run_btn = ttk.Button(f, text="Process Images", command=self._run)
        self._run_btn.grid(row=8, column=0, columnspan=3, pady=6, ipadx=20)

        # ── progress ──────────────────────────────────────────────────────
        self._progress = ttk.Progressbar(f, length=540, mode="determinate")
        self._progress.grid(row=9, column=0, columnspan=3, padx=10, pady=4)

        # ── log ───────────────────────────────────────────────────────────
        log_frame = ttk.Frame(f)
        log_frame.grid(row=10, column=0, columnspan=3, sticky="nsew", padx=10, pady=6)

        self._log_box = tk.Text(
            log_frame, height=10, width=70, state="disabled",
            wrap="word", font=("Courier", 10),
        )
        scroll = ttk.Scrollbar(log_frame, command=self._log_box.yview)
        self._log_box.configure(yscrollcommand=scroll.set)
        self._log_box.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

    # ── folder pickers ────────────────────────────────────────────────────────
    def _pick_input(self):
        d = filedialog.askdirectory(title="Select input folder", initialdir=self._input.get())
        if d:
            self._input.set(d)

    def _pick_output(self):
        d = filedialog.askdirectory(title="Select output folder", initialdir=self._output.get())
        if d:
            self._output.set(d)

    def _toggle_brands(self):
        state = "normal" if self._show_brand.get() else "disabled"
        for cb in self._brand_checks.values():
            cb.configure(state=state)

    # ── processing ────────────────────────────────────────────────────────────
    def _run(self):
        input_dir = self._input.get().strip()
        output_dir = self._output.get().strip()

        if not input_dir or not Path(input_dir).is_dir():
            messagebox.showerror("Input error", f"Folder not found:\n{input_dir}")
            return

        enabled = None
        if self._show_brand.get():
            enabled = {b for b, v in self._brand_vars.items() if v.get()}

        self._log_clear()
        self._progress["value"] = 0
        self._run_btn.configure(state="disabled")

        threading.Thread(
            target=self._worker,
            args=(input_dir, output_dir, self._size.get(), self._show_brand.get(), enabled),
            daemon=True,
        ).start()
        self.after(100, self._poll)

    def _worker(self, input_dir, output_dir, size, show_brand, enabled):
        try:
            wb.process_folder(
                input_dir,
                output_dir,
                output_side=size,
                show_brand_mark=show_brand,
                enabled_brands=enabled,
                progress_callback=lambda cur, tot: self._queue.put(("progress", cur, tot)),
                log_callback=lambda msg: self._queue.put(("log", msg)),
            )
            self._queue.put(("done", None))
        except Exception as exc:
            self._queue.put(("error", str(exc)))

    def _poll(self):
        try:
            while True:
                item = self._queue.get_nowait()
                kind = item[0]
                if kind == "log":
                    self._log_append(item[1])
                elif kind == "progress":
                    _, cur, tot = item
                    self._progress["maximum"] = tot
                    self._progress["value"] = cur
                elif kind == "done":
                    self._run_btn.configure(state="normal")
                    return
                elif kind == "error":
                    self._log_append(f"Error: {item[1]}")
                    messagebox.showerror("Error", item[1])
                    self._run_btn.configure(state="normal")
                    return
        except queue.Empty:
            pass
        self.after(100, self._poll)

    # ── log helpers ───────────────────────────────────────────────────────────
    def _log_append(self, msg):
        self._log_box.configure(state="normal")
        self._log_box.insert("end", msg + "\n")
        self._log_box.see("end")
        self._log_box.configure(state="disabled")

    def _log_clear(self):
        self._log_box.configure(state="normal")
        self._log_box.delete("1.0", "end")
        self._log_box.configure(state="disabled")


if __name__ == "__main__":
    App().mainloop()
