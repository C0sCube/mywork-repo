import tkinter as tk
from tkinter import Canvas, filedialog, Frame, Scrollbar, Button, Checkbutton, BooleanVar, Entry, messagebox, ttk
import fitz  # type: ignore
from PIL import Image, ImageTk  # type: ignore
import json


def pdf_to_image(pdf_path, page_number=0, scale_factor=1.0):
    try:
        doc = fitz.open(pdf_path)
        if page_number < 0 or page_number >= len(doc):
            return None, None, None, None

        page = doc.load_page(page_number)
        pix = page.get_pixmap(matrix=fitz.Matrix(scale_factor, scale_factor))
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        return img, scale_factor, page.rect.width, page.rect.height

    except Exception as e:
        print(f"Error in pdf_to_image: {e}")
        return None, None, None, None


class Application(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        self.pack(fill=tk.BOTH, expand=1)

        self.canvas = None
        self.scroll_y = Scrollbar(self, orient="vertical")
        self.scroll_y.pack(side="right", fill="y")
        self.scroll_x = Scrollbar(self, orient="horizontal")
        self.scroll_x.pack(side="bottom", fill="x")

        self.pdf_path = None
        self.pdf_doc = None
        self.page_number = 0
        self.total_pages = 0
        self.fit_to_screen = BooleanVar(value=False)
        self.scale_factor = 1.0
        self.pdf_width = 1
        self.pdf_height = 1

        self.rect = None
        self.start_x = None
        self.start_y = None

        self.control_frame = Frame(self)
        self.control_frame.pack(fill="x")

        self.create_widgets()
        self.named_sets = {}
        self.selected_set_name = tk.StringVar()
        self.add_named_set_controls()

    def create_widgets(self):
        Button(self.control_frame, text="Open PDF", command=self.load_pdf).pack(side="left")
        Button(self.control_frame, text="< Prev", command=self.prev_page).pack(side="left")
        Button(self.control_frame, text="Next >", command=self.next_page).pack(side="left")

        Checkbutton(self.control_frame, text="Fit to Screen", variable=self.fit_to_screen, command=self.load_page).pack(side="left")

        self.page_label = tk.Label(self.control_frame, text="")
        self.page_label.pack(side="left")

        self.page_entry = Entry(self.control_frame, width=5)
        self.page_entry.pack(side="left")
        Button(self.control_frame, text="Go", command=self.jump_to_page).pack(side="left")

    def load_pdf(self):
        self.pdf_path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")], title="Select a PDF file")
        if not self.pdf_path:
            return
        try:
            self.pdf_doc = fitz.open(self.pdf_path)
            self.total_pages = len(self.pdf_doc)
            self.page_number = 0
            self.load_page()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open PDF: {e}")

    def load_page(self):
        if not self.pdf_doc or self.page_number < 0 or self.page_number >= self.total_pages:
            return

        if self.canvas:
            self.canvas.delete("all")
            self.canvas.pack_forget()

        img, self.scale_factor, self.pdf_width, self.pdf_height = pdf_to_image(self.pdf_path, self.page_number)

        if self.fit_to_screen.get():
            canvas_width = self.winfo_width()
            canvas_height = self.winfo_height() - 50
            scale_x = canvas_width / self.pdf_width
            scale_y = canvas_height / self.pdf_height
            self.scale_factor = min(scale_x, scale_y)
            img, self.scale_factor, self.pdf_width, self.pdf_height = pdf_to_image(
                self.pdf_path, self.page_number, scale_factor=self.scale_factor)

        self.canvas_image = ImageTk.PhotoImage(img)
        self.canvas = Canvas(self, width=img.width, height=img.height,
                             xscrollcommand=self.scroll_x.set, yscrollcommand=self.scroll_y.set, bg="white")
        self.canvas.create_image(0, 0, anchor="nw", image=self.canvas_image)
        self.canvas.pack(side="left", fill="both", expand=True)

        self.scroll_x.config(command=self.canvas.xview)
        self.scroll_y.config(command=self.canvas.yview)
        self.canvas.config(scrollregion=self.canvas.bbox("all"))

        self.canvas.bind("<ButtonPress-1>", self.start_draw)
        self.canvas.bind("<B1-Motion>", self.draw_rect)
        self.canvas.bind("<ButtonRelease-1>", self.end_draw)

        self.update_page_label()

    def update_page_label(self):
        self.page_label.config(text=f"Page {self.page_number + 1} of {self.total_pages}")

    def jump_to_page(self):
        try:
            page_num = int(self.page_entry.get()) - 1
            if 0 <= page_num < self.total_pages:
                self.page_number = page_num
                self.load_page()
        except ValueError:
            pass

    def next_page(self):
        if self.page_number < self.total_pages - 1:
            self.page_number += 1
            self.load_page()

    def prev_page(self):
        if self.page_number > 0:
            self.page_number -= 1
            self.load_page()

    def start_draw(self, event):
        self.start_x = self.canvas.canvasx(event.x)
        self.start_y = self.canvas.canvasy(event.y)
        self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline='orange')

    def draw_rect(self, event):
        cur_x, cur_y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        self.canvas.coords(self.rect, self.start_x, self.start_y, cur_x, cur_y)

    def end_draw(self, event):
        pass  # To be extended


