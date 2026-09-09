<!-- LOVABLE:BEGIN -->
> [!IMPORTANT]
> This project is connected to [Lovable](https://lovable.dev). Avoid rewriting
> published git history — force pushing, or rebasing/amending/squashing commits
> that are already pushed — as it rewrites history on Lovable's side and the
> user will likely lose their project history.
>
> Commits you push to the connected branch sync back to Lovable and show up in
> the editor, so keep the branch in a working state.
<!-- LOVABLE:END -->

## Production data safety

**Never push local database data to the live server.** Deploys must ship code/images only. Do not upload local `db.sqlite3`, SQL/pg dumps, `_prod_data.json`, or fixture dumps; do not run `seed_local_demo`, `loaddata`, `flush`, or restore local dumps on production. Live Postgres lives in Docker volumes on the VPS; only server-side backups under `/opt/joyclub/backups` may touch production data.
