import fitz  # PyMuPDF
from PIL import Image
import io
import pytesseract

class PdfTextExtractor:
    def __init__(self, tesseract_cmd=None):
        """
        Inizializza PdfTextExtractor con un percorso opzionale all'eseguibile di Tesseract.
        Se tesseract_cmd è None, pytesseract cercherà l'eseguibile nel PATH.
        """
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    def _pdf_to_images(self, pdf_path):
        """Converte le pagine di un PDF in immagini PIL."""
        images = []
        try:
            pdf_document = fitz.open(pdf_path)
            for page_num in range(pdf_document.page_count):
                page = pdf_document.load_page(page_num)
                pix = page.get_pix()
                img_data = pix.tobytes("ppm")
                image = Image.open(io.BytesIO(img_data))
                images.append(image)
            pdf_document.close()
        except Exception as e:
            print(f"Errore durante la conversione del PDF in immagini: {e}")
        return images

    def extract_text_from_image(self, image, lang='ita'):
        """Estrae il testo da una singola immagine utilizzando Tesseract."""
        try:
            text = pytesseract.image_to_string(image, lang=lang)
            return text
        except pytesseract.TesseractNotFoundError:
            print("Errore: Tesseract non è installato o non è nel PATH.")
            print("Assicurati che Tesseract sia installato e che il percorso all'eseguibile sia configurato correttamente.")
            return ""
        except Exception as e:
            print(f"Errore durante l'estrazione del testo dall'immagine con Tesseract: {e}")
            return ""

    def extract_text_from_pdf(self, pdf_path, lang='ita'):
        """Estrae il testo da un PDF, gestendo sia PDF nativi che scansioni utilizzando Tesseract."""
        try:
            pdf_document = fitz.open(pdf_path)
            text = ""
            is_scanned = False
            for page_num in range(pdf_document.page_count):
                page = pdf_document.load_page(page_num)
                page_text = page.get_text("text")
                if not page_text.strip():
                    is_scanned = True
                    break  # Se una pagina è vuota, probabilmente è una scansione
                text += page_text + "\n"
            pdf_document.close()

            if is_scanned:
                print(f"Il PDF '{pdf_path}' sembra essere una scansione. Eseguendo l'OCR con Tesseract...")
                images = self._pdf_to_images(pdf_path)
                full_text = ""
                for image in images:
                    page_text = self.extract_text_from_image(image, lang=lang)
                    full_text += page_text + "\n"
                return full_text
            else:
                print(f"Il PDF '{pdf_path}' sembra essere un PDF nativo.")
                return text

        except Exception as e:
            print(f"Errore durante l'elaborazione del PDF '{pdf_path}': {e}")
            return ""

def main():
    # Se Tesseract non è nel PATH, specifica il percorso all'eseguibile:
    # tesseract_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    # extractor = PdfTextExtractor(tesseract_path)
    extractor = PdfTextExtractor()
    pdf_file = "esempio_contratto.pdf"  # Sostituisci con il percorso del tuo PDF
    language = 'ita'  # Imposta la lingua per l'OCR (ISO 639-1 code)

    extracted_text = extractor.extract_text_from_pdf(pdf_file, lang=language)

    if extracted_text:
        print("\nTesto estratto dal PDF (con Tesseract):")
        print(extracted_text)
    else:
        print("Nessun testo estratto dal PDF.")

if __name__ == "__main__":
    main()