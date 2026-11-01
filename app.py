import platform
from pathlib import Path
from tkinter import messagebox
from typing import Callable, Dict, Any, Optional

import customtkinter as ctk
from PIL import Image, ImageTk

import database

# Configure global CustomTkinter appearance
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

BASE_DIR = Path(__file__).resolve().parent
ICON_PNG_PATH = BASE_DIR / "icon.png"
ICON_ICO_PATH = BASE_DIR / "icon.ico"

PREVIEW_MAX_CHARS = 120

MOOD_OPTIONS = [
    "😊 Happy",
    "😌 Calm",
    "🤩 Excited",
    "🤔 Reflective",
    "😴 Tired",
    "😢 Sad",
    "😤 Stressed",
]

MOOD_COLORS = {
    "😊 Happy": "#2eab66",
    "😌 Calm": "#3b8ed0",
    "🤩 Excited": "#d97706",
    "🤔 Reflective": "#8b5cf6",
    "😴 Tired": "#64748b",
    "😢 Sad": "#475569",
    "😤 Stressed": "#dc2626",
}


def format_snippet(content: str, max_length: int = PREVIEW_MAX_CHARS) -> str:
    """Collapse excessive whitespace and truncate content to a preview snippet."""
    normalized = " ".join(content.split())
    if len(normalized) <= max_length:
        return normalized
    return normalized[:max_length].rstrip() + "..."


class EntryCard(ctk.CTkFrame):
    """A visual card representing a single past journal entry with truncated preview and edit/delete actions."""

    def __init__(
        self,
        master: Any,
        entry: Dict[str, Any],
        on_edit: Callable[[Dict[str, Any]], None],
        on_delete: Callable[[int], None],
        is_editing: bool = False,
        **kwargs: Any,
    ) -> None:
        border_color = ("#2563eb", "#3b8ed0") if is_editing else ("#cbd5e1", "#334155")
        border_width = 2 if is_editing else 1

        super().__init__(
            master,
            corner_radius=12,
            fg_color=("#f1f5f9", "#1e293b"),
            border_width=border_width,
            border_color=border_color,
            cursor="hand2",
            **kwargs,
        )
        self.entry = entry
        self.entry_id = entry["id"]
        self.on_edit = on_edit
        self.on_delete = on_delete

        self.grid_columnconfigure(0, weight=1)

        # Header frame: Title, Mood badge, Edit button, and Delete button
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 4))
        header_frame.grid_columnconfigure(0, weight=1)

        title_label = ctk.CTkLabel(
            header_frame,
            text=entry["title"],
            font=ctk.CTkFont(size=17, weight="bold"),
            anchor="w",
            justify="left",
            cursor="hand2",
        )
        title_label.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        mood_color = MOOD_COLORS.get(entry["mood"], "#3b8ed0")
        mood_badge = ctk.CTkLabel(
            header_frame,
            text=entry["mood"],
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=mood_color,
            text_color="white",
            corner_radius=8,
            padx=10,
            pady=2,
            cursor="hand2",
        )
        mood_badge.grid(row=0, column=1, padx=(0, 8))

        edit_btn = ctk.CTkButton(
            header_frame,
            text="Edit",
            width=60,
            height=28,
            corner_radius=6,
            fg_color="#3b8ed0",
            hover_color="#2563eb",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._handle_edit,
        )
        edit_btn.grid(row=0, column=2, padx=(0, 6))

        delete_btn = ctk.CTkButton(
            header_frame,
            text="Delete",
            width=68,
            height=28,
            corner_radius=6,
            fg_color="#dc2626",
            hover_color="#b91c1c",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._handle_delete,
        )
        delete_btn.grid(row=0, column=3)

        # Timestamp
        date_label = ctk.CTkLabel(
            self,
            text=f"🕒 {entry['created_at']}",
            font=ctk.CTkFont(size=12),
            text_color=("#64748b", "#94a3b8"),
            anchor="w",
            cursor="hand2",
        )
        date_label.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 8))

        # Truncated snippet body
        snippet_text = format_snippet(entry["content"], PREVIEW_MAX_CHARS)
        content_label = ctk.CTkLabel(
            self,
            text=snippet_text,
            font=ctk.CTkFont(size=14),
            text_color=("#1e293b", "#e2e8f0"),
            anchor="w",
            justify="left",
            wraplength=460,
            cursor="hand2",
        )
        content_label.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 16))

        # Bind clicking anywhere on the card or its labels to edit the entry
        for widget in (self, header_frame, title_label, mood_badge, date_label, content_label):
            widget.bind("<Button-1>", lambda _event: self._handle_edit())

    def _handle_edit(self) -> None:
        self.on_edit(self.entry)

    def _handle_delete(self) -> None:
        self.on_delete(self.entry_id)


