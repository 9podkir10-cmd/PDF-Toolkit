import os
import sys
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import cpu_count
import fitz
import cv2
import numpy as np
from PIL import Image
from pyzbar.pyzbar import decode, ZBarSymbol

NUM_WORKERS = max(1, cpu_count() - 1)
ZOOM_LEVEL = 2.0

def check_code39_on_page(page_data, target_codes):
    try:
        page_bytes, page_num, pdf_path = page_data
        
        doc = fitz.open("pdf", page_bytes)
        if len(doc) == 0:
            return (pdf_path, page_num, False)
        
        page = doc[0]
        
        mat = fitz.Matrix(ZOOM_LEVEL, ZOOM_LEVEL)
        pix = page.get_pixmap(matrix=mat)
        
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        img_np = np.array(img)
        
        if len(img_np.shape) == 3:
            gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_np
        
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        
        barcodes = decode(
            Image.fromarray(enhanced),
            symbols=[ZBarSymbol.CODE39]
        )
        
        doc.close()
        
        for barcode in barcodes:
            try:
                barcode_data = barcode.data.decode('utf-8').strip()
                barcode_clean = barcode_data.replace(" ", "").upper()
                
                for target in target_codes:
                    target_clean = target.replace(" ", "").upper()
                    if barcode_clean == target_clean:
                        return (pdf_path, page_num, True)
            except Exception:
                continue
        
        return (pdf_path, page_num, False)
        
    except Exception:
        return (pdf_path, page_num, False)


def find_code39_pages_parallel(pdf_path, target_codes):
    try:
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
    except Exception:
        return pdf_path, []
    
    page_data_list = []
    for page_num in range(total_pages):
        single_page_doc = fitz.open()
        single_page_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
        page_bytes = single_page_doc.write()
        single_page_doc.close()
        page_data_list.append((page_bytes, page_num, pdf_path))
    
    doc.close()
    
    barcode_pages = []
    
    with ProcessPoolExecutor(max_workers=NUM_WORKERS) as executor:
        future_to_page = {
            executor.submit(check_code39_on_page, page_data, target_codes): page_data[1]
            for page_data in page_data_list
        }
        
        for future in as_completed(future_to_page):
            _, page_num, has_barcode = future.result()
            if has_barcode:
                barcode_pages.append(page_num)
    
    barcode_pages.sort()
    return pdf_path, barcode_pages


def split_pdf_by_code39(pdf_path, barcode_pages, output_dir=None):
    if not barcode_pages:
        return []
    
    pdf_file = Path(pdf_path)
    if output_dir is None:
        output_dir = pdf_file.parent / f"{pdf_file.stem}_split"
    else:
        output_dir = Path(output_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    
    barcode_pages.sort()
    
    created_files = []
    part_number = 1
    start_page = 0
    
    all_separators = barcode_pages + [total_pages]
    
    for separator in all_separators:
        if separator <= start_page:
            continue
        
        new_doc = fitz.open()
        
        for page_num in range(start_page, separator):
            new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
        
        output_filename = output_dir / f"{pdf_file.stem}_part{part_number}.pdf"
        new_doc.save(str(output_filename))
        new_doc.close()
        
        created_files.append(str(output_filename))
        
        part_number += 1
        start_page = separator + 1
    
    doc.close()
    return created_files


def process_single_pdf_file(pdf_path, target_codes, output_dir=None):
    pdf_file = Path(pdf_path)
    
    if not pdf_file.exists() or not pdf_file.is_file() or not pdf_path.lower().endswith('.pdf'):
        return []
    
    file_path, barcode_pages = find_code39_pages_parallel(pdf_path, target_codes)
    
    if not barcode_pages:
        return []
    
    created_files = split_pdf_by_code39(pdf_path, barcode_pages, output_dir)
    return created_files


def find_pdf_files(directory):
    directory = Path(directory)
    
    if not directory.exists():
        return []
    
    unique_pdf_files = {}
    
    for pdf_file in directory.rglob('*'):
        if pdf_file.is_file() and pdf_file.suffix.lower() == '.pdf':
            abs_path = str(pdf_file.absolute())
            unique_pdf_files[abs_path] = str(pdf_file)
    
    return list(unique_pdf_files.values())


def process_directory(dir_path, target_codes, output_dir=None):
    dir_path_obj = Path(dir_path)
    
    if not dir_path_obj.exists() or not dir_path_obj.is_dir():
        return {}
    
    pdf_files = find_pdf_files(dir_path)
    
    if not pdf_files:
        return {}
    
    results = {}
    
    for i, pdf_file in enumerate(pdf_files, 1):
        try:
            created_files = process_single_pdf_file(pdf_file, target_codes, output_dir)
            results[pdf_file] = created_files if created_files else []
        except Exception:
            results[pdf_file] = []

    return {
        "results": results,
        "cpu_cores": cpu_count(),
        "workers": NUM_WORKERS,
        "target_codes": target_codes
    }