

### README.md
```markdown
# Books CRUD App

A full-stack CRUD application for managing a single `books` table.

## Prerequisites

- Node.js 26
- npm

## Running the Server

```bash
cd server
npm install
npm start
```

The API listens on `http://localhost:3001` (override with the `PORT` env var).

## Running the Client (dev)

In a **separate** terminal:

```bash
cd client
npm install
npm run dev
```

The UI is served at `http://localhost:5173`. The Vite dev server proxies all `/api/*` requests to `http://localhost:3001`.

## Building the Client (production)

```bash
cd client
npm run build
```

The production bundle is written to `client/dist/`.
```

### server/package.json
```json
{
  "name": "books-server",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "start": "node index.js"
  },
  "dependencies": {
    "better-sqlite3": "^11.10.0",
    "express": "^4.21.0"
  }
}
```

### server/index.js
```javascript
const express = require('express');
const Database = require('better-sqlite3');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3001;

// ── Database setup ──────────────────────────────────────────────
const db = new Database(path.join(__dirname, 'data.db'));
db.pragma('journal_mode = WAL');
db.exec(`
  CREATE TABLE IF NOT EXISTS books (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT    NOT NULL,
    author TEXT   NOT NULL,
    year  INTEGER,
    read  BOOLEAN NOT NULL DEFAULT 0
  )
`);

// ── Helpers ─────────────────────────────────────────────────────
function mapBook(row) {
  if (!row) return row;
  return { ...row, read: Boolean(row.read) };
}

app.use(express.json());

// ── GET /api/books ──────────────────────────────────────────────
app.get('/api/books', (_req, res) => {
  const rows = db.prepare('SELECT * FROM books ORDER BY id').all();
  res.json(rows.map(mapBook));
});

// ── GET /api/books/:id ──────────────────────────────────────────
app.get('/api/books/:id', (req, res) => {
  const row = db.prepare('SELECT * FROM books WHERE id = ?').get(req.params.id);
  if (!row) return res.status(404).json({ error: 'Book not found' });
  res.json(mapBook(row));
});

// ── POST /api/books ─────────────────────────────────────────────
app.post('/api/books', (req, res) => {
  const { title, author, year, read } = req.body ?? {};

  if (!title || typeof title !== 'string' || title.trim() === '') {
    return res.status(400).json({ error: 'title is required' });
  }
  if (!author || typeof author !== 'string' || author.trim() === '') {
    return res.status(400).json({ error: 'author is required' });
  }

  const stmt = db.prepare(
    'INSERT INTO books (title, author, year, read) VALUES (?, ?, ?, ?)'
  );
  const info = stmt.run(
    title.trim(),
    author.trim(),
    year != null ? Number(year) : null,
    read ? 1 : 0
  );
  const row = db.prepare('SELECT * FROM books WHERE id = ?').get(info.lastInsertRowid);
  res.status(201).json(mapBook(row));
});

// ── PUT /api/books/:id ──────────────────────────────────────────
app.put('/api/books/:id', (req, res) => {
  const existing = db.prepare('SELECT * FROM books WHERE id = ?').get(req.params.id);
  if (!existing) return res.status(404).json({ error: 'Book not found' });

  const { title, author, year, read } = req.body ?? {};

  if (!title || typeof title !== 'string' || title.trim() === '') {
    return res.status(400).json({ error: 'title is required' });
  }
  if (!author || typeof author !== 'string' || author.trim() === '') {
    return res.status(400).json({ error: 'author is required' });
  }

  db.prepare('UPDATE books SET title = ?, author = ?, year = ?, read = ? WHERE id = ?').run(
    title.trim(),
    author.trim(),
    year != null ? Number(year) : null,
    read ? 1 : 0,
    req.params.id
  );
  const row = db.prepare('SELECT * FROM books WHERE id = ?').get(req.params.id);
  res.json(mapBook(row));
});

// ── DELETE /api/books/:id ───────────────────────────────────────
app.delete('/api/books/:id', (req, res) => {
  const existing = db.prepare('SELECT * FROM books WHERE id = ?').get(req.params.id);
  if (!existing) return res.status(404).json({ error: 'Book not found' });
  db.prepare('DELETE FROM books WHERE id = ?').run(req.params.id);
  res.json({ message: 'Book deleted' });
});

// ── Start ───────────────────────────────────────────────────────
app.listen(PORT, () => {
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
    "react": "^19.1.0",
    "react-dom": "^19.1.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.5.0",
    "vite": "^6.3.0"
  }
}
```

### client/vite.config.js
```javascript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:3001'
    }
  }
});
```

### client/index.html
```html
<!DOCTYPE html>
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

const initialForm = { title: '', author: '', year: '', read: false };

