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
from ml_scorer import score_families, train_model, MODEL_PATH
from utils import (validate_item, validate_capacity, validate_family,
                   check_supply_warnings, export_text, export_csv, build_text_report)

# ── Theme ─────────────────────────────────────────────────────────────────────
BG       = "#F5F4F1"
CARD     = "#FFFFFF"
BORDER   = "#E2E0D8"
NAV_BG   = "#1E1B4B"
NAV_ACC  = "#312E81"
PRIMARY  = "#1A1A1A"
MUTED    = "#6B6A65"
ACCENT   = "#4F46E5"
SUCCESS  = "#16A34A"
WARNING  = "#D97706"
DANGER   = "#DC2626"
BTNFG    = "#FFFFFF"

FN       = ("Helvetica", 11)
FN_SM    = ("Helvetica", 10)
FN_B     = ("Helvetica", 11, "bold")
FN_H1    = ("Helvetica", 16, "bold")
FN_H2    = ("Helvetica", 12, "bold")


# ── Shared state ──────────────────────────────────────────────────────────────
class State:
    def reset(self):
        self.items:        list[ReliefItem] = []
        self.capacity_kg:  float = 10.0
        self.supply:       int   = 0
        self.families:     list[Family] = []
        self.disaster:     str = ""
        self.barangay:     str = ""
        self.use_ml:       bool = True
        self.bag_contents: list[ReliefItem] = []
        self.bag_weight:   float = 0.0
        self.bag_benefit:  int   = 0
        self.summary       = None

    def __init__(self):
        self.reset()

S = State()


# ── Tiny helpers ──────────────────────────────────────────────────────────────
def lbl(parent, text, font=FN, fg=PRIMARY, bg=BG, **kw):
    return tk.Label(parent, text=text, font=font, fg=fg, bg=bg, **kw)

def btn(parent, text, cmd, color=ACCENT, width=13):
    return tk.Button(parent, text=text, command=cmd, bg=color, fg=BTNFG,
                     font=FN_B, relief="flat", bd=0, padx=10, pady=6,
                     cursor="hand2", activebackground=color, width=width)

def card_frame(parent, **kw):
    return tk.Frame(parent, bg=CARD,
                    highlightbackground=BORDER, highlightthickness=1, **kw)

def scrollable(parent):
    """Return (outer_frame, inner_frame) with a vertical scrollbar."""
    outer = tk.Frame(parent, bg=CARD)
    canvas = tk.Canvas(outer, bg=CARD, highlightthickness=0)
    sb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
    inner = tk.Frame(canvas, bg=CARD)
    inner.bind("<Configure>",
               lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=inner, anchor="nw")
    canvas.configure(yscrollcommand=sb.set)
    canvas.pack(side="left", fill="both", expand=True)
    sb.pack(side="right", fill="y")
    return outer, inner

def col_header(parent, cols, bg="#EEECEA"):
    f = tk.Frame(parent, bg=bg)
    f.pack(fill="x", padx=10)
    for txt in cols:
        lbl(f, txt, font=FN_SM, fg=MUTED, bg=bg).pack(side="left", padx=10, pady=4)
    return f


