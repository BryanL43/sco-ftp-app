import tkinter as tk
from tkinter import messagebox

class ErrorDialog:

    @staticmethod
    def show(title: str, message: str, parent=None):
        if parent is not None:
            ErrorDialog._make_topmost(parent)
            messagebox.showerror(title, message, parent=parent)
            return

        root = tk.Tk()
        root.withdraw()
        ErrorDialog._make_topmost(root)
        messagebox.showerror(title, message, parent=root)
        root.destroy()

    @staticmethod
    def _make_topmost(root):
        root.attributes("-topmost", True)
        root.lift()
        root.focus_force()
