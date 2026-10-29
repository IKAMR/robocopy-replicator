# Robocopy Replicator

A Python-based Windows GUI for copying and replicating files, folders and drive contents using Microsoft Robocopy.

Robocopy Replicator provides a graphical interface for configuring, executing and monitoring Robocopy jobs without manually constructing command-line commands.

## Features

- **Multiple sources** — Add folders and individual files to a single replication job.
- **Source management** — Reorder, remove and organize sources before execution.
- **Drag and drop** — Add sources from Windows Explorer when `tkinterdnd2` is installed.
- **Target selection** — Copy folder contents directly into the selected destination, without adding the source folder name.
- **Drive replication** — Copy between drive roots, such as `D:\` to `E:\`.
- **Live output** — Monitor Robocopy execution in the application.
- **Job summaries** — Review results, status, duration and success or failure for each source.
- **Logging** — Save logs locally, at the source or at the destination.
- **Dry run** — Preview operations using Robocopy's `/L` option without copying files.
- **Advanced options** — Configure recursion, mirroring, retries, wait intervals, multithreading, exclusions and additional Robocopy parameters.
- **Profiles** — Save and load reusable configurations.
- **Saved jobs** — Save, load and restore replication jobs.
- **Command preview** — Inspect or copy generated commands before execution.
- **Resizable interface** — Adjustable source/output panels and vertical scrolling.

## Requirements

- Windows 10 or Windows 11
- Python 3.10 or newer
- Microsoft Robocopy (included with Windows)

Optional drag-and-drop support:

```bash
pip install tkinterdnd2
```

## Running the application

Start with `src\robocopy-replicator.bat`, or run:

```bash
python src/robocopy-replicator.py
```

## Basic usage

1. Add one or more source folders, files or drive roots.
2. Select the target folder or drive.
3. Configure the desired replication options.
4. Optionally enable **Dry run /L** to preview the operation.
5. Click **START REPLICATION**.
6. Monitor the live output and review the final job summary.

## Configuration and logging

The application supports persistent settings, reusable profiles and saved jobs using JSON files. Robocopy execution logs and final job summaries can be saved for later review.

## Version

**v1.0.3**

## Maintainer

**IKAMR — Interkommunalt arkiv for Møre og Romsdal**
