# Robocopy Replicator

A Python-based Windows GUI for copying and replicating files and folders using Microsoft Robocopy.

Robocopy Replicator provides a graphical interface for configuring, executing and monitoring Robocopy jobs without manually constructing command-line commands.

## Features

- **Multiple sources** — Add folders and individual files to a single replication job.
- **Source management** — Reorder, remove and organize sources before execution.
- **Drag and drop** — Add sources directly from Windows Explorer when `tkinterdnd2` is installed.
- **Target selection** — Choose the destination folder for replication.
- **Live output** — Monitor Robocopy execution and progress in the application.
- **Job summaries** — View execution results, status, duration and success or failure for each source.
- **Logging** — Save Robocopy logs locally, at the source or at the destination.
- **Dry run** — Preview replication using Robocopy's `/L` option without copying files.
- **Advanced options** — Configure recursion, mirroring, retries, wait intervals, multithreading, exclusions and additional Robocopy parameters.
- **Profiles** — Save and load reusable Robocopy configurations.
- **Saved jobs** — Save, load and restore replication jobs.
- **Command preview** — Inspect or copy the generated Robocopy commands before execution.
- **Resizable interface** — Adjustable source/output panels and vertical scrolling for smaller screens.

## Requirements

- Windows 10 or Windows 11
- Python 3.10 or newer
- Microsoft Robocopy (included with Windows)

The application uses Python's standard library.

Optional dependency for drag-and-drop support:

```bash
pip install tkinterdnd2
```

## Running the application

Start the application using:

```text
src\robocopy-replicator.bat
```

Or run it directly with Python:

```bash
python src/robocopy-replicator.py
```

## Basic usage

1. Add one or more source folders or files.
2. Select the target folder.
3. Configure the desired replication options.
4. Optionally enable **Dry run /L** to preview the operation.
5. Click **START REPLICATION**.
6. Monitor the live output and review the final job summary.

## Configuration and logging

The application supports persistent settings, reusable profiles and saved jobs using JSON files.

Robocopy execution logs and final job summaries can be saved for documentation and later review.

## Version

Initial repository version: **v1.0.2**

## License

No license has been specified.

## Maintainer

**IKAMR — Interkommunalt arkiv for Møre og Romsdal**

