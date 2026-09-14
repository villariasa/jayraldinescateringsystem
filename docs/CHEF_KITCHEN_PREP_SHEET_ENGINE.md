# Chef Kitchen Prep Sheet Engine & Batch Scaling

## 1. Batch Calculation Formula
Calculates raw ingredient procurement quantities based on confirmed guest headcount:

$$\text{Required Batch} = \text{Base Ingredient Quantity} \times \left(\frac{\text{Booking Guest Count}}{\text{Standard Recipe Yield}}\right) \times (1 + \text{Buffer Factor})$$

- **Standard Buffer Factor**: $5\%$ for standard buffet service; $10\%$ for high-volume corporate events.
- **Prep Categorization**: Groups kitchen tasks by station: Butchery, Marinades, Hot Kitchen, Pastry & Cold Larder.