# ── Main window ───────────────────────────────────────────────────────────────
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Barangay Relief Pack Optimizer")
        self.geometry("1080x700")
        self.minsize(900, 600)
        self.configure(bg=BG)
        self._screens = {}
        self._build_nav()
        self.show("inventory")

    # ── Navigation ────────────────────────────────────────────────────────────
    def _build_nav(self):
        self.nav = tk.Frame(self, bg=NAV_BG, width=190)
        self.nav.pack(side="left", fill="y")
        self.nav.pack_propagate(False)

        lbl(self.nav, "Relief\nOptimizer", font=("Helvetica", 14, "bold"),
            fg="white", bg=NAV_BG, justify="left").pack(anchor="w", padx=16, pady=(20, 2))
        lbl(self.nav, "Barangay System", font=("Helvetica", 9),
            fg="#A5B4FC", bg=NAV_BG).pack(anchor="w", padx=16)
        tk.Frame(self.nav, bg="#3730A3", height=1).pack(fill="x", padx=12, pady=12)

        self._nav_btns = {}
        for key, txt in [("inventory","  Inventory Setup"),
                         ("families", "  Family Registry"),
                         ("results",  "  Results")]:
            b = tk.Button(self.nav, text=txt, font=FN, fg="#C7D2FE", bg=NAV_BG,
                          relief="flat", bd=0, anchor="w", padx=12, pady=10,
                          cursor="hand2", activebackground=NAV_ACC, activeforeground="white",
                          command=lambda k=key: self.show(k))
            b.pack(fill="x")
            self._nav_btns[key] = b

        tk.Frame(self.nav, bg="#3730A3", height=1).pack(fill="x", padx=12, pady=12)
        btn(self.nav, "New Disaster", self._reset, color=DANGER, width=16).pack(padx=12)

        # Meta fields
        for attr, label_txt in [("_dis_var","Disaster:"),("_bar_var","Barangay:")]:
            lbl(self.nav, label_txt, font=FN_SM, fg="#A5B4FC", bg=NAV_BG).pack(
                anchor="w", padx=14, pady=(14,0))
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
        lbl(parent, "Inventory Setup", font=FN_H1).pack(anchor="w", padx=24, pady=(20,2))
        lbl(parent, "Enter available relief goods, set bag capacity and bag count.",
            font=FN_SM, fg=MUTED).pack(anchor="w", padx=24)

        # Capacity / supply row
        top = card_frame(parent)
        top.pack(fill="x", padx=24, pady=(10,4))
        row = tk.Frame(top, bg=CARD)
        row.pack(fill="x", padx=16, pady=12)
        lbl(row, "Max bag weight (kg):", bg=CARD).pack(side="left")
        self._cap = tk.StringVar(value=str(S.capacity_kg))
        tk.Entry(row, textvariable=self._cap, width=7, font=FN,
                 relief="solid", bd=1).pack(side="left", padx=6)
        lbl(row, "  Bags available:", bg=CARD).pack(side="left")
        self._sup = tk.StringVar(value=str(S.supply))
        tk.Entry(row, textvariable=self._sup, width=6, font=FN,
                 relief="solid", bd=1).pack(side="left", padx=6)

        # Items card
        ic = card_frame(parent)
        ic.pack(fill="both", expand=True, padx=24, pady=4)

        hdr = tk.Frame(ic, bg=CARD)
        hdr.pack(fill="x", padx=12, pady=(10,4))
        lbl(hdr, "Relief Items", font=FN_H2, bg=CARD).pack(side="left")
        btn(hdr, "+ Add row", self._add_item_row, width=9).pack(side="right")

        col_header(ic, ["Item name","Weight (kg)","Benefit (1–10)","Qty",""])

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

        bot = tk.Frame(ic, bg=CARD)
        bot.pack(fill="x", padx=12, pady=8)
        self._inv_status = lbl(bot, "", fg=MUTED, bg=CARD, font=FN_SM)
        self._inv_status.pack(side="left")
        btn(bot, "Optimize Bag", self._run_knapsack, color=SUCCESS).pack(side="right")

    def _add_item_row(self, item=None):
        row = tk.Frame(self._item_inner, bg=CARD)
        row.pack(fill="x", pady=2)
        nv = tk.StringVar(value=item.name        if item else "")
        wv = tk.StringVar(value=str(item.weight_kg) if item else "")
        bv = tk.StringVar(value=str(item.benefit)   if item else "")
        qv = tk.StringVar(value=str(item.quantity)  if item else "")
        for var, w in [(nv,20),(wv,10),(bv,13),(qv,6)]:
            tk.Entry(row, textvariable=var, width=w, font=FN,
                     relief="solid", bd=1).pack(side="left", padx=4)
        data = (nv, wv, bv, qv)
        def rm():
            self._item_vars.remove(data)
            row.destroy()
        tk.Button(row, text="✕", font=FN_SM, fg=DANGER, bg=CARD,
                  relief="flat", cursor="hand2", command=rm).pack(side="left")
        self._item_vars.append(data)

    def _run_knapsack(self):
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
        lbl(parent, "Family Registry", font=FN_H1).pack(anchor="w", padx=24, pady=(20,2))
        lbl(parent, "Register affected families. Priority scores are computed automatically.",
            font=FN_SM, fg=MUTED).pack(anchor="w", padx=24)

        # Add family form
        fc = card_frame(parent)
        fc.pack(fill="x", padx=24, pady=(10,4))
        frm = tk.Frame(fc, bg=CARD)
        frm.pack(fill="x", padx=16, pady=12)

        labels = ["Family ID","Size","Vulnerable members","Damage level (1–3)"]
        for i, txt in enumerate(labels):
            lbl(frm, txt, bg=CARD, font=FN_SM).grid(row=0, column=i, sticky="w", padx=4)

        self._fid = tk.StringVar(value="F-001")
        self._fsz = tk.StringVar()
        self._fvl = tk.StringVar(value="0")
        self._fdm = tk.StringVar(value="1")

        tk.Entry(frm, textvariable=self._fid, width=10, font=FN,
                 relief="solid", bd=1).grid(row=1, column=0, padx=4, pady=4)
        tk.Entry(frm, textvariable=self._fsz, width=6,  font=FN,
                 relief="solid", bd=1).grid(row=1, column=1, padx=4)
        tk.Entry(frm, textvariable=self._fvl, width=8,  font=FN,
                 relief="solid", bd=1).grid(row=1, column=2, padx=4)
        ttk.Combobox(frm, textvariable=self._fdm, values=["1","2","3"],
                     width=5, state="readonly").grid(row=1, column=3, padx=4)
        btn(frm, "Add Family", self._add_family, width=11).grid(row=1, column=4, padx=12)

        self._fam_status = lbl(frm, "", fg=MUTED, bg=CARD, font=FN_SM)
        self._fam_status.grid(row=1, column=5, padx=6)

        # Table
        tc = card_frame(parent)
        tc.pack(fill="both", expand=True, padx=24, pady=4)

        hdr = tk.Frame(tc, bg=CARD)
        hdr.pack(fill="x", padx=12, pady=(10,4))
        self._fam_count = lbl(hdr, f"Families: {len(S.families)}", font=FN_H2, bg=CARD)
        self._fam_count.pack(side="left")
        btn(hdr, "Clear all", self._clear_fams, color=DANGER, width=9).pack(side="right")

        col_header(tc, ["Family ID","Size","Vulnerable","Damage","Formula score","Action"])

        outer, self._fam_inner = scrollable(tc)
        outer.pack(fill="both", expand=True, padx=10)
        self._render_fam_rows()

        bot = tk.Frame(tc, bg=CARD)
        bot.pack(fill="x", padx=12, pady=8)
        self._ml_var = tk.BooleanVar(value=S.use_ml)
        tk.Checkbutton(bot, text="Use ML scoring (blended with formula)",
                       variable=self._ml_var, bg=CARD, font=FN_SM,
                       command=lambda: setattr(S, "use_ml", self._ml_var.get())
                       ).pack(side="left")
        btn(bot, "Generate Assignment", self._run_assignment, color=SUCCESS).pack(side="right")

    def _add_family(self):
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
            row.pack(fill="x", pady=1)
            for val in [f.family_id, f.size, f.vulnerable_count,
                        f.damage_level, f.formula_score]:
                lbl(row, str(val), bg=CARD, font=FN_SM).pack(side="left", padx=14, pady=2)
            def rm(fam=f):
                S.families.remove(fam)
                self._fam_count.configure(text=f"Families: {len(S.families)}")
                self._render_fam_rows()
            tk.Button(row, text="Remove", font=FN_SM, fg=DANGER, bg=CARD,
                      relief="flat", cursor="hand2", command=rm).pack(side="left", padx=6)

    def _run_assignment(self):
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

        if S.use_ml:
            score_families(S.families)

        S.summary = assign_bags(
            S.families, S.bag_contents,
            S.bag_weight, S.bag_benefit,
            S.supply, use_ml=S.use_ml,
        )
        self.show("results")

    # ── Screen 3 — Results ────────────────────────────────────────────────────
    def _results(self, parent):
        if not S.summary:
            lbl(parent, "Run the assignment first (Family Registry → Generate Assignment).",
                fg=MUTED).pack(pady=60)
            return

        sm = S.summary

        lbl(parent, "Results", font=FN_H1).pack(anchor="w", padx=24, pady=(20,2))

        # Summary strip
        strip = tk.Frame(parent, bg=BG)
        strip.pack(fill="x", padx=24, pady=6)
        for title, val, color in [
            ("Families served",  str(sm.served),                   SUCCESS),
            ("Unserved",         str(sm.unserved),                  DANGER if sm.unserved else MUTED),
            ("Total benefit",    str(sm.total_benefit_delivered),   ACCENT),
            ("Bag weight",       f"{sm.bag_weight} kg",             PRIMARY),
        ]:
            c = card_frame(strip)
            c.pack(side="left", padx=5)
            lbl(c, val,   font=("Helvetica",18,"bold"), fg=color, bg=CARD).pack(padx=18, pady=(8,0))
            lbl(c, title, font=FN_SM, fg=MUTED, bg=CARD).pack(padx=18, pady=(0,8))

        # Two-column layout
        cols = tk.Frame(parent, bg=BG)
        cols.pack(fill="both", expand=True, padx=24, pady=4)

        # Left — bag manifest + DP table button
        left = card_frame(cols)
        left.pack(side="left", fill="y", padx=(0,6), pady=2)
        lbl(left, "Optimized Bag", font=FN_H2, bg=CARD).pack(anchor="w", padx=14, pady=(10,4))
        for it in sm.bag_contents:
            lbl(left, f"  {it.name}", bg=CARD, font=FN_SM).pack(anchor="w", padx=14)
            lbl(left, f"    {it.weight_kg} kg  •  benefit {it.benefit}",
                bg=CARD, font=FN_SM, fg=MUTED).pack(anchor="w", padx=14)
        tk.Frame(left, bg=BORDER, height=1).pack(fill="x", padx=14, pady=6)
        lbl(left, f"Total:  {sm.bag_weight} kg  •  benefit {sm.bag_benefit}",
            bg=CARD, font=FN_B).pack(anchor="w", padx=14, pady=(0,8))
        btn(left, "View DP Table", self._show_dp_table, color=MUTED, width=14).pack(padx=14, pady=(0,12))

        # Right — ranked assignment table
        right = card_frame(cols)
        right.pack(side="left", fill="both", expand=True, pady=2)
        lbl(right, "Priority Assignment", font=FN_H2, bg=CARD).pack(anchor="w", padx=14, pady=(10,4))

        col_header(right, ["#","Family","Score","ML","Size","Vuln","Dmg","Status"])

        outer, rows_inner = scrollable(right)
        outer.pack(fill="both", expand=True, padx=10)

        for rank, a in enumerate(sm.assignments, 1):
            f   = a.family
            bg  = "#F0FDF4" if a.served else "#FEF2F2"
            row = tk.Frame(rows_inner, bg=bg)
            row.pack(fill="x", pady=1)
            for val in [rank, f.family_id, f"{f.final_score:.1f}",
                        f"{f.ml_score:.0f}", f.size, f.vulnerable_count, f.damage_level]:
                lbl(row, str(val), bg=bg, font=FN_SM).pack(side="left", padx=10, pady=3)
            sc = SUCCESS if a.served else DANGER
            lbl(row, "SERVED" if a.served else "NO SUPPLY",
                bg=bg, font=FN_SM, fg=sc).pack(side="left", padx=10)

        # Export row
        exp = tk.Frame(parent, bg=BG)
        exp.pack(fill="x", padx=24, pady=6)
        btn(exp, "Export TXT", self._exp_txt, color=ACCENT).pack(side="right", padx=4)
        btn(exp, "Export CSV", self._exp_csv, color=ACCENT).pack(side="right", padx=4)

    def _show_dp_table(self):
        if not S.items:
            messagebox.showinfo("No data", "No items loaded."); return
        dp, items, W, PREC = get_dp_table(S.items, S.capacity_kg)
        win = tk.Toplevel(self)
        win.title("DP Table — 0/1 Knapsack")
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

        step   = max(1, W // 20)
        w_cols = list(range(0, W + 1, step))
        tv["columns"] = [str(w) for w in w_cols]
        tv.heading("#0", text="Item \\ Cap")
        tv.column("#0", width=110, anchor="w")
        for w in w_cols:
            cap = w / PREC
            tv.heading(str(w), text=f"{cap:.1f}")
            tv.column(str(w), width=42, anchor="center")

        for i in range(len(items) + 1):
            row_label = "Base" if i == 0 else items[i-1].name[:12]
            values     = [str(dp[i][w]) for w in w_cols]
            tv.insert("", "end", text=row_label, values=values)

        xsb.pack(side="bottom", fill="x")
        ysb.pack(side="right",  fill="y")
        tv.pack(fill="both", expand=True)

    def _exp_txt(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".txt", filetypes=[("Text","*.txt")],
            initialfile="relief_report.txt")
        if path:
            export_text(S.summary, path, S.disaster, S.barangay)
            messagebox.showinfo("Exported", f"Saved to:\n{path}")

    def _exp_csv(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".csv", filetypes=[("CSV","*.csv")],
            initialfile="relief_report.csv")
        if path:
            export_csv(S.summary, path)
            messagebox.showinfo("Exported", f"Saved to:\n{path}")

# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if not os.path.exists(MODEL_PATH):
        print("First run — training ML model…")
        train_model(verbose=False)
    App().mainloop()
