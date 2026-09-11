# Data folder

This directory is intentionally left for local, downloaded data files.

The CFPB complaint dataset used in this project is not stored in the repository because it is large and not suitable for GitHub version control.

## Required file

Download the raw Kaggle dataset and place it here:

- data/rows.csv

Alternatively, keep a subfolder such as:

- data/raw/rows.csv

Then update the `DATA_PATH` variable in the notebook to match the actual local path.

## Notes

- Keep this folder out of source control using the repository `.gitignore`.
- Do not commit raw CSV files or extracted archives.
- If you want to share derived outputs, save cleaned parquet or CSV versions in a separate `outputs/` folder instead.
