"""Create a fictional text-layer PDF for the quick start and screenshots."""

from pathlib import Path

from reportlab.pdfgen import canvas

OUTPUT = Path(__file__).with_name("sample.pdf")


def main() -> None:
    pdf = canvas.Canvas(str(OUTPUT), pagesize=(612, 792))
    pdf.setTitle("Fictional lab report sample")
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(48, 740, "Fictional lab report")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(48, 716, "Training example only. No real patient data.")
    rows = [
        "WBC 6.2 x10^3/uL 3.6-11.0",
        "Hemoglobin 9.8 g/dL 11.5-16.5 L",
        "Platelet Count 250 x10^3/uL 140-400",
        "Sodium 140 mmol/L 134-144",
        "TSH 2.1 uIU/mL 0.45-4.5",
    ]
    for index, row in enumerate(rows):
        pdf.drawString(48, 675 - 22 * index, row)
    pdf.save()
    print(f"wrote {OUTPUT}")


if __name__ == "__main__":
    main()
