name: 🟢 Live 1-Minute Fixed

on:
  schedule:
    - cron: '*/5 * * * *'
  workflow_dispatch:

jobs:
  live:
    runs-on: ubuntu-latest
    env:
      PAGE_ID: ${{ secrets.PAGE_ID }}
      PAGE_ACCESS_TOKEN: ${{ secrets.PAGE_ACCESS_TOKEN }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install requests

      - name: Run Bot
        run: python bot.py

      - name: Save State
        uses: stefanzweifel/git-auto-commit-action@v5
        with:
          commit_message: "🟢 state"
          file_pattern: 'posted_state.json'
