import tkinter as tk

from app.config.settings import load_settings
from app.ui.tkinter_app import PalmTkinterApp


def main():
    settings = load_settings()

    root = tk.Tk()
    app = PalmTkinterApp(root, settings)

    root.mainloop()


if __name__ == "__main__":
    main()