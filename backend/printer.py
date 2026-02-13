import os
from PIL import Image, ImageWin
import win32print
import win32ui
import win32con
from config import PRINTER_NAME, PRINTER_QUEUE, PRINTER_PRINTED

def print_image(file_path):
    """Local print on SELPHY CP1500 without margins"""
    img = Image.open(file_path)

    # Rotate if needed
    w, h = img.size
    if w > h:
        img = img.rotate(90, expand=True)

    hprinter = win32print.OpenPrinter(PRINTER_NAME)
    printer_dc = win32ui.CreateDC()
    printer_dc.CreatePrinterDC(PRINTER_NAME)

    printer_dc.StartDoc(file_path)
    printer_dc.StartPage()

    dib = ImageWin.Dib(img)
    dib.draw(printer_dc.GetHandleOutput(), (0, 0, img.width, img.height))

    printer_dc.EndPage()
    printer_dc.EndDoc()
    printer_dc.DeleteDC()
    win32print.ClosePrinter(hprinter)

    # Move the file to the printed folder
    dst = os.path.join(PRINTER_PRINTED, os.path.basename(file_path))
    os.rename(file_path, dst)
    return dst
