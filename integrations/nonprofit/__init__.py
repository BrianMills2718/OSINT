"""
Nonprofit organization data source integrations.

This package provides integrations for nonprofit research databases
and investigative journalism resources.

Modules:
    propublica_integration: ProPublica Nonprofit Explorer API
"""

from integrations.nonprofit.propublica_integration import ProPublicaIntegration

__all__ = ["ProPublicaIntegration"]
