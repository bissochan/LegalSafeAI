from shadowAgent import ShadowAgent
from pdfExtractor import PdfTextExtractor
from summaryAgent import ContractAnalyzerAgent

# Example usage in the main script
if __name__ == "__main__":
    ShadAgent = ShadowAgent()
    SummAgent = ContractAnalyzerAgent()

    # Analyze a custom contract
    custom_contract = """
    This is a custom contract. The second party agrees to pay $500 upfront. The first party will deliver services
    within 30 days. The contract is governed by the laws of New York.
    """
    extractor = PdfTextExtractor()
    pdf_file = "esempio_contratto.pdf"  # Sostituisci con il percorso del tuo PDF
    language = 'ita'  # Imposta la lingua per l'OCR (ISO 639-1 code)

    contract = extractor.extract_text_from_pdf(pdf_file, lang=language)
    print(ShadAgent.analyze(contract))
    print(SummAgent.analyze(contract))

    # Analyze using the placeholder contract
    #print("\nPlaceholder Contract Analysis:")
    #print(agent.analyze())