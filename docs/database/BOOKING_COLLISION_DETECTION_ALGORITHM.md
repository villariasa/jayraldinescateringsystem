# Booking Collision Detection Algorithm Specification

## 1. Conflict Criteria
A scheduling conflict occurs when:
$$\text{Venue}_A = \text{Venue}_B \quad \land \quad \text{Date}_A = \text{Date}_B \quad \land \quad [\text{Start}_A, \text{End}_A] \cap [\text{Start}_B, \text{End}_B] \neq \emptyset$$

## 2. Prevention Behavior
- The calendar interface displays visual red collision alerts.
- A confirmation dialog warns the cashier before saving overlapping bookings.
