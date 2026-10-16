import os
import re
import sys
import subprocess
import json
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

# ============================================================
# DxMediaCenter — Premium Dark Style
# ============================================================

APP_NAME = "DxMediaCenter"
APP_VERSION = "1.1"

# Exakte Farbpalette aus deinem DxDataManager übernommen
BG = "#050505"
SIDEBAR = "#090909"
PANEL = "#111111"
CARD = "#191919"
CARD_HOVER = "#2A1717"
BORDER = "#382021"
ACCENT = "#FF7918"  # Kräftiges Orange für Aktionen
ACCENT_HOVER = "#FF963D"
TEXT = "#F7F3EF"
MUTED = "#A7A0A0"
GREEN = "#75D69A"
RED_DARK = "#39070E"
RED_ACCENT = "#FF243D"

# Unterstützte Videoformate
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".m4v"}

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")


class DxMediaCenter(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME}  •  v{APP_VERSION}")
        self.geometry("1100x780")
        self.minsize(900, 600)
        self.configure(fg_color=BG)

        # Icon direkt in der Anwendung hinterlegen
        self.load_application_icon()

        self.library_path = None
        self.movies = []  # Liste von Dicts: {"title":..., "path":...}
        self.shows = {}  # Struktur: {"Show Name": {"Staffel X": [{"ep": 1, "path":...}]}}
        self.state_path = self.get_state_path()
        self.saved_state = self.load_state()
        self.series_tabs = {}
        self.tabview = None
        self.scroll_frame = None
        self.player_window = None
        self.vlc_instance = None
        self.vlc_player = None
        self.player_media_path = None
        self.player_active_item = None
        self.player_seek_updating = False
        self.controls_visible = True
        self.hide_controls_job = None
        self.last_mouse_pos = (0, 0)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.apply_windows_style()

        # UI-Shell aufbauen
        self.shell = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        self.shell.pack(fill="both", expand=True)

        self.build_layout()
        self.show_welcome_screen()
        saved_folder = self.saved_state.get("library_path")
        if saved_folder and os.path.isdir(saved_folder):
            self.library_path = saved_folder
            self.scan_videos(saved_folder)

    def load_application_icon(self):
        """Prüft, ob die logo.ico im lokalen Verzeichnis existiert und setzt diese als Anwendungs-Icon."""
        icon_name = "logo.ico"
        # Falls als Exe via PyInstaller gepackt, korrekten Basispfad ermitteln
        if getattr(sys, 'frozen', False):
            base_dir = sys._MEIPASS
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))

        icon_path = os.path.join(base_dir, icon_name)

        # Fallback falls im Root-Ordner direkt
        if not os.path.exists(icon_path):
            icon_path = os.path.abspath(icon_name)

        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                try:
                    # Alternativer plattformübergreifender Ansatz für Tkinter-Fenster
                    img = tk.PhotoImage(file=icon_path)
                    self.wm_iconphoto(True, img)
                except Exception:
                    pass

    def apply_windows_style(self):
        if sys.platform != "win32":
            return
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id()) or self.winfo_id()
            value = ctypes.c_int(1)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(value), ctypes.sizeof(value))
            corners = ctypes.c_int(2)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(corners), ctypes.sizeof(corners))
        except Exception:
            pass

    # ----------------------------- UI Helper -----------------------------

    def button(self, parent, text, command, kind="primary", width=None, height=38):
        styles = {
            "primary": dict(fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color="#1A0900"),
            "secondary": dict(fg_color="#262020", hover_color="#3A2525", text_color=TEXT, border_width=1, border_color="#56302A"),
            "danger": dict(fg_color=RED_DARK, hover_color=RED_ACCENT, text_color="#FFF0F1"),
            "quiet": dict(fg_color="transparent", hover_color=CARD_HOVER, text_color=MUTED),
        }
        return ctk.CTkButton(
            parent, text=text, command=command, height=height, width=width or 0,
            corner_radius=10, font=("Segoe UI", 12, "bold" if kind == "primary" else "normal"),
            **styles[kind]
        )

    def label(self, parent, text, size=13, color=TEXT, weight="normal", **kwargs):
        return ctk.CTkLabel(parent, text=text, font=("Segoe UI", size, weight), text_color=color, **kwargs)

    # ----------------------------- Layout -----------------------------

    def build_layout(self):
        # Links: Sidebar
        self.sidebar = ctk.CTkFrame(self.shell, width=240, fg_color=SIDEBAR, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Brand Header in Sidebar
        brand = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand.pack(fill="x", padx=20, pady=(25, 28))
        ctk.CTkFrame(brand, width=4, height=32, fg_color=RED_ACCENT, corner_radius=2).pack(side="left", padx=(0, 11))
        title_frame = ctk.CTkFrame(brand, fg_color="transparent")
        title_frame.pack(side="left", fill="x", expand=True)
        self.label(title_frame, APP_NAME, 16, TEXT, "bold").pack(anchor="w")
        self.label(title_frame, "PREMIUM MEDIA HUB", 9, MUTED, "bold").pack(anchor="w", pady=(2, 0))

        # Navigation / Aktionen
        self.label(self.sidebar, "MEDIATHEK", 10, "#667080", "bold").pack(anchor="w", padx=22, pady=(10, 8))

        self.btn_load = self.button(self.sidebar, "▦  Ordner hinzufügen", self.select_folder, kind="secondary")
        self.btn_load.pack(fill="x", padx=15, pady=5)

        # Trennlinie & Entwickler-Info aus deinem Stil
        spacer = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        spacer.pack(fill="both", expand=True)
        ctk.CTkFrame(self.sidebar, height=1, fg_color=BORDER).pack(fill="x", padx=18, pady=12)
        self.label(self.sidebar, "LOKALES STREAMING", 10, GREEN, "bold").pack(anchor="w", padx=22, pady=(0, 4))
        self.label(self.sidebar, "Entwickelt von Lets Chico / Christopher k.", 11, MUTED, wraplength=190, justify="left").pack(anchor="w", padx=22, pady=(0, 15))

        # Rechts: Hauptinhalt
        self.content_area = ctk.CTkFrame(self.shell, fg_color=BG, corner_radius=0)
        self.content_area.pack(side="left", fill="both", expand=True)

        # Topbar für Überschriften
        self.topbar = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.topbar.pack(fill="x", padx=30, pady=(25, 12))

        self.page_title = self.label(self.topbar, "Willkommen", 26, TEXT, "bold")
        self.page_title.pack(anchor="w")
        self.page_subtitle = self.label(self.topbar, "Wähle einen Ordner aus, um deine Videos zu durchsuchen.", 12, MUTED)
        self.page_subtitle.pack(anchor="w", pady=(4, 0))

        # Bibliothek und automatisch gespeicherte Serien-Tabs
        self.tabview = ctk.CTkTabview(
            self.content_area, fg_color=BG, segmented_button_fg_color=PANEL,
            segmented_button_selected_color=ACCENT,
            segmented_button_selected_hover_color=ACCENT_HOVER,
            segmented_button_unselected_color=CARD,
            segmented_button_unselected_hover_color=CARD_HOVER,
            text_color=TEXT
        )
        self.tabview.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        self.tabview.add("Mediathek")
        self.tabview.add("Aktive Wiedergabe")
        self.active_frame = ctk.CTkScrollableFrame(self.tabview.tab("Aktive Wiedergabe"), fg_color="transparent")
        self.active_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.scroll_frame = ctk.CTkScrollableFrame(self.tabview.tab("Mediathek"), fg_color="transparent")
        self.scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.render_active_video()

    def show_welcome_screen(self):
        # Platzhalter-Inhalt beim Start
        empty_view = ctk.CTkFrame(self.scroll_frame, fg_color=PANEL, corner_radius=16, border_width=1, border_color=BORDER)
        empty_view.pack(fill="x", pady=40, padx=10)
        self.label(empty_view, "Deine Mediathek ist leer", 18, TEXT, "bold").pack(pady=(25, 5))
        self.label(empty_view, "Klicke links auf 'Ordner hinzufügen', um ein Verzeichnis mit Filmen\noder Serienfolgen einzulesen.", 12, MUTED, justify="center").pack(pady=(0, 25))

    # ----------------------------- Logik: Scannen & Parsen -----------------------------

    def select_folder(self):
        folder = filedialog.askdirectory(title="Video-Ordner auswählen")
        if not folder:
            return

        self.library_path = folder
        self.saved_state["library_path"] = folder
        self.save_state()
        self.scan_videos(folder)

    def scan_videos(self, base_folder):
        self.movies = []
        self.shows = {}

        # Regex für Serien-Episoden (z.B. S01E02, 1x04, Episode 3, etc.)
        series_pattern = re.compile(
            r"^(.*?)(?:[._\-\s]+)?(?:[sS](\d+)[eE](\d+)|(\d+)x(\d+)|[eE][pP_](\d+))(.*)$"
        )

        for root, _, files in os.walk(base_folder):
            for file in files:
                basename, ext = os.path.splitext(file)
                if ext.lower() in VIDEO_EXTENSIONS:
                    full_path = os.path.join(root, file)

                    match = series_pattern.match(basename)
                    if match:
                        raw_show_name = match.group(1)

                        if match.group(2) and match.group(3):  # S01E02
                            season_num = int(match.group(2))
                            ep_num = int(match.group(3))
                        elif match.group(4) and match.group(5):  # 1x02
                            season_num = int(match.group(4))
                            ep_num = int(match.group(5))
                        else:  # Reine Episodennummer
                            season_num = 1
                            ep_num = int(match.group(6))

                        show_name = re.sub(r"[._\-\s]+", " ", raw_show_name).strip().title()
                        if not show_name:
                            show_name = "Unbekannte Serie"

                        self.shows.setdefault(show_name, {})
                        season_key = f"Staffel {season_num:02d}"
                        self.shows[show_name].setdefault(season_key, [])

                        self.shows[show_name][season_key].append({
                            "episode": ep_num,
                            "filename": file,
                            "path": full_path
                        })
                    else:
                        clean_title = re.sub(r"[._\-\s]+", " ", basename).strip()
                        self.movies.append({
                            "title": clean_title,
                            "filename": file,
                            "path": full_path
                        })

        # Sortierungen vornehmen
        self.movies.sort(key=lambda x: x["title"].lower())
        for show in self.shows:
            for season in self.shows[show]:
                self.shows[show][season].sort(key=lambda x: x["episode"])

        self.render_library()
        self.render_active_video()

    # ----------------------------- UI: Rendering der Mediathek -----------------------------

    def render_library(self):
        # GUI bereinigen
        for child in self.scroll_frame.winfo_children():
            child.destroy()

        total_items = len(self.movies) + sum(len(eps) for s in self.shows.values() for eps in s.values())
        self.page_title.configure(text="Deine Mediathek")
        self.page_subtitle.configure(text=f"{total_items} Videodateien im Verzeichnis gefunden.")

        if total_items == 0:
            self.show_welcome_screen()
            return

        # --- SEKTION 1: SERIEN (Automatisch gruppiert) ---
        if self.shows:
            header_frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
            header_frame.pack(fill="x", pady=(10, 5))
            self.label(header_frame, "SERIEN", 12, ACCENT, "bold").pack(anchor="w")

            for show_name, seasons in sorted(self.shows.items()):
                show_card = ctk.CTkFrame(self.scroll_frame, fg_color=PANEL, corner_radius=12, border_width=1, border_color=BORDER)
                show_card.pack(fill="x", pady=6, padx=2)

                show_header = ctk.CTkFrame(show_card, fg_color="transparent")
                show_header.pack(fill="x", padx=15, pady=12)

                self.label(show_header, f"🎬  {show_name}", 15, TEXT, "bold").pack(side="left")
                total_eps = sum(len(v) for v in seasons.values())
                self.label(show_header, f"({len(seasons)} Staffel(n) · {total_eps} Folgen)", 11, MUTED).pack(side="left", padx=10, pady=(2, 0))

                show_body = ctk.CTkFrame(show_card, fg_color="transparent")
                show_body.pack(fill="x", padx=15, pady=(0, 12))

                for season_name, episodes in sorted(seasons.items()):
                    self.label(show_body, season_name, 12, ACCENT, "bold").pack(anchor="w", pady=(8, 4))

                    for ep in episodes:
                        ep_row = ctk.CTkFrame(show_body, fg_color=CARD, corner_radius=8, border_width=1, border_color="#2A1C1D")
                        ep_row.pack(fill="x", pady=3)

                        ep_label = f"Folge {ep['episode']:02d} — {Path(ep['path']).stem}"
                        self.label(ep_row, ep_label, 12, TEXT).pack(side="left", padx=12, pady=8)

                        self.button(
                            ep_row, "▶ Abspielen",
                            lambda p=ep['path'], sn=show_name, sea=season_name, en=ep['episode']: self.play_episode(p, sn, sea, en),
                            kind="primary", width=95, height=28
                        ).pack(side="right", padx=8)

        # --- SEKTION 2: EINZELNE FILME / VIDEOS ---
        if self.movies:
            movie_header_frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
            movie_header_frame.pack(fill="x", pady=(25, 5))
            self.label(movie_header_frame, "EINZELNE FILME / VIDEOS", 12, ACCENT, "bold").pack(anchor="w")

            movie_container = ctk.CTkFrame(self.scroll_frame, fg_color=PANEL, corner_radius=12, border_width=1, border_color=BORDER)
            movie_container.pack(fill="x", pady=6, padx=2)

            for movie in self.movies:
                movie_row = ctk.CTkFrame(movie_container, fg_color=CARD, corner_radius=8)
                movie_row.pack(fill="x", padx=12, pady=5)

                self.label(movie_row, f"🎥  {movie['title']}", 12, TEXT).pack(side="left", padx=12, pady=10)

                self.button(movie_row, "▶ Abspielen", lambda m=movie: self.play_movie(m),
                            kind="primary", width=95, height=28).pack(side="right", padx=8)

        self.restore_series_tabs()

    # ----------------------------- Fortschritt & Serien-Tabs -----------------------------

    def get_state_path(self):
        if sys.platform == "win32":
            base = os.environ.get("APPDATA") or str(Path.home())
            folder = Path(base) / APP_NAME
        else:
            folder = Path.home() / ".config" / APP_NAME
        folder.mkdir(parents=True, exist_ok=True)
        return folder / "state.json"

    def load_state(self):
        try:
            with self.state_path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            if isinstance(data, dict):
                data.setdefault("library_path", None)
                data.setdefault("series_progress", {})
                data.setdefault("open_series", [])
                data.setdefault("active_video", None)
                data.setdefault("active_videos", [])
                data.setdefault("volume", 70)  # Standardlautstärke 70%
                return data
        except (OSError, json.JSONDecodeError):
            pass
        return {"library_path": None, "series_progress": {}, "open_series": [], "active_video": None, "active_videos": [], "volume": 70}

    def save_state(self):
        # Fortschritt und geöffnete Tabs bei jeder relevanten Änderung sichern.
        self.saved_state["library_path"] = self.library_path
        self.saved_state["open_series"] = list(self.series_tabs.keys())
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            temp_path = self.state_path.with_name("state.json.tmp")
            with temp_path.open("w", encoding="utf-8") as handle:
                json.dump(self.saved_state, handle, ensure_ascii=False, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, self.state_path)
        except (OSError, TypeError, ValueError) as exc:
            messagebox.showerror(
                "Speicherfehler",
                f"Der Serienfortschritt konnte nicht gespeichert werden.\n\n"
                f"Speicherort: {self.state_path}\nFehler: {exc}"
            )

    def play_episode(self, video_path, show_name, season_name, episode_number):
        if not os.path.exists(video_path):
            messagebox.showerror("Fehler", "Die Datei wurde nicht gefunden oder verschoben.")
            return
        progress = self.saved_state.setdefault("series_progress", {})
        progress[show_name] = {
            "path": video_path,
            "season": season_name,
            "episode": episode_number,
            "filename": Path(video_path).name
        }
        self.add_active_video({
            "path": video_path, "title": Path(video_path).stem,
            "show": show_name, "season": season_name, "episode": episode_number
        })
        self.open_series_tab(show_name, select=True)
        self.refresh_series_tab(show_name)
        self.save_state()
        self.render_active_video()
        self.play_video(video_path)

    def open_series_tab(self, show_name, select=False):
        if show_name in self.series_tabs:
            if select:
                self.tabview.set(self.series_tabs[show_name])
            self.refresh_series_tab(show_name)
            return

        # Tab-Namen dürfen in CustomTkinter nicht doppelt vorkommen.
        tab_name = show_name
        if tab_name == "Mediathek":
            tab_name = f"{show_name} (Serie)"
        self.tabview.add(tab_name)
        tab = self.tabview.tab(tab_name)
        self.series_tabs[show_name] = tab_name

        header = ctk.CTkFrame(tab, fg_color="transparent")
        header.pack(fill="x", padx=18, pady=(18, 8))
        self.label(header, show_name, 20, TEXT, "bold").pack(side="left", anchor="w")
        self.button(header, "Tab schließen", lambda name=show_name: self.close_series_tab(name),
                    kind="danger", width=115, height=32).pack(side="right")

        body = ctk.CTkFrame(tab, fg_color=PANEL, corner_radius=12, border_width=1, border_color=BORDER)
        body.pack(fill="x", padx=18, pady=8)
        self.series_tab_bodies = getattr(self, "series_tab_bodies", {})
        self.series_tab_bodies[show_name] = body
        self.refresh_series_tab(show_name)
        if select:
            self.tabview.set(tab_name)

    def refresh_series_tab(self, show_name):
        body = getattr(self, "series_tab_bodies", {}).get(show_name)
        if body is None:
            return
        for child in body.winfo_children():
            child.destroy()
        progress = self.saved_state.get("series_progress", {}).get(show_name)
        if not progress:
            self.label(body, "Noch keine Folge gestartet.", 13, MUTED).pack(anchor="w", padx=16, pady=16)
            return
        self.label(body, "LETZTER FORTSCHRITT", 10, ACCENT, "bold").pack(anchor="w", padx=16, pady=(16, 5))
        self.label(body, f"{progress.get('season', 'Staffel ?')} · Folge {int(progress.get('episode', 0)):02d}",
                   17, TEXT, "bold").pack(anchor="w", padx=16, pady=(0, 4))
        self.label(body, progress.get("filename", Path(progress.get("path", "")).name),
                   11, MUTED, wraplength=700).pack(anchor="w", padx=16, pady=(0, 12))
        video_path = progress.get("path", "")
        actions = ctk.CTkFrame(body, fg_color="transparent")
        actions.pack(fill="x", padx=16, pady=(0, 16))
        self.button(actions, "▶ Bei dieser Folge weitermachen",
                    lambda name=show_name: self.resume_series(name),
                    kind="primary", width=220).pack(side="left", padx=(0, 8))
        self.button(actions, "⏭ Nächstes Video",
                    lambda name=show_name: self.play_next_episode(name),
                    kind="secondary", width=150).pack(side="left")

    def render_active_video(self):
        """Zeigt das zuletzt über DxMediaCenter gestartete Video im Tab Aktive Wiedergabe."""
        if not hasattr(self, "active_frame"):
            return
        for child in self.active_frame.winfo_children():
            child.destroy()
        self.label(self.active_frame, "Aktive Wiedergabe", 12, ACCENT, "bold").pack(anchor="w", padx=8, pady=(8, 10))
        active_items = self.saved_state.setdefault("active_videos", [])
        # Alte Zustandsdateien migrieren: bisherigen Einzel-Eintrag übernehmen.
        old_active = self.saved_state.get("active_video")
        if old_active and not active_items:
            active_items.append(old_active)
            self.saved_state["active_video"] = None
            self.save_state()
        if not active_items:
            panel = ctk.CTkFrame(self.active_frame, fg_color=PANEL, corner_radius=12, border_width=1, border_color=BORDER)
            panel.pack(fill="x", padx=4, pady=4)
            self.label(panel, "Keine aktiven Einträge. Starte ein Video in der Mediathek.", 13, MUTED).pack(anchor="w", padx=16, pady=18)
            return
        for item_index, active in enumerate(list(active_items)):
            path = active.get("path", "")
            panel = ctk.CTkFrame(self.active_frame, fg_color=PANEL, corner_radius=12, border_width=1, border_color=BORDER)
            panel.pack(fill="x", padx=4, pady=6)
            self.label(panel, active.get("title", Path(path).stem), 16, TEXT, "bold").pack(anchor="w", padx=16, pady=(16, 5))
            show_name = active.get("show")
            if show_name:
                details = f"{show_name} · {active.get('season', 'Staffel ?')} · Folge {int(active.get('episode', 0)):02d}"
            else:
                details = "Einzelvideo / Film"
            self.label(panel, details, 12, MUTED, wraplength=750).pack(anchor="w", padx=16, pady=(0, 12))
            actions = ctk.CTkFrame(panel, fg_color="transparent")
            actions.pack(fill="x", padx=16, pady=(0, 16))
            position = max(0, int(active.get("position_seconds", 0) or 0))
            duration = max(0, int(active.get("duration_seconds", 0) or 0))
            progress_text = f"Fortschritt: {self.format_time(position)}"
            if duration:
                progress_text += f" / {self.format_time(duration)}"
            self.label(panel, progress_text, 11, GREEN).pack(anchor="w", padx=16, pady=(0, 10))
            self.button(actions, "▶ Fortsetzen", lambda a=active: self.reopen_active(a), kind="primary", width=130).pack(side="left", padx=(0, 8))
            self.button(actions, "⏭ Nächstes Video", lambda a=active: self.play_next_from_active(a), kind="secondary", width=150).pack(side="left", padx=(0, 8))
            self.button(actions, "✕ Aus aktiver Wiedergabe entfernen", lambda a=active: self.remove_active_video(a), kind="danger", width=205).pack(side="left")

    def add_active_video(self, item):
        items = self.saved_state.setdefault("active_videos", [])
        path_key = os.path.normcase(os.path.abspath(item.get("path", "")))
        items[:] = [existing for existing in items
                    if os.path.normcase(os.path.abspath(existing.get("path", ""))) != path_key]
        items.insert(0, item)
        self.saved_state["active_video"] = None
        self.save_state()
        self.render_active_video()

    def remove_active_video(self, item):
        items = self.saved_state.setdefault("active_videos", [])
        target = os.path.normcase(os.path.abspath(item.get("path", "")))
        items[:] = [existing for existing in items
                    if os.path.normcase(os.path.abspath(existing.get("path", ""))) != target]
        self.save_state()
        self.render_active_video()

    @staticmethod
    def format_time(seconds):
        seconds = max(0, int(seconds or 0))
        hours, remainder = divmod(seconds, 3600)
        minutes, secs = divmod(remainder, 60)
        return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes}:{secs:02d}"

    def find_active_item(self, path):
        target = os.path.normcase(os.path.abspath(path))
        return next((item for item in self.saved_state.setdefault("active_videos", [])
                     if os.path.normcase(os.path.abspath(item.get("path", ""))) == target), None)

    def play_next_from_active(self, active):
        show_name = active.get("show")
        if show_name:
            # Den Fortschritt auf genau den Eintrag setzen, dessen Nächstes-Button gedrückt wurde.
            self.saved_state.setdefault("series_progress", {})[show_name] = {
                "path": active.get("path", ""), "season": active.get("season", "Staffel ?"),
                "episode": active.get("episode", 0), "filename": Path(active.get("path", "")).name
            }
            self.remove_active_video(active)  # Löscht die aktuelle Folge aus aktiven Filmen
            self.play_next_episode(show_name)
            return
        # Bei Einzelvideos gilt die alphabetische Reihenfolge der Mediathek.
        movies = self.movies
        current = os.path.normcase(os.path.abspath(active.get("path", "")))
        index = next((i for i, movie in enumerate(movies)
                      if os.path.normcase(os.path.abspath(movie["path"])) == current), None)
        if index is None:
            messagebox.showinfo("Nächstes Video", "Dieses Video ist nicht mehr in der aktuellen Mediathek.")
        elif index + 1 >= len(movies):
            messagebox.showinfo("Kein weiteres Video", "Das ist das letzte Einzelvideo in der alphabetischen Liste.")
        else:
            self.remove_active_video(active)  # Löscht den aktuellen Film
            self.play_movie(movies[index + 1])

    def play_movie(self, movie):
        item = {"path": movie["path"], "title": movie.get("title", Path(movie["path"]).stem), "show": None,
                "position_seconds": 0, "duration_seconds": 0}
        self.add_active_video(item)
        self.play_video(movie["path"])

    def resume_series(self, show_name):
        progress = self.saved_state.get("series_progress", {}).get(show_name, {})
        video_path = progress.get("path", "")
        if not video_path or not os.path.isfile(video_path):
            messagebox.showerror(
                "Datei nicht gefunden",
                "Die gespeicherte Folge wurde nicht gefunden. Bitte prüfe den Medienordner."
            )
            return
        self.add_active_video({
            "path": video_path, "title": Path(video_path).stem, "show": show_name,
            "season": progress.get("season", "Staffel ?"), "episode": progress.get("episode", 0)
        })
        self.play_video(video_path)

    def get_ordered_episodes(self, show_name):
        episodes = []
        for season_name, season_episodes in self.shows.get(show_name, {}).items():
            match = re.search(r"(\d+)", season_name)
            season_number = int(match.group(1)) if match else 1
            for episode in season_episodes:
                episodes.append({
                    **episode,
                    "season_name": season_name,
                    "season_number": season_number,
                })
        return sorted(episodes, key=lambda item: (item["season_number"], item["episode"], item["filename"].lower()))

    def play_next_episode(self, show_name):
        episodes = self.get_ordered_episodes(show_name)
        progress = self.saved_state.get("series_progress", {}).get(show_name, {})
        current_path = os.path.normcase(os.path.abspath(progress.get("path", ""))) if progress.get("path") else ""
        current_index = next(
            (index for index, episode in enumerate(episodes)
             if os.path.normcase(os.path.abspath(episode["path"])) == current_path),
            None
        )
        if current_index is None:
            if episodes:
                target = episodes[0]
            else:
                messagebox.showinfo("Keine Folgen", "Für diese Serie wurden keine Folgen gefunden.")
                return
        elif current_index + 1 >= len(episodes):
            messagebox.showinfo("Keine weitere Folge", "Du bist bereits bei der letzten gefundenen Folge.")
            return
        else:
            target = episodes[current_index + 1]
        self.play_episode(target["path"], show_name, target["season_name"], target["episode"])

    def restore_series_tabs(self):
        open_names = self.saved_state.get("open_series", [])
        for name in open_names:
            if name in self.shows:
                self.open_series_tab(name, select=False)

    def close_series_tab(self, show_name):
        tab_name = self.series_tabs.pop(show_name, None)
        getattr(self, "series_tab_bodies", {}).pop(show_name, None)
        if tab_name:
            try:
                self.tabview.delete(tab_name)
            except Exception:
                pass
        self.save_state()

    # ----------------------------- Integrierter Videoplayer -----------------------------

    def set_volume(self, value):
        """Ändert die Lautstärke des VLC-Players und speichert sie."""
        if self.vlc_player:
            try:
                vol = int(float(value))
                self.vlc_player.audio_set_volume(vol)
                self.saved_state["volume"] = vol
                self.save_state()
            except Exception:
                pass

    def play_video(self, video_path):
        """Spielt Videos in einem VLC-Fenster innerhalb der Anwendung ab.

        Voraussetzung: VLC Media Player ist installiert und `python-vlc` ist installiert
        (pip install python-vlc). Die Wiedergabeposition wird regelmäßig gespeichert.
        """
        if not os.path.isfile(video_path):
            messagebox.showerror("Fehler", "Die Datei wurde nicht gefunden oder verschoben.")
            return
        try:
            import vlc
        except ImportError:
            messagebox.showerror(
                "Videoplayer fehlt",
                "Für die integrierte Wiedergabe wird VLC Media Player und das Python-Paket "
                "'python-vlc' benötigt.\n\nInstalliere VLC und führe danach im Terminal aus:\n"
                "python -m pip install python-vlc"
            )
            return

        if self.player_window is not None and self.player_window.winfo_exists():
            if self.player_media_path == os.path.abspath(video_path):
                self.player_window.lift()
                self.player_window.attributes("-topmost", True)
                self.player_window.attributes("-topmost", False)
                if self.vlc_player:
                    self.vlc_player.play()
                return
            self.save_player_position()
            try:
                self.vlc_player.stop()
                self.vlc_player.set_media(None)
            except Exception:
                pass
        else:
            try:
                # Unterdrücke stale plugin cache Warnungen in der Konsole durch VLC CLI Argumente
                self.vlc_instance = vlc.Instance("--no-plugins-cache", "--quiet")
                self.vlc_player = self.vlc_instance.media_player_new()
                self.player_window = ctk.CTkToplevel(self)
                self.player_window.title(f"{APP_NAME} – Videoplayer")

                # Direkt im Vordergrund öffnen und Vollbild aktivieren
                self.player_window.attributes("-topmost", True)
                self.player_window.attributes("-fullscreen", True)

                self.player_window.configure(fg_color=BG)
                self.player_window.protocol("WM_DELETE_WINDOW", self.close_player)

                # Gesamtes UI Layout des Players in ein Hauptframe
                self.player_main_container = ctk.CTkFrame(self.player_window, fg_color="#000000", corner_radius=0)
                self.player_main_container.pack(fill="both", expand=True)

                self.video_surface = ctk.CTkFrame(self.player_main_container, fg_color="#000000", corner_radius=0)
                self.video_surface.place(x=0, y=0, relwidth=1, relheight=1)
                self.video_surface.bind("<Configure>", self.resize_video_surface)

                # Kontroll-Overlay unten fixieren
                self.player_controls_panel = ctk.CTkFrame(self.player_main_container, fg_color="transparent")
                self.player_controls_panel.pack(side="bottom", fill="x", padx=20, pady=20)

                self.player_title_label = self.label(self.player_controls_panel, "", 14, TEXT, "bold")
                self.player_title_label.pack(anchor="w", padx=6, pady=(0, 4))

                controls = ctk.CTkFrame(self.player_controls_panel, fg_color="#090909", corner_radius=10, border_width=1, border_color=BORDER)
                controls.pack(fill="x")

                self.player_play_button = self.button(controls, "⏸ Pause", self.toggle_player, kind="primary", width=100)
                self.player_play_button.pack(side="left", padx=10, pady=10)

                # Nächstes Video Button hinzufügen
                self.player_next_button = self.button(controls, "⏭ Nächstes", self.player_click_next, kind="secondary", width=100)
                self.player_next_button.pack(side="left", padx=5, pady=10)

                self.player_time_label = self.label(controls, "0:00 / 0:00", 11, MUTED)
                self.player_time_label.pack(side="left", padx=10)

                self.player_seek = tk.Scale(controls, from_=0, to=100, orient="horizontal", showvalue=0,
                                            resolution=1, bg="#090909", fg=TEXT, troughcolor=CARD,
                                            highlightthickness=0, activebackground=ACCENT,
                                            command=self.seek_player)
                self.player_seek.pack(side="left", fill="x", expand=True, padx=10)

                # Lautstärke-Bereich hinzufügen
                self.label(controls, "🔊", 12, MUTED).pack(side="left", padx=(10, 2))
                saved_vol = self.saved_state.get("volume", 70)
                self.player_volume = tk.Scale(controls, from_=0, to=100, orient="horizontal", showvalue=0,
                                              resolution=1, bg="#090909", fg=TEXT, troughcolor=CARD,
                                              highlightthickness=0, activebackground=ACCENT,
                                              width=12, length=80,
                                              command=self.set_volume)
                self.player_volume.pack(side="left", padx=(0, 10))
                self.player_volume.set(saved_vol)

                self.button(controls, "Schließen", self.close_player, kind="secondary", width=100).pack(side="right", padx=10, pady=10)

                # Bindings für Mausbewegung und Tastatur
                self.player_window.bind("<space>", lambda event: self.toggle_player())
                self.player_window.bind("<Escape>", lambda event: self.close_player())

                # Binde Bewegung direkt an das übergeordnete Fenster
                self.player_window.bind("<Motion>", self.on_player_mouse_motion)
                self.player_main_container.bind("<Motion>", self.on_player_mouse_motion)
                self.video_surface.bind("<Motion>", self.on_player_mouse_motion)
                controls.bind("<Motion>", self.on_player_mouse_motion)

                # Initiale Mausposition sichern
                self.last_mouse_pos = self.player_window.winfo_pointerxy()

                self.reset_controls_timer()

            except Exception as exc:
                messagebox.showerror("Playerfehler", f"Der integrierte Videoplayer konnte nicht gestartet werden:\n{exc}")
                return

        self.player_media_path = os.path.abspath(video_path)
        self.player_active_item = self.find_active_item(video_path)
        if self.player_active_item is None:
            self.player_active_item = {"path": video_path, "title": Path(video_path).stem,
                                       "position_seconds": 0, "duration_seconds": 0}
            self.add_active_video(self.player_active_item)
            self.player_active_item = self.find_active_item(video_path)
        self.player_title_label.configure(text=self.player_active_item.get("title", Path(video_path).stem))
        media = self.vlc_instance.media_new(video_path)
        self.vlc_player.set_media(media)
        self.player_window.update_idletasks()
        self.resize_video_surface()
        self.vlc_player.play()

        # Initiale Lautstärke nach Play-Befehl setzen, da VLC manchmal erst beim Laden initialisiert
        init_vol = self.saved_state.get("volume", 70)
        self.after(200, lambda: self.set_volume(init_vol))

        self.show_controls()
        self.after(350, self.restore_player_position)
        self.after(700, self.update_player_progress)

    def player_click_next(self):
        if self.player_active_item:
            current_active = self.player_active_item
            self.close_player()
            self.play_next_from_active(current_active)

    def on_player_mouse_motion(self, event=None):
        self.show_controls()
        self.reset_controls_timer()

    def reset_controls_timer(self):
        if self.hide_controls_job:
            self.player_window.after_cancel(self.hide_controls_job)
        self.hide_controls_job = self.player_window.after(3000, self.hide_controls)

    def show_controls(self):
        if not self.controls_visible:
            self.player_controls_panel.pack(side="bottom", fill="x", padx=20, pady=20)
            self.player_window.configure(cursor="")
            self.controls_visible = True

    def hide_controls(self):
        if self.controls_visible and self.player_window and self.player_window.winfo_exists():
            # Überprüfen ob Maus über den Controls steht
            x, y = self.player_window.winfo_pointerxy()
            try:
                widget = self.player_window.winfo_containing(x, y)
                if widget and (widget == self.player_controls_panel or self.player_controls_panel in widget.winfo_ancestors() or "scale" in str(widget).lower()):
                    self.reset_controls_timer()
                    return
            except Exception:
                pass
            self.player_controls_panel.pack_forget()
            self.player_window.configure(cursor="none")
            self.controls_visible = False

    def resize_video_surface(self, _event=None):
        if not self.vlc_player or not self.player_window or not self.player_window.winfo_exists():
            return
        try:
            self.video_surface.update_idletasks()
            handle = self.video_surface.winfo_id()
            if sys.platform == "win32":
                self.vlc_player.set_hwnd(handle)
            elif sys.platform == "darwin":
                self.vlc_player.set_nsobject(handle)
            else:
                self.vlc_player.set_xwindow(handle)
        except Exception:
            pass

    def reopen_active(self, active):
        self.play_video(active.get("path", ""))

    def restore_player_position(self):
        if not self.vlc_player or not self.player_active_item:
            return
        try:
            position = max(0, int(self.player_active_item.get("position_seconds", 0) or 0))
            if position:
                self.vlc_player.set_time(position * 1000)
        except Exception:
            pass

    def toggle_player(self):
        if not self.vlc_player:
            return
        try:
            if self.vlc_player.is_playing():
                self.vlc_player.pause()
                self.player_play_button.configure(text="▶ Weiter")
                self.save_player_position()
            else:
                self.vlc_player.play()
                self.player_play_button.configure(text="⏸ Pause")
        except Exception:
            pass

    def seek_player(self, value):
        if self.player_seek_updating or not self.vlc_player:
            return
        try:
            duration = self.vlc_player.get_length()
            if duration > 0:
                self.vlc_player.set_time(int(float(value) / 100 * duration))
        except Exception:
            pass

    def update_player_progress(self):
        if not self.player_window or not self.player_window.winfo_exists():
            return
        try:
            # Polling-Fallback für Mausbewegungen, da VLC das native Handle überzeichnet
            # und Standard Tkinter Motion-Events über der Video-Oberfläche blockieren kann.
            current_mouse_pos = self.player_window.winfo_pointerxy()
            if current_mouse_pos != self.last_mouse_pos:
                self.last_mouse_pos = current_mouse_pos
                self.on_player_mouse_motion()

            if self.vlc_player:
                current_ms = max(0, self.vlc_player.get_time())
                duration_ms = max(0, self.vlc_player.get_length())
                current = current_ms // 1000
                duration = duration_ms // 1000
                if self.player_active_item is not None:
                    self.player_active_item["position_seconds"] = current
                    self.player_active_item["duration_seconds"] = duration
                    self.save_state()
                self.player_time_label.configure(text=f"{self.format_time(current)} / {self.format_time(duration)}")
                self.player_seek_updating = True
                self.player_seek.configure(state="normal", to=100)
                self.player_seek.set((current_ms / duration_ms * 100) if duration_ms > 0 else 0)
                self.player_seek_updating = False
                if self.vlc_player.is_playing():
                    self.player_play_button.configure(text="⏸ Pause")
                elif self.vlc_player.get_state() == 6:  # VLC Ended
                    if self.player_active_item is not None:
                        current_item = self.player_active_item
                        self.close_player()
                        self.remove_active_video(current_item)  # Aus aktiven Filmen komplett löschen

                        # MODIFICATION HERE: Automatically play the next video after the current one ends
                        # We can utilize the logic inside play_next_from_active, but since it requires a root schedule,
                        # we should use self.after to prevent tkinter/VLC deadlocks during state callback.
                        self.after(100, lambda: self.play_next_from_active(current_item))
                        return
        except Exception:
            self.player_seek_updating = False
        self.after(1000, self.update_player_progress)

    def save_player_position(self):
        if not self.vlc_player or not self.player_active_item:
            return
        try:
            current_ms = self.vlc_player.get_time()
            duration_ms = self.vlc_player.get_length()
            if current_ms >= 0:
                self.player_active_item["position_seconds"] = current_ms // 1000
            if duration_ms > 0:
                self.player_active_item["duration_seconds"] = duration_ms // 1000
            self.save_state()
            self.render_active_video()
        except Exception:
            pass

    def close_player(self):
        if self.hide_controls_job:
            try:
                self.player_window.after_cancel(self.hide_controls_job)
            except Exception:
                pass
        self.save_player_position()
        try:
            if self.vlc_player:
                self.vlc_player.stop()
        except Exception:
            pass
        if self.player_window is not None:
            try:
                self.player_window.destroy()
            except Exception:
                pass
        self.player_window = None
        self.vlc_player = None
        self.vlc_instance = None
        self.player_media_path = None
        self.player_active_item = None

    def on_close(self):
        self.save_player_position()
        try:
            if self.vlc_player:
                self.vlc_player.stop()
        except Exception:
            pass
        self.save_state()
        self.destroy()


if __name__ == "__main__":
    app = DxMediaCenter()
    app.mainloop()