try:
    import PyPDF2
    with open(r'd:\stockagent\NSE_Complete_Project_Blueprint.pdf', 'rb') as f:
        reader = PyPDF2.PdfReader(f)
        for i, page in enumerate(reader.pages):
            print('--- PAGE', i+1, '---')
            print(page.extract_text())
            print()
except ImportError:
    print("PyPDF2 not installed. Trying pdfplumber...")
    try:
        import pdfplumber
        with pdfplumber.open(r'd:\stockagent\NSE_Complete_Project_Blueprint.pdf') as pdf:
            for i, page in enumerate(pdf.pages):
                print('--- PAGE', i+1, '---')
                print(page.extract_text())
                print()
    except ImportError:
        print("Neither PyPDF2 nor pdfplumber available. Using raw file inspection...")
        with open(r'd:\stockagent\NSE_Complete_Project_Blueprint.pdf', 'r', encoding='latin-1', errors='ignore') as f:
            content = f.read()
            # Extract readable text
            import re
            text = re.sub(r'[^\x20-\x7e\n\t]', '', content)
            print(text[:2000])
