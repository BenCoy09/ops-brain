# Ops Brain

A server that files its own incident tickets in Sanity and fixes itself after a human approves.

- opsbrain.py: the agent. Detects a down service, creates an incident in Sanity, and executes approved actions from a hard-coded allowlist.
- schemaTypes/incident.ts: the Sanity schema.

Run: SANITY_PROJECT_ID=your_id SANITY_TOKEN=your_editor_token sudo -E python3 opsbrain.py

Sanity project ID: hhoxq5y4
