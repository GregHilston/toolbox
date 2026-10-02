

### README.md
```markdown
# Books CRUD App

A small full-stack CRUD app for managing a list of books.

## Project Structure

- `server/` – Node.js + Express + SQLite REST API
- `client/` – React + Vite frontend

## Running

### 1. Start the API (terminal 1)

```bash
cd server
npm install
npm start
```

The API listens on `http://localhost:3001` (or the port in the `PORT` env var).

### 2. Start the UI (terminal 2)

```bash
cd client
npm install
npm run dev
```

Open the URL Vite prints (default `http://localhost:5173`).

### Production build

```bash
cd client
npm run build
```

## API Endpoints

| Method | Path             | Description              |
|--------|------------------|--------------------------|
| GET    | /api/books       | List all books           |
| GET    | /api/books/:id   | Get one book             |
| POST   | /api/books       | Create a book            |
| PUT    | /api/books/:id   | Update a book            |
| DELETE | /api/books/:id   | Delete a book            |

`title` and `author` are required; missing/empty values return **400**. Unknown ids return **404**.
```

### server/package.json
```json
{
  "name": "books-server",
  "version": "1.0.0",
  "private": true,
  "main": "index.js",
  "scripts": {
    "start": "node index.js"
  },
  "engines": {
    "node": ">=26"
  },
  "dependencies": {
    "better-sqlite3": "^12.2.0",
    "express": "^4.21.2"
  }
}
```

### server/index.js
```javascript
const express = require('express');
const Database = require('better-sqlite3');
const path = require('path');

const app = express();
app.use(express.json());

// ── SQLite setup ──────────────────────────────────────────────────────────────
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

// ── Helpers ───────────────────────────────────────────────────────────────────
function validate(body) {
  if (!body.title || !String(body.title).trim()) return 'title is required';
  if (!body.author || !String(body.author).trim()) return 'author is required';
  return null;
}

function yearOrNull(year) {
  if (year === undefined || year === null || year === '') return null;
  const n = parseInt(year, 10);
  return Number.isNaN(n) ? null : n;
}

// ── Routes ────────────────────────────────────────────────────────────────────

// GET /api/books
app.get('/api/books', (_req, res) => {
  const books = db.prepare('SELECT * FROM books ORDER BY id').all();
  res.json(books);
});

// GET /api/books/:id
app.get('/api/books/:id', (req, res) => {
  const book = db.prepare('SELECT * FROM books WHERE id = ?').get(req.params.id);
  if (!book) return res.status(404).json({ error: 'Book not found' });
  res.json(book);
});

// POST /api/books
app.post('/api/books', (req, res) => {
  const err = validate(req.body);
  if (err) return res.status(400).json({ error: err });

  const { title, author } = req.body;
  const year = yearOrNull(req.body.year);
  const read = req.body.read ? 1 : 0;

  const result = db
    .prepare('INSERT INTO books (title, author, year, read) VALUES (?, ?, ?, ?)')
    .run(title.trim(), author.trim(), year, read);

  const book = db.prepare('SELECT * FROM books WHERE id = ?').get(result.lastInsertRowid);
  res.status(201).json(book);
});

// PUT /api/books/:id
app.put('/api/books/:id', (req, res) => {
  const existing = db.prepare('SELECT * FROM books WHERE id = ?').get(req.params.id);
  if (!existing) return res.status(404).json({ error: 'Book not found' });

  const err = validate(req.body);
  if (err) return res.status(400).json({ error: err });

  const { title, author } = req.body;
  const year = yearOrNull(req.body.year);
  const read = req.body.read ? 1 : 0;

  db.prepare('UPDATE books SET title = ?, author = ?, year = ?, read = ? WHERE id = ?')
    .run(title.trim(), author.trim(), year, read, req.params.id);

  const book = db.prepare('SELECT * FROM books WHERE id = ?').get(req.params.id);
  res.json(book);
});

// DELETE /api/books/:id
app.delete('/api/books/:id', (req, res) => {
  const existing = db.prepare('SELECT * FROM books WHERE id = ?').get(req.params.id);
  if (!existing) return res.status(404).json({ error: 'Book not found' });

  db.prepare('DELETE FROM books WHERE id = ?').run(req.params.id);
  res.json({ message: 'Book deleted' });
});

// ── Start ─────────────────────────────────────────────────────────────────────
const PORT = process.env.PORT || 3001;
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
    "@vitejs/plugin-react": "^4.4.1",
    "vite": "^6.3.5"
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

