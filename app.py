import platform
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Dict, Any, Optional, List
from collections import Counter

import customtkinter as ctk
from PIL import Image, ImageTk

try:
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    MATPLOTLIB_AVAILABLE = True
except Exception:
    MATPLOTLIB_AVAILABLE = False

import database

# Configure global CustomTkinter appearance
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

BASE_DIR = Path(__file__).resolve().parent
ICON_PNG_PATH = BASE_DIR / "icon.png"
ICON_ICO_PATH = BASE_DIR / "icon.ico"

PREVIEW_MAX_CHARS = 120
AUTO_LOCK_TIMEOUT_SECONDS = 300  # 5 minutes
DRAFT_DEBOUNCE_MS = 2000         # 2 seconds of inactivity

# ------------------------------------------------------------------------------
# macOS Dark Mode Design System Constants
# ------------------------------------------------------------------------------
COLOR_WINDOW_BG = "#1E1E1E"       # Base macOS dark window background
COLOR_PANEL_BG = "#2B2B2B"        # Cards, side panels, elevated surfaces
COLOR_CARD_HOVER = "#323232"      # Interactive hover
COLOR_INPUT_BG = "#1A1A1A"        # Inset fields
COLOR_BORDER = "#3D3D3D"          # Subtle separators and outlines
COLOR_ACCENT = "#0A84FF"          # macOS system blue
COLOR_ACCENT_HOVER = "#0071E3"    # Pressed/hover blue
COLOR_DESTRUCTIVE = "#FF453A"     # macOS system red
COLOR_DESTRUCTIVE_HOVER = "#D70015"
COLOR_SUCCESS = "#30D158"         # macOS system green
COLOR_SUCCESS_HOVER = "#24A144"
COLOR_SECONDARY_BTN = "#3A3A3C"   # Subtle secondary button fill
COLOR_SECONDARY_HOVER = "#48484A"

COLOR_TEXT_PRIMARY = "#FFFFFF"
COLOR_TEXT_SECONDARY = "#98989D"
COLOR_TEXT_MUTED = "#636366"

# Mood states
MOOD_OPTIONS = [
    "Happy",
    "Calm",
    "Productive",
    "Neutral",
    "Tired",
    "Stressed",
    "Anxious",
    "Sad",
]

MOOD_COLORS: Dict[str, str] = {
    "Happy": "#30D158",       # Green
    "Calm": "#64D2FF",        # Light cyan
    "Productive": "#0A84FF",  # Blue
    "Neutral": "#8E8E93",     # Slate/Gray
    "Tired": "#BF5AF2",       # Purple
    "Stressed": "#FF9F0A",    # Amber
    "Anxious": "#FF6961",     # Soft Orange
    "Sad": "#FF453A",         # Red
}

DEFAULT_MOOD_COLOR = "#8E8E93"

# Journaling prompt templates
JOURNAL_TEMPLATES = {
    "Templates": "",
    "Daily Gratitude": (
        "3 Things I'm Grateful For:\n"
        "1. \n"
        "2. \n"
        "3. \n\n"
        "Today's Primary Focus:\n"
        "- \n\n"
        "Positive Highlight of the Day:\n"
        "- "
    ),
    "Evening Review": (
        "What Went Well Today:\n"
        "- \n\n"
        "What Could Have Gone Better:\n"
        "- \n\n"
        "Key Lessons Learned:\n"
        "- \n\n"
        "Plan for Tomorrow:\n"
        "- "
    ),
    "Brain Dump": (
        "Open Thoughts & Musings:\n"
        "- \n\n"
        "Pending Tasks & Priorities:\n"
        "- \n\n"
        "Unresolved Questions:\n"
        "- "
    ),
}


def get_mood_color(mood_raw: str) -> str:
    """Safely match mood to color palette, handling legacy or unexpected values."""
    if not mood_raw:
        return DEFAULT_MOOD_COLOR
    clean = mood_raw.split()[-1].capitalize()
    return MOOD_COLORS.get(clean, MOOD_COLORS.get(mood_raw, DEFAULT_MOOD_COLOR))


def normalize_mood_name(mood_raw: str) -> str:
    """Normalize legacy mood strings to match new clean labels."""
    if not mood_raw:
        return "Neutral"
    clean = mood_raw.split()[-1].capitalize()
    if clean in MOOD_OPTIONS:
        return clean
    if mood_raw in MOOD_OPTIONS:
        return mood_raw
    return clean


def format_snippet(content: str, max_length: int = PREVIEW_MAX_CHARS) -> str:
    """Collapse excessive whitespace and truncate content to a preview snippet."""
    normalized = " ".join(content.split())
    if len(normalized) <= max_length:
        return normalized
    return normalized[:max_length].rstrip() + "..."


