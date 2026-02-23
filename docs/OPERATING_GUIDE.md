# Operating Guide

## 1) Install

```bash
make install
```

## 2) Initialize Database (Alembic)

```bash
make init-db
```

## 3) Seed Demo Data

```bash
make seed
```

Expected seed shape on a fresh DB:
- 1 case
- 50 contractors
- 2000 submissions
- duplicates + conflicts present

## 4) Run API

```bash
make dev-api
```

## 5) Run Dashboard

In a new terminal:

```bash
make dev-ui
```

## 6) Run Checks

```bash
make lint
make test
```

## 7) Suggested Demo Flow

1. Open dashboard and select seeded case.
2. Show deadline countdown, throughput, pass rate, pending review.
3. Open Review Queue and inspect a conflicted submission.
4. Use manager actions (approve/reject/escalate).
5. Open event audit trail for that submission.
6. Export approved records (JSON/CSV).
7. Show Contractor Leaderboard updating from decisions.

## Troubleshooting

If migrations fail because tables already exist from pre-Alembic runs:

```bash
rm -f data/sentinel_ops.db
make init-db
make seed
```
