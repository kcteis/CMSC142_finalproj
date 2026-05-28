"""
Barangay Relief Pack Optimizer — GUI
=====================================
Screens:
  1. Inventory Setup   — items + bag capacity + bag count
  2. Family Registry   — register families, auto-score
  3. Results           — optimized bag + ranked assignment
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import ReliefItem, Family
from knapsack import optimize_bag, get_dp_table
from priority import assign_bags
from utils import (validate_item, validate_capacity, validate_family,
                   check_supply_warnings, export_text, export_csv, build_text_report)

BG      = "#F5F4F1"
CARD    = "#FFFFFF"
BORDER  = "#E2E0D8"
NAV_BG  = "#1E1B4B"
NAV_ACC = "#4F46E5"   
PRIMARY = "#1A1A1A"
MUTED   = "#6B6A65"
ACCENT  = "#4F46E5"
SUCCESS = "#16A34A"
WARNING = "#D97706"
DANGER  = "#DC2626"
BTNFG   = "#FFFFFF"
TBL_HDR = "#F1F0EC"   

FN    = ("Helvetica", 11)
FN_SM = ("Helvetica", 10)
FN_B  = ("Helvetica", 11, "bold")
FN_H1 = ("Helvetica", 16, "bold")
FN_H2 = ("Helvetica", 12, "bold")

_NAV_ITEMS = [
    ("inventory", "Inventory Setup"),
    ("families",  "Family Registry"),
    ("results",   "Results"),
]

# Column definitions for the items table (label, grid weight)
_ITEM_COL_DEFS = [
    ("Item name",      3),
    ("Weight (kg)",    2),
    ("Benefit (1\u201310)", 2),   # 1–10
    ("Qty",            1),
    ("Action",         1),
]

# Column definitions for the families table
_FAM_COL_DEFS = [
    ("Family ID",     2),
    ("Size",          1),
    ("Vulnerable",    2),
    ("Damage",        2),
    ("Formula score", 2),
    ("Action",        2),
]

_RESULT_COL_DEFS = [
    ("#",      1),
    ("Family", 2),
    ("Score",  2),
    ("Size",   1),
    ("Vuln",   1),
    ("Dmg",    1),
    ("Status", 2),
]


# ── Shared state (global memory object) ──────────────────────────────────────────────────────────────
class State:
    def reset(self):
        self.items:        list[ReliefItem] = []
        self.capacity_kg:  float = 10.0
        self.supply:       int   = 0
        self.families:     list[Family] = []
        self.disaster:     str = ""
        self.barangay:     str = ""
        self.bag_contents: list[ReliefItem] = []
        self.bag_weight:   float = 0.0
        self.bag_benefit:  int   = 0
        self.summary       = None

    def __init__(self):
        self.reset()

S = State()


# ── Tiny helpers (UI) ──────────────────────────────────────────────────────────────
def lbl(parent, text, font=FN, fg=PRIMARY, bg=BG, **kw):
    return tk.Label(parent, text=text, font=font, fg=fg, bg=bg, **kw)

def btn(parent, text, cmd, color=ACCENT, width=13):
    return tk.Button(parent, text=text, command=cmd, bg=color, fg=BTNFG,
                     font=FN_B, relief="flat", bd=0, padx=10, pady=6,
                     cursor="hand2", activebackground=color, width=width)

def outline_btn(parent, text, cmd, color=DANGER, width=10):
    return tk.Button(parent, text=text, command=cmd, bg=CARD, fg=color,
                     font=FN_B, relief="solid", bd=1, padx=10, pady=6,
                     cursor="hand2", activebackground="#FEF2F2",
                     activeforeground=color, width=width)

def card_frame(parent, **kw):
    return tk.Frame(parent, bg=CARD,
                    highlightbackground=BORDER, highlightthickness=1, **kw)

def scrollable(parent):
    """Return (outer_frame, inner_frame) with a vertical scrollbar.
    The inner frame is kept at the canvas width so grid-based rows expand correctly."""
    outer  = tk.Frame(parent, bg=CARD)
    canvas = tk.Canvas(outer, bg=CARD, highlightthickness=0)
    sb     = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
    inner  = tk.Frame(canvas, bg=CARD)
    inner.bind("<Configure>",
               lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    win_id = canvas.create_window((0, 0), window=inner, anchor="nw")
    canvas.configure(yscrollcommand=sb.set)
    # Keep inner frame as wide as the canvas so fill="x" rows have a defined width
    canvas.bind("<Configure>",
                lambda e, wid=win_id: canvas.itemconfig(wid, width=e.width))
    canvas.pack(side="left", fill="both", expand=True)
    sb.pack(side="right", fill="y")
    return outer, inner

_SB_W = 17

def tbl_header(parent, col_defs, sb_pad=False):
    """Render an aligned table header whose column weights match the data rows.

    When ``sb_pad`` is True, reserves space on the right for a vertical
    scrollbar in the scrollable rows area below, keeping every column under
    its header. Columns are placed in a ``uniform`` group so their widths
    are strictly proportional to their weights, independent of content.
    """
    f = tk.Frame(parent, bg=TBL_HDR)
    f.pack(fill="x", padx=(10, 10 + _SB_W) if sb_pad else 10)
    for col, (txt, wt) in enumerate(col_defs):
        f.columnconfigure(col, weight=wt, uniform="tblcols")
        tk.Label(f, text=txt, font=FN_SM, fg=MUTED, bg=TBL_HDR,
                 anchor="center").grid(row=0, column=col, sticky="ew",
                                       padx=4, pady=7)
    return f

def col_header(parent, cols, bg="#EEECEA"):
    """Simple pack-based header (used on Results screen)."""
    f = tk.Frame(parent, bg=bg)
    f.pack(fill="x", padx=10)
    for txt in cols:
        lbl(f, txt, font=FN_SM, fg=MUTED, bg=bg).pack(side="left", padx=10, pady=4)
    return f


# ── Main window ───────────────────────────────────────────────────────────────
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Relief Pack Optimizer")
        self.geometry("1080x700")
        self.minsize(900, 600)
        self.configure(bg=BG)
        self._screens = {}
        self._build_nav()
        self.show("inventory")

    # ── Navigation ────────────────────────────────────────────────────────────
    def _build_nav(self):
        self.nav = tk.Frame(self, bg=NAV_BG, width=210)
        self.nav.pack(side="left", fill="y")
        self.nav.pack_propagate(False)

        lbl(self.nav, "Relief Pack\nOptimizer", font=("Helvetica", 14, "bold"),
            fg="white", bg=NAV_BG, justify="left").pack(
                anchor="w", padx=24, pady=(28, 8))
        lbl(self.nav, "Barangay System", font=("Helvetica", 10),
            fg="#A5B4FC", bg=NAV_BG).pack(anchor="w", padx=24)

        tk.Frame(self.nav, bg="#3730A3", height=1).pack(fill="x", padx=12, pady=10)

        # ── Nav buttons ───────────────────────────────────────────────────────
        self._nav_btns = {}
        for key, txt in _NAV_ITEMS:
            b = tk.Button(
                self.nav,
                text=f"  {txt}",
                font=FN, fg="#C7D2FE", bg=NAV_BG,
                relief="flat", bd=0, anchor="w", padx=12, pady=10,
                cursor="hand2",
                activebackground=NAV_ACC, activeforeground="white",
                command=lambda k=key: self.show(k)
            )
            b.pack(fill="x", padx=6, pady=1)
            self._nav_btns[key] = b

        tk.Frame(self.nav, bg="#3730A3", height=1).pack(fill="x", padx=12, pady=10)

        btn(self.nav, "New Disaster", self._reset,
            color=DANGER, width=17).pack(padx=12)

        # Disaster / Barangay meta fields
        for attr, label_txt in [("_dis_var", "Disaster:"), ("_bar_var", "Barangay:")]:
            lbl(self.nav, label_txt, font=FN_SM, fg="#A5B4FC", bg=NAV_BG).pack(
                anchor="w", padx=14, pady=(14, 0))
            var = tk.StringVar()
            setattr(self, attr, var)
            tk.Entry(self.nav, textvariable=var, font=FN_SM,
                     bg="#312E81", fg="white", relief="flat",
                     insertbackground="white").pack(fill="x", padx=12, pady=2)

        self.content = tk.Frame(self, bg=BG)
        self.content.pack(side="left", fill="both", expand=True)

    def show(self, name):
        for k, b in self._nav_btns.items():
            b.configure(bg=NAV_BG, fg="#C7D2FE")
        self._nav_btns[name].configure(bg=NAV_ACC, fg="white")
        for f in self.content.winfo_children():
            f.destroy()
        {"inventory": self._inventory,
         "families":  self._families,
         "results":   self._results}[name](self.content)

    def _reset(self):
        if messagebox.askyesno("New Disaster", "Clear all data and start fresh?"):
            S.reset()
            self._dis_var.set(""); self._bar_var.set("")
            self.show("inventory")

    # ── Screen 1 — Inventory ──────────────────────────────────────────────────
    def _inventory(self, parent):
        lbl(parent, "Inventory Setup", font=FN_H1).pack(anchor="w", padx=24, pady=(20, 2))
        lbl(parent, "Enter available relief goods, set bag capacity and bag count.",
            font=FN_SM, fg=MUTED).pack(anchor="w", padx=24)

        # ── Capacity / supply card ─────────────────────────────────────────────
        top = card_frame(parent)
        top.pack(fill="x", padx=24, pady=(10, 4))
        row = tk.Frame(top, bg=CARD)
        row.pack(fill="x", padx=16, pady=12)

        lbl(row, "Max bag weight (kg):", bg=CARD).pack(side="left")
        self._cap = tk.StringVar(value=str(S.capacity_kg))
        ttk.Spinbox(row, textvariable=self._cap, from_=0.1, to=500.0,
                    increment=0.5, width=8, font=FN).pack(side="left", padx=6)

        lbl(row, "  Bags available:", bg=CARD).pack(side="left")
        self._sup = tk.StringVar(value=str(S.supply))
        ttk.Spinbox(row, textvariable=self._sup, from_=0, to=99999,
                    increment=1, width=7, font=FN).pack(side="left", padx=6)

        # ── Relief items card ──────────────────────────────────────────────────
        ic = card_frame(parent)
        ic.pack(fill="both", expand=True, padx=24, pady=4)

        # Card header row: gift icon + title + Add row button
        hdr = tk.Frame(ic, bg=CARD)
        hdr.pack(fill="x", padx=12, pady=(10, 4))

        title_row = tk.Frame(hdr, bg=CARD)
        title_row.pack(side="left")
        lbl(title_row, "\U0001f381", font=("Helvetica", 14), bg=CARD).pack(
            side="left", padx=(0, 6))
        lbl(title_row, "Relief Items", font=FN_H2, bg=CARD).pack(side="left")

        btn(hdr, "+ Add row", self._add_item_row, width=9).pack(side="right")

        # Aligned column headers
        tbl_header(ic, _ITEM_COL_DEFS, sb_pad=True)

        outer, self._item_inner = scrollable(ic)
        outer.pack(fill="both", expand=True, padx=10)

        self._item_vars = []
        defaults = S.items or [
            ReliefItem("Rice",         3.0, 9, 50),
            ReliefItem("Canned goods", 1.5, 7, 80),
            ReliefItem("Water",        2.0, 8, 60),
            ReliefItem("Medicine",     0.5,10, 40),
            ReliefItem("Blanket",      1.5, 5, 30),
            ReliefItem("Hygiene kit",  0.5, 6, 50),
        ]
        for it in defaults:
            self._add_item_row(it)

        # ── Optimize Bag button ──────────────────────────────────────────────────
        bot = tk.Frame(ic, bg=CARD)
        bot.pack(fill="x", padx=12, pady=8)
        self._inv_status = lbl(bot, "", fg=MUTED, bg=CARD, font=FN_SM)
        self._inv_status.pack(side="left")
        btn(bot, "\U0001f381  Optimize Bag", self._run_knapsack,
            color=SUCCESS, width=16).pack(side="right")

    def _add_item_row(self, item=None):
        row = tk.Frame(self._item_inner, bg=CARD)
        row.pack(fill="x", pady=2)
        # Mirror the column weights from _ITEM_COL_DEFS
        for col, (_, wt) in enumerate(_ITEM_COL_DEFS):
            row.columnconfigure(col, weight=wt, uniform="itemcols")

        nv = tk.StringVar(value=item.name           if item else "")
        wv = tk.StringVar(value=str(item.weight_kg) if item else "")
        bv = tk.StringVar(value=str(item.benefit)   if item else "")
        qv = tk.StringVar(value=str(item.quantity)  if item else "")

        for col, var in enumerate([nv, wv, bv, qv]):
            tk.Entry(row, textvariable=var, font=FN, relief="solid", bd=1,
                     highlightthickness=0).grid(row=0, column=col,
                                                sticky="ew", padx=5, pady=5)

        data = (nv, wv, bv, qv)

        def rm():
            self._item_vars.remove(data)
            row.destroy()

        tk.Button(row, text="\U0001f5d1", font=("Helvetica", 13),
                  fg=DANGER, bg=CARD, relief="flat", bd=0,
                  cursor="hand2", command=rm).grid(row=0, column=4, padx=4, pady=5)
        self._item_vars.append(data)

    def _run_knapsack(self):
        # Validates input -> builds ReliefItem objects -> calls optimize_bag()
        # from knapsack.py (the 0/1 knapsack DP algorithm) -> saves the result to S.
        ok, msg = validate_capacity(self._cap.get())
        if not ok: messagebox.showerror("Error", msg); return
        try:
            sup = int(self._sup.get())
            if sup < 0: raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Bags available must be a positive whole number."); return

        items = []
        for nv, wv, bv, qv in self._item_vars:
            ok, msg = validate_item(nv.get(), wv.get(), bv.get(), qv.get())
            if not ok: messagebox.showerror("Item error", msg); return
            items.append(ReliefItem(nv.get().strip(), float(wv.get()),
                                    int(bv.get()), int(qv.get())))
        if not items:
            messagebox.showerror("Error", "Add at least one item."); return

        S.items       = items
        S.capacity_kg = float(self._cap.get())
        S.supply      = sup
        S.disaster    = self._dis_var.get()
        S.barangay    = self._bar_var.get()

        sel, wt, ben  = optimize_bag(items, S.capacity_kg)
        S.bag_contents = sel
        S.bag_weight   = wt
        S.bag_benefit  = ben

        self._inv_status.configure(
            text=f"Bag optimized: {len(sel)} items, {wt} kg, benefit={ben}",
            fg=SUCCESS)
        messagebox.showinfo("Done!",
            f"Optimal bag packed!\n"
            f"Items: {len(sel)}\nWeight: {wt} / {S.capacity_kg} kg\nBenefit: {ben}\n\n"
            "Go to Family Registry next.")

    # ── Screen 2 — Families ───────────────────────────────────────────────────
    def _families(self, parent):
        lbl(parent, "Family Registry", font=FN_H1).pack(anchor="w", padx=24, pady=(22, 4))
        lbl(parent, "Register affected families. Priority scores are computed automatically.",
            font=FN_SM, fg=MUTED).pack(anchor="w", padx=24)

        # Add-family form card
        fc = card_frame(parent)
        fc.pack(fill="x", padx=24, pady=(18, 4))
        frm = tk.Frame(fc, bg=CARD)
        frm.pack(fill="x", padx=24, pady=18)
        for col, wt in enumerate([2, 1, 2, 2, 2, 1]):
            frm.columnconfigure(col, weight=wt)

        labels = ["Family ID", "Size", "Vulnerable members", "Damage level (1\u20133)"]
        for i, txt in enumerate(labels):
            lbl(frm, txt, bg=CARD, font=FN_B).grid(row=0, column=i, sticky="w", padx=(0, 18))

        self._fid = tk.StringVar(value="F-001")
        self._fsz = tk.StringVar()
        self._fvl = tk.StringVar(value="0")
        self._fdm = tk.StringVar(value="1")

        tk.Entry(frm, textvariable=self._fid, width=12, font=FN,
                 relief="solid", bd=1).grid(row=1, column=0, sticky="ew", padx=(0, 18), pady=(10, 4), ipady=5)
        tk.Entry(frm, textvariable=self._fsz, width=8,  font=FN,
                 relief="solid", bd=1).grid(row=1, column=1, sticky="ew", padx=(0, 18), pady=(10, 4), ipady=5)
        tk.Entry(frm, textvariable=self._fvl, width=14,  font=FN,
                 relief="solid", bd=1).grid(row=1, column=2, sticky="ew", padx=(0, 18), pady=(10, 4), ipady=5)
        ttk.Combobox(frm, textvariable=self._fdm, values=["1", "2", "3"],
                     width=12, state="readonly").grid(row=1, column=3, sticky="ew", padx=(0, 28), pady=(10, 4), ipady=5)
        btn(frm, "Add Family", self._add_family, width=13).grid(row=1, column=4, sticky="ew", pady=(10, 4), ipady=1)

        self._fam_status = lbl(frm, "", fg=MUTED, bg=CARD, font=FN_SM)
        self._fam_status.grid(row=1, column=5, padx=6)

        # Family list table card
        tc = card_frame(parent)
        tc.pack(fill="both", expand=True, padx=24, pady=(18, 4))

        hdr = tk.Frame(tc, bg=CARD)
        hdr.pack(fill="x", padx=20, pady=(20, 10))
        self._fam_count = lbl(hdr, f"Families: {len(S.families)}", font=FN_H2, bg=CARD)
        self._fam_count.pack(side="left")
        outline_btn(hdr, "Clear all", self._clear_fams, color=DANGER, width=9).pack(side="right")

        tbl_header(tc, _FAM_COL_DEFS, sb_pad=True)

        outer, self._fam_inner = scrollable(tc)
        outer.pack(fill="both", expand=True, padx=10)
        self._render_fam_rows()

        bot = tk.Frame(tc, bg=CARD)
        bot.pack(fill="x", padx=20, pady=14)
        btn(bot, "Generate Assignment", self._run_assignment,
            color=SUCCESS, width=20).pack(side="right", ipadx=4, ipady=2)

    def _add_family(self):
        # Validates input, prevents duplicate IDs, creates a Family object,
        # and calls f.compute_formula_score() which computes a priority score
        # using a formula (e.g., size x weight + vulnerable x weight + damage x weight).
        ok, msg = validate_family(self._fid.get(), self._fsz.get(),
                                  self._fvl.get(), self._fdm.get())
        if not ok: messagebox.showerror("Error", msg); return
        fid = self._fid.get().strip()
        if any(f.family_id == fid for f in S.families):
            messagebox.showerror("Duplicate", f"'{fid}' already registered."); return

        f = Family(fid, int(self._fsz.get()), int(self._fvl.get()),
                   int(self._fdm.get()), len(S.families) + 1)
        f.compute_formula_score()
        S.families.append(f)
        self._fam_count.configure(text=f"Families: {len(S.families)}")
        self._fam_status.configure(text=f"Added {fid}  score={f.formula_score:.0f}", fg=SUCCESS)
        self._fid.set(f"F-{len(S.families)+1:03d}")
        self._render_fam_rows()

    def _clear_fams(self):
        if messagebox.askyesno("Clear", "Remove all registered families?"):
            S.families.clear()
            self._fam_count.configure(text="Families: 0")
            self._render_fam_rows()

    def _render_fam_rows(self):
        for w in self._fam_inner.winfo_children():
            w.destroy()
        for f in S.families:
            row = tk.Frame(self._fam_inner, bg=CARD)
            row.pack(fill="x", pady=0)
            for col, (_, wt) in enumerate(_FAM_COL_DEFS):
                row.columnconfigure(col, weight=wt, uniform="famcols")
            for col, val in enumerate([f.family_id, f.size, f.vulnerable_count,
                                       f.damage_level, f.formula_score]):
                lbl(row, str(val), bg=CARD, font=FN_SM,
                    anchor="center").grid(row=0, column=col,
                                          sticky="ew", padx=14, pady=11)

            def rm(fam=f):
                S.families.remove(fam)
                self._fam_count.configure(text=f"Families: {len(S.families)}")
                self._render_fam_rows()

            tk.Button(row, text="Remove", font=FN_SM, fg=DANGER, bg="#FEF2F2",
                      relief="solid", bd=1, cursor="hand2", command=rm,
                      activebackground="#FEE2E2", activeforeground=DANGER
                      ).grid(row=0, column=5, sticky="ew", padx=14, pady=8)
            tk.Frame(self._fam_inner, bg=BORDER, height=1).pack(fill="x")

    def _run_assignment(self):
        # Triggered when "Generate Assignment" is clicked.
        # Checks prerequisites -> calls assign_bags() -> jumps to the Results screen.
        if not S.bag_contents:
            messagebox.showerror("Error", "Run 'Optimize Bag' on the Inventory screen first."); return
        if not S.families:
            messagebox.showerror("Error", "Register at least one family."); return
        if S.supply < 1:
            messagebox.showerror("Error", "Set 'Bags available' > 0 on the Inventory screen."); return

        warns = check_supply_warnings(S.families, S.supply)
        if warns:
            if not messagebox.askyesno("Warning", "\n".join(f"• {w}" for w in warns)
                                       + "\n\nContinue?"):
                return

        S.summary = assign_bags(
            S.families, S.bag_contents,
            S.bag_weight, S.bag_benefit,
            S.supply,
        )
        self.show("results")

    # ── Screen 3 — Results ────────────────────────────────────────────────────
    def _results(self, parent):
        if not S.summary:
            empty = card_frame(parent)
            empty.pack(fill="x", padx=24, pady=60)
            lbl(empty, "No Results Yet", font=FN_H1, bg=CARD).pack(pady=(22, 4))
            lbl(empty, "Run the assignment first from Family Registry.",
                fg=MUTED, bg=CARD).pack(pady=(0, 22))
            return

        sm = S.summary

        lbl(parent, "Results", font=FN_H1).pack(anchor="w", padx=24, pady=(22, 4))
        lbl(parent, "Review the optimized bag and ranked family assignment.",
            font=FN_SM, fg=MUTED).pack(anchor="w", padx=24)

        # Summary strip
        strip = tk.Frame(parent, bg=BG)
        strip.pack(fill="x", padx=24, pady=(18, 10))
        for title, val, color in [
            ("Families served",  str(sm.served),                   SUCCESS),
            ("Unserved",         str(sm.unserved),                  DANGER if sm.unserved else MUTED),
            ("Total benefit",    str(sm.total_benefit_delivered),   ACCENT),
            ("Bag weight",       f"{sm.bag_weight} kg",             PRIMARY),
        ]:
            c = card_frame(strip)
            c.pack(side="left", fill="x", expand=True, padx=5)
            lbl(c, val,   font=("Helvetica", 22, "bold"), fg=color, bg=CARD).pack(padx=18, pady=(12, 0))
            lbl(c, title, font=FN_SM, fg=MUTED, bg=CARD).pack(padx=18, pady=(0, 12))

        # Two-column layout
        cols = tk.Frame(parent, bg=BG)
        cols.pack(fill="both", expand=True, padx=24, pady=(0, 4))

        # Left — bag manifest + DP table button
        left = card_frame(cols)
        left.pack(side="left", fill="both", padx=(0, 8), pady=2)
        lbl(left, "Optimized Bag", font=FN_H2, bg=CARD).pack(anchor="w", padx=18, pady=(18, 4))
        lbl(left, "Items included in one relief pack.", font=FN_SM, fg=MUTED,
            bg=CARD).pack(anchor="w", padx=18, pady=(0, 10))

        manifest = tk.Frame(left, bg=CARD)
        manifest.pack(fill="both", expand=True, padx=14)
        for it in sm.bag_contents:
            row = tk.Frame(manifest, bg=CARD)
            row.pack(fill="x", pady=5)
            lbl(row, it.name, bg=CARD, font=FN_B).pack(anchor="w")
            lbl(row, f"{it.weight_kg} kg  \u2022  benefit {it.benefit}",
                bg=CARD, font=FN_SM, fg=MUTED).pack(anchor="w")

        tk.Frame(left, bg=BORDER, height=1).pack(fill="x", padx=18, pady=10)
        lbl(left, f"Total:  {sm.bag_weight} kg  \u2022  benefit {sm.bag_benefit}",
            bg=CARD, font=FN_B).pack(anchor="w", padx=18, pady=(0, 10))
        btn(left, "View DP Table", self._show_dp_table, color=MUTED, width=16).pack(
            fill="x", padx=18, pady=(0, 18), ipady=2)

        # Right — ranked assignment table
        right = card_frame(cols)
        right.pack(side="left", fill="both", expand=True, pady=2)
        rh = tk.Frame(right, bg=CARD)
        rh.pack(fill="x", padx=20, pady=(18, 10))
        lbl(rh, "Priority Assignment", font=FN_H2, bg=CARD).pack(side="left")

        tbl_header(right, _RESULT_COL_DEFS, sb_pad=True)

        outer, rows_inner = scrollable(right)
        outer.pack(fill="both", expand=True, padx=10)

        for rank, a in enumerate(sm.assignments, 1):
            f   = a.family
            bg  = "#F0FDF4" if a.served else "#FEF2F2"
            row = tk.Frame(rows_inner, bg=bg)
            row.pack(fill="x", pady=0)
            for col, (_, wt) in enumerate(_RESULT_COL_DEFS):
                row.columnconfigure(col, weight=wt, uniform="rescols")
            values = [rank, f.family_id, f"{f.final_score:.1f}",
                      f.size, f.vulnerable_count, f.damage_level]
            for col, val in enumerate(values):
                lbl(row, str(val), bg=bg, font=FN_SM, anchor="center").grid(
                    row=0, column=col, sticky="ew", padx=8, pady=11)
            sc = SUCCESS if a.served else DANGER
            status = "Served" if a.served else "No Supply"
            lbl(row, status, bg=bg, font=FN_B, fg=sc, anchor="center").grid(
                row=0, column=6, sticky="ew", padx=8, pady=11)
            tk.Frame(rows_inner, bg=BORDER, height=1).pack(fill="x")

        # Export row
        exp = tk.Frame(parent, bg=BG)
        exp.pack(fill="x", padx=24, pady=(8, 14))
        btn(exp, "Export TXT", self._exp_txt, color=ACCENT, width=14).pack(side="right", padx=4, ipady=2)
        btn(exp, "Export CSV", self._exp_csv, color=ACCENT, width=14).pack(side="right", padx=4, ipady=2)

    def _show_dp_table(self):
        # Opens a popup window that visualizes the 0/1 Knapsack DP table.
        # Useful for showing how the algorithm builds up the optimal solution
        # cell-by-cell (rows = items considered, columns = capacity in 0.1 kg steps).
        if not S.items:
            messagebox.showinfo("No data", "No items loaded."); return

        # Ask knapsack.py for the filled DP matrix plus its dimensions.
        # PREC is the scale factor (e.g. 10) used to convert kg into integer steps.
        dp, items, W, PREC = get_dp_table(S.items, S.capacity_kg)

        # Create a new top-level window (separate from the main app window).
        win = tk.Toplevel(self)
        win.title("DP Table \u2014 0/1 Knapsack")
        win.configure(bg=BG)
        win.geometry("860x420")
        lbl(win, "0/1 Knapsack DP Table  (rows = items added, columns = capacity in 0.1 kg steps)",
            font=FN_SM, fg=MUTED, bg=BG).pack(anchor="w", padx=14, pady=6)
       
        frame = tk.Frame(win, bg=BG)
        frame.pack(fill="both", expand=True, padx=10, pady=4)

        xsb = ttk.Scrollbar(frame, orient="horizontal")
        ysb = ttk.Scrollbar(frame, orient="vertical")

        tv  = ttk.Treeview(frame, xscrollcommand=xsb.set, yscrollcommand=ysb.set)
        xsb.configure(command=tv.xview)
        ysb.configure(command=tv.yview)

        # The full DP table can be huge, so sample at most ~20 columns evenly across
        # the capacity range to keep the display readable.
        step   = max(1, W // 20)
        w_cols = list(range(0, W + 1, step))

        # Configure the table's column headers: leftmost shows item name,
        # the rest show capacity values (converted back to kg via / PREC).
        tv["columns"] = [str(w) for w in w_cols]
        tv.heading("#0", text="Item \\ Cap")
        tv.column("#0", width=110, anchor="w")
        for w in w_cols:
            cap = w / PREC
            tv.heading(str(w), text=f"{cap:.1f}")
            tv.column(str(w), width=42, anchor="center")

        # Fill each row with the DP values. Row 0 is the "Base" case (no items yet);
        # row i corresponds to having considered the first i items.
        for i in range(len(items) + 1):
            row_label = "Base" if i == 0 else items[i-1].name[:12]
            values     = [str(dp[i][w]) for w in w_cols]
            tv.insert("", "end", text=row_label, values=values)

        xsb.pack(side="bottom", fill="x")
        ysb.pack(side="right",  fill="y")
        tv.pack(fill="both", expand=True)

    def _exp_txt(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".txt", filetypes=[("Text", "*.txt")],
            initialfile="relief_report.txt")
        if path:
            export_text(S.summary, path, S.disaster, S.barangay)
            messagebox.showinfo("Exported", f"Saved to:\n{path}")

    def _exp_csv(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".csv", filetypes=[("CSV", "*.csv")],
            initialfile="relief_report.csv")
        if path:
            export_csv(S.summary, path)
            messagebox.showinfo("Exported", f"Saved to:\n{path}")

# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    App().mainloop()
