

### README.md
```markdown
# Books CRUD

A small full-stack CRUD app that manages a single `books` table in SQLite.

- **Backend:** Node.js REST API in `server/` (zero dependencies, uses `node:sqlite`), data stored in `server/data.db`.
- **Frontend:** React + Vite app in `client/`. The Vite dev server proxies `/api` to `http://localhost:3001`.

## Prerequisites

- Node.js 26

## Run the API

```bash
cd server
npm install
npm start
```

The API listens on the `PORT` environment variable, defaulting to **3001**.
`data.db` is created automatically on first run.

## Run the client

```bash
cd client
npm install
npm run dev
```

Then open http://localhost:5173 in your browser.

## Build the client

```bash
cd client
npm run build
```

## API endpoints

| Method | Path             | Description                    |
| ------ | ---------------- | ------------------------------ |
| GET    | /api/books       | List all books                 |
| GET    | /api/books/:id   | Get one book (404 if missing)  |
| POST   | /api/books       | Create a book (400 if title/author missing) |
| PUT    | /api/books/:id   | Update a book (400/404)        |
| DELETE | /api/books/:id   | Delete a book (404 if missing) |

All responses are JSON.
```

### .gitignore
```
node_modules/
client/dist/
server/data.db
```

### server/package.json
```json
{
  "name": "books-server",
  "version": "1.0.0",
  "private": true,
  "type": "module",
  "main": "server.js",
  "scripts": {
    "start": "node server.js"
  }
}
```

### server/server.js
```js
import http from 'node:http';
import { DatabaseSync } from 'node:sqlite';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DB_PATH = path.join(__dirname, 'data.db');

const db = new DatabaseSync(DB_PATH);
db.exec(`
  CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    read INTEGER NOT NULL DEFAULT 0
  );
`);

function rowToBook(row) {
  return {
    id: row.id,
    title: row.title,
    author: row.author,
    year: row.year === null ? null : row.year,
    read: row.read === 1,
  };
}

function sendJSON(res, status, data) {
  res.writeHead(status, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify(data));
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let data = '';
    req.on('data', (chunk) => { data += chunk; });
    req.on('end', () => resolve(data));
    req.on('error', reject);
  });
}

function parseJSONBody(raw) {
  const text = raw && raw.trim() !== '' ? raw : '{}';
  const body = JSON.parse(text);
  if (typeof body !== 'object' || body === null || Array.isArray(body)) {
    throw new Error('Body must be a JSON object');
  }
  return body;
}

function validateBody(body) {
  const title = typeof body.title === 'string' ? body.title.trim() : '';
  const author = typeof body.author === 'string' ? body.author.trim() : '';
  if (!title || !author) return null;

  let year = null;
  if (body.year !== undefined && body.year !== null && body.year !== '') {
    const n = Number(body.year);
    if (Number.isInteger(n)) year = n;
  }

  return { title, author, year, read: Boolean(body.read) };
}

async function handleApi(req, res, url) {
  const segments = url.pathname.split('/').filter(Boolean);
  if (segments[0] !== 'api' || segments[1] !== 'books' || segments.length > 3) {
    return sendJSON(res, 404, { error: 'Not found' });
  }

  const idPart = segments[2];

  // Collection routes: /api/books
  if (idPart === undefined) {
    if (req.method === 'GET') {
      const rows = db.prepare('SELECT * FROM books ORDER BY id').all();
      return sendJSON(res, 200, rows.map(rowToBook));
    }
    if (req.method === 'POST') {
      let body;
      try {
        body = parseJSONBody(await readBody(req));
      } catch {
        return sendJSON(res, 400, { error: 'Invalid JSON body' });
      }
      const book = validateBody(body);
      if (!book) {
        return sendJSON(res, 400, { error: 'title and author are required' });
      }
      const info = db
        .prepare('INSERT INTO books (title, author, year, read) VALUES (?, ?, ?, ?)')
        .run(book.title, book.author, book.year, book.read ? 1 : 0);
      const row = db.prepare('SELECT * FROM books WHERE id = ?').get(Number(info.lastInsertRowid));
      return sendJSON(res, 201, rowToBook(row));
    }
    return sendJSON(res, 405, { error: 'Method not allowed' });
  }

  // Item routes: /api/books/:id
  const id = Number(idPart);
  if (!Number.isInteger(id) || id <= 0) {
    return sendJSON(res, 404, { error: 'Book not found' });
  }
  const existing = db.prepare('SELECT * FROM books WHERE id = ?').get(id);

  if (req.method === 'GET') {
    if (!existing) return sendJSON(res, 404, { error: 'Book not found' });
    return sendJSON(res, 200, rowToBook(existing));
  }

  if (req.method === 'PUT') {
    let body;
    try {
      body = parseJSONBody(await readBody(req));
    } catch {
      return sendJSON(res, 400, { error: 'Invalid JSON body' });
    }
    const book = validateBody(body);
    if (!book) {
      return sendJSON(res, 400, { error: 'title and author are required' });
    }
    if (!existing) return sendJSON(res, 404, { error: 'Book not found' });
    db.prepare('UPDATE books SET title = ?, author = ?, year = ?, read = ? WHERE id = ?')
      .run(book.title, book.author, book.year, book.read ? 1 : 0, id);
    const row = db.prepare('SELECT * FROM books WHERE id = ?').get(id);
    return sendJSON(res, 200, rowToBook(row));
  }

  if (req.method === 'DELETE') {
    if (!existing) return sendJSON(res, 404, { error: 'Book not found' });
    db.prepare('DELETE FROM books WHERE id = ?').run(id);
    return sendJSON(res, 200, { ok: true });
  }

  return sendJSON(res, 405, { error: 'Method not allowed' });
}