const thStyle = {
  borderBottom: '2px solid #333',
  padding: '0.5rem 0.6rem',
  textAlign: 'left'
};
const tdStyle = {
  borderBottom: '1px solid #ddd',
  padding: '0.5rem 0.6rem'
};
const btnStyle = {
  cursor: 'pointer',
  padding: '0.3rem 0.6rem',
  marginRight: '0.3rem'
};

export default function App() {
  const [books, setBooks] = useState([]);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({ title: '', author: '', year: '', read: false });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  const fetchBooks = useCallback(async () => {
    try {
      const res = await fetch('/api/books');
      const data = await res.json();
      setBooks(data);
    } catch {
      setError('Failed to fetch books');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchBooks();
  }, [fetchBooks]);

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
      const url = editing ? `/api/books/${editing.id}` : '/api/books';
      const method = editing ? 'PUT' : 'POST';

      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        setError(body.error || `Request failed (${res.status})`);
        return;
      }

      setForm({ title: '', author: '', year: '', read: false });
      setEditing(null);
      await fetchBooks();
    } catch {
      setError('Network error');
    }
  };

  const handleEdit = (book) => {
    setEditing(book);
    setForm({
      title: book.title,
      author: book.author,
      year: book.year != null ? String(book.year) : '',
      read: !!book.read
    });
    setError('');
  };

  const handleCancel = () => {
    setEditing(null);
    setForm({ title: '', author: '', year: '', read: false });
    setError('');
  };

  const handleToggleRead = async (book) => {
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

  if (loading) return <p>Loading…</p>;

  return (
    <div style={{ maxWidth: 820, margin: '2rem auto', padding: '0 1rem', fontFamily: 'system-ui, -apple-system, sans-serif' }}>
      <h1>📚 Books</h1>

      {error && (
        <p style={{ color: '#c0392b', background: '#fdecea', padding: '0.5rem', borderRadius: 4 }}>
          {error}
        </p>
      )}

      {/* Create / Edit form */}
      <form onSubmit={handleSubmit} style={{ display: 'grid', gap: '0.5rem', marginBottom: '1.5rem', padding: '1rem', background: '#f9f9f9', borderRadius: 6 }}>
        <h2 style={{ margin: 0 }}>{editing ? 'Edit Book' : 'Add a Book'}</h2>
        <input
          placeholder="Title *"
          value={form.title}
          onChange={(e) => setForm({ ...form, title: e.target.value })}
          required
        />
        <input
          placeholder="Author *"
          value={form.author}
          onChange={(e) => setForm({ ...form, author: e.target.value })}
          required
        />
        <input
          placeholder="Year (optional)"
          type="number"
          value={form.year}
          onChange={(e) => setForm({ ...form, year: e.target.value })}
        />
        <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          <input
            type="checkbox"
            checked={form.read}
            onChange={(e) => setForm({ ...form, read: e.target.checked })}
          />
          Read
        </label>
        <div>
          <button type="submit" style={btnStyle}>
            {editing ? 'Update' : 'Add Book'}
          </button>
          {editing && (
            <button type="button" onClick={handleCancel} style={btnStyle}>
              Cancel
            </button>
          )}
        </div>
      </form>

      {/* Table */}
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            <th style={thStyle}>#</th>
            <th style={thStyle}>Title</th>
            <th style={thStyle}>Author</th>
            <th style={thStyle}>Year</th>
            <th style={thStyle}>Read</th>
            <th style={thStyle}>Actions</th>
          </tr>
        </thead>
        <tbody>
          {books.length === 0 && (
            <tr>
              <td colSpan={6} style={{ ...tdStyle, textAlign: 'center', color: '#888' }}>
                No books yet. Add one above!
              </td>
            </tr>
          )}
          {books.map((book) => (
            <tr key={book.id}>
              <td style={tdStyle}>{book.id}</td>
              <td style={tdStyle}>{book.title}</td>
              <td style={tdStyle}>{book.author}</td>
              <td style={tdStyle}>{book.year != null ? book.year : '—'}</td>
              <td style={tdStyle}>{book.read ? '✅' : '❌'}</td>
              <td style={tdStyle}>
                <button onClick={() => handleEdit(book)} style={btnStyle}>Edit</button>
                <button onClick={() => handleToggleRead(book)} style={btnStyle}>
                  {book.read ? 'Mark Unread' : 'Mark Read'}
                </button>
                <button
                  onClick={() => handleDelete(book.id)}
                  style={{ ...btnStyle, color: '#c0392b' }}
                >
                  Delete
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```