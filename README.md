# Anime Notebook

A lightweight Streamlit app for browsing a personal anime and manga list saved to a local JSON file.

## Features

- Browse 43 anime titles and one manga entry, grouped by category
- Search titles and filter by category or media type
- View and update season-by-season progress, overall totals, and ratings
- Calculate viewing percentage automatically and estimate watch time at 24 minutes per episode
- Add anime entries and optional cover image URLs; saved covers appear in title details
- Persist the list locally in `data/watchlist.json`

## Run locally

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Data storage

The supplied list is stored in `data/watchlist.json` and remains on the local machine.

## Share as read-only

Set `ANIME_NOTEBOOK_READ_ONLY=true` in the host environment, or add this to Streamlit app secrets:

```toml
ANIME_NOTEBOOK_READ_ONLY = "true"
```

This hides the add action and editing forms in the shared app. The local app remains editable when the setting is not enabled.

## Publish local changes to the public app

The local watchlist is stored in `data/watchlist.json`. To publish the latest local copy, create a [GitHub fine-grained personal access token](https://github.com/settings/personal-access-tokens/new) limited to the `affranphanjampee-art/kuroya` repository with **Contents: Read and write** permission. Do not paste the token into chat or commit it.

Paste the token directly into `.streamlit/secrets.toml` on the local machine. The `.streamlit/` directory is ignored by Git. Then use **เผยแพร่รายการล่าสุด** in the local app. The hosted app remains read-only and refreshes from the repository after the commit.
