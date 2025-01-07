import tkinter as tk
from tkinter import Canvas, Scrollbar, Button, filedialog
import fitz  # PyMuPDF

def load_pdf():
    global pdf_document, scale
    file_path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
    if file_path:
        pdf_document = fitz.open(file_path)
        display_page(0)

def display_page(page_num):
    global current_page, page_image, scale
    current_page = page_num
    page = pdf_document.load_page(page_num)
    pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))  # Scale the image up for better resolution
    scale = 1.5  # Keep track of the scaling factor
    photo = tk.PhotoImage(width=pix.width, height=pix.height, data=pix.tobytes())
    page_image.config(image=photo)
    page_image.image = photo  # keep a reference!
    page_label.config(text=f"Page {page_num + 1} of {pdf_document.page_count}")
    page_bboxes[current_page] = []  # Initialize a list for this page

def next_page():
    if current_page < pdf_document.page_count - 1:
        display_page(current_page + 1)

def exit_app():
    print(page_bboxes)
    root.destroy()

def on_mouse_down(event):
    global start_x, start_y
    start_x, start_y = event.x, event.y

def on_mouse_up(event):
    end_x, end_y = event.x, event.y
    canvas.create_rectangle(start_x, start_y, end_x, end_y, outline="red")
    # Store the bbox coordinates adjusted by the scale factor
    bbox = (start_x / scale, start_y / scale, end_x / scale, end_y / scale)
    page_bboxes[current_page].append(bbox)

# Set up the main window
root = tk.Tk()
root.title("PDF Viewer")
root.geometry("800x600")

current_page = 0
start_x, start_y = 0, 0
page_bboxes = {}  # Dictionary to hold bboxes for each page
scale = 1.0  # Default scaling factor

# Frame for page navigation
nav_frame = tk.Frame(root)
nav_frame.pack(fill='x', side='top')

page_label = tk.Label(nav_frame, text="")
page_label.pack(side='left')

next_button = Button(nav_frame, text="Next Page", command=next_page)
next_button.pack(side='left')

exit_button = Button(nav_frame, text="Exit", command=exit_app)
exit_button.pack(side='right')

load_button = Button(nav_frame, text="Load PDF", command=load_pdf)
load_button.pack(side='right')

canvas = Canvas(root, width=600, height=500, bg="gray")
canvas.pack(side='top', fill='both', expand=True)

canvas.bind("<Button-1>", on_mouse_down)
canvas.bind("<ButtonRelease-1>", on_mouse_up)

# Label to display the current page image
page_image = tk.Label(canvas)
page_image.pack()

root.mainloop()
