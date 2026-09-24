"""
plantlab - a deliberately vulnerable mock of the Deccan OT-03 environment.

For teaching and incident-reconstruction practice only.
All hosts are loopback. All entities are fictional.

Layout mirrors the two-site reality the case study describes: there is no
firewall object in this package because the corporate-to-plant boundary is a
log source in the scenario, not a barrier that stopped anything.
"""

__all__ = [
    "config", "stores", "protocol", "safety_controller",
    "control_system", "process_model", "historian", "corporate",
]
