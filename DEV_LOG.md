# Development Log

## Overview
Daily tracking and development notes for Jayraldine's Catering System.

### Project Structure
- Catering: Core web platform and backend services
- Tablet: Tablet application modules
- Tablet_Android_APK: Android wrapper and APK build
- Tablet_PWA: PWA packaging and offline assets

### Documentation Checklist
- [x] Project proposal documentation
- [x] APK build guidelines
- [ ] Offline sync optimization notes

### Catering Modules
- Reservations and event scheduling
- Menu and package configurations
- Inventory tracking and item management

### Tablet Interface
- Optimized touch layouts for order taking
- Real-time POS integration
- Responsive styling for various screen orientations

### Android Build Notes
- Verified Gradle wrapper configuration
- Android SDK build tools version verification
- Asset packaging for offline resources

### PWA Deployment
- Service worker caching strategies
- Offline asset manifest verification
- LocalStorage fallback mechanisms

### Quality Assurance
- Unit test coverage for core calculation helpers
- Integration tests for reservation workflows
- Mobile view verification across devices

### Database & Schema
- SQLite local caching on client devices
- Backend MySQL/MariaDB sync endpoints
- Conflict resolution strategies for offline updates

### Styling Guidelines
- Cohesive color scheme and typography hierarchy
- Button states, micro-interactions, and accessibility
- Standardized modal dialogs and alert banners

### Reporting Engine
- Export to PDF with customized branding
- Excel data export for sales and ledger analysis
- Automated summary logs for daily transactions

### Billing & Invoicing
- Itemized statements and discount computation
- Payment tracking (Cash, Card, Digital)
- Statement generation timestamp tracking

### Network Handling
- Online/offline event listeners in client scripts
- Request queuing when connectivity drops
- Automatic sync retry upon reconnection

### Release Verification
- Lint and syntax checks
- Build artifact size audit
- Cross-browser and WebView testing

### Maintenance
- Daily logs updated and verified
- Repository documentation in sync with current state

## Colab Build Notes
- Python 3.11 environment setup steps documented.
- NDK installation auto-fetch fallback verified.

## SQLite Kiosk Schema
- Documented migration strategy for offline tables.
- Added version check on kiosk database initialization.

## Service Worker Strategy
- Network-first for dynamic API routes, cache-first for static assets.
- Version bump triggers automatic cache clear.

## Offline Mode Checklist
- Disconnect wifi and test cart persistency.
- Verify cached Lottie animations load without external fetch.
- Verify local order creation and pending sync badges.

## Kiosk Display Configuration
- Touch area padding for 10-inch and 8-inch portrait tablets.
- Prevent double-tap zoom via viewport meta constraints.

## Catering Packages
- Documented base package pax tiers and add-on rates.
- Added note on customized dish swapping rules.

## Asset Optimization
- Converted vector animations to bundled JS objects for zero-latency offline display.
- Removed unused keyframes in cloche loading animation.

## Order Status Lifecycle
- Pending -> Confirmed -> In Preparation -> Delivered -> Completed.
- Cancellation transition locks order from further edits.

## PIN Security
- Admin PIN stored using hash verification.
- Lockout timeout after 5 consecutive failed attempts.

## WebViewAssetLoader
- Custom domain handler for local apk assets.
- Eliminates CORS restrictions on file:// URLs inside Android WebView.

## Sync Queue Protocol
- Exponential backoff retry (5s, 15s, 30s, 60s).
- Batch synchronization on network status recovery.

## Performance Benchmarks
- Time to Interactive (TTI) < 1.2s on target tablet.
- Reduced DOM reflow by eliminating backdrop filter blurs.

## Booking Flow
- Step 1: Customer details & event date selection.
- Step 2: Package & menu selection.
- Step 3: Add-ons & special requests.
- Step 4: Summary & confirmation.

## Reporting Engine Config
- Standardized header logo and currency formatting (PHP).
- Auto-fit columns for Excel sales export.

