

### README.md
```md
# Books CRUD

## Server (API)

```bash
cd server
npm install
npm start
```

The API listens on the port given by `PORT` (default `3001`).

## Client (UI)

```bash
cd client
npm install
npm run dev
```

The Vite dev-server proxies `/api` → `http://localhost:3001`.
`npm run build` produces a static bundle in `client/dist`.
```

### server/package.json
```json
{
  "name": "books-server",
  "version": "1.0.0",
  "private": true,
  "type": "module",
  "scripts": {
    "start": "node index.js"
  },
  "dependencies": {
    "better-sqlite3": "^11.4.0",
    "express": "^4.21.2"
  }
}
```

### server/index.js
```js
import express from 'express';
import Database from 'better-sqlite3';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const db = new Database(path.join(__dirname, 'data.db'));

db.exec(`
  CREATE TABLE IF NOT EXISTS books (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT    NOT NULL,
    author TEXT   NOT NULL,
    year  INTEGER,
    read  INTEGER NOT NULL DEFAULT 0
  )
`);

const app = express();
app.use(express.json());

// ---------- helpers ----------
function rowToBook(row) {
  return {
    id: row.id,
    title: row.title,
    author: row.author,
    year: row.year,          // null when absent
    read: Boolean(row.read),
  };
}

// ---------- routes ----------

// GET all books
app.get('/api/books', (_req, res) => {
  const rows = db.prepare('SELECT * FROM books').all();
  res.json(rows.map(rowToBook));
});

// GET one book
app.get('/api/books/:id', (req, res) => {
  const row = db.prepare('SELECT * FROM books WHERE id = ?').get(Number(req.params.id));
  if (!row) return res.status(404).json({ error: 'Not found' });
  res.json(rowToBook(row));
});

// POST create
app.post('/api/books', (req, res) => {
  const { title, author, year, read } = req.body;
  if (!title || title.trim() === '' || !author || author.trim() === '') {
    return res.status(400).json({ error: 'title and author are required' });
  }

  const info = db
    .prepare('INSERT INTO books (title, author, year, read) VALUES (?, ?, ?, ?)')
    .run(title.trim(), author.trim(), year ?? null, read ? 1 : 0);

  const row = db.prepare('SELECT * FROM books WHERE id = ?').get(info.lastInsertRowid);
  res.status(201).json(rowToBook(row));
});

// PUT update
app.put('/api/books/:id', (req, res) => {
  const id = Number(req.params.id);
  const existing = db.prepare('SELECT * FROM books WHERE id = ?').get(id);
  if (!existing) return res.status(404).json({ error: 'Not found' });

  const { title, author, year, read } = req.body;
  if (!title || title.trim() === '' || !author || author.trim() === '') {
    return res.status(400).json({ error: 'title and author are required' });
  }

  db.prepare('UPDATE books SET title = ?, author = ?, year = ?, read = ? WHERE id = ?')
    .run(title.trim(), author.trim(), year ?? null, read ? 1 : 0, id);

  const row = db.prepare('SELECT * FROM books WHERE id = ?').get(id);
  res.json(rowToBook(row));
});

// DELETE
app.delete('/api/books/:id', (req, res) => {
  const id = Number(req.params.id);
  const info = db.prepare('DELETE FROM books WHERE id = ?').run(id);
  if (info.changes === 0) return res.status(404).json({ error: 'Not found' });
  res.status(204).end();
});

// ---------- start ----------
const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
  console.log(`API server listening on http://localhost:${PORT}`);
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
    "@vitejs/plugin-react": "^4.3.1",
    "vite": "^5.4.7"
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
    proxy: {
      '/api': 'http://localhost:3001',
    },
  },
});
```

### client/index.html
```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
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

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

