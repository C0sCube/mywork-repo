import json
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pdf2image import convert_from_path
from PIL import Image, ImageTk

class HorizontalScrolledFrame(ttk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.canvas = tk.Canvas(self, height=150, bg="#2f2f2f", highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(xscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="top", fill="both", expand=True)
        self.scrollbar.pack(side="bottom", fill="x")

        self.inner_frame = ttk.Frame(self.canvas)
        self.inner_frame_id = self.canvas.create_window((0, 0), window=self.inner_frame, anchor="nw")

        self.inner_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

    def _on_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.inner_frame_id, height=event.height)

class JsonPdfCompareApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Scheme JSON & PDF Viewer")
        self.root.geometry("1000x650")
        self.root.configure(bg="#2f2f2f")

        self.data = None
        self.records = []
        self.current_index = None
        self.entries = {}

        style = ttk.Style()
        style.theme_use('default')
        style.configure("TLabel", background="#2f2f2f", foreground="white")
        style.configure("TEntry", fieldbackground="#4a4a4a", foreground="white")
        style.configure("TFrame", background="#2f2f2f")
        style.configure("TButton", background="#3a3a3a", foreground="white")
        style.map("TButton", background=[('active', '#5a5a5a')])

        top_frame = ttk.Frame(root)
        top_frame.pack(side="top", fill="x", padx=10, pady=5)

        ttk.Button(top_frame, text="Load JSON", command=self.load_json).pack(side="left")
        ttk.Button(top_frame, text="Save JSON", command=self.save_json).pack(side="left", padx=(10,0))
        ttk.Button(top_frame, text="Load PDF", command=self.load_pdf).pack(side="left", padx=(10,0))

        main_frame = ttk.Frame(root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Left: Scheme listbox
        left_frame = ttk.Frame(main_frame, width=250)
        left_frame.pack(side="left", fill="y")

        self.scheme_listbox = tk.Listbox(left_frame, bg="#3a3a3a", fg="white", activestyle='none')
        self.scheme_listbox.pack(fill="both", expand=True)
        self.scheme_listbox.bind("<<ListboxSelect>>", self.on_scheme_select)

        # Right: Split horizontally into JSON editor and PDF preview
        right_paned = ttk.Panedwindow(main_frame, orient=tk.HORIZONTAL)
        right_paned.pack(side="left", fill="both", expand=True, padx=(10,0))

        # JSON editor frame
        self.json_frame = ttk.Frame(right_paned)
        right_paned.add(self.json_frame, weight=3)

        # PDF preview frame
        self.pdf_frame = ttk.Frame(right_paned, width=300)
        right_paned.add(self.pdf_frame, weight=1)

        # JSON editor scrollable canvas inside json_frame
        self.canvas = tk.Canvas(self.json_frame, bg="#2f2f2f", highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.json_frame, orient="vertical", command=self.canvas.yview)
        self.details_frame = ttk.Frame(self.canvas)

        self.details_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.details_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # PDF preview area inside pdf_frame
        self.pdf_label = ttk.Label(self.pdf_frame, text="No PDF loaded", foreground="white", background="#2f2f2f")
        self.pdf_label.pack(pady=10)

        self.pdf_canvas = tk.Canvas(self.pdf_frame, bg="#1e1e1e", width=280, height=400)
        self.pdf_canvas.pack(pady=10)

        self.pdf_image = None  # to hold PhotoImage ref

    def load_json(self):
        filepath = filedialog.askopenfilename(
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        if not filepath:
            return

        with open(filepath, "r", encoding="utf-8") as f:
            self.data = json.load(f)

        self.records = self.data.get("records", [])
        self.scheme_listbox.delete(0, tk.END)
        for r in self.records:
            name = r.get("value", {}).get("main_scheme_name", "Unnamed")
            self.scheme_listbox.insert(tk.END, name)

        if self.records:
            self.scheme_listbox.selection_set(0)
            self.current_index = 0
            self.load_selected_scheme(0)
        else:
            self.current_index = None
            self.clear_details()

    def clear_details(self):
        for widget in self.details_frame.winfo_children():
            widget.destroy()
        self.entries.clear()

    def on_scheme_select(self, event):
        if not self.scheme_listbox.curselection():
            return
        index = self.scheme_listbox.curselection()[0]
        self.current_index = index
        self.load_selected_scheme(index)

    def load_selected_scheme(self, idx):
        self.clear_details()
        record = self.records[idx]
        value_dict = record.get("value", {})

        row = 0
        for key, val in value_dict.items():
            key_label = tk.Label(self.details_frame, text=key, fg="white", bg="#2f2f2f",
                                 font=("Arial", 12, "bold"), anchor="w")
            key_label.grid(row=row, column=0, sticky="nw", padx=5, pady=10)

            if key == "field_location" and isinstance(val, dict):
                frame = ttk.Frame(self.details_frame)
                frame.grid(row=row, column=1, sticky="nw", padx=5, pady=5)

                col = 0
                for subkey, subval in val.items():
                    subkey_label = tk.Label(frame, text=subkey, fg="white", bg="#2f2f2f",
                                            font=("Arial", 10, "bold"), anchor="center")
                    subkey_label.grid(row=0, column=col, padx=5, sticky="n")

                    entry = ttk.Entry(frame, width=15)
                    entry.grid(row=1, column=col, padx=5, pady=2)
                    entry.insert(0, str(subval))

                    self.entries.setdefault(key, []).append((subkey, entry))
                    col += 1

            elif key in ("fund_manager", "load", "metrics") and isinstance(val, list) and val and isinstance(val[0], dict):
                hsframe = HorizontalScrolledFrame(self.details_frame)
                hsframe.grid(row=row, column=1, sticky="nw", padx=5, pady=5)

                for idx2, item in enumerate(val):
                    item_frame = ttk.LabelFrame(hsframe.inner_frame, text=f"Item {idx2+1}", width=220)
                    item_frame.pack(side="left", padx=5, pady=5, fill="y")

                    for subkey, subval in item.items():
                        subkey_label = tk.Label(item_frame, text=subkey, fg="white", bg="#2f2f2f",
                                                font=("Arial", 10, "bold"), anchor="w")
                        subkey_label.pack(anchor="w", padx=5, pady=(5,0))

                        entry = ttk.Entry(item_frame)
                        entry.pack(fill="x", padx=10, pady=2)
                        entry.insert(0, str(subval))

                        self.entries.setdefault(key, []).append((idx2, subkey, entry))

            else:
                entry = ttk.Entry(self.details_frame)
                entry.grid(row=row, column=1, sticky="we", padx=5, pady=5)
                entry.insert(0, str(val))
                self.entries[key] = entry

            row += 1

        self.details_frame.columnconfigure(1, weight=1)

    def save_json(self):
        if self.current_index is None:
            messagebox.showwarning("Warning", "No scheme selected")
            return

        updated_value = {}

        for key, val in self.entries.items():
            if key == "field_location":
                updated_value[key] = {subkey: entry.get() for subkey, entry in val}
            elif key in ("fund_manager", "load", "metrics"):
                grouped = {}
                for idx2, subkey, entry in val:
                    if idx2 not in grouped:
                        grouped[idx2] = {}
                    grouped[idx2][subkey] = entry.get()
                updated_value[key] = list(grouped.values())
            else:
                updated_value[key] = val.get()

        self.records[self.current_index]["value"] = updated_value

        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        if not filepath:
            return

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4, ensure_ascii=False)

        messagebox.showinfo("Success", "JSON saved successfully!")

    def load_pdf(self):
        pdf_path = filedialog.askopenfilename(
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        if not pdf_path:
            return

        self.pdf_label.config(text=f"Loaded: {os.path.basename(pdf_path)}")

        try:
            pages = convert_from_path(pdf_path, first_page=1, last_page=1, size=(600, None))
            if pages:
                page = pages[0]
                page.thumbnail((280, 400))
                self.pdf_image = ImageTk.PhotoImage(page)
                self.pdf_canvas.delete("all")
                self.pdf_canvas.create_image(0, 0, anchor="nw", image=self.pdf_image)
        except Exception as e:
            messagebox.showerror("PDF Load Error", f"Failed to load PDF preview:\n{e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = JsonPdfCompareApp(root)
    root.mainloop()
