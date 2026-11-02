import os
import sys
import re
import ctypes
import threading
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# ── Admin ──────────────────────────────────────────────────────────────────────
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False

def run_as_admin():
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)

# ── 7-Zip: bundled (sama folder exe) → installed ──────────────────────────────
def find_7zip():
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(sys.argv[0])))
    bundled = os.path.join(base, "7z.exe")
    if os.path.exists(bundled):
        return bundled
    for p in [r"C:\Program Files\7-Zip\7z.exe", r"C:\Program Files (x86)\7-Zip\7z.exe"]:
        if os.path.exists(p):
            return p
    try:
        r = subprocess.run(["where", "7z"], capture_output=True, text=True)
        if r.returncode == 0:
            return r.stdout.strip().splitlines()[0]
    except Exception:
        pass
    return None

# ── App ────────────────────────────────────────────────────────────────────────
class SymlinkMoverApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Storage Optimizer Pro — Batch")
        self.root.geometry("620x480")
        self.root.resizable(False, False)
        self.root.configure(bg="#F3F3F3")
        self.target_path = tk.StringVar()
        self.use_compress = tk.BooleanVar(value=True)
        self.sevenzip = find_7zip()
        self.queue = []
        self.running = False
        self.setup_ui()

    def setup_ui(self):
        f = tk.Frame(self.root, bg="#F3F3F3", padx=20, pady=16)
        f.pack(fill=tk.BOTH, expand=True)

        # Target
        tk.Label(f, text="Drive/Folder Tujuan (USB):", font=("Segoe UI", 10, "bold"), bg="#F3F3F3").pack(anchor=tk.W)
        trow = tk.Frame(f, bg="#F3F3F3")
        trow.pack(fill=tk.X, pady=(4, 12))
        tk.Entry(trow, textvariable=self.target_path, state="readonly", font=("Segoe UI", 10)).pack(
            side=tk.LEFT, fill=tk.X, expand=True, ipady=4, padx=(0, 10))
        tk.Button(trow, text="Browse", command=self.browse_target, font=("Segoe UI", 9),
                  relief=tk.GROOVE, cursor="hand2").pack(side=tk.RIGHT, ipadx=10)

        # Queue list
        tk.Label(f, text="Antrian Folder:", font=("Segoe UI", 10, "bold"), bg="#F3F3F3").pack(anchor=tk.W)
        list_frame = tk.Frame(f, bg="#F3F3F3")
        list_frame.pack(fill=tk.X, pady=(4, 4))
        self.listbox = tk.Listbox(list_frame, font=("Segoe UI", 9), height=8,
                                  selectmode=tk.EXTENDED, relief=tk.GROOVE,
                                  activestyle="none", bg="white", fg="#222222")
        self.listbox.pack(side=tk.LEFT, fill=tk.X, expand=True)
        sb = tk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.listbox.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.config(yscrollcommand=sb.set)

        # Queue buttons
        btn_row = tk.Frame(f, bg="#F3F3F3")
        btn_row.pack(fill=tk.X, pady=(4, 4))
        tk.Button(btn_row, text="+ Tambah Folder", command=self.add_folders,
                  font=("Segoe UI", 9), relief=tk.GROOVE, cursor="hand2", bg="#E8F0FE").pack(side=tk.LEFT, ipadx=10, padx=(0, 6))
        tk.Button(btn_row, text="✕ Hapus Dipilih", command=self.remove_selected,
                  font=("Segoe UI", 9), relief=tk.GROOVE, cursor="hand2").pack(side=tk.LEFT, ipadx=10, padx=(0, 6))
        tk.Button(btn_row, text="Bersihkan Semua", command=self.clear_queue,
                  font=("Segoe UI", 9), relief=tk.GROOVE, cursor="hand2").pack(side=tk.LEFT, ipadx=10)

        self.queue_label = tk.Label(f, text="0 folder dalam antrian", font=("Segoe UI", 8),
                                    fg="#888888", bg="#F3F3F3")
        self.queue_label.pack(anchor=tk.E, pady=(2, 6))

        # Compress toggle
        cf = tk.Frame(f, bg="#F3F3F3")
        cf.pack(fill=tk.X, pady=(0, 8))
        self.compress_check = tk.Checkbutton(
            cf, text="Compress dulu (7-Zip) → lebih cepat untuk USB",
            variable=self.use_compress, bg="#F3F3F3", font=("Segoe UI", 9),
            state=tk.NORMAL if self.sevenzip else tk.DISABLED
        )
        self.compress_check.pack(side=tk.LEFT)
        if not self.sevenzip:
            tk.Label(cf, text="⚠ 7z.exe tidak ditemukan — taruh di folder yang sama dengan .exe",
                     fg="#CC4400", bg="#F3F3F3", font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=8)

        # Progress
        self.progress_label = tk.Label(f, text="", font=("Segoe UI", 9), bg="#F3F3F3", fg="#444444")
        self.progress_label.pack(anchor=tk.W)
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(f, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=(2, 12))

        self.process_btn = tk.Button(f, text="Proses Semua Antrian", command=self.start_batch,
                                     font=("Segoe UI", 11, "bold"), bg="#005A9E", fg="white",
                                     relief=tk.FLAT, cursor="hand2", pady=8)
        self.process_btn.pack(fill=tk.X)

    # ── Queue ──────────────────────────────────────────────────────────────────
    def add_folders(self):
        while True:
            p = filedialog.askdirectory(
                title=f"Pilih folder ({len(self.queue)} dipilih) — Cancel jika sudah selesai"
            )
            if not p:
                break
            norm = os.path.normpath(p)
            if norm not in self.queue:
                self.queue.append(norm)
                display = norm
                self.listbox.insert(tk.END, display)
                if os.path.isdir(os.path.join(norm, "node_modules")):
                    self.listbox.itemconfig(tk.END, fg="#CC6600")
        self._update_counter()

    def remove_selected(self):
        for i in reversed(self.listbox.curselection()):
            self.listbox.delete(i)
            self.queue.pop(i)
        self._update_counter()

    def clear_queue(self):
        self.queue.clear()
        self.listbox.delete(0, tk.END)
        self._update_counter()

    def _update_counter(self):
        self.queue_label.config(text=f"{len(self.queue)} folder dalam antrian")

    def browse_target(self):
        p = filedialog.askdirectory(title="Pilih Lokasi Tujuan (USB)")
        if p:
            self.target_path.set(p)

    # ── Batch start ────────────────────────────────────────────────────────────
    def start_batch(self):
        if self.running:
            return
        if not self.queue:
            messagebox.showwarning("Kosong", "Tidak ada folder dalam antrian.")
            return
        if not self.target_path.get():
            messagebox.showwarning("Peringatan", "Pilih folder tujuan terlebih dahulu.")
            return

        nm_folders = [q for q in self.queue if os.path.isdir(os.path.join(q, "node_modules"))]
        if nm_folders and self.use_compress.get():
            names = "\n".join(f"  • {os.path.basename(p)}" for p in nm_folders)
            if not messagebox.askyesno(
                "node_modules Terdeteksi",
                f"Folder berikut mengandung node_modules:\n{names}\n\n"
                "⚠ Disarankan skip compress untuk folder ini (binary tidak mengecil).\n\n"
                "Lanjut dengan compress tetap aktif?",
                icon="warning"
            ):
                return

        self.running = True
        self.process_btn.config(state=tk.DISABLED, bg="#666666", text="Memproses...")
        self.progress_var.set(0)
        threading.Thread(target=self.run_batch, daemon=True).start()

    # ── Batch runner ───────────────────────────────────────────────────────────
    def run_batch(self):
        total = len(self.queue)
        target_norm = os.path.normpath(self.target_path.get())
        errors = []

        for idx, source_norm in enumerate(self.queue[:]):
            folder_name = os.path.basename(source_norm)
            final_target = os.path.join(target_norm, folder_name)
            base_pct = idx / total * 100
            slot = 100 / total

            self._set_label(f"[{idx+1}/{total}] {folder_name}")
            self.root.after(0, self.listbox.itemconfig, idx, {"bg": "#FFF8DC"})

            try:
                if source_norm == final_target:
                    raise RuntimeError("Sumber dan tujuan sama")
                if self.use_compress.get() and self.sevenzip:
                    self._process_compressed(source_norm, target_norm, folder_name, final_target, base_pct, slot)
                else:
                    self._process_robocopy(source_norm, final_target, base_pct, slot)
                self.root.after(0, self.listbox.itemconfig, idx, {"bg": "#E8F5E9", "fg": "#2E7D32"})
            except Exception as e:
                errors.append(f"{folder_name}: {e}")
                self.root.after(0, self.listbox.itemconfig, idx, {"bg": "#FFEBEE", "fg": "#C62828"})

        self._set_progress(100)
        if errors:
            self.root.after(0, messagebox.showerror, "Selesai dengan Error",
                            "Selesai, tapi ada error:\n" + "\n".join(errors))
        else:
            self.root.after(0, messagebox.showinfo, "Sukses",
                            f"Semua {total} folder berhasil dipindah & symlink dibuat!")
        self._set_label(f"Selesai — {total} folder diproses")
        self.running = False
        self.root.after(0, self.process_btn.config,
                        {"state": tk.NORMAL, "bg": "#005A9E", "text": "Proses Semua Antrian"})

    # ── Compress mode ──────────────────────────────────────────────────────────
    def _process_compressed(self, source_norm, target_norm, folder_name, final_target, base_pct, slot):
        archive_name = folder_name + ".7z"
        archive_src = os.path.join(os.path.dirname(source_norm), archive_name)
        archive_dst = os.path.join(target_norm, archive_name)

        self._run_7zip(
            [self.sevenzip, "a", "-t7z", archive_src, source_norm, "-mx=1", "-mmt=on", "-bsp1"],
            base_pct, base_pct + slot * 0.45, "Compressing"
        )
        self._set_label(f"Transfer archive {folder_name}...")
        subprocess.run(
            ["robocopy", os.path.dirname(archive_src), target_norm, archive_name, "/MOVE", "/NP", "/NJH", "/NJS"],
            capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW
        )
        self._set_progress(base_pct + slot * 0.65)
        self._run_7zip(
            [self.sevenzip, "x", archive_dst, f"-o{target_norm}", "-bsp1", "-y"],
            base_pct + slot * 0.65, base_pct + slot * 0.90, "Extracting"
        )
        try:
            os.remove(archive_dst)
        except Exception:
            pass
        subprocess.run(["cmd", "/c", "rd", "/s", "/q", source_norm],
                       capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
        self._make_symlink(source_norm, final_target)
        self._set_progress(base_pct + slot)

    def _run_7zip(self, cmd, pct_start, pct_end, label):
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        for line in proc.stdout:
            m = re.search(r"(\d{1,3})%", line)
            if m:
                pct = int(m.group(1))
                self._set_progress(pct_start + (pct_end - pct_start) * pct / 100)
                self._set_label(f"{label}: {pct}%")
        proc.wait()

    # ── Robocopy mode ──────────────────────────────────────────────────────────
    def _process_robocopy(self, source_norm, final_target, base_pct, slot):
        total_files = self._count_files(source_norm)
        copied = 0
        proc = subprocess.Popen(
            ["robocopy", source_norm, final_target, "/E", "/MOVE", "/MT:32", "/NP", "/NDL", "/NJH", "/NJS"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, creationflags=subprocess.CREATE_NO_WINDOW
        )
        for line in proc.stdout:
            if line.strip():
                copied += 1
                self._set_progress(base_pct + min(copied / total_files * slot * 0.95, slot * 0.95))
        proc.wait()
        self._make_symlink(source_norm, final_target)
        self._set_progress(base_pct + slot)

    def _count_files(self, source):
        try:
            r = subprocess.run(
                ["robocopy", source, source, "/L", "/E", "/NP", "/NFL", "/NDL", "/NJH"],
                capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
            for line in r.stdout.splitlines():
                m = re.search(r"Files\s*:\s*(\d+)", line)
                if m:
                    return max(int(m.group(1)), 1)
        except Exception:
            pass
        return 1

    # ── Symlink ────────────────────────────────────────────────────────────────
    def _make_symlink(self, source_norm, final_target):
        mk = subprocess.run(
            ["cmd", "/c", "mklink", "/D", source_norm, final_target],
            capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW
        )
        if mk.returncode != 0:
            raise RuntimeError(f"Symlink gagal: {mk.stderr.strip()}")

    def _set_label(self, text):
        self.root.after(0, self.progress_label.config, {"text": text})

    def _set_progress(self, val):
        self.root.after(0, self.progress_var.set, val)


if __name__ == "__main__":
    if not is_admin():
        run_as_admin()
        sys.exit()
    root = tk.Tk()
    SymlinkMoverApp(root)
    root.mainloop()