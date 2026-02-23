#ui_pannels.py
import tkinter as tk
from tkinter import ttk


class FilterableCheckboxPanel(ttk.Frame):

    def __init__(self, parent, groups, single_select=False):

        super().__init__(parent)

        self.groups = groups
        self.single_select = single_select

        self.vars = {}
        self.group_vars = {}

        for group, items in groups.items():

            ttk.Label(self, text=group, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(5, 0))

            gvar = tk.BooleanVar(master=self)
            self.group_vars[group] = gvar

            chk_all = ttk.Checkbutton(
                self,
                text="Select All",
                variable=gvar,
                command=lambda g=group: self.toggle_group(g),
            )

            chk_all.pack(anchor="w", padx=10)

            btn = ttk.Button(
                self,
                text="Filter / Search",
                width=25,
                command=lambda g=group: self.open_popup(g),
            )

            btn.pack(anchor="w", padx=10, pady=(0, 5))

    def toggle_group(self, group):

        state = self.group_vars[group].get()

        for col in self.groups[group]:

            if col not in self.vars:
                self.vars[col] = tk.BooleanVar(master=self)

            self.vars[col].set(state)

    def get_selected(self):

        return [k for k, v in self.vars.items() if v.get()]

    def open_popup(self, group):

        popup = tk.Toplevel(self)
        popup.title(group)
        popup.geometry("250x300")

        search_var = tk.StringVar()

        ttk.Entry(popup, textvariable=search_var).pack(fill="x", padx=5, pady=5)

        frame = ttk.Frame(popup)
        frame.pack(fill="both", expand=True)

        canvas = tk.Canvas(frame)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)

        inner = ttk.Frame(canvas)

        inner.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )

        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        for item in self.groups[group]:

            if item not in self.vars:
                self.vars[item] = tk.BooleanVar(master=self)

            ttk.Checkbutton(inner, text=item, variable=self.vars[item]).pack(anchor="w")

        def filter_items(*args):

            term = search_var.get().lower()

            for widget in inner.winfo_children():

                text = widget.cget("text").lower()

                widget.pack_forget()

                if term in text:
                    widget.pack(anchor="w")

        search_var.trace_add("write", filter_items)