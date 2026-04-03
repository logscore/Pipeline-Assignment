# Pipeline-Assignment

Next.js app lives in **`web/`**. Postgres is **Supabase** (local via Docker, or hosted for production). Shop data starts in **`shop.db`** (SQLite) and is loaded into Postgres with the ETL script under **`scripts/`**.

## Prerequisites

- **Docker Desktop** (running) — required for local Supabase
- **Supabase CLI** — [install](https://supabase.com/docs/guides/cli/getting-started)

  Windows (Scoop):

  ```
  scoop bucket add supabase https://github.com/supabase/scoop-bucket.git
  scoop install supabase
  ```

  macOS:

  ```
  brew install supabase/tap/supabase
  ```

- **Bun** or **Node** — for installing and running the app (`bun` recommended; use `npm` / `npx` if you do not use Bun)
- **Python 3** + **pip** — for one-time SQLite → Postgres import

## Local development

From the repository root:

1. **Install JS dependencies** (must be inside `web/`):

   ```
   cd web
   bun i
   ```

2. **Start local Supabase** (Postgres, Studio, etc.):

   ```
   bun run dev:up
   ```

   Confirm with `supabase status`. The default DB URL is:

   `postgresql://postgres:postgres@127.0.0.1:54322/postgres`

3. **Configure the app** — in `web/.env` set:

   ```
   DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:54322/postgres
   ```

   (Add other vars from `.env.example` if you use them.)

4. **Apply database migrations** (creates auth + shop tables):

   ```
   cd web
   npx drizzle-kit migrate
   ```

   If you use Bun: `bun run migrate` (runs `drizzle-kit migrate`).

5. **Load `shop.db` into Postgres** (one-time per machine / DB):

   ```
   cd ..
   pip install -r scripts/requirements-etl.txt
   python scripts/import_sqlite_to_pg.py
   ```

   Set `DATABASE_URL` in the shell to the same value as `web/.env` if it is not already exported.

6. **Run the Next app**:

   ```
   cd web
   bun dev
   ```

   Open **http://localhost:3000/select-customer** (the default home page is still the stock Next starter). Supabase Studio: **http://127.0.0.1:54323**

## Production (short)

1. Create a **hosted Supabase** project and copy the **connection string** (for serverless, prefer the **transaction pooler** URI).
2. Set **`DATABASE_URL`** in your host (e.g. Vercel) to that string; set **Root Directory** to **`web`** if you deploy there.
3. Run **`npx drizzle-kit migrate`** (from `web/`) once with **`DATABASE_URL`** pointing at production.
4. Run **`python scripts/import_sqlite_to_pg.py`** once with the same production **`DATABASE_URL`** to load data (keep credentials secret).

See **`FIXES.md`** for known gaps (e.g. scoring on Vercel, optional seed file).
