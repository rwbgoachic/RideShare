# Implemented but Not Documented

## Driver app UI pages exist (Airport Queue, Auth, Dashboard, Earnings, Onboarding, Profile, Trip)

**Evidence:**
- ui:apps/driver-app/src/pages/AirportQueuePage.tsx
- ui:apps/driver-app/src/pages/AuthPage.tsx
- ui:apps/driver-app/src/pages/DashboardPage.tsx
- ui:apps/driver-app/src/pages/EarningsPage.tsx
- ui:apps/driver-app/src/pages/OnboardingPage.tsx
- ui:apps/driver-app/src/pages/ProfilePage.tsx
- ui:apps/driver-app/src/pages/TripPage.tsx

**Why not in requirements:**
The provided requirements batch focuses on build gates/process and tenancy/personas; it does not specify driver-app page-level UI capabilities. (Note: existence of pages is evidenced, but functionality behind them is not evidenced.)

## Rider app Booking page exists

**Evidence:**
- ui:apps/rider-app/src/pages/BookingPage.tsx

**Why not in requirements:**
The provided requirements batch does not describe rider booking UI screens/flows; only personas/tenancy/process gates. (Only page existence is evidenced.)

## Core ride-share domain tables exist in database schema (drivers, vehicles, trips, bookings, quotes, payments, ratings, airport_queues, etc.)

**Evidence:**
- file:(AS-IS summary) Database schema lists tables: drivers, vehicles, driver_locations, trips, ride_offers, riders, bookings, quotes, payments, ratings, airport_queues, driver_payouts, payment_refunds, saved_payment_methods, driver_bank_accounts

**Why not in requirements:**
The batch does not enumerate DB schema for these entities. However, the AS-IS evidence lacks db:table.column lines (columns unknown), so this is only evidence of table names existing, not full implemented data model.
