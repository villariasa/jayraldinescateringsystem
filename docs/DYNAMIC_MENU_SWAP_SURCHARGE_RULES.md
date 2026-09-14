# Dynamic Package Dish Upgrade & Surcharge Calculations

## 1. Price Differential Logic
When a guest swaps a standard package dish with a premium item:

$$\Delta\text{Price} = \max(0, \text{Custom Item Price} - \text{Base Category Allowance})$$

$$\text{Total Package Surcharge} = \Delta\text{Price} \times \text{Booking Guest Count}$$
