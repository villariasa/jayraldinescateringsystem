# ReportLab Custom Font Registration & Unicode Support

## 1. Font Embedding Procedure
```python
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Register professional typography
pdfmetrics.registerFont(TTFont('Inter-Regular', 'assets/fonts/Inter-Regular.ttf'))
pdfmetrics.registerFont(TTFont('Inter-Bold', 'assets/fonts/Inter-Bold.ttf'))
```
- Guarantees exact rendering of Philippine Peso currency symbols (`₱`) across all generated PDF receipts.
