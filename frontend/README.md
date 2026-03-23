# Frontend

This is the first-generation mocked advisory frontend for the Barita skills challenge repo.

## Run locally

1. Open a terminal in `frontend/`
2. Install dependencies:

```powershell
npm.cmd install
```

3. Start the Vite dev server:

```powershell
npm.cmd run dev
```

4. Open the local URL printed by Vite, fill out the investor profile form, submit it, and review the mocked recommendation results.

## Current integration boundary

- UI components call only `src/services/api.js`
- `api.js` currently delegates to `mockApi.js`
- a future backend route should replace the mock implementation without requiring page or component rewrites
