# Frontend

`src/app/` composes the workbench, routes, query client, and global styles.
`src/features/` contains descriptive page and feature component files.
`src/shared/` contains reusable UI, charts, API transport, domain contracts,
formatting, and replay state.

Run `npm ci`, then `npm run dev -- --host 127.0.0.1`. The development server proxies
`/api` to `http://127.0.0.1:8000`; override with `VITE_API_PROXY_TARGET` in the
project-root `.env`.
Use `npm run build`, `npm run lint`, and `npm run test:e2e` to verify changes.
Install the browser once with `npx playwright install chromium` if needed.
