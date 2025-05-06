from shadowAgent import ShadowAgent
from pdfExtractor import PdfTextExtractor
from summaryAgent import ContractAnalyzerAgent

if __name__ == "__main__":
    # Initialize agents
    ShadAgent = ShadowAgent()
    SummAgent = ContractAnalyzerAgent()

    # Set up PDF extractor
    extractor = PdfTextExtractor()
    pdf_file = "esempio_contratto.pdf"
    language = 'ita'

    try:
        # Extract text from PDF
        contract = extractor.extract_text_from_pdf(pdf_file, lang=language)
        
        print("\n" + "="*80)
        print("SHADOW ANALYSIS (Potential Issues and Risks):")
        print("="*80)
        shadow_analysis = ShadAgent.analyze(contract)
        print(shadow_analysis)
        
        print("\n" + "="*80)
        print("DETAILED CONTRACT ANALYSIS:")
        print("="*80)
        summary_analysis = SummAgent.analyze(contract)
        SummAgent.print_analysis(summary_analysis)
        
        # Save the summary analysis to JSON
        json_path = SummAgent.save_analysis(summary_analysis, "Contract Analysis")
        print(f"\nFull analysis saved to: {json_path}")
        
    except Exception as e:
        print(f"Error processing contract: {e}")