import pdfplumber
import os

pdf_files = [
    ('CRU_2023_Report', 'data/raw/CRU2024132_Energy_Monitoring_Report_for_2023.pdf'),
    ('CRU_2022_Report', 'data/raw/Energy-Monitoring-Report.pdf')
]

for label, path in pdf_files:
    print(f"\n==========================================")
    print(f"Inspecting {label}: {path}")
    print(f"==========================================")
    with pdfplumber.open(path) as pdf:
        print(f"Total pages: {len(pdf.pages)}")
        for idx, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            # Search for switching, market share, renegotiation, etc.
            keywords = ['switching', 'supplier', 'market share', 'renegotiat', 'domestic']
            found_kw = [kw for kw in keywords if kw in text.lower()]
            if 'switch' in text.lower() or 'market share' in text.lower():
                tables = page.extract_tables()
                if tables:
                    print(f"\n--- Page {idx+1} ({label}) | Tables found: {len(tables)} | Keywords: {found_kw} ---")
                    # print first 5 lines of text
                    preview = [line for line in text.split('\n') if any(k in line.lower() for k in ['table', 'figure', 'switch', 'share'])][:4]
                    print("  Text snippet:", preview)
                    for t_idx, t in enumerate(tables):
                        print(f"  Table {t_idx+1} (dims {len(t)}x{len(t[0]) if t else 0}):")
                        for r in t[:6]:
                            print("    ", r)
