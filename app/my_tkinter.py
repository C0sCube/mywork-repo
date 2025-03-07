import tkinter as tk
from tkinter import Canvas, filedialog, Frame, Scrollbar, Button, Checkbutton, BooleanVar, Entry, messagebox
import fitz  # type: ignore
from PIL import Image, ImageTk  # type: ignore

def pdf_to_image(pdf_path, page_number=0, scale_factor=1.0):
    try:
        doc = fitz.open(pdf_path)
        if page_number < 0 or page_number >= len(doc):
            print(f"Invalid page number: {page_number}")
            return None, None, None, None

        page = doc.load_page(page_number)
        if not page:
            print(f"Failed to load page {page_number}")
            return None, None, None, None

        pix = page.get_pixmap(matrix=fitz.Matrix(scale_factor, scale_factor))
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        return img, scale_factor, page.rect.width, page.rect.height  # Return original PDF size

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

        self.create_widgets()
        self.rect = None
        self.start_x = None
        self.start_y = None

    def create_widgets(self):
        control_frame = Frame(self)
        control_frame.pack(fill="x")

        Button(control_frame, text="Open PDF", command=self.load_pdf).pack(side="left")
        Button(control_frame, text="< Prev", command=self.prev_page).pack(side="left")
        Button(control_frame, text="Next >", command=self.next_page).pack(side="left")

        Checkbutton(control_frame, text="Fit to Screen", variable=self.fit_to_screen, command=self.load_page).pack(side="left")

        self.page_label = tk.Label(control_frame, text="")
        self.page_label.pack(side="left")

        self.page_entry = Entry(control_frame, width=5)
        self.page_entry.pack(side="left")
        Button(control_frame, text="Go", command=self.jump_to_page).pack(side="left")

    def load_pdf(self):
        self.pdf_path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")], title="Select a PDF file")
        if not self.pdf_path:
            return  # User canceled file selection

        try:
            self.pdf_doc = fitz.open(self.pdf_path)
            self.total_pages = len(self.pdf_doc)
            self.page_number = 0
            print(f"Loaded PDF with {self.total_pages} pages.")
            self.load_page()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to open PDF: {e}")
            print(f"Error loading PDF: {e}")
            self.pdf_doc = None

    def load_page(self):
        if not self.pdf_doc or self.page_number < 0 or self.page_number >= self.total_pages:
            print(f"Invalid page number {self.page_number}. Total pages: {self.total_pages}")
            return

        if self.canvas:
            self.canvas.delete("all")
            self.canvas.pack_forget()

        img, self.scale_factor, self.pdf_width, self.pdf_height = pdf_to_image(self.pdf_path, self.page_number)

        if img is None:
            print("Failed to load image for the page.")
            return

        if self.fit_to_screen.get():
            canvas_width = self.winfo_width()
            canvas_height = self.winfo_height() - 50  # Account for control panel height
            scale_x = canvas_width / self.pdf_width
            scale_y = canvas_height / self.pdf_height
            self.scale_factor = min(scale_x, scale_y)

            img, self.scale_factor, self.pdf_width, self.pdf_height = pdf_to_image(
                self.pdf_path, self.page_number, scale_factor=self.scale_factor
            )

            if img is None:
                return

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
            else:
                print(f"Invalid page number: {page_num + 1}")
        except ValueError:
            print("Invalid input in jump to page")

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
        end_x, end_y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)

        pdf_x1 = self.start_x / self.scale_factor
        pdf_y1 = self.start_y / self.scale_factor
        pdf_x2 = end_x / self.scale_factor
        pdf_y2 = end_y / self.scale_factor

        print(f"PDF BBox: ({pdf_x1:.2f}, {pdf_y1:.2f}, {pdf_x2:.2f}, {pdf_y2:.2f})")

root = tk.Tk()
root.geometry("800x600")
app = Application(master=root)
app.mainloop()