const server = http.createServer((req, res) => {
  const url = new URL(req.url, `http://${req.headers.host || 'localhost'}`);
  if (url.pathname === '/api' || url.pathname.startsWith('/api/')) {
    handleApi(req, res, url).catch((err) => {
      console.error(err);
      sendJSON(res, 500, { error: 'Internal server error' });
    });
  } else {
    sendJSON(res, 404, { error: 'Not found' });
  }
});

const PORT = Number(process.env.PORT) || 3001;
server.listen(PORT, () => {
  console.log(`Books API listening on http://localhost:${PORT}`);
});
```

### client/package.json
```json
{
  "name": "books-client",
  "version": "1.0.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.3.4",
    "vite": "^5.4.11"
  }
}
```

### client/vite.config.js
```js
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:3001',
    },
  },
});
```

### client/index.html
```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Books</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
```

### client/src/main.jsx
```jsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.jsx';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

### client/src/index.css
```css
* {
  box-sizing: border-box;
}

body {
  margin: 0;
  font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  background: #f4f5f7;
  color: #222;
}

.container {
  max-width: 860px;
  margin: 0 auto;
  padding: 24px 16px 48px;
}

h1 {
  margin-top: 0;
}

form.book-form {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: flex-end;
  background: #fff;
  border: 1px solid #dcdfe3;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 24px;
}

form.book-form label {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 13px;
  font-weight: 600;
}

form.book-form input[type="text"],
form.book-form input[type="number"] {
  padding: 6px 8px;
  border: 1px solid #c3c8cf;
  border-radius: 6px;
  font-size: 14px;
}

.read-check {
  flex-direction: row;
  align-items: center;
  gap: 6px;
  padding-bottom: 8px;
}

.read-check input {
  width: 16px;
  height: 16px;
}

.btn {
  border: none;
  border-radius: 6px;
  padding: 8px 14px;
  font-size: 14px;
  cursor: pointer;
  background: #2563eb;
  color: #fff;
}

.btn:hover {
  background: #1d4ed8;
}

.btn.secondary {
  background: #e5e7eb;
  color: #222;
}

.btn.secondary:hover {
  background: #d1d5db;
}

.btn.danger {
  background: #dc2626;
}

.btn.danger:hover {
  background: #b91c1c;
}

table {
  width: 100%;
  border-collapse: collapse;
  background: #fff;
  border: 1px solid #dcdfe3;
  border-radius: 8px;
  overflow: hidden;
}

th,
td {
  text-align: left;
  padding: 10px 12px;
  border-bottom: 1px solid #e5e7eb;
  font-size: 14px;
}

th {
  background: #f9fafb;
  font-size: 13px;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  color: #555;
}

tr:last-child td {
  border-bottom: none;
}

.read-badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
}

.read-badge.read {
  background: #d1fae5;
  color: #065f46;
}

.read-badge.unread {
  background: #e5e7eb;
  color: #374151;
}

.error {
  background: #fee2e2;
  color: #991b1b;
  border: 1px solid #fca5a5;
  border-radius: 6px;
  padding: 8px 12px;
  margin-bottom: 16px;
  font-size: 14px;
}

.empty {
  text-align: center;
  color: #6b7280;
  padding: 24px !important;
}
```

