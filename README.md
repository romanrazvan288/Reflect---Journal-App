# Reflect

Reflect is a minimalist desktop journaling and mood tracking application built with Python and CustomTkinter. It provides a local, private workspace to record thoughts and monitor daily moods without cloud dependencies or complex setup.

---

## Highlights

* Clean and responsive user interface built using modern CustomTkinter components.
* Mood tracking integrated directly into daily journal logs.
* Local SQLite storage keeping all data entirely on your machine.
* Cross-platform support with native launcher integration on Linux and single-binary packaging for Windows.

---

## Requirements

* Python 3.10 or higher
* Git

---

## Installation

Clone the repository and enter the project folder:

```bash
git clone [https://github.com/romanrazvan288/Personal-Journal---App.git](https://github.com/romanrazvan288/Personal-Journal---App.git)
cd Personal-Journal---App
Create and activate a virtual environment:

Bash
# Linux
python3 -m venv .venv
source .venv/bin/activate

# Windows
python -m venv .venv
.venv\Scripts\activate
Install the project dependencies:

Bash
pip install -r requirements.txt
Running the Application
Linux
Start the application from terminal:

Bash
python3 app.py
If you installed the desktop shortcut, you can also launch it directly by searching for Reflect in the Ubuntu application menu.

Windows
Run using Python:

Bash
python app.py
Building an Executable for Windows
To compile the application into an independent executable that runs without requiring Python installed, execute the following command inside PowerShell or Command Prompt on Windows:

Bash
pyinstaller --noconsole --onefile --name "Reflect" --icon="icon.ico" --add-data "icon.ico;." --add-data "icon.png;." --collect-all customtkinter app.py
The resulting binary will be generated at dist/Reflect.exe.

Repository Structure
Plaintext
Personal-Journal---App/
├── app.py             # Application UI and event logic
├── database.py        # Database schema and SQLite interactions
├── requirements.txt   # Third-party dependencies
├── icon.png           # Window and desktop shortcut icon for Linux
├── icon.ico           # Executable and window icon for Windows
├── .gitignore         # Rules excluding databases, caches, and build files
└── README.md          # Project documentation
Data Privacy
All journal entries and mood selections are stored exclusively inside a local SQLite file (journal.db). The database is excluded from version control through .gitignore to keep personal reflections strictly private and off remote repositories.
