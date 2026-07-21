"""Service layer.

Services hold business logic and are the only place that mutates the database
for a given domain concept. Views (HTML) and API resources call into services
rather than touching models directly, which keeps request handlers thin and the
business rules testable in isolation.
"""
