# BREAKOUT · Automatic 12-hour updates — $0 setup

This is the **automatic-update version** of your Roblox Breakout Watch site. It keeps the existing dark-themed research dashboard and adds a live signal panel at the top of Overview. It uses **GitHub Actions + GitHub Pages**, both available for free public repositories.

## Set it up once (no coding required)

1. Make a free GitHub account at <https://github.com/signup> (or log in).
2. Go to <https://github.com/new> and create a **Public** repository named `roblox-breakout-watch`. Make sure the default branch is **main**. You can initialise it with a README.
3. **Unzip this package** on your computer. In GitHub, open the new repository, choose **Add file → Upload files**, then drag the **contents of the unzipped folder**, including the hidden `.github` folder, into the browser. Commit them to **main**. (On a Mac, use Command+Shift+Period in Finder to show hidden `.github`.) Do **not** upload the ZIP as a single file; GitHub Pages needs the actual files.
4. In your GitHub repository, go to **Settings → Pages**. Set **Source = GitHub Actions**. Save if requested.
5. Go to **Actions → Update and publish BREAKOUT → Run workflow → Run workflow**. If GitHub asks you to enable workflows, do so. Let it finish and look for a green check mark.
6. Return to **Settings → Pages** and open the published URL. It should look like `https://YOUR-GITHUB-USERNAME.github.io/roblox-breakout-watch/`. Share this link with your friends.

If the workflow fails to push updated JSON, check **Settings → Actions → General → Workflow permissions**, and ensure Actions can write repository contents. The workflow requests only `contents: write` to save its measurement history.

## What will happen automatically?

Twice a day (at **00:17 and 12:17 UTC**), GitHub Actions will:

- Fetch **point-in-time** public Roblox current-player counts for the 20 tracked games.
- Record the figures with exact timestamps in `auto-data.json`.
- After at least 7 days of readings, calculate a roughly matched **7-day sampled-player-count change**, and write a careful rules-based trend summary.
- Publish the refreshed dashboard to your existing GitHub Pages link.

The website also detects when the latest reading is older than 18 hours and shows a stale-data warning. Scheduled Actions may run late or occasionally be skipped. Public Roblox APIs can also be unavailable.

**Not included:** importing the separate ChatGPT 12-hour Roblox Breakout Watch prose alerts automatically. Those alerts are not available to this GitHub job. The original reports in the Research Feed remain historical and need manual import. A separate integration would be required to transfer the full AI-written report text.

**Crucial data distinction:** A 12-hour point-in-time reading is not the same as daily-average concurrent users (CCU). The website never silently inserts scheduled samples into the original daily-average charts or implies viral growth from a single point. Category findings are limited to this watchlist, not all Roblox games.

## How to add a new tracked game later

Open `watchlist.json` in GitHub (pencil icon) and add a new object using the other entries as a guide, supplying the public Roblox URL's number as `placeId`, the game name and a category. Leave `universeId` set to `null`: the workflow will resolve it. New games will appear in the **automatic live panel** on the next run; adding them to the original historical archive is still manual.

## Troubleshooting

- **Site shows 'Awaiting first refresh':** Open Actions and run the workflow; make sure the API-fetch step succeeds.
- **GitHub says the Pages environment does not exist:** Check that `Settings → Pages → Source` is set to **GitHub Actions**.
- **All API calls failed:** The Action turns red; see the logs. This is an upstream data-source problem, not proof that every game has zero players.
- **The site shows an old date:** The latest successful collection is stale. Try a manual workflow run.
- **You already published via Netlify Drop?** You can use this as a new GitHub Pages URL (free), or later link the GitHub repo to the same Netlify project. Manual Netlify Drop uploads by themselves will not auto-update.
- **Want exactly 9 am and 9 pm in Australia?** The schedule currently uses fixed UTC times (00:17 and 12:17), so Sydney wall-clock times change during daylight-saving switches. The important feature is twice per day, not exact local hours.

## Files and security

- `index.html`: complete public website with the new automatic panel.
- `.github/workflows/refresh-and-publish.yml`: the free twice-daily job and publish process.
- `scripts/update_stats.py`: collector, historical sample storage, and cautious rules-based analysis.
- `watchlist.json`: public games you want to track.
- `game_ids.json`: cached place-ID-to-universe-ID lookup, so repeat updates make fewer API calls.
- `auto-data.json`: latest measurements and historical observations.
- `START-HERE.md`: this guide (not published to the site).

No paid APIs, passwords, cookies, tokens, or Roblox account credentials are required. The repository must be public on GitHub Free for Pages. Your research dashboard is independent and not affiliated with Roblox.