## Summary
- Dev logs and architecture references synced.

## September 4, 2026 - Daily Development Log

### Offline Storage & IndexedDB Synchronization
- IndexedDB table `orders_offline_cache` structured to buffer transaction payloads when offline.
- Added versioning migration for payload schema v2 containing timestamp and device ID.
- Background sync dispatcher periodically queries pending records and commits them sequentially upon network reconnection.

### Kiosk Touch Responsiveness & Gesture Rejection
- Disabled iOS/Android elastic scroll overscroll bounce on full screen containers via CSS `overscroll-behavior: none`.
- Added touch deadzone filtering around edge margins to prevent accidental swipe dismissals during customer order entry.
- Fine-tuned active tap highlight threshold to 80ms for instant visual tap feedback.

### Lottie Animation Frame Rate Budget & Memory Management
- Configured Lottie canvas renderer with maximum target FPS capped at 45 to preserve tablet battery and thermal profile.
- Explicitly destroy Lottie instances on modal unmount to prevent detached DOM tree references and memory leakage.
- Validated heap allocation stability during repeated cart add/remove cycles.

### Thermal Printer ESC/POS Protocol Specifications
- Documented standard 80mm ESC/POS command bytes (`0x1B, 0x40` initialize, `0x1D, 0x56, 0x42` paper cut).
- Structured bilingual receipt template with header logo bit-image rasterization.
- Defined fallback retry buffer when Bluetooth socket connection drops mid-print.

### Menu Item Allergen Tagging & Dietary Filters
- Added standard allergen metadata flags (Peanuts, Dairy, Gluten, Shellfish, Eggs).
- Documented filtering pipeline allowing customers to exclude items matching specific allergen profiles in real time.
- Integrated dietary badge iconography alongside menu item pricing cards.

### Order Receipt Layout & Typography Standards
- Standardized monospace font hierarchy for receipt line items, quantities, and totals.
- Added explicit column formatting: Description (24 chars), Qty (4 chars), Unit Price (8 chars), Total (10 chars).
- Configured tax breakdown, service charge calculations, and QR transaction verification footer.

### POS Order Queue Status Transitions
- Outlined state transitions: `NEW` -> `ACKNOWLEDGED` -> `PREPARING` -> `READY_FOR_PICKUP` -> `COMPLETED`.
- Defined timeout threshold (15 minutes) for unacknowledged orders to trigger audible supervisory alerts.
- Added state reconciliation check on app resume to detect remote updates from manager portal.

### Cash Drawer Trigger Specifications
- Specified 24V pulse command (`0x1B, 0x70, 0x00, 0x19, 0xFA`) sent through receipt printer RJ12 port.
- Documented manual key-lock override procedure and audit logging on cash drawer open events.
- Restricted cash drawer kick command permissions exclusively to Cashier and Admin role tokens.

### Audio Feedback & Chime Notifications
- Integrated Web Audio API synthesized tones (440Hz / 880Hz soft marimba chime) for item selection and successful checkout.
- Configured audio volume limiting capped at 65dB to avoid ambient disruption in dining hall environments.
- Added mute toggle override in kiosk supervisor settings menu.

### Portrait Kiosk Orientation Locking Policies
- Enforced portrait orientation (`screen.orientation.lock('portrait-primary')`) with manifest `orientation: portrait`.
- Documented polyfill and fullscreen handler for legacy Android WebViews lacking Screen Orientation API support.
- Set minimum supported resolution to 800x1280 portrait tablet standards.

### Catering Packages Headcount Computation Rules
- Tier 1: 50–99 pax (base flat rate + per-head tier A surcharge).
- Tier 2: 100–249 pax (discounted per-head tier B pricing + complimentary beverage station).
- Tier 3: 250+ pax (custom executive package with custom staffing and logistics allowance).
- Documented automatic recalculation of buffer portions (10% extra buffer allocation).
