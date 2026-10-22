"""FastAPI backend wrapping the quimrag/ research library as a real HTTP
service -- see docs/production/ARCHITECTURE_DECISIONS.md for why this is a
modular monolith (one process) rather than separate microservices, and why
SQLite is the default store rather than Postgres."""
