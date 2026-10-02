Build a small full-stack CRUD web app. It manages ONE database table, `books`, with columns: id (integer primary key), title (text, required), author (text, required), year (integer, optional), read (boolean, default false).

Requirements:

- Backend: a Node.js REST API in `server/`, storing data in SQLite in the file `server/data.db`. Endpoints: GET /api/books, GET /api/books/:id, POST /api/books, PUT /api/books/:id, DELETE /api/books/:id. All return JSON. POST or PUT with a missing or empty title or author returns HTTP 400. An unknown id returns 404. The server listens on the port in the PORT environment variable, defaulting to 3001. The runtime is Node.js 26.
- Frontend: a React app built with Vite in `client/`. It lists every book in a table and lets the user create a book, edit a book, toggle read, and delete a book. The Vite dev server proxies /api to http://localhost:3001.
- `server/` and `client/` each have their own package.json. `npm install && npm start` in `server/` starts the API. `npm install && npm run dev` in `client/` serves the UI, and `npm run build` must succeed.
- A short README.md at the root with the run commands.

You cannot run anything; I will install, run and test exactly what you write. Output every file in full. Put each one in its own fenced code block, and put the file's path relative to the project root on the line directly before the block, like this:

### server/package.json
```json
{ ... }
```

Do not output lockfiles or node_modules.