### client/src/App.jsx
```jsx
import { useEffect, useState } from 'react';

const API = '/api/books';

const EMPTY_FORM = { title: '', author: '', year: '', read: false };

export default function App() {
  const [books, setBooks] = useState([]);
  const [form, setForm] = useState(EMPTY_FORM);
  const [editingId, setEditingId] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  async function refresh() {
    try {
      const res = await fetch(API);
      if (!res.ok) throw new Error(`Failed to load books (${res.status})`);
      setBooks(await res.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  function resetForm() {
    setForm(EMPTY_FORM);
    setEditingId(null);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    const payload = {
      title: form.title.trim(),
      author: form.author.trim(),
      year: form.year === '' ? null : Number(form.year),
      read: form.read,
    };
    const res = editingId
      ? await fetch(`${API}/${editingId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        })
      : await fetch(API, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      setError(data.error || `Request failed (${res.status})`);
      return;
    }
    resetForm();
    await refresh();
  }

  function startEdit(book) {
    setEditingId(book.id);
    setForm({
      title: book.title,
      author: book.author,
      year: book.year === null ? '' : String(book.year),
      read: book.read,
    });
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  async function toggleRead(book) {
    const res = await fetch(`${API}/${book.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title: book.title,
        author: book.author,
        year: book.year,
        read: !book.read,
      }),
    });
    if (!res.ok) {
      setError(`Failed to update book (${res.status})`);
      return;
    }
    await refresh();
  }

  async function removeBook(book) {
    if (!window.confirm(`Delete "${book.title}"?`)) return;
    const res = await fetch(`${API}/${book.id}`, { method: 'DELETE' });
    if (!res.ok) {
      setError(`Failed to delete book (${res.status})`);
      return;
    }
    if (editingId === book.id) resetForm();
    await refresh();
  }

  return (
    <div className="container">
      <h1>Books</h1>

      {error && <div className="error">{error}</div>}

      <form className="book-form" onSubmit={handleSubmit}>
        <label>
          Title
          <input
            type="text"
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
            required
          />
        </label>
        <label>
          Author
          <input
            type="text"
            value={form.author}
            onChange={(e) => setForm({ ...form, author: e.target.value })}
            required
          />
        </label>
        <label>
          Year
          <input
            type="number"
            value={form.year}
            onChange={(e) => setForm({ ...form, year: e.target.value })}
            placeholder="e.g. 1999"
          />
        </label>
        <label className="read-check">
          <input
            type="checkbox"
            checked={form.read}
            onChange={(e) => setForm({ ...form, read: e.target.checked })}
          />
          Read
        </label>
        <button type="submit" className="btn">
          {editingId ? 'Update book' : 'Add book'}
        </button>
        {editingId && (
          <button type="button" className="btn secondary" onClick={resetForm}>
            Cancel
          </button>
        )}
      </form>

      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Title</th>
            <th>Author</th>
            <th>Year</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {loading ? (
            <tr>
              <td colSpan={6} className="empty">
                Loading…
              </td>
            </tr>
          ) : books.length === 0 ? (
            <tr>
              <td colSpan={6} className="empty">
                No books yet. Add one above.
              </td>
            </tr>
          ) : (
            books.map((book) => (
              <tr key={book.id}>
                <td>{book.id}</td>
                <td>{book.title}</td>
                <td>{book.author}</td>
                <td>{book.year === null ? '—' : book.year}</td>
                <td>
                  <span className={`read-badge ${book.read ? 'read' : 'unread'}`}>
                    {book.read ? 'Read' : 'Unread'}
                  </span>
                </td>
                <td>
                  <button className="btn secondary" onClick={() => startEdit(book)}>
                    Edit
                  </button>{' '}
                  <button className="btn secondary" onClick={() => toggleRead(book)}>
                    {book.read ? 'Mark unread' : 'Mark read'}
                  </button>{' '}
                  <button className="btn danger" onClick={() => removeBook(book)}>
                    Delete
                  </button>
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
```

Notes on choices:

- **Zero server dependencies**: the API uses only built-in `node:http` and `node:sqlite` (stable in Node 26), so `npm install` in `server/` is a no-op and `npm start` can't fail on dependency builds. `server/data.db` is created automatically on first run (it's gitignored, not shipped).
- **Validation order on PUT**: malformed/missing title or author → 400; valid body with unknown id → 404, per the requirements.
- The `read` column is stored as `0`/`1` in SQLite and serialized as a real boolean in JSON.