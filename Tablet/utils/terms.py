"""
Catering Terms & Conditions ("Service Information") shown to the customer
before an order can be confirmed on the tablet (Tablet-mode.md sections 6/7).

Source: /jayraldinescateringsystem/SERVICE INFORMATION.docx (provided by the
business owner). CURRENT_TERMS_VERSION must be bumped every time this text
changes so historical orders keep the exact version they agreed to
(terms_acknowledgements.ta_version) - never edit old accepted text in place.
"""

CURRENT_TERMS_VERSION = "1.0"

TERMS_TITLE = "Jayraldine's Catering Services — Terms & Conditions"

TERMS_TEXT = """JAYRALDINE'S CATERING SERVICES
Located at 121 Katipunan Street, Barangay Calamba, Cebu City.
Tel. Globe: 255-3113 / 0917-651-9555 · Sun: 0922-775-9213 · Dito: 0991-652-8017

SERVICE INFORMATION:

1. Buffet style standard service for a minimum reservation of 60 persons within Cebu City; otherwise, below-minimum reservations will have special rates/packages.

2. VIP table service for limited-seating presidential tables (e.g. weddings) on reservations of 100 persons and above.

3. Tables and chairs are available for complimentary use up to the reservation amount on the day of the catering service.

4. Amenities include tissues, filtered drinking water, toothpicks, etc.

5. Ten backup plates/utensils are provided for every 60-persons-and-above reservation.

6. Optional chargeable items are available, including chair covers, additional entrees, extra soft drinks, individually bottled water, hot/cold water dispenser, extra ice cube/tube/block, and ice tea dispenser, etc.

7. Packed meals and snacks are also available.

8. Service is good for 3 hours from the start of the function. The customer is responsible for compensating waiters and drivers if the event extends beyond 3 hours, at a minimum of P500.00 per hour. (WE DON'T SELL OR SERVE LIQUOR.) The client should arrange for the guests after the 3 hours of service.

9. Extra food is provided to accommodate food service personnel; they may have their meals after guests have been served.

10. Additional delivery/transportation charges apply for venues such as: Mandaue City – P800, Talamban – P800, Cordova – P1,300, Talisay – P800, and Minglanilla – P1,200. Other places and mountain areas are subject to evaluation.

11. A porterage fee of P500.00 applies for venues not easily accessible by commercial vehicles, or located on the 3rd floor and above without elevator access.

12. In case of loss or damage of any caterer's equipment not due to handling by the food service personnel, a corresponding price shall be charged.

13. Jayraldine's Catering Event Place is optionally available as a venue for parties.

14. Our 2 function rooms are fully air-conditioned, with 80–100 person and 50–60 person capacity. A built-in sound system with microphone is available for free use. Function room maintenance fee is only P2,000 and P1,000 for 3 hours.

15. One elegant buffet table can be added for every hundred persons:
    • 100 persons = 1 Buffet Table
    • 200 persons = Maximum of 2 Buffet Tables
    • Additional Buffet Table: P500.00 each

16. One complimentary Presidential Table for a minimum of 100 persons. Additional Presidential Table: P500.00.

17. A reservation fee is required: minimum P2,000, or P5,000 for Weddings and Debuts. The reservation fee is non-refundable but will be deducted from the total bill. Half payment shall be made one week before the event.

18. Full payment shall be made before the start of the function. We only accept CASH PAYMENT.

19. NOTE: For the Wedding rate, an additional P30.00/head is charged for a minimum of 100 persons.
"""

TERMS_ACKNOWLEDGEMENT_LABEL = "I have read and understood the Catering Rules and Terms and Conditions."


# ─────────────────────────────────────────────────────────────────────────
# Post-event customer evaluation survey — captured in the same source
# document but NOT part of the Tablet-mode.md scope yet. Kept here, unused,
# for a future "Evaluation Survey" feature so the questions don't need to be
# re-transcribed later.
# ─────────────────────────────────────────────────────────────────────────
EVALUATION_SURVEY_QUESTIONS = [
    "Food Quality",
    "Overall Service",
    "Cleanliness",
    "Order Accuracy",
    "Speed of Service",
    "Value",
    "Overall Experience",
]
EVALUATION_SURVEY_SCALE = ["Excellent", "Good", "Average", "Dissatisfied"]
