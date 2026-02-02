# Feature Backend Configuration

- ID 02
- Name Backend Configuration
- Status: Planning

## Goal

Provide a flexible configuration system for the backend to manage different heat pump models, data sources, and user preferences.
The configuration shall be done at a central place in the code and be easily extendable for future features.
The configuration should support environment variables.
It has to be ensured that no code uses the environment variables directly, but only via the configuration system.
