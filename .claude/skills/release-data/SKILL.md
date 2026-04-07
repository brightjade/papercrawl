---
name: release-data
description: Zip the data/ directory and upload it as a GitHub Release asset. Use this skill when the user asks to "release the data", "publish data", "upload data", "push data to release", "update the release", or any variation of shipping the current data/ contents to GitHub Releases.
---

# Release Data

Packages the current `data/` directory into `data.zip` and uploads it to a GitHub Release so users can download it via `setup.sh`.

## Steps

1. **Verify data exists**

   ```bash
   ls data/ | head -5
   ```

   If `data/` is empty or missing, stop and tell the user.

2. **Zip the data directory**

   ```bash
   cd /Users/mincloud/workspaces/paper-explorer && zip -r data.zip data/
   ```

   Report the resulting zip size.

3. **Delete old data releases**

   List and delete all previous `data-*` releases so only the latest snapshot exists:

   ```bash
   gh release list --repo brightjade/paper-explorer --limit 100 \
     | awk -F'\t' '$3 ~ /^data-/ { print $3 }' \
     | while read tag; do
         echo "Deleting old release: $tag"
         gh release delete "$tag" --repo brightjade/paper-explorer --yes --cleanup-tag
       done
   ```

   `--cleanup-tag` also deletes the associated git tag.

4. **Create the new release**

   Use a date-based tag: `data-YYYY-MM-DD` (today's date).

   ```bash
   gh release create "data-YYYY-MM-DD" data.zip \
     --repo brightjade/paper-explorer \
     --title "Data release YYYY-MM-DD" \
     --notes "Paper data snapshot from YYYY-MM-DD. Download and extract with ./setup.sh" \
     --latest
   ```

5. **Clean up**

   ```bash
   rm data.zip
   ```

   `data.zip` is in `.gitignore` so it should never be committed, but clean up anyway.

6. **Confirm** -- report the release URL to the user.

## Important

- Never commit `data.zip` to git. It is in `.gitignore`.
- Always use `--latest` when creating a release so `setup.sh` (which defaults to `latest`) picks it up.
- If the user specifies a custom tag, use that instead of the date-based default.
