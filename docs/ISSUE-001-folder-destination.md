# Bug: selected target folder gets source folder name appended

**Type:** bug  
**Suggested labels:** bug, priority:high  
**Baseline:** v1.02.0 (app v1.0.2)

## Steps to reproduce

1. Select source folder `C:\mydata`.
2. Select target folder `D:\mydata`.
3. Open the Robocopy command preview.

## Actual behavior

Robocopy destination becomes `D:\mydata\mydata`.

## Expected behavior

The chosen destination is used exactly: `D:\mydata`.

## Code location

`src/robocopy-replicator.py`, method `build_command()`:

```python
if source_path.is_dir():
    robocopy_source = source_path
    robocopy_target = target_root / source_path.name
```

## Acceptance criteria

- A single selected folder maps directly to the selected destination.
- Command preview shows the correct destination before copying.
- File sources and multiple-folder jobs have an explicitly defined, tested destination policy.
- `/MIR` remains guarded against unexpected deletion.
- Dry-run (`/L`) test passes on Windows.

**Status:** Open / not fixed in initial repository baseline.
