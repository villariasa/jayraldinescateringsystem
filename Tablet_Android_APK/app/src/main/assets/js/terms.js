// Terms & Conditions data with structured HTML rendering for the kiosk UI.
const CURRENT_TERMS_VERSION = "1.0";
const TERMS_TITLE = "Jayraldine's Catering Services — Terms & Conditions";

const TERMS_TEXT = `JAYRALDINE'S CATERING SERVICES
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
19. NOTE: For the Wedding rate, an additional P30.00/head is charged for a minimum of 100 persons.`;

const TERMS_ACKNOWLEDGEMENT_LABEL = "I have read and understood the Catering Rules and Terms and Conditions.";

export function getTermsHtml() {
  return `
    <div class="terms-container">
      <!-- Business Header with Logo -->
      <div class="terms-business-card">
        <div style="display:flex; align-items:center; justify-content:center; gap:16px; margin-bottom:12px;">
          <img src="icons/logo.png" alt="Jayraldine's Catering Logo" class="terms-logo" style="width:68px; height:68px; min-width:68px; border-radius:12px; object-fit:cover; border:2.5px solid rgba(225,29,72,0.45); box-shadow:0 4px 16px rgba(0,0,0,0.2); display:block;">
          <div style="text-align:left;">
            <div class="terms-biz-title">JAYRALDINE'S CATERING SERVICES</div>
            <div class="terms-biz-address">📍 121 Katipunan Street, Barangay Calamba, Cebu City</div>
          </div>
        </div>
        <div class="terms-biz-contacts">
          <span class="contact-tag">📞 Globe: 255-3113 / 0917-651-9555</span>
          <span class="contact-tag">📞 Sun: 0922-775-9213</span>
          <span class="contact-tag">📞 Dito: 0991-652-8017</span>
        </div>
      </div>

      <!-- Section 1 -->
      <div class="terms-section">
        <div class="terms-section-header">
          <span class="sec-badge">1</span>
          <h4>Service Information &amp; Inclusions</h4>
        </div>
        <ul class="terms-list">
          <li><b>Standard Service:</b> Buffet-style standard service for a minimum reservation of <b>60 persons</b> within Cebu City (below-minimum reservations have special rates).</li>
          <li><b>VIP Table Service:</b> Available for limited-seating presidential tables (e.g. weddings) on bookings of 100 persons and above.</li>
          <li><b>Tables &amp; Chairs:</b> Complimentary use up to the reservation count on the event day.</li>
          <li><b>Amenities:</b> Includes tissues, filtered drinking water, toothpicks, etc.</li>
          <li><b>Backup Utensils:</b> 10 backup plates and utensils are provided for every 60+ pax reservation.</li>
          <li><b>Optional Extras:</b> Chair covers, extra entrees, soft drinks, bottled water, dispensers, and ice available upon request. Packed meals and snacks are also available.</li>
        </ul>
      </div>

      <!-- Section 2 -->
      <div class="terms-section">
        <div class="terms-section-header">
          <span class="sec-badge">2</span>
          <h4>Service Duration &amp; Overtime</h4>
        </div>
        <ul class="terms-list">
          <li><b>3 Hours Service:</b> Catering service is good for <b>3 hours</b> from the official start of the function.</li>
          <li><b>Overtime Fee:</b> The customer is responsible for compensating service staff/drivers for extensions beyond 3 hours at a minimum of <b>₱500.00 per hour</b>.</li>
          <li><b>Liquor Notice:</b> <span class="terms-alert">WE DO NOT SELL OR SERVE LIQUOR.</span> Clients must arrange beverage service for guests after 3 hours.</li>
          <li><b>Crew Meals:</b> Extra food is provided for service staff; crew meals are taken after all guests have been served.</li>
        </ul>
      </div>

      <!-- Section 3 -->
      <div class="terms-section">
        <div class="terms-section-header">
          <span class="sec-badge">3</span>
          <h4>Delivery, Venues &amp; Porterage Rates</h4>
        </div>
        <div class="terms-delivery-grid">
          <div class="rate-card"><span>Mandaue City</span><b>₱800</b></div>
          <div class="rate-card"><span>Talamban</span><b>₱800</b></div>
          <div class="rate-card"><span>Talisay City</span><b>₱800</b></div>
          <div class="rate-card"><span>Minglanilla</span><b>₱1,200</b></div>
          <div class="rate-card"><span>Cordova</span><b>₱1,300</b></div>
          <div class="rate-card"><span>Porterage (3F+ / no elevator)</span><b>₱500</b></div>
        </div>
        <p class="terms-subnote">Other areas and mountain locations are subject to custom evaluation. Any lost/damaged equipment will be charged accordingly.</p>
      </div>

      <!-- Section 4 -->
      <div class="terms-section">
        <div class="terms-section-header">
          <span class="sec-badge">4</span>
          <h4>Function Rooms &amp; Buffet Tables</h4>
        </div>
        <ul class="terms-list">
          <li><b>Event Place Function Rooms:</b> 2 fully air-conditioned rooms (80–100 pax and 50–60 pax capacity) with free built-in sound system &amp; mic. Maintenance fee: <b>₱2,000 / ₱1,000</b> for 3 hours.</li>
          <li><b>Buffet Tables:</b> 100 pax = 1 Buffet Table · 200 pax = Max 2 Tables (Additional Buffet Table: <b>₱500.00</b> each).</li>
          <li><b>Presidential Table:</b> 1 complimentary table for minimum 100 pax (Additional: <b>₱500.00</b> each).</li>
        </ul>
      </div>

      <!-- Section 5 -->
      <div class="terms-section">
        <div class="terms-section-header">
          <span class="sec-badge">5</span>
          <h4>Payment, Reservation &amp; Wedding Policy</h4>
        </div>
        <ul class="terms-list">
          <li><b>Reservation Fee:</b> Minimum <b>₱2,000.00</b> (or <b>₱5,000.00</b> for Weddings/Debuts). Non-refundable but deducted from the total balance.</li>
          <li><b>50% Payment:</b> Half payment is required <b>1 week prior</b> to the event date.</li>
          <li><b>Full Balance:</b> Full payment must be settled before the start of the function. <span class="terms-highlight">Cash or verified electronic payment only.</span></li>
          <li><b>Wedding Rate:</b> Additional <b>₱30.00 / head</b> for wedding bookings (minimum 100 persons).</li>
        </ul>
      </div>
    </div>
  `;
}

export function getTerms() {
  return {
    version: CURRENT_TERMS_VERSION,
    title: TERMS_TITLE,
    text: TERMS_TEXT,
    html: getTermsHtml(),
    acknowledgement_label: TERMS_ACKNOWLEDGEMENT_LABEL,
  };
}