export default function App() {
  const [books, setBooks] = useState([]);
  const [form, setForm] = useState(initialForm);
  const [editingId, setEditingId] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  const fetchBooks = useCallback(async () => {
    try {
      const res = await fetch('/api/books');
      if (!res.ok) throw new Error('Failed to fetch books');
      const data = await res.json();
      setBooks(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchBooks();
  }, [fetchBooks]);

  // ── Form handlers ─────────────────────────────────────────────
  const handleChange = (field) => (e) => {
    const value = field === 'read' ? e.target.checked : e.target.value;
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    const payload = {
      title: form.title,
      author: form.author,
      year: form.year !== '' ? parseInt(form.year, 10) : null,
      read: form.read
    };

    try {
      const opts = {
        method: editingId ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      };
      const url = editingId ? `/api/books/${editingId}` : '/api/books';
      const res = await fetch(url, opts);

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        setError(body.error || 'Request failed');
        return;
      }

      setForm(initialForm);
      setEditingId(null);
      await fetchBooks();
    } catch {
      setError('Network error');
    }
  };

  // ── Row actions ───────────────────────────────────────────────
  const startEdit = (book) => {
    setEditingId(book.id);
    setForm({
      title: book.title,
      author: book.author,
      year: book.year != null ? String(book.year) : '',
      read: book.read
    });
  };

  const cancelEdit = () => {
    setEditingId(null);
    setForm(initialForm);
    setError('');
  };

  const toggleRead = async (book) => {
    try {
      const res = await fetch(`/api/books/${book.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: book.title,
          author: book.author,
          year: book.year,
          read: !book.read
        })
      });
      if (res.ok) await fetchBooks();
    } catch {
      setError('Network error');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this book?')) return;
    try {
      const res = await fetch(`/api/books/${id}`, { method: 'DELETE' });
      if (res.ok) await fetchBooks();
    } catch {
      setError('Network error');
    }
  };

  // ── Render ────────────────────────────────────────────────────
  return (
    <div style={{ maxWidth: 820, margin: '2rem auto', padding: '0 1rem', fontFamily: 'system-ui, -apple-system, sans-serif' }}>
      <h1>📚 Books</h1>

      {error && (
        <p style={{ color: '#c0392b', background: '#fdecea', padding: '0.5rem 1rem', borderRadius: 4 }}>
          {error}
        </p>
      )}

      {/* Create / Edit form */}
      <form
        onSubmit={handleSubmit}
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: 8,
          alignItems: 'center',
          marginBottom: 1.5,
          padding: 12,
          background: '#f8f9fa',
          borderRadius: 6
        }}
      >
        <input
          placeholder="Title *"
          value={form.title}
          onChange={handleChange('title')}
          style={{ flex: '1 1 140px' }}
        />
        <input
          placeholder="Author *"
          value={form.author}
          onChange={handleChange('author')}
          style={{ flex: '1 1 140px' }}
        />
        <input
          placeholder="Year"
          type="number"
          value={form.year}
          onChange={handleChange('year')}
          style={{ width: 90 }}
        />
        <label style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <input
            type="checkbox"
            checked={form.read}
            onChange={handleChange('read')}
          />
          Read
        </label>
        <button type="submit" style={{ padding: '6px 16px' }}>
          {editingId ? 'Update' : 'Add Book'}
        </button>
        {editingId !== null && (
          <button type="button" onClick={cancelEdit} style={{ padding: '6px 16px' }}>
            Cancel
          </button>
        )}
      </form>

      {/* Books table */}
      {loading ? (
        <p>Loading…</p>
      ) : (
        <table
          style={{
            width: '100%',
            borderCollapse: 'collapse',
            fontSize: 15
          }}
        >
          <thead>
            <tr style={{ borderBottom: '2px solid #ddd', textAlign: 'left' }}>
              <th style={th}>Title</th>
              <th style={th}>Author</th>
              <th style={th}>Year</th>
              <th style={th}>Read</th>
              <th style={th}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {books.length === 0 && (
              <tr>
                <td colSpan={5} style={td}>
                  No books yet. Add one above!
                </td>
              </tr>
            )}
            {books.map((book) => (
              <tr key={book.id} style={{ borderBottom: '1px solid #eee' }}>
                <td style={td}>{book.title}</td>
                <td style={td}>{book.author}</td>
                <td style={td}>{book.year ?? '—'}</td>
                <td style={td}>{book.read ? '✅' : '⬜'}</td>
                <td style={td}>
                  <button onClick={() => startEdit(book)}>Edit</button>{' '}
                  <button onClick={() => toggleRead(book)}>
                    {book.read ? 'Mark Unread' : 'Mark Read'}
                  </button>{' '}
                  <button onClick={() => handleDelete(book.id)} style={{ color: '#c0392b' }}>
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

const th = { padding: '8px 12px', fontWeight: 600 };
const td = { padding: '8px 12px' };
```