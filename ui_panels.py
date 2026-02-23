#ui_pannels.py
import tkinter as tk
from tkinter import ttk


class CollapsibleGroup(ttk.Frame):

    def __init__(self, parent, title):

        super().__init__(parent)

        self.show = tk.BooleanVar(value=True)

        header = ttk.Checkbutton(
            self,
            text=title,
            variable=self.show,
            command=self.toggle,
            style="Toolbutton"
        )

        header.pack(fill="x")

        self.body = ttk.Frame(self)
        self.body.pack(fill="x")

    def toggle(self):

        if self.show.get():
            self.body.pack(fill="x")
        else:
            self.body.forget()


class FilterableCheckboxPanel(ttk.Frame):

    def __init__(self, parent, groups, single_select=False):

        super().__init__(parent)

        self.groups = groups
        self.single_select = single_select
        self.vars = {}

        # SEARCH
        self.search_var = tk.StringVar()

        search = ttk.Entry(self, textvariable=self.search_var)
        search.pack(fill="x", pady=5)

        self.search_var.trace_add("write", self.filter)

        # SCROLL AREA
        canvas = tk.Canvas(self, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, command=canvas.yview)

        self.inner = ttk.Frame(canvas)

        self.inner.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.inner, anchor="nw")

        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.checks = []

        for group, items in groups.items():

            g = CollapsibleGroup(self.inner, group)
            g.pack(fill="x", pady=5)

            for item in items:

                var = tk.BooleanVar()
                self.vars[item] = var

                cb = ttk.Checkbutton(g.body, text=item, variable=var)
                cb.pack(anchor="w", padx=10)

                self.checks.append(cb)

    def filter(self, *args):

        term = self.search_var.get().lower()

        for cb in self.checks:

            text = cb.cget("text").lower()

            if term in text:
                cb.pack(anchor="w", padx=10)
            else:
                cb.pack_forget()

    def get_selected(self):

        return [k for k, v in self.vars.items() if v.get()]