class AnnotatedPDFViewer(Application):
    def __init__(self, master=None):
        super().__init__(master)
        self.bbox_data = {}
        self.loaded_bboxes = {}
        self.source_page = tk.StringVar()
        self.add_annotator_controls()

    def add_annotator_controls(self):
        Button(self.control_frame, text="Save BBoxes", command=self.save_bboxes).pack(side="right")
        Button(self.control_frame, text="Load BBoxes", command=self.load_bboxes).pack(side="right")

        self.reuse_menu = ttk.Combobox(self.control_frame, width=6, textvariable=self.source_page)
        self.reuse_menu.pack(side="right")
        Button(self.control_frame, text="Reuse from Page", command=self.reuse_bboxes).pack(side="right")
    
    def end_draw(self, event):
        end_x = self.canvas.canvasx(event.x)
        end_y = self.canvas.canvasy(event.y)

        pdf_x1 = round(self.start_x / self.scale_factor, 2)
        pdf_y1 = round(self.start_y / self.scale_factor, 2)
        pdf_x2 = round(end_x / self.scale_factor, 2)
        pdf_y2 = round(end_y / self.scale_factor, 2)

        bbox = [pdf_x1, pdf_y1, pdf_x2, pdf_y2]
        self.bbox_data.setdefault(str(self.page_number), []).append(bbox)
        print(f"Added bbox on page {self.page_number + 1}: {bbox}")

        # Draw rectangle with tag so it can be removed later
        self.canvas.create_rectangle(self.start_x, self.start_y, end_x, end_y, outline="orange", width=2, tags="rect")

    def save_bboxes(self):
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if path:
            with open(path, "w") as f:
                json.dump(self.bbox_data, f, indent=2)
            messagebox.showinfo("Saved", f"BBoxes saved to {path}")

    def load_bboxes(self):
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if path:
            with open(path, "r") as f:
                self.loaded_bboxes = json.load(f)
            self.reuse_menu['values'] = list(self.loaded_bboxes.keys())
            self.render_loaded_bboxes()

    def reuse_bboxes(self):
        src = self.source_page.get()
        if src in self.loaded_bboxes:
            self.bbox_data[str(self.page_number)] = self.loaded_bboxes[src]
            self.render_loaded_bboxes()

    def render_loaded_bboxes(self):
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self.canvas_image)
        for bbox in self.bbox_data.get(str(self.page_number), []):
            x0, y0, x1, y1 = [v * self.scale_factor for v in bbox]
            self.canvas.create_rectangle(x0, y0, x1, y1, outline="green", width=2)

    def add_named_set_controls(self):
        # Entry to name bbox set
        self.set_name_entry = Entry(self.control_frame, width=15)
        self.set_name_entry.pack(side="right")
        Button(self.control_frame, text="Save Set", command=self.save_named_set).pack(side="right")

        # Dropdown + Apply button
        self.named_set_dropdown = ttk.Combobox(self.control_frame, width=15, textvariable=self.selected_set_name)
        self.named_set_dropdown.pack(side="right")
        Button(self.control_frame, text="Apply Set", command=self.apply_named_set).pack(side="right")

        Button(self.control_frame, text="Clear Annotations", command=self.clear_current_page_annotations).pack(side="left")

    def clear_current_page_annotations(self):
        if str(self.page_number) in self.bbox_data:
            del self.bbox_data[str(self.page_number)]
            self.render_loaded_bboxes()
            messagebox.showinfo("Cleared", f"Annotations removed from page {self.page_number + 1}")
        else:
            messagebox.showinfo("No Annotations", "No annotations to remove on this page.")

    def render_loaded_bboxes(self):
        self.canvas.delete("rect")  # remove previous drawn rects with tag 'rect'
        bboxes = self.bbox_data.get(str(self.page_number), [])
        for bbox in bboxes:
            x0, y0, x1, y1 = [coord * self.scale_factor for coord in bbox]
            self.canvas.create_rectangle(x0, y0, x1, y1, outline="orange", width=2, tags="rect")
        
    def apply_named_set(self):
        name = self.selected_set_name.get()
        if name not in self.named_sets:
            messagebox.showwarning("Invalid", "Select a valid saved set.")
            return
        self.bbox_data[str(self.page_number)] = self.named_sets[name].copy()
        self.render_loaded_bboxes()

    
    def save_named_set(self):
        name = self.set_name_entry.get().strip()
        if not name:
            messagebox.showwarning("No Name", "Please enter a name for the set.")
            return
        bboxes = self.bbox_data.get(str(self.page_number), [])
        if not bboxes:
            messagebox.showwarning("No BBoxes", "No bounding boxes to save.")
            return
        self.named_sets[name] = bboxes.copy()
        self.named_set_dropdown['values'] = list(self.named_sets.keys())
        messagebox.showinfo("Saved", f"Saved current page BBoxes as '{name}'")


if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("1000x700")
    root.title("PDF BBox Annotator with Reuse")
    app = AnnotatedPDFViewer(master=root)
    app.mainloop()
