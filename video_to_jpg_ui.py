import os
import threading
import queue
import time
from dataclasses import dataclass
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import cv2
from PIL import Image
import piexif


SUPPORTED_VIDEO_HINT = "Alle Formate, die OpenCV lesen kann (z.B. mp4/avi/mkv/...)"

@dataclass
class JobConfig:
    video_path: Path
    out_base_dir: Path
    base_name: str
    target_fps: float
    write_exif: bool


class VideoToJPGApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Video → JPG Extraktion (FPS wählbar)")
        self.geometry("760x420")
        self.minsize(720, 380)

        self._worker_thread = None
        self._cancel_flag = threading.Event()
        self._q = queue.Queue()

        self.video_path_var = tk.StringVar()
        self.out_dir_var = tk.StringVar()
        self.base_name_var = tk.StringVar()
        self.target_fps_var = tk.StringVar(value="10")
        self.native_fps_var = tk.StringVar(value="-")
        self.total_frames_var = tk.StringVar(value="-")
        self.status_var = tk.StringVar(value="Bereit.")
        self.progress_var = tk.StringVar(value="0 von 0 Frames")
        self.write_exif_var = tk.BooleanVar(value=True)

        self._build_ui()
        self.after(100, self._poll_queue)

    def _build_ui(self):
        pad = 10

        frm = ttk.Frame(self, padding=pad)
        frm.pack(fill="both", expand=True)

        # Row 0: Video
        row0 = ttk.Frame(frm)
        row0.pack(fill="x", pady=(0, 8))

        ttk.Label(row0, text="Video:").pack(side="left")
        self.video_entry = ttk.Entry(row0, textvariable=self.video_path_var)
        self.video_entry.pack(side="left", fill="x", expand=True, padx=(8, 8))
        ttk.Button(row0, text="Auswählen…", command=self.pick_video).pack(side="left")

        hint = ttk.Label(frm, text=SUPPORTED_VIDEO_HINT, foreground="#555")
        hint.pack(anchor="w", pady=(0, 12))

        # Row 1: Output directory
        row1 = ttk.Frame(frm)
        row1.pack(fill="x", pady=(0, 8))

        ttk.Label(row1, text="Speicherort (Basisordner):").pack(side="left")
        self.out_entry = ttk.Entry(row1, textvariable=self.out_dir_var)
        self.out_entry.pack(side="left", fill="x", expand=True, padx=(8, 8))
        ttk.Button(row1, text="Ordner wählen…", command=self.pick_out_dir).pack(side="left")

        # Row 2: Base name + FPS
        row2 = ttk.Frame(frm)
        row2.pack(fill="x", pady=(0, 8))

        ttk.Label(row2, text="Bild-Basisname:").pack(side="left")
        base = ttk.Entry(row2, textvariable=self.base_name_var, width=30)
        base.pack(side="left", padx=(8, 18))

        ttk.Label(row2, text="FPS (Ziel):").pack(side="left")
        fps = ttk.Entry(row2, textvariable=self.target_fps_var, width=8)
        fps.pack(side="left", padx=(8, 8))

        ttk.Checkbutton(row2, text="EXIF-Metadaten schreiben", variable=self.write_exif_var).pack(side="left", padx=(12, 0))

        # Row 3: Video info
        row3 = ttk.Frame(frm)
        row3.pack(fill="x", pady=(4, 12))

        ttk.Label(row3, text="Native FPS:").pack(side="left")
        ttk.Label(row3, textvariable=self.native_fps_var, width=10).pack(side="left", padx=(8, 24))

        ttk.Label(row3, text="Total Frames:").pack(side="left")
        ttk.Label(row3, textvariable=self.total_frames_var, width=12).pack(side="left", padx=(8, 24))

        # Progress
        prog_box = ttk.Labelframe(frm, text="Fortschritt", padding=pad)
        prog_box.pack(fill="x", pady=(0, 10))

        self.progressbar = ttk.Progressbar(prog_box, mode="determinate")
        self.progressbar.pack(fill="x", pady=(0, 6))

        info_row = ttk.Frame(prog_box)
        info_row.pack(fill="x")
        ttk.Label(info_row, textvariable=self.progress_var).pack(side="left")
        ttk.Label(info_row, textvariable=self.status_var).pack(side="right")

        # Buttons
        btn_row = ttk.Frame(frm)
        btn_row.pack(fill="x", pady=(8, 0))

        self.start_btn = ttk.Button(btn_row, text="Start", command=self.start)
        self.start_btn.pack(side="left")

        self.cancel_btn = ttk.Button(btn_row, text="Abbrechen", command=self.cancel, state="disabled")
        self.cancel_btn.pack(side="left", padx=(8, 0))

        ttk.Button(btn_row, text="Beenden", command=self.destroy).pack(side="right")

    def pick_video(self):
        path = filedialog.askopenfilename(
            title="Video auswählen",
            filetypes=[("Video (OpenCV)", "*.*")],
        )
        if not path:
            return
        self.video_path_var.set(path)

        p = Path(path)
        # Defaults
        self.out_dir_var.set(str(p.parent))
        self.base_name_var.set(p.stem)

        # Try reading metadata
        self._update_video_info(p)

    def pick_out_dir(self):
        initial = self.out_dir_var.get() or str(Path.home())
        path = filedialog.askdirectory(title="Speicherordner wählen", initialdir=initial)
        if not path:
            return
        self.out_dir_var.set(path)

    def _update_video_info(self, video_path: Path):
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            self.native_fps_var.set("-")
            self.total_frames_var.set("-")
            return
        fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        cap.release()

        self.native_fps_var.set(f"{fps:.3f}" if fps > 0 else "unbekannt")
        self.total_frames_var.set(str(total) if total > 0 else "unbekannt")

    def _validate(self) -> JobConfig | None:
        video = self.video_path_var.get().strip()
        out_dir = self.out_dir_var.get().strip()
        base = self.base_name_var.get().strip()
        fps_s = self.target_fps_var.get().strip()

        if not video:
            messagebox.showerror("Fehler", "Bitte ein Video auswählen.")
            return None
        if not Path(video).exists():
            messagebox.showerror("Fehler", "Video-Pfad existiert nicht.")
            return None
        if not out_dir:
            messagebox.showerror("Fehler", "Bitte einen Speicherort wählen.")
            return None
        if not Path(out_dir).exists():
            messagebox.showerror("Fehler", "Speicherort existiert nicht.")
            return None
        if not base:
            messagebox.showerror("Fehler", "Bitte einen Bild-Basisnamen angeben.")
            return None

        try:
            target_fps = float(fps_s)
            if target_fps <= 0:
                raise ValueError
            # sinnvoller Bereich (du wolltest 5..120 können; technisch lassen wir mehr zu)
            if target_fps > 1000:
                messagebox.showerror("Fehler", "FPS ist unrealistisch hoch.")
                return None
        except ValueError:
            messagebox.showerror("Fehler", "FPS muss eine positive Zahl sein (z.B. 5, 30, 120).")
            return None

        return JobConfig(
            video_path=Path(video),
            out_base_dir=Path(out_dir),
            base_name=base,
            target_fps=target_fps,
            write_exif=bool(self.write_exif_var.get()),
        )

    def start(self):
        cfg = self._validate()
        if cfg is None:
            return

        # prevent double start
        if self._worker_thread and self._worker_thread.is_alive():
            return

        self._cancel_flag.clear()
        self.start_btn.config(state="disabled")
        self.cancel_btn.config(state="normal")

        self.status_var.set("Initialisiere…")
        self.progress_var.set("0 von 0 Frames")
        self.progressbar["value"] = 0
        self.progressbar["maximum"] = 1

        self._worker_thread = threading.Thread(target=self._worker, args=(cfg,), daemon=True)
        self._worker_thread.start()

    def cancel(self):
        self._cancel_flag.set()
        self.status_var.set("Abbruch angefordert…")

    def _poll_queue(self):
        try:
            while True:
                msg = self._q.get_nowait()
                kind = msg.get("kind")

                if kind == "init":
                    total = msg.get("total_frames", 0)
                    self.progressbar["maximum"] = max(total, 1)
                    self.progressbar["value"] = 0
                    self.progress_var.set(f"0 von {total} Frames")
                    self.status_var.set(msg.get("status", "Läuft…"))

                elif kind == "progress":
                    i = msg.get("frame_idx", 0)
                    total = msg.get("total_frames", 1)
                    self.progressbar["value"] = min(i, total)
                    self.progress_var.set(f"{i} von {total} Frames")
                    self.status_var.set(msg.get("status", "Läuft…"))

                elif kind == "done":
                    self.start_btn.config(state="normal")
                    self.cancel_btn.config(state="disabled")
                    self.status_var.set(msg.get("status", "Fertig."))
                    out_dir = msg.get("out_dir")
                    extracted = msg.get("extracted", 0)
                    messagebox.showinfo(
                        "Fertig",
                        f"Extraktion abgeschlossen.\n\nExtrahierte Bilder: {extracted}\nOrdner: {out_dir}"
                    )

                elif kind == "cancelled":
                    self.start_btn.config(state="normal")
                    self.cancel_btn.config(state="disabled")
                    self.status_var.set("Abgebrochen.")
                    messagebox.showwarning("Abgebrochen", msg.get("status", "Vorgang wurde abgebrochen."))

                elif kind == "error":
                    self.start_btn.config(state="normal")
                    self.cancel_btn.config(state="disabled")
                    self.status_var.set("Fehler.")
                    messagebox.showerror("Fehler", msg.get("status", "Unbekannter Fehler."))

        except queue.Empty:
            pass

        self.after(100, self._poll_queue)

    def _make_unique_dir(self, base_dir: Path, folder_name: str) -> Path:
        folder = base_dir / folder_name
        if not folder.exists():
            return folder
        # falls es schon existiert: _1, _2, ...
        k = 1
        while True:
            cand = base_dir / f"{folder_name}_{k}"
            if not cand.exists():
                return cand
            k += 1

    def _write_jpeg_with_optional_exif(self, bgr_frame, out_path: Path, exif_dict: dict | None):
        # OpenCV BGR -> RGB
        rgb = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb)

        if exif_dict is None:
            img.save(out_path, format="JPEG", quality=95, subsampling=0)
            return

        exif_bytes = piexif.dump(exif_dict)
        img.save(out_path, format="JPEG", quality=95, subsampling=0, exif=exif_bytes)

    def _worker(self, cfg: JobConfig):
        try:
            cap = cv2.VideoCapture(str(cfg.video_path))
            if not cap.isOpened():
                self._q.put({"kind": "error", "status": "Video konnte nicht geöffnet werden (OpenCV)."})
                return

            native_fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

            if native_fps <= 0 or total_frames <= 0:
                # OpenCV kann das manchmal nicht liefern; wir laufen trotzdem, aber Progress ist dann eingeschränkt
                total_frames = total_frames if total_frames > 0 else 1

            # Ziel-FPS auf native begrenzen
            target_fps = min(cfg.target_fps, native_fps) if native_fps > 0 else cfg.target_fps

            # Output folder = base name (wie gefordert: "Diese Bilder sollen aber in einem Ordner mit dem Namen sein.")
            out_dir = self._make_unique_dir(cfg.out_base_dir, cfg.base_name)
            out_dir.mkdir(parents=True, exist_ok=True)

            self._q.put({"kind": "init", "total_frames": total_frames, "status": f"Läuft (Ziel-FPS: {target_fps:.3f})…"})
            extracted = 0

            # time-based sampling: nimm Frames, wenn deren Zeit >= next_time
            next_time = 0.0
            frame_idx = 0

            # Schutz gegen Division durch 0
            dt = (1.0 / target_fps) if target_fps > 0 else 0.0
            inv_native = (1.0 / native_fps) if native_fps > 0 else None

            last_ui = 0.0

            while True:
                if self._cancel_flag.is_set():
                    cap.release()
                    self._q.put({"kind": "cancelled", "status": "Vorgang wurde abgebrochen."})
                    return

                ok, frame = cap.read()
                if not ok:
                    break

                frame_idx += 1

                # UI update throttling (nicht zu oft)
                now = time.time()
                if now - last_ui > 0.05:
                    self._q.put({
                        "kind": "progress",
                        "frame_idx": frame_idx,
                        "total_frames": total_frames,
                        "status": f"Extrahiert: {extracted}"
                    })
                    last_ui = now

                # timestamp für diesen Frame
                if inv_native is not None:
                    t = (frame_idx - 1) * inv_native
                else:
                    # fallback: CAP_PROP_POS_MSEC
                    t = (cap.get(cv2.CAP_PROP_POS_MSEC) or 0.0) / 1000.0

                if t + 1e-9 >= next_time:
                    extracted += 1
                    out_name = f"{cfg.base_name}_{extracted}.jpg"
                    out_path = out_dir / out_name

                    exif = None
                    if cfg.write_exif:
                        # EXIF Felder: ImageDescription + UserComment
                        # (nicht sichtbar im Bild, nur Metadaten)
                        desc = f"SourceVideo={cfg.video_path.name}; FrameIndex={frame_idx}; TimeSec={t:.6f}; NativeFPS={native_fps:.6f}; TargetFPS={target_fps:.6f}"
                        exif = {
                            "0th": {
                                piexif.ImageIFD.ImageDescription: desc.encode("utf-8", errors="replace"),
                            },
                            "Exif": {
                                piexif.ExifIFD.UserComment: desc.encode("utf-8", errors="replace"),
                            },
                            "GPS": {},
                            "1st": {},
                            "thumbnail": None,
                        }

                    self._write_jpeg_with_optional_exif(frame, out_path, exif)
                    next_time += dt

            cap.release()
            self._q.put({
                "kind": "progress",
                "frame_idx": min(frame_idx, total_frames),
                "total_frames": total_frames,
                "status": f"Extrahiert: {extracted}"
            })
            self._q.put({
                "kind": "done",
                "status": "Fertig.",
                "out_dir": str(out_dir),
                "extracted": extracted
            })

        except Exception as e:
            self._q.put({"kind": "error", "status": f"Unerwarteter Fehler: {e}"})


if __name__ == "__main__":
    app = VideoToJPGApp()
    app.mainloop()

