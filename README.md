# Reflect

A minimalist, privacy-focused desktop personal journal built with Python and CustomTkinter, designed with a modern macOS dark aesthetic.

---

## Overview

**Reflect** is an offline personal journaling application created to offer a distraction-free writing environment. It keeps all data strictly local, encrypts authentication using local cryptographic hashing, and provides visual mood insights without external cloud dependencies.

---

## Features

### Minimalist Writing Experience
- **macOS Dark Mode Aesthetics**: Custom dark palette, smooth rounded corners, clean hierarchy, and no emojis.
- **Zen / Focus Mode (`F11`)**: Fullscreen, distraction-free view hiding all navigation bars and lists to keep the focus solely on writing.
- **Journaling Templates**: Pre-configured prompts ("Daily Gratitude", "Evening Review", "Brain Dump") to jumpstart entries.
- **Auto-Save Drafts**: Automatically preserves unsaved text in real time so thoughts are never lost if the window is closed.

### Organization & Search
- **Real-Time Search**: Instant dynamic search by keyword across titles and content.
- **Quick Mood Filter Chips**: One-click filtering by specific mood states.
- **Date Range Filters**: Filter entries by "All Time", "Today", "This Week", or "This Month".
- **Pin to Top**: Anchor important reflections to the top of the entry list.
- **"On This Day" Widget**: Highlights entries written on the same calendar date in past months or years.

### Analytics & Security
- **Mood Analytics**: Visual chart breakdown tracking emotional balance (Happy, Calm, Productive, Neutral, Tired, Stressed, Anxious, Sad).
- **Local PIN Protection**: Secure launch screen backed by salted PBKDF2/SHA-256 local hashing.
- **Auto-Lock on Inactivity**: Automatically secures the app after 5 minutes of idle time.
- **100% Local Storage**: Powered by an offline SQLite database (`journal.db`).

---

## Tech Stack

- **GUI**: [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)
- **Database**: SQLite3 (Local storage)
- **Analytics / Plotting**: Matplotlib
- **Security**: Python standard `hashlib`

---

## Installation & Setup

### Prerequisites
- Python 3.10 or higher
- Git

### Quickstart

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/romanrazvan288/Personal-Journal---App.git](https://github.com/romanrazvan288/Personal-Journal---App.git)
   cd Personal-Journal---App
Install dependencies:

Bash
pip install -r requirements.txt
Run the application:

Bash
python3 app.py
