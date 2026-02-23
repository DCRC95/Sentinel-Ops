# Architecture

## High-Level Flow

Contributors
↓
Submission Gateway (FastAPI)
↓
Validation Engine
↓
Conflict Detection
↓
Event Ledger
↓
Scoring & Enrichment
↓
Operations Dashboard (Streamlit)
↓
Manager Decisions
↓
Export Pipeline

## Components

### API Layer
Handles ingestion and exposes operational endpoints.

### Core Logic Layer (`/sentinel`)
Pure deterministic business logic:
- validation
- scoring
- hashing
- conflict detection

### Persistence Layer
SQLite database implementing append-only event sourcing.

### Presentation Layer
Streamlit dashboard for operational control.

## Architectural Style

Event-driven system using derived state.

State is reconstructed from events rather than mutated records.