class Reflect(ctk.CTk):
    """Main application window for the Reflect desktop journal app."""

    def __init__(self) -> None:
        super().__init__()

        self.title("Reflect")
        self.geometry("1060x680")
        self.minsize(880, 540)

        self._set_app_icon()

        # Track the ID of the entry currently being edited (None when creating a new entry)
        self.editing_entry_id: Optional[int] = None

        # Configure two-column layout
        self.grid_columnconfigure(0, weight=2, uniform="col")
        self.grid_columnconfigure(1, weight=3, uniform="col")
        self.grid_rowconfigure(0, weight=1)

        self._build_left_column()
        self._build_right_column()
        self.refresh_entries()

    def _set_app_icon(self) -> None:
        """Dynamically load the desktop window icon across Windows and Linux."""
        current_os = platform.system()
        try:
            if current_os == "Windows" and ICON_ICO_PATH.exists():
                self.iconbitmap(str(ICON_ICO_PATH))
            elif ICON_PNG_PATH.exists():
                # Load via PIL for Linux window managers
                img = Image.open(ICON_PNG_PATH)
                self._photo_icon = ImageTk.PhotoImage(img)
                self.wm_iconphoto(True, self._photo_icon)
        except Exception:
            # Fallback gracefully if display environment restricts icon application
            pass

    def _build_left_column(self) -> None:
        """Create the left column form for adding or editing a journal entry."""
        self.left_frame = ctk.CTkFrame(self, corner_radius=14)
        self.left_frame.grid(row=0, column=0, sticky="nsew", padx=(20, 10), pady=20)
        self.left_frame.grid_columnconfigure(0, weight=1)
        self.left_frame.grid_rowconfigure(6, weight=1)

        self.form_header = ctk.CTkLabel(
            self.left_frame,
            text="✍️ New Journal Entry",
            font=ctk.CTkFont(size=22, weight="bold"),
            anchor="w",
        )
        self.form_header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 16))

        # Title input
        title_label = ctk.CTkLabel(
            self.left_frame,
            text="Title",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        )
        title_label.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 4))

        self.title_entry = ctk.CTkEntry(
            self.left_frame,
            placeholder_text="What's on your mind today?",
            height=38,
            font=ctk.CTkFont(size=14),
        )
        self.title_entry.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 14))

        # Mood dropdown
        mood_label = ctk.CTkLabel(
            self.left_frame,
            text="Current Mood",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        )
        mood_label.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 4))

        self.mood_var = ctk.StringVar(value=MOOD_OPTIONS[0])
        self.mood_dropdown = ctk.CTkOptionMenu(
            self.left_frame,
            values=MOOD_OPTIONS,
            variable=self.mood_var,
            height=38,
            font=ctk.CTkFont(size=14),
            dropdown_font=ctk.CTkFont(size=13),
        )
        self.mood_dropdown.grid(row=4, column=0, sticky="ew", padx=20, pady=(0, 14))

        # Content multi-line box
        content_label = ctk.CTkLabel(
            self.left_frame,
            text="Thoughts & Reflections",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        )
        content_label.grid(row=5, column=0, sticky="ew", padx=20, pady=(0, 4))

        self.content_textbox = ctk.CTkTextbox(
            self.left_frame,
            font=ctk.CTkFont(size=14),
            wrap="word",
            corner_radius=8,
            border_width=1,
            border_color=("#cbd5e1", "#334155"),
        )
        self.content_textbox.grid(
            row=6, column=0, sticky="nsew", padx=20, pady=(0, 16)
        )

        # Action buttons container (Save/Update + Cancel Edit)
        self.button_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        self.button_frame.grid(row=7, column=0, sticky="ew", padx=20, pady=(0, 20))
        self.button_frame.grid_columnconfigure(0, weight=1)

        self.save_button = ctk.CTkButton(
            self.button_frame,
            text="Save Entry",
            height=42,
            corner_radius=8,
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self.submit_form,
        )
        self.save_button.grid(row=0, column=0, sticky="ew")

        self.cancel_edit_button = ctk.CTkButton(
            self.button_frame,
            text="Cancel Edit",
            height=42,
            corner_radius=8,
            fg_color=("#64748b", "#475569"),
            hover_color=("#475569", "#334155"),
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.cancel_edit,
        )

    def _build_right_column(self) -> None:
        """Create the right column containing the scrollable list of past entries."""
        self.right_frame = ctk.CTkFrame(self, corner_radius=14)
        self.right_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 20), pady=20)
        self.right_frame.grid_columnconfigure(0, weight=1)
        self.right_frame.grid_rowconfigure(1, weight=1)

        header_bar = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        header_bar.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        header_bar.grid_columnconfigure(0, weight=1)

        history_title = ctk.CTkLabel(
            header_bar,
            text="📖 Past Entries",
            font=ctk.CTkFont(size=22, weight="bold"),
            anchor="w",
        )
        history_title.grid(row=0, column=0, sticky="w")

        self.count_label = ctk.CTkLabel(
            header_bar,
            text="0 entries",
            font=ctk.CTkFont(size=13),
            text_color=("#64748b", "#94a3b8"),
        )
        self.count_label.grid(row=0, column=1, sticky="e")

        self.scrollable_entries = ctk.CTkScrollableFrame(
            self.right_frame,
            fg_color="transparent",
            corner_radius=10,
        )
        self.scrollable_entries.grid(
            row=1, column=0, sticky="nsew", padx=12, pady=(0, 14)
        )
        self.scrollable_entries.grid_columnconfigure(0, weight=1)

    def start_edit_entry(self, entry: Dict[str, Any]) -> None:
        """Populate the left-hand form with the selected entry's data and switch to Edit mode."""
        self.editing_entry_id = entry["id"]

        self.form_header.configure(text="✏️ Edit Journal Entry")
        self.save_button.configure(
            text="Update Entry",
            fg_color="#2eab66",
            hover_color="#238c53",
        )
        self.button_frame.grid_columnconfigure(1, weight=1)
        self.save_button.grid_configure(padx=(0, 6))
        self.cancel_edit_button.grid(row=0, column=1, sticky="ew", padx=(6, 0))

        self.title_entry.delete(0, "end")
        self.title_entry.insert(0, entry["title"])

        if entry["mood"] in MOOD_OPTIONS:
            self.mood_var.set(entry["mood"])
        else:
            self.mood_var.set(MOOD_OPTIONS[0])

        self.content_textbox.delete("1.0", "end")
        self.content_textbox.insert("1.0", entry["content"])
        self.content_textbox.focus()

        self.refresh_entries()

    def cancel_edit(self) -> None:
        """Clear the form and exit Edit mode back to New Entry mode."""
        self.editing_entry_id = None

        self.form_header.configure(text="✍️ New Journal Entry")
        self.save_button.configure(
            text="Save Entry",
            fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"],
            hover_color=ctk.ThemeManager.theme["CTkButton"]["hover_color"],
        )
        self.cancel_edit_button.grid_forget()
        self.button_frame.grid_columnconfigure(1, weight=0)
        self.save_button.grid_configure(padx=0)

        self._clear_form_inputs()
        self.refresh_entries()

    def _clear_form_inputs(self) -> None:
        """Reset Title, Mood, and Content inputs to their default blank states."""
        self.title_entry.delete(0, "end")
        self.content_textbox.delete("1.0", "end")
        self.mood_var.set(MOOD_OPTIONS[0])

    def submit_form(self) -> None:
        """Validate form inputs and either create a new entry or update the existing one."""
        title = self.title_entry.get().strip()
        mood = self.mood_var.get()
        content = self.content_textbox.get("1.0", "end-1c").strip()

        if not title:
            messagebox.showwarning(
                "Missing Title", "Please enter a title for your journal entry."
            )
            self.title_entry.focus()
            return

        if not content:
            messagebox.showwarning(
                "Missing Content", "Please write some content before saving."
            )
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
        else:
            database.add_entry(title=title, content=content, mood=mood)
            self._clear_form_inputs()
            self.refresh_entries()

    def delete_existing_entry(self, entry_id: int) -> None:
        """Confirm and delete an entry by ID, then refresh the card list."""
        confirm = messagebox.askyesno(
            "Delete Entry",
            "Are you sure you want to permanently delete this journal entry?",
        )
        if confirm:
            database.delete_entry(entry_id)
            if self.editing_entry_id == entry_id:
                self.cancel_edit()
            else:
                self.refresh_entries()

    def refresh_entries(self) -> None:
        """Reload all entries from the database and populate the scrollable list."""
        for widget in self.scrollable_entries.winfo_children():
            widget.destroy()

        entries = database.get_all_entries()
        total = len(entries)
        self.count_label.configure(
            text=f"{total} {'entry' if total == 1 else 'entries'}"
        )

        if not entries:
            empty_label = ctk.CTkLabel(
                self.scrollable_entries,
                text="No journal entries yet.\nWrite your first reflection on the left!",
                font=ctk.CTkFont(size=15),
                text_color=("#64748b", "#94a3b8"),
                justify="center",
            )
            empty_label.grid(row=0, column=0, pady=80, padx=20)
            return

        for idx, entry in enumerate(entries):
            card = EntryCard(
                self.scrollable_entries,
                entry=entry,
                on_edit=self.start_edit_entry,
                on_delete=self.delete_existing_entry,
                is_editing=(entry["id"] == self.editing_entry_id),
            )
            card.grid(row=idx, column=0, sticky="ew", padx=6, pady=6)


if __name__ == "__main__":
    database.init_db()
    app = Reflect()
    app.mainloop()
