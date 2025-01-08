import tkinter as tk
from tkinter import Canvas, filedialog, Frame, Scrollbar, Button
import fitz  # PyMuPDF
from PIL import Image, ImageTk

def pdf_to_image(pdf_path, page_number=0):
    doc = fitz.open(pdf_path)
    page = doc.load_page(page_number)  # Load the specific page
    pix = page.get_pixmap()  # Render page to an image
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    doc.close()
    return img

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
        self.page_label = tk.Label(control_frame, text="")
        self.page_label.pack(side="left")

    def load_pdf(self):
        # Open file dialog to select a PDF
        self.pdf_path = filedialog.askopenfilename(
            filetypes=[("PDF files", "*.pdf")],
            title="Select a PDF file"
        )
        if self.pdf_path:
            self.pdf_doc = fitz.open(self.pdf_path)
            self.total_pages = len(self.pdf_doc)
            self.page_number = 0
            self.load_page()

    def load_page(self):
        if self.canvas:
            self.canvas.delete("all")
            self.canvas.pack_forget()

        img = pdf_to_image(self.pdf_path, self.page_number)
        self.canvas_image = ImageTk.PhotoImage(img)
        self.canvas = Canvas(self, width=min(img.width, self.winfo_width()), height=min(img.height, self.winfo_height()), 
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
        print(f"Rectangle coordinates: ({self.start_x}, {self.start_y}, {end_x}, {end_y})")
        # Here you can use the coordinates as needed

root = tk.Tk()
root.geometry("800x600")  # Set initial size of the window
app = Application(master=root)
app.mainloop()

