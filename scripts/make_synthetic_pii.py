"""Write eval/data/synthetic_pii.pdf: an obviously fictional employee record full of PII.

`python -m scripts.make_synthetic_pii`

Every value is invented. Emails use reserved `.example` domains, the US phone is
in the 555-01xx fiction range, and the card is the standard Visa test number.
The PDF is written by hand (one page, Helvetica) to avoid a PDF-writing dependency.
"""

from pathlib import Path

OUTPUT = Path(__file__).resolve().parent.parent / "eval" / "data" / "synthetic_pii.pdf"

# Tests import this to assert that none of these strings ever leaves the machine.
RAW_VALUES = {
    "PERSON": ["Ananya Kulkarni", "Rohan Deshpande", "Meera Kulkarni"],
    "EMAIL_ADDRESS": [
        "ananya.kulkarni@tamarind.example",
        "ananya.k@example.com",
        "rohan.deshpande@tamarind.example",
    ],
    "PHONE_NUMBER": ["+91 90000 00001", "+1 212 555 0142", "+91 90000 00002"],
    "IN_PAN": ["ABCPK1234Z"],
    "IN_AADHAAR": ["2345 6789 0123"],
    "CREDIT_CARD": ["4111 1111 1111 1111"],
}

LINES = [
    "FICTIONAL TEST RECORD. Every person, number and address below is invented.",
    "",
    "Employee profile: Ananya Kulkarni",
    "Ananya Kulkarni is a data engineer at Tamarind Labs in Pune. She joined in 2022",
    "and works on the Payments Data Platform team, where she maintains the LedgerLoom",
    "reconciliation pipeline.",
    "",
    "Contact details",
    "Work email: ananya.kulkarni@tamarind.example",
    "Personal email: ananya.k@example.com",
    "Mobile: +91 90000 00001",
    "Work phone (New York office): +1 212 555 0142",
    "",
    "Identity documents",
    "PAN: ABCPK1234Z",
    "Aadhaar: 2345 6789 0123",
    "",
    "Corporate card",
    "Card number: 4111 1111 1111 1111, used only for team travel.",
    "",
    "Reporting line",
    "Her manager is Rohan Deshpande (rohan.deshpande@tamarind.example).",
    "",
    "Emergency contact",
    "Meera Kulkarni (sister), mobile +91 90000 00002.",
]


def _pdf_bytes(lines: list[str]) -> bytes:
    def escape(text: str) -> str:
        return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    # One text block: 11pt Helvetica, 15pt leading, T* moves to the next line.
    stream = "BT /F1 11 Tf 15 TL 50 790 Td\n"
    stream += "".join(f"({escape(line)}) Tj T*\n" for line in lines)
    stream += "ET"

    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        "/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream",
    ]

    out = "%PDF-1.4\n"
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n{body}\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n"
    out += "".join(f"{offset:010d} 00000 n \n" for offset in offsets)
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n"
    return out.encode("latin-1")


if __name__ == "__main__":
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_bytes(_pdf_bytes(LINES))
    print(f"wrote {OUTPUT}")
