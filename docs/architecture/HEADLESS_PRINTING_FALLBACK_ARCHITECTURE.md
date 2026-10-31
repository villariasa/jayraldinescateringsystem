# Headless Printing Fallback Architecture

## 1. Fallback Topology
1. **Primary**: Windows GDI / Qt PrintSupport driver for thermal receipt and laser jet printers.
2. **Secondary Fallback**: Headless ReportLab vector PDF generation with automatic local spooling.
3. **Tertiary Fallback**: Raw ESC/POS socket stream on port 9100.
