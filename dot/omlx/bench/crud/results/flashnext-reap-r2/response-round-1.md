

The root cause: `better-sqlite3` tries to build native C++ bindings and fails on Node.js 26 (and would keep failing on future Node versions that change V8 internals). I'll drop that dependency entirely and use Node.js's **built-in** SQLite (`node:sqlite`, stable since 22.5+), which ships with Node 26 and needs no native compilation. Only the two server files change.

### server/package.json
```json
{
  "name": "books-api",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "start": "node --experimental-sqlite index.js"
  },
  "dependencies": {
    "express": "^4.21.2"
  }
}
```

### server/index.js
```js
import express from 'express';
import { DatabaseSync } from 'node:sqlite';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const db = new DatabaseSync(path.join(__dirname, 'data.db'));

db.exec(`
  CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    read INTEGER NOT NULL DEFAULT 0
  );
`);

const app = express();
app.use(express.json());

const toRow = (r) => ({ ...r, read: Boolean(r.read) });

// GET /api/books
app.get('/api/books', (req, res) => {
  const rows = db.prepare('SELECT * FROM books ORDER BY id').all();
  res.json(rows.map(toRow));
});

// GET /api/books/:id
app.get('/api/books/:id', (req, res) => {
  const row = db.prepare('SELECT * FROM books WHERE id = ?').get(Number(req.params.id));
  if (!row) return res.status(404).json({ error: 'Not found' });
  res.json(toRow(row));
});

// POST /api/books
app.post('/api/books', (req, res) => {
  const { title, author, year, read } = req.body;
  if (!title || !String(title).trim() || !author || !String(author).trim()) {
    return res.status(400).json({ error: 'title and author are required' });
  }
  const info = db
    .prepare('INSERT INTO books (title, author, year, read) VALUES (?, ?, ?, ?)')
    .run(String(title).trim(), String(author).trim(), year != null ? Number(year) : null, read ? 1 : 0);
  const row = db.prepare('SELECT * FROM books WHERE id = ?').get(Number(info.lastInsertRowid));
  res.status(201).json(toRow(row));
});

// PUT /api/books/:id
app.put('/api/books/:id', (req, res) => {
  const id = Number(req.params.id);
  const existing = db.prepare('SELECT * FROM books WHERE id = ?').get(id);
  if (!existing) return res.status(404).json({ error: 'Not found' });

  const { title, author, year, read } = req.body;
  if (!title || !String(title).trim() || !author || !String(author).trim()) {
    return res.status(400).json({ error: 'title and author are required' });
  }

  db.prepare('UPDATE books SET title = ?, author = ?, year = ?, read = ? WHERE id = ?')
    .run(String(title).trim(), String(author).trim(), year != null ? Number(year) : null, read ? 1 : 0, id);

  const row = db.prepare('SELECT * FROM books WHERE id = ?').get(id);
  res.json(toRow(row));
});

// DELETE /api/books/:id
app.delete('/api/books/:id', (req, res) => {
  const info = db.prepare('DELETE FROM books WHERE id = ?').run(Number(req.params.id));
  if (info.changes === 0) return res.status(404).json({ error: 'Not found' });
  res.json({ ok: true });
});

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
  console.log(`Books API listening on http://localhost:${PORT}`);
});
```

### README.md
```md
# Books CRUD

## Prerequisites

- Node.js 26+ (uses the built-in `node:sqlite` module; no native compilation needed)

## Run the API

```bash
cd server
npm install   # only installs express
npm start     # starts on PORT (default 3001)
```

## Run the UI

```bash
cd client
npm install
npm run dev   # Vite dev server on http://localhost:5173 (proxies /api → :3001)
```

## Build the UI (production bundle)

```bash
cd client
npm run build
```
```