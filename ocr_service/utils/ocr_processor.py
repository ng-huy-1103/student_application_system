# -*- coding: utf-8 -*-
"""
OCR Processor for extracting text from documents using Tesseract OCR.
"""
import os
import cv2
import numpy as np
import pytesseract
import fitz  #
from PIL import Image 
import langdetect
import docx 

from skimage.transform import radon
from skimage.filters import threshold_otsu
from skimage.transform import rotate
from skimage.color import rgb2gray
from skimage.util import img_as_ubyte

class OCRProcessor:
    """
    Class for processing documents and extracting text.
    Uses Tesseract OCR for images/PDFs, and direct extraction for TXT/DOCX.
    Supports multiple languages for OCR, focusing on English and Russian.
    Implements layout analysis for structured documents.
    """

    def __init__(self):
        """Initialize OCR processor.
        Tesseract installation and tesseract_cmd path should be handled in environment setup.
        Example for Windows (in setup_environment.md):
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        """
        try:
            pytesseract.get_tesseract_version()
            print("Tesseract OCR found.")
        except pytesseract.TesseractNotFoundError:
            print("Warning: Tesseract OCR not found or not in PATH. OCR will fail.")
        except Exception as e:
            print(f"Warning: Error checking Tesseract version: {e}")

    def detect_language(self, text):
        """
        Detect the language of the text using langdetect.
        Args:
            text (str): Text to detect language from
        Returns:
            str: Language code (e.g., 'en', 'ru')
        """
        try:
            if not text or len(text.strip()) < 10:
                return 'en'
            lang = langdetect.detect(text)
            if lang in ['ru', 'uk', 'bg', 'sr', 'mk']:
                return 'rus'
            elif lang == 'en':
                return 'eng'
            return lang
        except langdetect.lang_detect_exception.LangDetectException:
            return 'en'
        except Exception as e:
            return 'en'

    def _deskew(self, image_gray_ubyte):
        """
        Deskew a grayscale image using Radon transform.
        """
        try:
            if image_gray_ubyte.ndim == 3:
                 image_gray_ubyte = cv2.cvtColor(image_gray_ubyte, cv2.COLOR_BGR2GRAY)
            
            thresh_val = threshold_otsu(image_gray_ubyte)
            binary = image_gray_ubyte > thresh_val

            angles = np.deg2rad(np.arange(-10.0, 10.0, 0.2))
            projections = radon(binary, theta=angles, circle=False)
            
            variances = np.std(projections, axis=0)
            best_angle_rad = angles[np.argmax(variances)]
            best_angle_deg = np.rad2deg(best_angle_rad)
            
            if np.issubdtype(image_gray_ubyte.dtype, np.floating):
                image_for_rotate = image_gray_ubyte
                cval = np.max(image_gray_ubyte)
            else:
                image_for_rotate = image_gray_ubyte / 255.0
                cval = 1.0

            deskewed_image_float = rotate(image_for_rotate, best_angle_deg, resize=True, cval=cval, mode='edge')
            deskewed_image_ubyte = img_as_ubyte(deskewed_image_float)
            return deskewed_image_ubyte
        except Exception as e:
            print(f"Error during deskewing: {e}. Returning original image.")
            return image_gray_ubyte

    def _ocr_image_tesseract(self, image_cv, lang='eng+rus'):
        """
        Perform OCR on a single OpenCV image (BGR) after preprocessing and deskewing.
        """
        gray_image = cv2.cvtColor(image_cv, cv2.COLOR_BGR2GRAY)
        deskewed_gray_image = self._deskew(gray_image)
        ocr_ready_image = deskewed_gray_image

        try:
            custom_config = f'-l {lang} --psm 3'
            text = pytesseract.image_to_string(Image.fromarray(ocr_ready_image), config=custom_config)
            return text
        except pytesseract.TesseractError as e:
            print(f"Tesseract OCR error: {e}")
            return ""
        except Exception as e:
            print(f"Unexpected error during Tesseract OCR: {e}")
            return ""

    def _analyze_layout_and_ocr(self, image_cv, lang='eng+rus'):
        """
        Perform layout analysis and OCR for structured documents.
        Optimization: Limit number of contours, adjust min area.
        """

        gray_image = cv2.cvtColor(image_cv, cv2.COLOR_BGR2GRAY)

        deskewed_gray = self._deskew(gray_image)


        _, binary_img = cv2.threshold(deskewed_gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)


        contours, _ = cv2.findContours(binary_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
 
        
        extracted_texts = []
    
        min_contour_area = 750  
        min_w, min_h = 40, 15
        max_contours_to_process = 200 

        contours = sorted(contours, key=lambda ctr: (cv2.boundingRect(ctr)[1], cv2.boundingRect(ctr)[0]))

        processed_contour_count = 0
        for i, contour in enumerate(contours):
            if processed_contour_count >= max_contours_to_process:

                break

            x, y, w, h = cv2.boundingRect(contour)
            # print(f"Contour {i}: x={x}, y={y}, w={w}, h={h}, area={cv2.contourArea(contour)}")
            if w > min_w and h > min_h and cv2.contourArea(contour) > min_contour_area:
                # print(f"Processing contour {i} with sufficient area/size.")
                cropped_region_gray = deskewed_gray[y:y+h, x:x+w]
                
                custom_config = f'-l {lang} --psm 6' 
                try:
                    # print(f"  OCR-ing region for contour {i}...")
                    region_text = pytesseract.image_to_string(Image.fromarray(cropped_region_gray), config=custom_config)
                    # print(f"  Region text for contour {i}: '{region_text[:50].strip()}...' ")
                    if region_text.strip():
                        extracted_texts.append(region_text.strip())
                except pytesseract.TesseractError as e:
                    print(f"Tesseract error on region {i}: {e}")
                except Exception as e:
                    print(f"Error OCRing region {i}: {e}")
                processed_contour_count += 1


        return "\n\n".join(extracted_texts)

    def _process_pdf(self, pdf_path, document_type, lang='eng+rus'):
        """
        Extract text from a PDF file using Tesseract OCR.
        """
        extracted_text_parts = []
        structured_doc_keywords = ['degree', 'certificate', 'additional_documents'] 
        is_structured = False
        if document_type:
            for keyword in structured_doc_keywords:
                if keyword in document_type.lower():
                    is_structured = True
                    break
        
        print(f"Processing PDF: {pdf_path}, Type: {document_type}, Structured: {is_structured}")

        try:
            doc = fitz.open(pdf_path)
            for page_num in range(len(doc)):
                # print(f"Processing page {page_num + 1}/{len(doc)} of PDF: {pdf_path}")
                page = doc.load_page(page_num)
                zoom = 2.0  # 144 DPI
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                
                img_np = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
                img_cv = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)

                page_text = ""
                if is_structured:
                    # print(f"  Applying layout analysis for page {page_num + 1}...")
                    page_text = self._analyze_layout_and_ocr(img_cv, lang=lang)
                else:
                    # print(f"  Applying standard OCR for page {page_num + 1}...")
                    page_text = self._ocr_image_tesseract(img_cv, lang=lang)
                
                extracted_text_parts.append(page_text)
                # print(f"  Finished processing page {page_num + 1}. Text length: {len(page_text)}")
            doc.close()
        except Exception as e:
            print(f"Error processing PDF {pdf_path}: {e}")
            raise Exception(f"Failed to process PDF with Tesseract: {str(e)}")
            
        return "\n\n--- Page Break ---\n\n".join(extracted_text_parts)

    def _process_image(self, image_path, lang='eng+rus'):
        """
        Extract text from an image file using Tesseract OCR.
        """
        img_cv = cv2.imread(image_path)
        if img_cv is None:
            raise ValueError(f"Could not read image file: {image_path}")
        return self._ocr_image_tesseract(img_cv, lang=lang)

    def process_document(self, file_path, document_type=None):
        """
        Main method to process a document based on its type.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Document not found at path: {file_path}")

        file_ext = os.path.splitext(file_path)[1].lower()
        ocr_lang = 'eng+rus'

        if file_ext == '.txt':
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except UnicodeDecodeError:
                encodings = ['latin-1', 'cp1251', 'iso-8859-5']
                for enc in encodings:
                    try:
                        with open(file_path, 'r', encoding=enc) as f:
                            return f.read()
                    except Exception:
                        continue
                raise Exception(f"Could not decode text file {file_path} with any supported encoding.")
            except Exception as e:
                raise Exception(f"Error processing text file {file_path}: {str(e)}")

        elif file_ext == '.docx':
            try:
                doc = docx.Document(file_path)
                full_text = [para.text for para in doc.paragraphs]
                return '\n'.join(full_text)
            except Exception as e:
                raise Exception(f"Error processing DOCX file {file_path}: {str(e)}")
        
        elif file_ext == '.pdf':
            return self._process_pdf(file_path, document_type, lang=ocr_lang)
        
        elif file_ext in ['.png', '.jpg', '.jpeg', '.bmp', '.tiff']:
            return self._process_image(image_path=file_path, lang=ocr_lang)
        else:
            raise ValueError(f"Unsupported file format: {file_ext} for document {file_path}")

if __name__ == '__main__':
    processor = OCRProcessor()
    print("OCR Processor initialized for local test.")
    test_dir = 'ocr_test_files_temp'
    os.makedirs(test_dir, exist_ok=True)
    txt_file = os.path.join(test_dir, 'test.txt')
    with open(txt_file, 'w', encoding='utf-8') as f:
        f.write("This is a test text file in English.\nЭто тестовый текстовый файл на русском языке.")
    print(f"\n--- Testing TXT file: {txt_file} ---")
    try:
        text_result = processor.process_document(txt_file)
        print(f"TXT Result:\n{text_result}")
    except Exception as e:
        print(f"Error processing TXT: {e}")

