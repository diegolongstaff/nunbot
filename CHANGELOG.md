# Changelog

## Unreleased

### Updated
- Refreshed `nun_procedimientos.csv` honorarios to match the *Valores referenciales de las complejidades del Nomenclador Único Nacional (NUN) de Traumatología y Ortopedia — Marzo 2026* PDF.
- Added regression coverage to verify that every procedure complexity maps to the March 2026 reference values.
- Documented the March 2026 tariff update in the README and architecture snapshot.

### Verification
- `python3.11 -m pytest -q` → `13 passed`