### client/src/App.jsx
```jsx
import { useState, useEffect, useCallback } from 'react';

const API = '/api/books';

function emptyForm() {
  return { title: '', author: '', year: '', read: false };
}

export default function App() {
  const [books, setBooks] = useState([]);
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState(null);   // null → add mode
  const [error, setError] = useState('');

  const fetchBooks = useCallback(async () => {
    const res = await fetch(API);
    const data = await res.json();
    setBooks(data);
  }, []);

  useEffect(() => { fetchBooks(); }, [fetchBooks]);

  // ---------- helpers ----------
  const update = (field, value) => setForm(f => ({ ...f, [field]: value }));

  const resetForm = () => {
    setForm(emptyForm());
    setEditingId(null);
    setError('');
  };

  // ---------- CRUD ----------
  const submit = async (e) => {
    e.preventDefault();
    setError('');

    const body = {
      title: form.title,
      author: form.author,
      year: form.year !== '' ? Number(form.year) : null,
      read: form.read,
    };

    const url = editingId !== null ? `${API}/${editingId}` : API;
    const method = editingId !== null ? 'PUT' : 'POST';

    const res = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    if (!res.ok) {
      const msg = await res.json().catch(() => ({ error: 'Request failed' }));
      setError(msg.error || `HTTP ${res.status}`);
      return;
    }

    resetForm();
    fetchBooks();
  };

  const edit = (book) => {
    setForm({
      title: book.title,
      author: book.author,
      year: book.year != null ? String(book.year) : '',
      read: book.read,
    });
    setEditingId(book.id);
    setError('');
  };

  const deleteBook = async (id) => {
    if (!confirm('Delete this book?')) return;
    await fetch(`${API}/${id}`, { method: 'DELETE' });
    if (editingId === id) resetForm();
    fetchBooks();
  };

  const toggleRead = async (book) => {
    const body = {
      title: book.title,
      author: book.author,
      year: book.year,
      read: !book.read,
    };
    await fetch(`${API}/${book.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    fetchBooks();
  };

  // ---------- render ----------
  return (
    <div style={{ maxWidth: 900, margin: '2rem auto', fontFamily: 'system-ui, sans-serif' }}>
      <h1>📚 Books</h1>

      {/* ---- form ---- */}
      <form
        onSubmit={submit}
        style={{
          background: '#f4f4f5',
          padding: '1rem 1.5rem',
          borderRadius: 8,
          marginBottom: 24,
        }}
      >
        <h2 style={{ marginTop: 0 }}>
          {editingId !== null ? `Edit #${editingId}` : 'Add book'}
        </h2>

        {error && <p style={{ color: 'red' }}>{error}</p>}

        <label>
          Title *
          <input
            value={form.title}
            onChange={e => update('title', e.target.value)}
            required
            style={{ display: 'block', width: '100%', boxSizing: 'border-box', margin: '4px 0 12px' }}
          />
        </label>

        <label>
          Author *
          <input
            value={form.author}
            onChange={e => update('author', e.target.value)}
            required
            style={{ display: 'block', width: '100%', boxSizing: 'border-box', margin: '4px 0 12px' }}
          />
        </label>

        <label>
          Year
          <input
            type="number"
            value={form.year}
            onChange={e => update('year', e.target.value)}
            placeholder="(optional)"
            style={{ display: 'block', width: '100%', boxSizing: 'border-box', margin: '4px 0 12px' }}
          />
        </label>

        <label style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
          Read
          <input
            type="checkbox"
            checked={form.read}
            onChange={e => update('read', e.target.checked)}
          />
        </label>

        <div style={{ display: 'flex', gap: 8 }}>
          <button type="submit">{editingId !== null ? 'Update' : 'Create'}</button>
          {editingId !== null && (
            <button type="button" onClick={resetForm}>Cancel</button>
          )}
        </div>
      </form>

      {/* ---- table ---- */}
      {books.length === 0 && <p>No books yet.</p>}

      {books.length > 0 && (
        <table border="1" cellPadding="6" style={{ borderCollapse: 'collapse', width: '100%' }}>
          <thead>
            <tr>
              <th>Id</th>
              <th>Title</th>
              <th>Author</th>
              <th>Year</th>
              <th>Read</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {books.map(b => (
              <tr key={b.id}>
                <td>{b.id}</td>
                <td>{b.title}</td>
                <td>{b.author}</td>
                <td>{b.year ?? ''}</td>
                <td>
                  <input
                    type="checkbox"
                    checked={b.read}
                    onChange={() => toggleRead(b)}
                  />
                </td>
                <td style={{ display: 'flex', gap: 6 }}>
                  <button onClick={() => edit(b)}>Edit</button>
                  <button onClick={() => deleteBook(b.id)} style={{ color: 'red' }}>
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
```