class ConfirmDialog(ctk.CTkToplevel):
    """Custom macOS dark-themed modal confirmation dialog."""

    def __init__(
        self,
        parent: ctk.CTk,
        title: str,
        message: str,
        confirm_text: str = "Confirm",
        cancel_text: str = "Cancel",
        confirm_color: str = COLOR_DESTRUCTIVE,
        confirm_hover: str = COLOR_DESTRUCTIVE_HOVER,
    ) -> None:
        super().__init__(parent)
        self.result: bool = False

        self.title(title)
        self.geometry("380x180")
        self.resizable(False, False)
        self.configure(fg_color=COLOR_WINDOW_BG)
        self.transient(parent)
        self.grab_set()

        parent.update_idletasks()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        px = parent.winfo_x()
        py = parent.winfo_y()
        x = max(0, px + (pw - 380) // 2)
        y = max(0, py + (ph - 180) // 2)
        self.geometry(f"380x180+{x}+{y}")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        container = ctk.CTkFrame(
            self,
            corner_radius=14,
            fg_color=COLOR_PANEL_BG,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        container.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
        container.grid_columnconfigure((0, 1), weight=1)

        msg_label = ctk.CTkLabel(
            container,
            text=message,
            font=ctk.CTkFont(family="SF Pro Display", size=13),
            text_color=COLOR_TEXT_PRIMARY,
            wraplength=310,
            justify="center",
        )
        msg_label.grid(row=0, column=0, columnspan=2, padx=16, pady=(22, 18), sticky="ew")

        cancel_btn = ctk.CTkButton(
            container,
            text=cancel_text,
            height=34,
            corner_radius=8,
            fg_color=COLOR_SECONDARY_BTN,
            hover_color=COLOR_SECONDARY_HOVER,
            text_color=COLOR_TEXT_PRIMARY,
            font=ctk.CTkFont(family="SF Pro Display", size=13, weight="bold"),
            command=self._on_cancel,
        )
        cancel_btn.grid(row=1, column=0, padx=(16, 6), pady=(0, 16), sticky="ew")

        confirm_btn = ctk.CTkButton(
            container,
            text=confirm_text,
            height=34,
            corner_radius=8,
            fg_color=confirm_color,
            hover_color=confirm_hover,
            text_color=COLOR_TEXT_PRIMARY,
            font=ctk.CTkFont(family="SF Pro Display", size=13, weight="bold"),
            command=self._on_confirm,
        )
        confirm_btn.grid(row=1, column=1, padx=(6, 16), pady=(0, 16), sticky="ew")

        self.bind("<Escape>", lambda _e: self._on_cancel())
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.wait_window()

    def _on_confirm(self) -> None:
        self.result = True
        self.destroy()

    def _on_cancel(self) -> None:
        self.result = False
        self.destroy()


class MessageDialog(ctk.CTkToplevel):
    """Custom macOS dark-themed alert dialog."""

    def __init__(self, parent: ctk.CTk, title: str, message: str) -> None:
        super().__init__(parent)
        self.title(title)
        self.geometry("360x170")
        self.resizable(False, False)
        self.configure(fg_color=COLOR_WINDOW_BG)
        self.transient(parent)
        self.grab_set()

        parent.update_idletasks()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        px = parent.winfo_x()
        py = parent.winfo_y()
        x = max(0, px + (pw - 360) // 2)
        y = max(0, py + (ph - 170) // 2)
        self.geometry(f"360x170+{x}+{y}")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        container = ctk.CTkFrame(
            self,
            corner_radius=14,
            fg_color=COLOR_PANEL_BG,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        container.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
        container.grid_columnconfigure(0, weight=1)

        msg_label = ctk.CTkLabel(
            container,
            text=message,
            font=ctk.CTkFont(family="SF Pro Display", size=13),
            text_color=COLOR_TEXT_PRIMARY,
            wraplength=290,
            justify="center",
        )
        msg_label.grid(row=0, column=0, padx=16, pady=(24, 16), sticky="ew")

        ok_btn = ctk.CTkButton(
            container,
            text="OK",
            width=100,
            height=34,
            corner_radius=8,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            text_color=COLOR_TEXT_PRIMARY,
            font=ctk.CTkFont(family="SF Pro Display", size=13, weight="bold"),
            command=self.destroy,
        )
        ok_btn.grid(row=1, column=0, pady=(0, 16))

        self.bind("<Return>", lambda _e: self.destroy())
        self.bind("<Escape>", lambda _e: self.destroy())
        self.wait_window()


class ChangePinDialog(ctk.CTkToplevel):
    """Modal dialog allowing the user to update their security PIN."""

    def __init__(self, parent: ctk.CTk) -> None:
        super().__init__(parent)
        self.success = False

        self.title("Change Security PIN")
        self.geometry("380x370")
        self.resizable(False, False)
        self.configure(fg_color=COLOR_WINDOW_BG)
        self.transient(parent)
        self.grab_set()

        parent.update_idletasks()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        px = parent.winfo_x()
        py = parent.winfo_y()
        x = max(0, px + (pw - 380) // 2)
        y = max(0, py + (ph - 370) // 2)
        self.geometry(f"380x370+{x}+{y}")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        container = ctk.CTkFrame(
            self,
            corner_radius=14,
            fg_color=COLOR_PANEL_BG,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        container.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
        container.grid_columnconfigure(0, weight=1)

        title_lbl = ctk.CTkLabel(
            container,
            text="Change Security PIN",
            font=ctk.CTkFont(family="SF Pro Display", size=17, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY,
        )
        title_lbl.grid(row=0, column=0, pady=(16, 14), sticky="ew")

        # Current PIN
        self.cur_entry = ctk.CTkEntry(
            container,
            placeholder_text="Current PIN",
            show="*",
            height=38,
            corner_radius=8,
            fg_color=COLOR_INPUT_BG,
            border_color=COLOR_BORDER,
            font=ctk.CTkFont(family="SF Pro Display", size=13),
        )
        self.cur_entry.grid(row=1, column=0, padx=22, pady=6, sticky="ew")

        # New PIN
        self.new_entry = ctk.CTkEntry(
            container,
            placeholder_text="New PIN (4-16 characters)",
            show="*",
            height=38,
            corner_radius=8,
            fg_color=COLOR_INPUT_BG,
            border_color=COLOR_BORDER,
            font=ctk.CTkFont(family="SF Pro Display", size=13),
        )
        self.new_entry.grid(row=2, column=0, padx=22, pady=6, sticky="ew")

        # Confirm New PIN
        self.confirm_entry = ctk.CTkEntry(
            container,
            placeholder_text="Confirm New PIN",
            show="*",
            height=38,
            corner_radius=8,
            fg_color=COLOR_INPUT_BG,
            border_color=COLOR_BORDER,
            font=ctk.CTkFont(family="SF Pro Display", size=13),
        )
        self.confirm_entry.grid(row=3, column=0, padx=22, pady=6, sticky="ew")

        self.error_label = ctk.CTkLabel(
            container,
            text="",
            font=ctk.CTkFont(family="SF Pro Display", size=12),
            text_color=COLOR_DESTRUCTIVE,
        )
        self.error_label.grid(row=4, column=0, padx=22, pady=(4, 8), sticky="ew")

        btn_row = ctk.CTkFrame(container, fg_color="transparent")
        btn_row.grid(row=5, column=0, padx=22, pady=(0, 16), sticky="ew")
        btn_row.grid_columnconfigure((0, 1), weight=1)

        cancel_btn = ctk.CTkButton(
            btn_row,
            text="Cancel",
            height=36,
            corner_radius=8,
            fg_color=COLOR_SECONDARY_BTN,
            hover_color=COLOR_SECONDARY_HOVER,
            text_color=COLOR_TEXT_PRIMARY,
            font=ctk.CTkFont(family="SF Pro Display", size=13, weight="bold"),
            command=self.destroy,
        )
        cancel_btn.grid(row=0, column=0, padx=(0, 6), sticky="ew")

        update_btn = ctk.CTkButton(
            btn_row,
            text="Update PIN",
            height=36,
            corner_radius=8,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            text_color=COLOR_TEXT_PRIMARY,
            font=ctk.CTkFont(family="SF Pro Display", size=13, weight="bold"),
            command=self._handle_update,
        )
        update_btn.grid(row=0, column=1, padx=(6, 0), sticky="ew")

        self.cur_entry.focus()
        self.bind("<Return>", lambda _e: self._handle_update())
        self.bind("<Escape>", lambda _e: self.destroy())
        self.wait_window()

    def _handle_update(self) -> None:
        current_pin = self.cur_entry.get().strip()
        new_pin = self.new_entry.get().strip()
        confirm_pin = self.confirm_entry.get().strip()

        if not current_pin:
            self.error_label.configure(text="Please enter your current PIN.")
            self.cur_entry.focus()
            return

        if not database.verify_pin(current_pin):
            self.error_label.configure(text="Current PIN is incorrect.")
            self.cur_entry.delete(0, "end")
            self.cur_entry.focus()
            return

        if len(new_pin) < 4 or len(new_pin) > 16:
            self.error_label.configure(text="New PIN must be 4 to 16 characters.")
            self.new_entry.focus()
            return

        if new_pin != confirm_pin:
            self.error_label.configure(text="New PINs do not match.")
            self.confirm_entry.delete(0, "end")
            self.confirm_entry.focus()
            return

        database.set_user_pin(new_pin)
        self.success = True
        self.destroy()


class EntryCard(ctk.CTkFrame):
    """A card representing a single entry with snippet preview, pin, edit, and delete actions."""

    def __init__(
        self,
        master: Any,
        entry: Dict[str, Any],
        on_edit: Callable[[Dict[str, Any]], None],
        on_delete: Callable[[int], None],
        on_toggle_pin: Callable[[int], None],
        is_editing: bool = False,
        **kwargs: Any,
    ) -> None:
        is_pinned = bool(entry.get("is_pinned", 0))
        border_color = COLOR_ACCENT if (is_editing or is_pinned) else COLOR_BORDER
        border_width = 2 if (is_editing or is_pinned) else 1

        super().__init__(
            master,
            corner_radius=12,
            fg_color=COLOR_PANEL_BG,
            border_width=border_width,
            border_color=border_color,
            cursor="hand2",
            **kwargs,
        )
        self.entry = entry
        self.entry_id = entry["id"]
        self.is_pinned = is_pinned
        self.on_edit = on_edit
        self.on_delete = on_delete
        self.on_toggle_pin = on_toggle_pin

        self.grid_columnconfigure(0, weight=1)

        # Header frame: Title, Pinned badge, Mood badge, Pin btn, Edit btn, Delete btn
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 4))
        header_frame.grid_columnconfigure(0, weight=1)

        title_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_box.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        title_box.grid_columnconfigure(1, weight=1)

        col_pos = 0
        if is_pinned:
            pinned_badge = ctk.CTkLabel(
                title_box,
                text="[Pinned]",
                font=ctk.CTkFont(family="SF Pro Display", size=10, weight="bold"),
                text_color=COLOR_ACCENT,
                cursor="hand2",
            )
            pinned_badge.grid(row=0, column=col_pos, padx=(0, 6), sticky="w")
            col_pos += 1

        title_label = ctk.CTkLabel(
            title_box,
            text=entry["title"],
            font=ctk.CTkFont(family="SF Pro Display", size=15, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY,
            anchor="w",
            justify="left",
            cursor="hand2",
        )
        title_label.grid(row=0, column=col_pos, sticky="ew")

        display_mood = normalize_mood_name(entry["mood"])
        mood_color = get_mood_color(display_mood)
        mood_badge = ctk.CTkLabel(
            header_frame,
            text=display_mood,
            font=ctk.CTkFont(family="SF Pro Display", size=11, weight="bold"),
            fg_color=mood_color,
            text_color="#000000" if display_mood in ("Calm", "Happy") else "#FFFFFF",
            corner_radius=6,
            padx=8,
            pady=2,
            cursor="hand2",
        )
        mood_badge.grid(row=0, column=1, padx=(0, 6))

        # Pin / Unpin button
        pin_btn = ctk.CTkButton(
            header_frame,
            text="Unpin" if is_pinned else "Pin",
            width=48,
            height=26,
            corner_radius=8,
            fg_color=COLOR_ACCENT if is_pinned else COLOR_SECONDARY_BTN,
            hover_color=COLOR_ACCENT_HOVER if is_pinned else COLOR_SECONDARY_HOVER,
            text_color=COLOR_TEXT_PRIMARY,
            font=ctk.CTkFont(family="SF Pro Display", size=11, weight="bold"),
            command=self._handle_pin,
        )
        pin_btn.grid(row=0, column=2, padx=(0, 6))

        edit_btn = ctk.CTkButton(
            header_frame,
            text="Edit",
            width=50,
            height=26,
            corner_radius=8,
            fg_color=COLOR_SECONDARY_BTN,
            hover_color=COLOR_SECONDARY_HOVER,
            text_color=COLOR_TEXT_PRIMARY,
            font=ctk.CTkFont(family="SF Pro Display", size=11, weight="bold"),
            command=self._handle_edit,
        )
        edit_btn.grid(row=0, column=3, padx=(0, 6))

        delete_btn = ctk.CTkButton(
            header_frame,
            text="Delete",
            width=56,
            height=26,
            corner_radius=8,
            fg_color=COLOR_DESTRUCTIVE,
            hover_color=COLOR_DESTRUCTIVE_HOVER,
            text_color=COLOR_TEXT_PRIMARY,
            font=ctk.CTkFont(family="SF Pro Display", size=11, weight="bold"),
            command=self._handle_delete,
        )
        delete_btn.grid(row=0, column=4)

        # Timestamp
        date_label = ctk.CTkLabel(
            self,
            text=entry["created_at"],
            font=ctk.CTkFont(family="SF Pro Display", size=11),
            text_color=COLOR_TEXT_MUTED,
            anchor="w",
            cursor="hand2",
        )
        date_label.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 4))

        # Snippet content
        snippet_text = format_snippet(entry["content"], PREVIEW_MAX_CHARS)
        content_label = ctk.CTkLabel(
            self,
            text=snippet_text,
            font=ctk.CTkFont(family="SF Pro Display", size=13),
            text_color=COLOR_TEXT_SECONDARY,
            anchor="w",
            justify="left",
            wraplength=440,
            cursor="hand2",
        )
        content_label.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 12))

        # Clicking the card activates editing
        for widget in (self, header_frame, title_box, title_label, mood_badge, date_label, content_label):
            widget.bind("<Button-1>", lambda _event: self._handle_edit())

    def _handle_pin(self) -> None:
        self.on_toggle_pin(self.entry_id)

    def _handle_edit(self) -> None:
        self.on_edit(self.entry)

    def _handle_delete(self) -> None:
        self.on_delete(self.entry_id)


class Reflect(ctk.CTk):
    """Main application window for Reflect."""

    def __init__(self) -> None:
        super().__init__()

        self.title("Reflect")
        self.geometry("1140x740")
        self.minsize(920, 580)
        self.configure(fg_color=COLOR_WINDOW_BG)

        self._set_app_icon()

        # Handle custom window close confirmation
        self.protocol("WM_DELETE_WINDOW", self.on_close_requested)

        self.editing_entry_id: Optional[int] = None
        self.all_entries: List[Dict[str, Any]] = []
        self.current_tab: str = "Journal"
        self.selected_mood_filter: str = "All"
        self.selected_time_filter: str = "All Time"
        self.filter_buttons: Dict[str, ctk.CTkButton] = {}

        # Zen / Focus Mode state
        self.is_zen_mode: bool = False

        # Auto-Save timer handle
        self._draft_timer_id: Optional[str] = None

        # Auto-Lock tracking
        self.is_authenticated: bool = False
        self.last_activity_time: float = time.time()

        # Global event listeners to track user activity
        self.bind_all("<Key>", self._on_user_interaction, add=True)
        self.bind_all("<Motion>", self._on_user_interaction, add=True)
        self.bind_all("<Button>", self._on_user_interaction, add=True)

        # Keyboard shortcuts for Zen Mode
        self.bind("<F11>", lambda _e: self.toggle_zen_mode())
        self.bind("<Escape>", self._on_escape_pressed)

        # Root layout configuration
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Container for main views
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.grid(row=0, column=0, sticky="nsew")
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(0, weight=1)

        # Inactivity monitor loop
        self._start_inactivity_checker()

        # Check authentication status
        if not database.is_pin_configured():
            self._show_pin_setup_view()
        else:
            self._show_pin_lock_view()

    def _set_app_icon(self) -> None:
        """Dynamically load the desktop window icon across Windows and Linux."""
        current_os = platform.system()
        try:
            if current_os == "Windows" and ICON_ICO_PATH.exists():
                self.iconbitmap(str(ICON_ICO_PATH))
            elif ICON_PNG_PATH.exists():
                img = Image.open(ICON_PNG_PATH)
                self._photo_icon = ImageTk.PhotoImage(img)
                self.wm_iconphoto(True, self._photo_icon)
        except Exception:
            pass

    def _on_escape_pressed(self, _event: Any = None) -> None:
        if self.is_zen_mode:
            self.toggle_zen_mode()

    # --------------------------------------------------------------------------
    # Auto-Lock & Activity Watcher
    # --------------------------------------------------------------------------
    def _on_user_interaction(self, _event: Any = None) -> None:
        self.last_activity_time = time.time()

    def _start_inactivity_checker(self) -> None:
        if self.is_authenticated:
            elapsed = time.time() - self.last_activity_time
            if elapsed >= AUTO_LOCK_TIMEOUT_SECONDS:
                self._lock_app()
        self.after(2000, self._start_inactivity_checker)

    def on_close_requested(self) -> None:
        self._save_draft_now()
        dialog = ConfirmDialog(
            parent=self,
            title="Exit Reflect",
            message="Are you sure you want to close Reflect?",
            confirm_text="Exit",
            cancel_text="Cancel",
            confirm_color=COLOR_DESTRUCTIVE,
            confirm_hover=COLOR_DESTRUCTIVE_HOVER,
        )
        if dialog.result:
            self.destroy()

    def _clear_main_container(self) -> None:
        for widget in self.main_container.winfo_children():
            widget.destroy()

    # --------------------------------------------------------------------------
    # PIN Setup & Lock Views
    # --------------------------------------------------------------------------
    def _show_pin_setup_view(self) -> None:
        self.is_authenticated = False
        self._clear_main_container()

        center_card = ctk.CTkFrame(
            self.main_container,
            corner_radius=16,
            fg_color=COLOR_PANEL_BG,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        center_card.place(relx=0.5, rely=0.5, anchor="center")
        center_card.configure(width=420)

        header = ctk.CTkLabel(
            center_card,
            text="Welcome to Reflect",
            font=ctk.CTkFont(family="SF Pro Display", size=22, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY,
        )
        header.grid(row=0, column=0, padx=32, pady=(28, 6), sticky="ew")

        sub = ctk.CTkLabel(
            center_card,
            text="Create a secure PIN to protect your personal journal.",
            font=ctk.CTkFont(family="SF Pro Display", size=13),
            text_color=COLOR_TEXT_SECONDARY,
        )
        sub.grid(row=1, column=0, padx=32, pady=(0, 20), sticky="ew")

        self.setup_pin_entry = ctk.CTkEntry(
            center_card,
            placeholder_text="Enter PIN (4-16 characters)",
            show="*",
            height=40,
            corner_radius=8,
            fg_color=COLOR_INPUT_BG,
            border_color=COLOR_BORDER,
            font=ctk.CTkFont(family="SF Pro Display", size=14),
            width=320,
        )
        self.setup_pin_entry.grid(row=2, column=0, padx=32, pady=6)

        self.setup_confirm_entry = ctk.CTkEntry(
            center_card,
            placeholder_text="Confirm PIN",
            show="*",
            height=40,
            corner_radius=8,
            fg_color=COLOR_INPUT_BG,
            border_color=COLOR_BORDER,
            font=ctk.CTkFont(family="SF Pro Display", size=14),
            width=320,
        )
        self.setup_confirm_entry.grid(row=3, column=0, padx=32, pady=6)

        self.setup_err_lbl = ctk.CTkLabel(
            center_card,
            text="",
            font=ctk.CTkFont(family="SF Pro Display", size=12),
            text_color=COLOR_DESTRUCTIVE,
        )
        self.setup_err_lbl.grid(row=4, column=0, padx=32, pady=(4, 12))

        setup_btn = ctk.CTkButton(
            center_card,
            text="Set PIN & Continue",
            height=40,
            width=320,
            corner_radius=8,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            text_color=COLOR_TEXT_PRIMARY,
            font=ctk.CTkFont(family="SF Pro Display", size=14, weight="bold"),
            command=self._handle_setup_pin,
        )
        setup_btn.grid(row=5, column=0, padx=32, pady=(0, 28))

        self.setup_pin_entry.focus()
        self.bind("<Return>", lambda _e: self._handle_setup_pin())

    def _handle_setup_pin(self) -> None:
        pin = self.setup_pin_entry.get().strip()
        confirm = self.setup_confirm_entry.get().strip()

        if len(pin) < 4 or len(pin) > 16:
            self.setup_err_lbl.configure(text="PIN must be between 4 and 16 characters.")
            self.setup_pin_entry.focus()
            return

        if pin != confirm:
            self.setup_err_lbl.configure(text="PIN entries do not match.")
            self.setup_confirm_entry.delete(0, "end")
            self.setup_confirm_entry.focus()
            return

        database.set_user_pin(pin)
        self.unbind("<Return>")
        self.is_authenticated = True
        self.last_activity_time = time.time()
        self._show_authenticated_app()

    def _show_pin_lock_view(self) -> None:
        self.is_authenticated = False
        self._clear_main_container()

        center_card = ctk.CTkFrame(
            self.main_container,
            corner_radius=16,
            fg_color=COLOR_PANEL_BG,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        center_card.place(relx=0.5, rely=0.5, anchor="center")
        center_card.configure(width=380)

        title_lbl = ctk.CTkLabel(
            center_card,
            text="Reflect",
            font=ctk.CTkFont(family="SF Pro Display", size=24, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY,
        )
        title_lbl.grid(row=0, column=0, padx=32, pady=(32, 4), sticky="ew")

        sub_lbl = ctk.CTkLabel(
            center_card,
            text="Enter your PIN to unlock your personal notes.",
            font=ctk.CTkFont(family="SF Pro Display", size=13),
            text_color=COLOR_TEXT_SECONDARY,
        )
        sub_lbl.grid(row=1, column=0, padx=32, pady=(0, 20), sticky="ew")

        self.unlock_pin_entry = ctk.CTkEntry(
            center_card,
            placeholder_text="Enter PIN",
            show="*",
            height=42,
            corner_radius=8,
            fg_color=COLOR_INPUT_BG,
            border_color=COLOR_BORDER,
            font=ctk.CTkFont(family="SF Pro Display", size=15),
            width=280,
            justify="center",
        )
        self.unlock_pin_entry.grid(row=2, column=0, padx=32, pady=6)

        self.unlock_err_lbl = ctk.CTkLabel(
            center_card,
            text="",
            font=ctk.CTkFont(family="SF Pro Display", size=12),
            text_color=COLOR_DESTRUCTIVE,
        )
        self.unlock_err_lbl.grid(row=3, column=0, padx=32, pady=(4, 12))

        unlock_btn = ctk.CTkButton(
            center_card,
            text="Unlock",
            height=40,
            width=280,
            corner_radius=8,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            text_color=COLOR_TEXT_PRIMARY,
            font=ctk.CTkFont(family="SF Pro Display", size=14, weight="bold"),
            command=self._handle_unlock,
        )
        unlock_btn.grid(row=4, column=0, padx=32, pady=(0, 32))

        self.unlock_pin_entry.focus()
        self.bind("<Return>", lambda _e: self._handle_unlock())

    def _handle_unlock(self) -> None:
        entered = self.unlock_pin_entry.get().strip()
        if not entered:
            self.unlock_err_lbl.configure(text="Please enter your PIN.")
            self.unlock_pin_entry.focus()
            return

        if database.verify_pin(entered):
            self.unbind("<Return>")
            self.is_authenticated = True
            self.last_activity_time = time.time()
            self._show_authenticated_app()
        else:
            self.unlock_err_lbl.configure(text="Incorrect PIN. Please try again.")
            self.unlock_pin_entry.delete(0, "end")
            self.unlock_pin_entry.focus()

    # --------------------------------------------------------------------------
    # Main Authenticated Application
    # --------------------------------------------------------------------------
    def _show_authenticated_app(self) -> None:
        self._clear_main_container()

        self.main_container.grid_rowconfigure(0, weight=0)
        self.main_container.grid_rowconfigure(1, weight=1)

        # ----------------------------------------------------------------------
        # Unified macOS Top Bar
        # ----------------------------------------------------------------------
        self.top_bar = ctk.CTkFrame(
            self.main_container,
            height=48,
            corner_radius=12,
            fg_color=COLOR_PANEL_BG,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        self.top_bar.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 10))
        self.top_bar.grid_propagate(False)

        self.top_bar.grid_columnconfigure(0, weight=1)
        self.top_bar.grid_columnconfigure(1, weight=0)
        self.top_bar.grid_columnconfigure(2, weight=1)
        self.top_bar.grid_rowconfigure(0, weight=1)

        # Left: App Title
        app_title = ctk.CTkLabel(
            self.top_bar,
            text="Reflect",
            font=ctk.CTkFont(family="SF Pro Display", size=18, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY,
        )
        app_title.grid(row=0, column=0, sticky="w", padx=(16, 0))

        # Center: Segmented Navigation
        self.nav_segmented = ctk.CTkSegmentedButton(
            self.top_bar,
            values=["Journal", "Insights"],
            command=self._on_nav_changed,
            height=30,
            corner_radius=15,
            border_width=1,
            font=ctk.CTkFont(family="SF Pro Display", size=13, weight="bold"),
            fg_color=COLOR_INPUT_BG,
            selected_color=COLOR_ACCENT,
            selected_hover_color=COLOR_ACCENT_HOVER,
            unselected_color=COLOR_INPUT_BG,
            unselected_hover_color=COLOR_CARD_HOVER,
            text_color=COLOR_TEXT_PRIMARY,
        )
        self.nav_segmented.set("Journal")
        self.nav_segmented.grid(row=0, column=1)

        # Right: Secondary Actions (Zen Mode, Change PIN, Lock)
        right_actions = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        right_actions.grid(row=0, column=2, sticky="e", padx=(0, 16))
        right_actions.grid_rowconfigure(0, weight=1)

        self.zen_toggle_btn = ctk.CTkButton(
            right_actions,
            text="Zen Mode",
            width=76,
            height=28,
            corner_radius=8,
            fg_color=COLOR_SECONDARY_BTN,
            hover_color=COLOR_SECONDARY_HOVER,
            text_color=COLOR_TEXT_PRIMARY,
            font=ctk.CTkFont(family="SF Pro Display", size=12, weight="bold"),
            command=self.toggle_zen_mode,
        )
        self.zen_toggle_btn.grid(row=0, column=0, padx=(0, 8), pady=10)

        change_pin_btn = ctk.CTkButton(
            right_actions,
            text="Change PIN",
            width=88,
            height=28,
            corner_radius=8,
            fg_color=COLOR_SECONDARY_BTN,
            hover_color=COLOR_SECONDARY_HOVER,
            text_color=COLOR_TEXT_PRIMARY,
            font=ctk.CTkFont(family="SF Pro Display", size=12, weight="bold"),
            command=self._open_change_pin_dialog,
        )
        change_pin_btn.grid(row=0, column=1, padx=(0, 8), pady=10)

        lock_btn = ctk.CTkButton(
            right_actions,
            text="Lock",
            width=62,
            height=28,
            corner_radius=8,
            fg_color=COLOR_SECONDARY_BTN,
            hover_color=COLOR_SECONDARY_HOVER,
            text_color=COLOR_TEXT_PRIMARY,
            font=ctk.CTkFont(family="SF Pro Display", size=12, weight="bold"),
            command=self._lock_app,
        )
        lock_btn.grid(row=0, column=2, pady=10)

        # ----------------------------------------------------------------------
        # Content Container
        # ----------------------------------------------------------------------
        self.content_container = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.content_container.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 14))
        self.content_container.grid_columnconfigure(0, weight=1)
        self.content_container.grid_rowconfigure(0, weight=1)

        self.journal_panel = ctk.CTkFrame(self.content_container, fg_color="transparent")
        self.insights_panel = ctk.CTkFrame(self.content_container, fg_color="transparent")

        self._build_journal_panel()
        self._build_insights_panel()

        self._switch_view("Journal")
        self.reload_entries()
        self._restore_draft()

    def _on_nav_changed(self, value: str) -> None:
        self._save_draft_now()
        self._switch_view(value)

    def _switch_view(self, view_name: str) -> None:
        self.current_tab = view_name
        if view_name == "Journal":
            self.insights_panel.grid_forget()
            self.journal_panel.grid(row=0, column=0, sticky="nsew")
        else:
            self.journal_panel.grid_forget()
            self.insights_panel.grid(row=0, column=0, sticky="nsew")
            self.refresh_insights()

    def _open_change_pin_dialog(self) -> None:
        dialog = ChangePinDialog(self)
        if dialog.success:
            MessageDialog(self, title="Success", message="Your security PIN has been updated.")

    def _lock_app(self) -> None:
        if self.is_zen_mode:
            self.toggle_zen_mode()
        self._save_draft_now()
        self.is_authenticated = False
        self.editing_entry_id = None
        self._show_pin_lock_view()

    # --------------------------------------------------------------------------
    # Zen / Focus Mode
    # --------------------------------------------------------------------------
    def toggle_zen_mode(self) -> None:
        """Toggle distraction-free writing environment."""
        self.is_zen_mode = not self.is_zen_mode

        if self.is_zen_mode:
            # Hide top bar and right list
            self.top_bar.grid_remove()
            self.right_frame.grid_remove()

            # Expand editor panel to full width
            self.journal_panel.grid_columnconfigure(0, weight=1)
            self.journal_panel.grid_columnconfigure(1, weight=0)
            self.left_frame.grid_configure(padx=80, pady=(20, 20))

            # Show floating exit button
            self.zen_exit_btn.grid(row=0, column=1, sticky="e", padx=(0, 20), pady=(16, 12))
            self.zen_toggle_btn.configure(text="Exit Zen")
        else:
            # Restore standard layout
            self.top_bar.grid()
            self.right_frame.grid()

            self.journal_panel.grid_columnconfigure(0, weight=2, uniform="col")
            self.journal_panel.grid_columnconfigure(1, weight=3, uniform="col")
            self.left_frame.grid_configure(padx=(0, 10), pady=0)

            self.zen_exit_btn.grid_remove()
            self.zen_toggle_btn.configure(text="Zen Mode")

    # --------------------------------------------------------------------------
    # Auto-Save Draft System
    # --------------------------------------------------------------------------
    def _schedule_auto_save(self, _event: Any = None) -> None:
        if self._draft_timer_id is not None:
            self.after_cancel(self._draft_timer_id)
        self._draft_timer_id = self.after(DRAFT_DEBOUNCE_MS, self._save_draft_now)

    def _save_draft_now(self) -> None:
        if self._draft_timer_id is not None:
            self.after_cancel(self._draft_timer_id)
            self._draft_timer_id = None

        if self.editing_entry_id is not None or not hasattr(self, "title_entry"):
            return

        title = self.title_entry.get().strip()
        mood = self.mood_var.get()
        content = self.content_textbox.get("1.0", "end-1c").strip()

        if title or content:
            database.save_draft(title=title, mood=mood, content=content)
        else:
            database.clear_draft()

    def _restore_draft(self) -> None:
        if self.editing_entry_id is not None or not hasattr(self, "title_entry"):
            return

        draft = database.load_draft()
        if draft:
            self.title_entry.delete(0, "end")
            self.title_entry.insert(0, draft.get("title", ""))

            mood = draft.get("mood", MOOD_OPTIONS[0])
            if mood in MOOD_OPTIONS:
                self.mood_var.set(mood)

            self.content_textbox.delete("1.0", "end")
            self.content_textbox.insert("1.0", draft.get("content", ""))

    # --------------------------------------------------------------------------
    # Quick Journaling Templates
    # --------------------------------------------------------------------------
    def _on_template_selected(self, template_name: str) -> None:
        if template_name not in JOURNAL_TEMPLATES or template_name == "Templates":
            return

        content = self.content_textbox.get("1.0", "end-1c").strip()
        if content:
            dialog = ConfirmDialog(
                parent=self,
                title="Overwrite Content",
                message="Applying this template will replace the current editor content. Continue?",
                confirm_text="Replace",
                cancel_text="Cancel",
                confirm_color=COLOR_ACCENT,
                confirm_hover=COLOR_ACCENT_HOVER,
            )
            if not dialog.result:
                self.template_dropdown.set("Templates")
                return

        template_text = JOURNAL_TEMPLATES[template_name]
        self.content_textbox.delete("1.0", "end")
        self.content_textbox.insert("1.0", template_text)
        self.content_textbox.focus()
        self._schedule_auto_save()
        self.template_dropdown.set("Templates")

    # --------------------------------------------------------------------------
    # Journal Panel (Two-Column Layout)
    # --------------------------------------------------------------------------
    def _build_journal_panel(self) -> None:
        self.journal_panel.grid_columnconfigure(0, weight=2, uniform="col")
        self.journal_panel.grid_columnconfigure(1, weight=3, uniform="col")
        self.journal_panel.grid_rowconfigure(0, weight=1)

        # Left Column: Form Panel
        self.left_frame = ctk.CTkFrame(
            self.journal_panel,
            corner_radius=14,
            fg_color=COLOR_PANEL_BG,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        self.left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=0)
        self.left_frame.grid_columnconfigure(0, weight=1)
        self.left_frame.grid_rowconfigure(7, weight=1)

        # Form Header row with Zen Exit button
        form_top_bar = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        form_top_bar.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 10))
        form_top_bar.grid_columnconfigure(0, weight=1)

        self.form_header = ctk.CTkLabel(
            form_top_bar,
            text="New Entry",
            font=ctk.CTkFont(family="SF Pro Display", size=18, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY,
            anchor="w",
        )
        self.form_header.grid(row=0, column=0, sticky="w")

        self.zen_exit_btn = ctk.CTkButton(
            form_top_bar,
            text="Exit Zen",
            width=70,
            height=26,
            corner_radius=8,
            fg_color=COLOR_SECONDARY_BTN,
            hover_color=COLOR_SECONDARY_HOVER,
            text_color=COLOR_TEXT_PRIMARY,
            font=ctk.CTkFont(family="SF Pro Display", size=11, weight="bold"),
            command=self.toggle_zen_mode,
        )
        # Hidden by default

        # Title Label & Template Selector in one row
        title_header_bar = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        title_header_bar.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 4))
        title_header_bar.grid_columnconfigure(0, weight=1)

        title_label = ctk.CTkLabel(
            title_header_bar,
            text="Title",
            font=ctk.CTkFont(family="SF Pro Display", size=12, weight="bold"),
            text_color=COLOR_TEXT_SECONDARY,
            anchor="w",
        )
        title_label.grid(row=0, column=0, sticky="w")

        # Quick Journaling Templates Dropdown
        self.template_dropdown = ctk.CTkOptionMenu(
            title_header_bar,
            values=["Templates", "Daily Gratitude", "Evening Review", "Brain Dump"],
            command=self._on_template_selected,
            height=26,
            width=130,
            corner_radius=8,
            fg_color=COLOR_INPUT_BG,
            button_color=COLOR_SECONDARY_BTN,
            button_hover_color=COLOR_SECONDARY_HOVER,
            dropdown_fg_color=COLOR_PANEL_BG,
            dropdown_hover_color=COLOR_CARD_HOVER,
            font=ctk.CTkFont(family="SF Pro Display", size=11),
            dropdown_font=ctk.CTkFont(family="SF Pro Display", size=11),
        )
        self.template_dropdown.set("Templates")
        self.template_dropdown.grid(row=0, column=1, sticky="e")

        self.title_entry = ctk.CTkEntry(
            self.left_frame,
            placeholder_text="Enter entry title...",
            height=36,
            corner_radius=8,
            fg_color=COLOR_INPUT_BG,
            border_color=COLOR_BORDER,
            font=ctk.CTkFont(family="SF Pro Display", size=13),
        )
        self.title_entry.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 12))
        self.title_entry.bind("<KeyRelease>", self._schedule_auto_save)

        # Mood dropdown
        mood_label = ctk.CTkLabel(
            self.left_frame,
            text="Mood",
            font=ctk.CTkFont(family="SF Pro Display", size=12, weight="bold"),
            text_color=COLOR_TEXT_SECONDARY,
            anchor="w",
        )
        mood_label.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 4))

        self.mood_var = ctk.StringVar(value=MOOD_OPTIONS[0])
        self.mood_dropdown = ctk.CTkOptionMenu(
            self.left_frame,
            values=MOOD_OPTIONS,
            variable=self.mood_var,
            command=lambda _val: self._schedule_auto_save(),
            height=36,
            corner_radius=8,
            fg_color=COLOR_INPUT_BG,
            button_color=COLOR_SECONDARY_BTN,
            button_hover_color=COLOR_SECONDARY_HOVER,
            dropdown_fg_color=COLOR_PANEL_BG,
            dropdown_hover_color=COLOR_CARD_HOVER,
            font=ctk.CTkFont(family="SF Pro Display", size=13),
            dropdown_font=ctk.CTkFont(family="SF Pro Display", size=12),
        )
        self.mood_dropdown.grid(row=4, column=0, sticky="ew", padx=20, pady=(0, 12))

        # Content
        content_label = ctk.CTkLabel(
            self.left_frame,
            text="Content",
            font=ctk.CTkFont(family="SF Pro Display", size=12, weight="bold"),
            text_color=COLOR_TEXT_SECONDARY,
            anchor="w",
        )
        content_label.grid(row=5, column=0, sticky="ew", padx=20, pady=(0, 4))

        self.content_textbox = ctk.CTkTextbox(
            self.left_frame,
            font=ctk.CTkFont(family="SF Pro Display", size=13),
            wrap="word",
            corner_radius=10,
            fg_color=COLOR_INPUT_BG,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        self.content_textbox.grid(row=6, column=0, sticky="nsew", padx=20, pady=(0, 14))
        self.content_textbox.bind("<KeyRelease>", self._schedule_auto_save)

        # Action Buttons
        self.button_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        self.button_frame.grid(row=7, column=0, sticky="ew", padx=20, pady=(0, 16))
        self.button_frame.grid_columnconfigure(0, weight=1)

        self.save_button = ctk.CTkButton(
            self.button_frame,
            text="Save Entry",
            height=38,
            corner_radius=8,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            text_color=COLOR_TEXT_PRIMARY,
            font=ctk.CTkFont(family="SF Pro Display", size=13, weight="bold"),
            command=self.submit_form,
        )
        self.save_button.grid(row=0, column=0, sticky="ew")

        self.cancel_edit_button = ctk.CTkButton(
            self.button_frame,
            text="Cancel Edit",
            height=38,
            corner_radius=8,
            fg_color=COLOR_SECONDARY_BTN,
            hover_color=COLOR_SECONDARY_HOVER,
            text_color=COLOR_TEXT_PRIMARY,
            font=ctk.CTkFont(family="SF Pro Display", size=13, weight="bold"),
            command=self.cancel_edit,
        )

        # Right Column: List, Search, Time Filter, Mood Chips, On This Day Widget
        self.right_frame = ctk.CTkFrame(
            self.journal_panel,
            corner_radius=14,
            fg_color=COLOR_PANEL_BG,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        self.right_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=0)
        self.right_frame.grid_columnconfigure(0, weight=1)
        self.right_frame.grid_rowconfigure(5, weight=1)

        # Header bar with Time Range Filter
        header_bar = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        header_bar.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 6))
        header_bar.grid_columnconfigure(0, weight=1)

        history_title = ctk.CTkLabel(
            header_bar,
            text="Entries",
            font=ctk.CTkFont(family="SF Pro Display", size=18, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY,
            anchor="w",
        )
        history_title.grid(row=0, column=0, sticky="w")

        # Time range filter
        self.time_filter_var = ctk.StringVar(value="All Time")
        time_options = ["All Time", "Today", "This Week", "This Month"]
        self.time_filter_dropdown = ctk.CTkOptionMenu(
            header_bar,
            values=time_options,
            variable=self.time_filter_var,
            command=self._on_time_filter_changed,
            height=26,
            width=100,
            corner_radius=8,
            fg_color=COLOR_INPUT_BG,
            button_color=COLOR_SECONDARY_BTN,
            button_hover_color=COLOR_SECONDARY_HOVER,
            dropdown_fg_color=COLOR_PANEL_BG,
            dropdown_hover_color=COLOR_CARD_HOVER,
            font=ctk.CTkFont(family="SF Pro Display", size=11, weight="bold"),
            dropdown_font=ctk.CTkFont(family="SF Pro Display", size=11),
        )
        self.time_filter_dropdown.grid(row=0, column=1, padx=(0, 10))

        self.count_label = ctk.CTkLabel(
            header_bar,
            text="0 entries",
            font=ctk.CTkFont(family="SF Pro Display", size=12),
            text_color=COLOR_TEXT_MUTED,
        )
        self.count_label.grid(row=0, column=2, sticky="e")

        # Search bar
        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.render_entry_cards())

        self.search_entry = ctk.CTkEntry(
            self.right_frame,
            textvariable=self.search_var,
            placeholder_text="Search entries...",
            height=34,
            corner_radius=8,
            fg_color=COLOR_INPUT_BG,
            border_color=COLOR_BORDER,
            font=ctk.CTkFont(family="SF Pro Display", size=13),
        )
        self.search_entry.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 6))

        # Mood Filter Chips Row
        chips_scroll = ctk.CTkScrollableFrame(
            self.right_frame,
            height=32,
            orientation="horizontal",
            fg_color="transparent",
        )
        chips_scroll.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 6))

        all_filter_options = ["All"] + MOOD_OPTIONS
        self.filter_buttons = {}

        for col_idx, mood in enumerate(all_filter_options):
            is_active = (mood == self.selected_mood_filter)
            chip_btn = ctk.CTkButton(
                chips_scroll,
                text=mood,
                width=0,
                height=26,
                corner_radius=13,
                font=ctk.CTkFont(family="SF Pro Display", size=11, weight="bold"),
                fg_color=COLOR_ACCENT if is_active else COLOR_INPUT_BG,
                hover_color=COLOR_ACCENT_HOVER if is_active else COLOR_CARD_HOVER,
                text_color=COLOR_TEXT_PRIMARY,
                border_width=1,
                border_color=COLOR_ACCENT if is_active else COLOR_BORDER,
                command=lambda m=mood: self._set_mood_filter(m),
            )
            chip_btn.grid(row=0, column=col_idx, padx=3, pady=2)
            self.filter_buttons[mood] = chip_btn

        # "On This Day" Widget (Collapsible Card)
        self.on_this_day_frame = ctk.CTkFrame(
            self.right_frame,
            corner_radius=10,
            fg_color=COLOR_INPUT_BG,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        self.on_this_day_frame.grid_columnconfigure(0, weight=1)
        # Will be gridded into row=3 dynamically if matching memories exist

        # Scrollable entry list
        self.scrollable_entries = ctk.CTkScrollableFrame(
            self.right_frame,
            fg_color="transparent",
            corner_radius=10,
        )
        self.scrollable_entries.grid(row=4, column=0, sticky="nsew", padx=10, pady=(0, 12))
        self.scrollable_entries.grid_columnconfigure(0, weight=1)

    def _on_time_filter_changed(self, value: str) -> None:
        self.selected_time_filter = value
        self.render_entry_cards()

    def _set_mood_filter(self, mood: str) -> None:
        self.selected_mood_filter = mood

        for m, btn in self.filter_buttons.items():
            if m == mood:
                btn.configure(
                    fg_color=COLOR_ACCENT,
                    hover_color=COLOR_ACCENT_HOVER,
                    border_color=COLOR_ACCENT,
                )
            else:
                btn.configure(
                    fg_color=COLOR_INPUT_BG,
                    hover_color=COLOR_CARD_HOVER,
                    border_color=COLOR_BORDER,
                )

        self.render_entry_cards()

    # --------------------------------------------------------------------------
    # "On This Day" Logic
    # --------------------------------------------------------------------------
    def _update_on_this_day_widget(self) -> None:
        """Find entries created on the same day-of-month and month in previous years/months."""
        for widget in self.on_this_day_frame.winfo_children():
            widget.destroy()

        today = datetime.now()
        current_date_str = today.strftime("%Y-%m-%d")
        current_day = today.day
        current_month = today.month

        matching_entries = []
        for e in self.all_entries:
            try:
                edate = datetime.strptime(e["created_at"].split()[0], "%Y-%m-%d")
                # Exclude entries written today
                if edate.strftime("%Y-%m-%d") == current_date_str:
                    continue
                # Same day and same month from a past year or exactly same day in past months
                if edate.day == current_day and (edate.month == current_month or edate < today - timedelta(days=27)):
                    matching_entries.append((edate, e))
            except Exception:
                continue

        if not matching_entries:
            self.on_this_day_frame.grid_remove()
            return

        # Show the most recent historical entry for today's date
        matching_entries.sort(key=lambda item: item[0], reverse=True)
        edate, target_entry = matching_entries[0]

        years_ago = today.year - edate.year
        months_ago = (today.year - edate.year) * 12 + (today.month - edate.month)
        if years_ago >= 1:
            time_tag = f"{years_ago} year{'s' if years_ago > 1 else ''} ago today"
        else:
            time_tag = f"{months_ago} month{'s' if months_ago > 1 else ''} ago today"

        self.on_this_day_frame.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 8))

        header_lbl = ctk.CTkLabel(
            self.on_this_day_frame,
            text=f"On This Day ({time_tag}): {target_entry['title']}",
            font=ctk.CTkFont(family="SF Pro Display", size=12, weight="bold"),
            text_color=COLOR_ACCENT,
            anchor="w",
            cursor="hand2",
        )
        header_lbl.grid(row=0, column=0, sticky="w", padx=12, pady=(8, 2))

        preview_lbl = ctk.CTkLabel(
            self.on_this_day_frame,
            text=format_snippet(target_entry["content"], 90),
            font=ctk.CTkFont(family="SF Pro Display", size=11),
            text_color=COLOR_TEXT_SECONDARY,
            anchor="w",
            justify="left",
            cursor="hand2",
        )
        preview_lbl.grid(row=1, column=0, sticky="w", padx=12, pady=(0, 8))

        for w in (self.on_this_day_frame, header_lbl, preview_lbl):
            w.bind("<Button-1>", lambda _e, ent=target_entry: self.start_edit_entry(ent))

    # --------------------------------------------------------------------------
    # Insights Panel (macOS Analytics Layout)
    # --------------------------------------------------------------------------
    def _build_insights_panel(self) -> None:
        self.insights_panel.grid_columnconfigure(0, weight=1)
        self.insights_panel.grid_rowconfigure(2, weight=1)

        insights_header = ctk.CTkFrame(self.insights_panel, fg_color="transparent")
        insights_header.grid(row=0, column=0, sticky="ew", padx=4, pady=(4, 10))
        insights_header.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            insights_header,
            text="Mood Analytics & Trends",
            font=ctk.CTkFont(family="SF Pro Display", size=18, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY,
            anchor="w",
        )
        title.grid(row=0, column=0, sticky="w")

        # Metric Cards row
        self.summary_frame = ctk.CTkFrame(self.insights_panel, fg_color="transparent")
        self.summary_frame.grid(row=1, column=0, sticky="ew", padx=0, pady=(0, 12))
        self.summary_frame.grid_columnconfigure((0, 1, 2), weight=1, uniform="metric")

        self.metric_total = self._create_metric_card(self.summary_frame, "Total Entries", "0", 0)
        self.metric_top_mood = self._create_metric_card(self.summary_frame, "Dominant Mood", "None", 1)
        self.metric_variety = self._create_metric_card(self.summary_frame, "Mood Variety", "0 / 8", 2)

        # Visualization container
        self.chart_container = ctk.CTkFrame(
            self.insights_panel,
            corner_radius=14,
            fg_color=COLOR_PANEL_BG,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        self.chart_container.grid(row=2, column=0, sticky="nsew", padx=0, pady=0)
        self.chart_container.grid_columnconfigure(0, weight=1)
        self.chart_container.grid_rowconfigure(0, weight=1)

    def _create_metric_card(self, parent: Any, label: str, value: str, col: int) -> ctk.CTkLabel:
        card = ctk.CTkFrame(
            parent,
            corner_radius=12,
            fg_color=COLOR_PANEL_BG,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        card.grid(row=0, column=col, sticky="ew", padx=4, pady=0)
        card.grid_columnconfigure(0, weight=1)

        title_lbl = ctk.CTkLabel(
            card,
            text=label,
            font=ctk.CTkFont(family="SF Pro Display", size=11, weight="bold"),
            text_color=COLOR_TEXT_MUTED,
        )
        title_lbl.grid(row=0, column=0, padx=12, pady=(10, 2))

        val_lbl = ctk.CTkLabel(
            card,
            text=value,
            font=ctk.CTkFont(family="SF Pro Display", size=18, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY,
        )
        val_lbl.grid(row=1, column=0, padx=12, pady=(0, 10))
        return val_lbl

    def refresh_insights(self) -> None:
        for widget in self.chart_container.winfo_children():
            widget.destroy()

        if not self.all_entries:
            self.metric_total.configure(text="0")
            self.metric_top_mood.configure(text="None")
            self.metric_variety.configure(text=f"0 / {len(MOOD_OPTIONS)}")

            empty_lbl = ctk.CTkLabel(
                self.chart_container,
                text="No entries recorded yet.\nStart writing in the Journal tab to generate insights.",
                font=ctk.CTkFont(family="SF Pro Display", size=14),
                text_color=COLOR_TEXT_MUTED,
                justify="center",
            )
            empty_lbl.grid(row=0, column=0, pady=80, padx=20)
            return

        total_entries = len(self.all_entries)
        mood_counts = Counter(normalize_mood_name(e["mood"]) for e in self.all_entries)

        most_common = mood_counts.most_common(1)
        top_mood_name = most_common[0][0] if most_common else "None"
        distinct_count = len([m for m in MOOD_OPTIONS if mood_counts[m] > 0])

        self.metric_total.configure(text=str(total_entries))
        self.metric_top_mood.configure(text=top_mood_name)
        self.metric_variety.configure(text=f"{distinct_count} / {len(MOOD_OPTIONS)}")

        if MATPLOTLIB_AVAILABLE:
            self._render_matplotlib_chart(mood_counts, total_entries)
        else:
            self._render_native_progress_bars(mood_counts, total_entries)

    def _render_matplotlib_chart(self, mood_counts: Counter, total_entries: int) -> None:
        labels = list(reversed(MOOD_OPTIONS))
        counts = [mood_counts[m] for m in labels]
        percentages = [(c / total_entries) * 100 for c in counts]
        colors = [get_mood_color(m) for m in labels]

        fig_bg = COLOR_PANEL_BG
        text_color = COLOR_TEXT_PRIMARY
        muted_color = COLOR_TEXT_SECONDARY
        grid_color = COLOR_BORDER

        fig = Figure(figsize=(8.5, 4.2), dpi=100, facecolor=fig_bg)
        ax = fig.add_subplot(111)
        ax.set_facecolor(fig_bg)

        y_positions = range(len(labels))
        bars = ax.barh(y_positions, percentages, color=colors, height=0.55, align="center")

        ax.set_yticks(y_positions)
        ax.set_yticklabels(labels, color=text_color, fontsize=10, fontweight="bold")
        ax.set_xlabel("Percentage of Entries (%)", color=muted_color, fontsize=11, fontweight="bold", labelpad=8)
        ax.tick_params(colors=muted_color, labelsize=9)

        max_pct = max(percentages) if percentages else 0
        upper_limit = max(100, int(max_pct + 15))
        ax.set_xlim(0, upper_limit)

        ax.grid(axis="x", linestyle="--", alpha=0.35, color=grid_color)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["bottom"].set_color(grid_color)
        ax.spines["left"].set_color(grid_color)

        for bar, count, pct in zip(bars, counts, percentages):
            if count > 0:
                ax.text(
                    bar.get_width() + 1.2,
                    bar.get_y() + bar.get_height() / 2,
                    f"{count} ({pct:.1f}%)",
                    va="center",
                    ha="left",
                    color=text_color,
                    fontsize=9,
                    fontweight="bold",
                )

        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=self.chart_container)
        canvas.draw()
        canvas_widget = canvas.get_tk_widget()
        canvas_widget.configure(bg=fig_bg, highlightthickness=0)
        canvas_widget.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)

    def _render_native_progress_bars(self, mood_counts: Counter, total_entries: int) -> None:
        scroll_bars = ctk.CTkScrollableFrame(self.chart_container, fg_color="transparent")
        scroll_bars.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
        scroll_bars.grid_columnconfigure(1, weight=1)

        for idx, mood in enumerate(MOOD_OPTIONS):
            count = mood_counts[mood]
            pct = (count / total_entries) if total_entries > 0 else 0

            lbl = ctk.CTkLabel(
                scroll_bars,
                text=mood,
                font=ctk.CTkFont(family="SF Pro Display", size=13, weight="bold"),
                text_color=COLOR_TEXT_PRIMARY,
                width=90,
                anchor="w",
            )
            lbl.grid(row=idx, column=0, padx=(0, 10), pady=6, sticky="w")

            prog = ctk.CTkProgressBar(
                scroll_bars,
                height=14,
                corner_radius=7,
                fg_color=COLOR_INPUT_BG,
            )
            prog.grid(row=idx, column=1, sticky="ew", padx=(0, 12), pady=6)
            prog.set(pct)
            prog.configure(progress_color=get_mood_color(mood))

            stat_lbl = ctk.CTkLabel(
                scroll_bars,
                text=f"{count} ({pct * 100:.1f}%)",
                font=ctk.CTkFont(family="SF Pro Display", size=12),
                text_color=COLOR_TEXT_SECONDARY,
                width=80,
                anchor="e",
            )
            stat_lbl.grid(row=idx, column=2, padx=(0, 4), pady=6, sticky="e")

    # --------------------------------------------------------------------------
    # Database Actions & State Management
    # --------------------------------------------------------------------------
    def reload_entries(self) -> None:
        self.all_entries = database.get_all_entries()
        self.render_entry_cards()
        self._update_on_this_day_widget()
        if self.current_tab == "Insights":
            self.refresh_insights()

    def toggle_pin(self, entry_id: int) -> None:
        """Toggle pinned status for entry and refresh list."""
        database.toggle_pin_entry(entry_id)
        self.reload_entries()

    def render_entry_cards(self) -> None:
        """Filter entries according to text search, mood chip, and time range."""
        for widget in self.scrollable_entries.winfo_children():
            widget.destroy()

        query = self.search_var.get().strip().lower()
        selected_mood = self.selected_mood_filter
        selected_time = self.selected_time_filter

        now = datetime.now()
        today_date = now.date()

        filtered = []
        for e in self.all_entries:
            norm_mood = normalize_mood_name(e["mood"])

            # 1. Mood Filter
            if selected_mood != "All" and norm_mood.lower() != selected_mood.lower():
                continue

            # 2. Time Range Filter
            if selected_time != "All Time":
                try:
                    entry_dt = datetime.strptime(e["created_at"], "%Y-%m-%d %H:%M:%S")
                    entry_date = entry_dt.date()

                    if selected_time == "Today":
                        if entry_date != today_date:
                            continue
                    elif selected_time == "This Week":
                        # Current calendar week (Monday to Sunday)
                        start_of_week = today_date - timedelta(days=today_date.weekday())
                        if entry_date < start_of_week or entry_date > today_date:
                            continue
                    elif selected_time == "This Month":
                        if entry_date.year != today_date.year or entry_date.month != today_date.month:
                            continue
                except Exception:
                    pass

            # 3. Search Query Filter
            if query:
                matches_search = (
                    query in e["title"].lower()
                    or query in e["content"].lower()
                    or query in norm_mood.lower()
                )
                if not matches_search:
                    continue

            filtered.append(e)

        total = len(filtered)
        if query or selected_mood != "All" or selected_time != "All Time":
            self.count_label.configure(text=f"{total} of {len(self.all_entries)} matches")
        else:
            self.count_label.configure(text=f"{total} {'entry' if total == 1 else 'entries'}")

        if not filtered:
            msg = "No entries match your search/filter." if (query or selected_mood != "All" or selected_time != "All Time") else "No entries yet.\nCreate your first entry on the left."
            empty_label = ctk.CTkLabel(
                self.scrollable_entries,
                text=msg,
                font=ctk.CTkFont(family="SF Pro Display", size=13),
                text_color=COLOR_TEXT_MUTED,
                justify="center",
            )
            empty_label.grid(row=0, column=0, pady=70, padx=20)
            return

        for idx, entry in enumerate(filtered):
            card = EntryCard(
                self.scrollable_entries,
                entry=entry,
                on_edit=self.start_edit_entry,
                on_delete=self.delete_existing_entry,
                on_toggle_pin=self.toggle_pin,
                is_editing=(entry["id"] == self.editing_entry_id),
            )
            card.grid(row=idx, column=0, sticky="ew", padx=4, pady=5)

    def start_edit_entry(self, entry: Dict[str, Any]) -> None:
        self._save_draft_now()
        self.editing_entry_id = entry["id"]

        if self.current_tab != "Journal":
            self.nav_segmented.set("Journal")
            self._switch_view("Journal")

        self.form_header.configure(text="Edit Entry")
        self.save_button.configure(
            text="Update Entry",
            fg_color=COLOR_SUCCESS,
            hover_color=COLOR_SUCCESS_HOVER,
        )
        self.button_frame.grid_columnconfigure(1, weight=1)
        self.save_button.grid_configure(padx=(0, 6))
        self.cancel_edit_button.grid(row=0, column=1, sticky="ew", padx=(6, 0))

        self.title_entry.delete(0, "end")
        self.title_entry.insert(0, entry["title"])

        matched_mood = normalize_mood_name(entry["mood"])
        if matched_mood in MOOD_OPTIONS:
            self.mood_var.set(matched_mood)
        else:
            self.mood_var.set(MOOD_OPTIONS[0])

        self.content_textbox.delete("1.0", "end")
        self.content_textbox.insert("1.0", entry["content"])
        self.content_textbox.focus()

        self.render_entry_cards()

    def cancel_edit(self) -> None:
        self.editing_entry_id = None

        self.form_header.configure(text="New Entry")
        self.save_button.configure(
            text="Save Entry",
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
        )
        self.cancel_edit_button.grid_forget()
        self.button_frame.grid_columnconfigure(1, weight=0)
        self.save_button.grid_configure(padx=0)

        self._clear_form_inputs()
        self._restore_draft()
        self.render_entry_cards()

    def _clear_form_inputs(self) -> None:
        self.title_entry.delete(0, "end")
        self.content_textbox.delete("1.0", "end")
        self.mood_var.set(MOOD_OPTIONS[0])

    def submit_form(self) -> None:
        title = self.title_entry.get().strip()
        mood = self.mood_var.get()
        content = self.content_textbox.get("1.0", "end-1c").strip()

        if not title:
            MessageDialog(self, title="Missing Title", message="Please enter a title for your entry.")
            self.title_entry.focus()
            return

        if not content:
            MessageDialog(self, title="Missing Content", message="Please enter content before saving.")
            self.content_textbox.focus()
            return

        if self.editing_entry_id is not None:
            database.update_entry(
                entry_id=self.editing_entry_id,
                title=title,
                content=content,
                mood=mood,
            )
            self.cancel_edit()
            self.reload_entries()
        else:
            database.add_entry(title=title, content=content, mood=mood)
            database.clear_draft()
            self._clear_form_inputs()
            self.reload_entries()

    def delete_existing_entry(self, entry_id: int) -> None:
        dialog = ConfirmDialog(
            parent=self,
            title="Delete Entry",
            message="Are you sure you want to delete this entry? This action cannot be undone.",
            confirm_text="Delete",
            cancel_text="Cancel",
            confirm_color=COLOR_DESTRUCTIVE,
            confirm_hover=COLOR_DESTRUCTIVE_HOVER,
        )
        if dialog.result:
            database.delete_entry(entry_id)
            if self.editing_entry_id == entry_id:
                self.cancel_edit()
            self.reload_entries()


if __name__ == "__main__":
    database.init_db()
    app = Reflect()
    app.mainloop()
