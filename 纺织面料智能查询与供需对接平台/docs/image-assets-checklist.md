# Image Assets Checklist (Internal Draft)

This checklist tracks image resources that are missing or need quality upgrades.
Current policy: do not block functional delivery on non-critical visuals.

| Asset Path | Status | Required to Run | Spec Suggestion | Owner | Due Date | Notes |
|---|---|---|---|---|---|---|
| `miniprogram/components/fabric-card/images/fabric-placeholder.png` | Missing | No | 600x600 PNG, <=80KB, neutral background | TBD | TBD | Optional fallback image. Current WXML already shows text placeholder when image is absent. |

## Naming Convention

- Use lowercase kebab-case file names.
- Keep semantic suffixes like `-active`, `-placeholder`, `-thumb`.
- Prefer PNG for icons/placeholders; WebP for large photos when supported.

## Handover Notes

- When official design assets arrive, replace files in-place to avoid code path changes.
- Record each asset update in this file with owner and date.
