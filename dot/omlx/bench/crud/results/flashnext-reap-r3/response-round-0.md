

### README.md
```md
# Books CRUD

## Run the API

```bash
cd server
npm install
npm start
```

## Run the frontend (dev server, proxies `/api` → :3001)

```bash
cd client
npm install
npm run dev
```

## Build the frontend

```bash
cd client
npm run build
```
```

### server/package.json
```json
{
  "name": "server",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "start": "node index.js"
  },
  "dependencies": {
    "express": "^4.21.0",
    "better-sqlite3": "^11.2.0"
  }
}
```

### server/index.js
```js
const path = require('path');
const Database = require('better-sqlite3');
const express = require('express');

const db = new Database(path.join(__dirname, 'data.db'));

db.pragma('journal_mode = WAL');

db.exec(`
  CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    "read" INTEGER NOT NULL DEFAULT 0
  );
`);

const app = express();
app.use(express.json());

function validateBook(body) {
  if (!body) return 'Invalid JSON body';
  const { title, author } = body;
  if (typeof title !== 'string' || title.trim() === '') return 'title is required and must be non-empty';
  if (typeof author !== 'string' || author.trim() === '') return 'author is required and must be non-empty';
  return null;
}

// GET /api/books – list all
app.get('/api/books', (_req, res) => {
  const rows = db.prepare('SELECT * FROM books ORDER BY id').all();
  res.json(rows.map(rowToJson));
});

// GET /api/books/:id – get one
app.get('/api/books/:id', (req, res) => {
  const id = Number(req.params.id);
  if (!Number.isInteger(id) || id < 1) {
    return res.status(404).json({ error: 'Not found' });
  }
  const row = db.prepare('SELECT * FROM books WHERE id = ?').get(id);
  if (!row) return res.status(404).json({ error: 'Not found' });
  res.json(rowToJson(row));
});

// POST /api/books – create
app.post('/api/books', (req, res) => {
  const err = validateBook(req.body);
  if (err) return res.status(400).json({ error: err });

  const { title, author, year, read } = req.body;

  let yearVal = null;
  if (year !== undefined && year !== null && year !== '') {
    yearVal = Number(year);
    if (!Number.isInteger(yearVal)) return res.status(400).json({ error: 'year must be an integer' });
  }

  const readVal = (read === true || read === 1 || read === '1') ? 1 : 0;

  const info = db.prepare(
    `INSERT INTO books (title, author, year, "read") VALUES (?, ?, ?, ?)`
  ).run(title.trim(), author.trim(), yearVal, readVal);

  const row = db.prepare('SELECT * FROM books WHERE id = ?').get(info.lastInsertRowid);
  res.status(201).json(rowToJson(row));
});

// PUT /api/books/:id – replace
app.put('/api/books/:id', (req, res) => {
  const id = Number(req.params.id);
  if (!Number.isInteger(id) || id < 1) {
    return res.status(404).json({ error: 'Not found' });
  }

  const existing = db.prepare('SELECT * FROM books WHERE id = ?').get(id);
  if (!existing) return res.status(404).json({ error: 'Not found' });

  const err = validateBook(req.body);
  if (err) return res.status(400).json({ error: err });

  const { title, author, year, read } = req.body;

  let yearVal = null;
  if (year !== undefined && year !== null && year !== '') {
    yearVal = Number(year);
    if (!Number.isInteger(yearVal)) return res.status(400).json({ error: 'year must be an integer' });
  }

  const readVal = (read === true || read === 1 || read === '1') ? 1 : 0;

  db.prepare('UPDATE books SET title = ?, author = ?, year = ?, "read" = ? WHERE id = ?')
    .run(title.trim(), author.trim(), yearVal, readVal, id);

  const row = db.prepare('SELECT * FROM books WHERE id = ?').get(id);
  res.json(rowToJson(row));
});

// DELETE /api/books/:id
app.delete('/api/books/:id', (req, res) => {
  const id = Number(req.params.id);
  if (!Number.isInteger(id) || id < 1) {
    return res.status(404).json({ error: 'Not found' });
  }
  const info = db.prepare('DELETE FROM books WHERE id = ?').run(id);
  if (info.changes === 0) return res.status(404).json({ error: 'Not found' });
  res.json({ deleted: true });
});

function rowToJson(row) {
  return {
    id: row.id,
    title: row.title,
    author: row.author,
    year: row.year,
    read: row.read === 1,
  };
}

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
  console.log(`API server listening on http://localhost:${PORT}`);
});
```

### client/package.json
```json
{
  "name": "client",
  "version": "1.0.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.0",
    "react-dom": "^18.3.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.3.0",
    "vite": "^5.4.0"
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
      '/api': {
        target: 'http://localhost:3001',
        changeOrigin: true,
      },
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
import App from './App';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

### client/src/App.jsx
```jsx
import { useState, useEffect, useCallback } from 'react';

const emptyForm = { title: '', author: '', year: '', read: false };

export default function App() {
  const [books, setBooks] = useState([]);
  const [editing, setEditing] = useState(null); // null | 'new' | number (book id)
  const [form, setForm] = useState(emptyForm);
  const [error, setError] = useState('');

  const fetchBooks = useCallback(async () => {
    const res = await fetch('/api/books');
    const data = await res.json();
    setBooks(data);
  }, []);

  useEffect(() => {
    fetchBooks();
  }, [fetchBooks]);

  function openNew() {
    setForm(emptyForm);
    setEditing('new');
    setError('');
  }

  function openEdit(book) {
    setForm({
      title: book.title,
      author: book.author,
      year: book.year != null ? String(book.year) : '',
      read: book.read,
    });
    setEditing(book.id);
    setError('');
  }

  function cancel() {
    setEditing(null);
    setForm(emptyForm);
    setError('');
  }

  function setField(field, value) {
    setForm(prev => ({ ...prev, [field]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    const body = {
      title: form.title,
      author: form.author,
      year: form.year !== '' ? Number(form.year) : null,
      read: form.read,
    };

    let url, method;
    if (editing === 'new') {
      url = '/api/books';
      method = 'POST';
    } else {
      url = `/api/books/${editing}`;
      method = 'PUT';
    }

    try {
      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const data = await res.json();
        setError(data.error || `Error ${res.status}`);
        return;
      }
      await fetchBooks();
      cancel();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleDelete(id) {
    if (!window.confirm('Delete this book?')) return;
    await fetch(`/api/books/${id}`, { method: 'DELETE' });
    await fetchBooks();
    if (editing === id) cancel();
  }

  async function handleToggleRead(book) {
    const body = {
      title: book.title,
      author: book.author,
      year: book.year,
      read: !book.read,
    };
    const res = await fetch(`/api/books/${book.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const data = await res.json();
      alert(data.error || 'Failed');
    } else {
      await fetchBooks();
    }
  }

  return (
    <div style={{ fontFamily: 'sans-serif', padding: '2rem', maxWidth: 800, margin: '0 auto' }}>
      <h1>Books</h1>
      <button onClick={openNew} style={{ marginBottom: '1rem', padding: '0.4rem 0.8rem' }}>
        + Add Book
      </button>

      {(editing !== null) && (
        <form onSubmit={handleSubmit} style={{ marginBottom: '1.5rem', padding: '1rem', background: '#f4f4f4', borderRadius: 8 }}>
          <h2>{editing === 'new' ? 'New Book' : 'Edit Book'}</h2>
          {error && <p style={{ color: 'red' }}>{error}</p>}

          <label>
            Title<br />
            <input value={form.title} onChange={e => setField('title', e.target.value)} required style={{ width: '100%', marginBottom: 8 }} />
          </label>
          <label>
            Author<br />
            <input value={form.author} onChange={e => setField('author', e.target.value)} required style={{ width: '100%', marginBottom: 8 }} />
          </label>
          <label>
            Year<br />
            <input type="number" value={form.year} onChange={e => setField('year', e.target.value)} style={{ width: '100%', marginBottom: 8 }} />
          </label>
          <label style={{ display: 'block', marginBottom: 8 }}>
            <input type="checkbox" checked={form.read} onChange={e => setField('read', e.target.checked)} /> Read
          </label>

          <div style={{ display: 'flex', gap: 8 }}>
            <button type="submit">Save</button>
            <button type="button" onClick={cancel}>Cancel</button>
          </div>
        </form>
      )}

      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            <th style={{ textAlign: 'left' }}>Title</th>
            <th style={{ textAlign: 'left' }}>Author</th>
            <th style={{ textAlign: 'left' }}>Year</th>
            <th style={{ textAlign: 'left' }}>Read</th>
            <th></th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {books.map(b => (
            <tr key={b.id} style={{ borderTop: '1px solid #ddd' }}>
              <td>{b.title}</td>
              <td>{b.author}</td>
              <td>{b.year ?? ''}</td>
              <td>{b.read ? '✓' : ''}</td>
              <td>
                <button onClick={() => handleToggleRead(b)} title="Toggle read">
                  {b.read ? 'Unread' : 'Read'}
                </button>
              </td>
              <td>
                <button onClick={() => openEdit(b)} style={{ marginRight: 4 }}>Edit</button>
                <button onClick={() => handleDelete(b.id)}>Delete</button>
              </td>
            </tr>
          ))}
          {books.length === 0 && (
            <tr><td colSpan={6} style={{ padding: 12, color: '#888' }}>No books yet.</td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
```