# Frontend MVP (Next.js)

## Run

Backend should be running first (default **http://127.0.0.1:8007**). Copy env:

```bash
cd frontend
cp .env.example .env.local   # or edit .env.local
npm install
npm run dev
```

Open **http://localhost:3000** (Next listens on port **3000** per `package.json`).

## API URL

The app reads **`NEXT_PUBLIC_API_URL`** (see `.env.example` and `.env.local`). Example:

```bash
# .env.local
NEXT_PUBLIC_API_URL=http://127.0.0.1:8007
```

If unset, the code falls back to `http://127.0.0.1:8007`.

## Optional Supabase (browser client)

Only needed if you integrate `@supabase/supabase-js` in the frontend. The main GEB API uses your FastAPI backend + `DATABASE_URL`, not the anon key, for data.
