# Development notes

## Initial repository import

The baseline Python file is the supplied working v1.0.2 without code modifications. The BAT launchers were renamed to point at `robocopy-replicator.py`. No Windows runtime test was performed when preparing the repository.

## Version directory names

Keep a consistent filename (`robocopy-replicator.py` and `.bat`) in each version directory. Use the folder name for the release, e.g. `v1.02`, and update the application version string for subsequent releases.

## Local data

The application derives settings, profiles, saved jobs and last-job filenames from the Python script's filename and directory. Renaming the program therefore changes where these files are found. Old settings are not automatically migrated. Historical versions keep separate local state.

## First change to implement

Issue #1: make selected target directory the exact destination for a single folder source, rather than automatically appending the source folder name. Clarify desired behavior for multiple sources and individual files; add tests for command construction and `/MIR` safety before release.

## Manual smoke tests on Windows

1. Open main BAT and historical BAT.
2. Add folder and file sources; inspect command preview.
3. Run `/L` dry run with and without advanced options.
4. Check output, summary logs, saved job and settings persistence.
5. Test window scrolling and source/output divider.
