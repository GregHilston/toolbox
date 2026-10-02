

### server/package.json
```json
{
  "name": "server",
  "version": "1.0.0",
  "private": true,
  "main": "index.js",
  "scripts": {
    "start": "node index.js"
  },
  "dependencies": {
    "express": "^4.21.0"
  }
}
```

### server/index.js
```js
const express = require('express');
const path = require('node:path');
const { DatabaseSync } = require('node:sqlite');

const app = express();
app.use(express.json());

const db = new DatabaseSync(path.join(__dirname, 'data.db'));

db.exec(`
  CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    read BOOLEAN DEFAULT 0
  )
`);

// GET /api/books
app.get('/api/books', (req, res) => {
  const rows = db.prepare('SELECT * FROM books ORDER BY id').all();
  res.json(rows);
});

// GET /api/books/:id
app.get('/api/books/:id', (req, res) => {
  const id = Number(req.params.id);
  const row = db.prepare('SELECT * FROM books WHERE id = ?').get(id);
  if (!row) {
    return res.status(404).json({ error: 'Book not found' });
  }
  res.json(row);
});

// POST /api/books
app.post('/api/books', (req, res) => {
  const { title, author, year, read } = req.body;

  if (!title || typeof title !== 'string' || title.trim() === '') {
    return res.status(400).json({ error: 'title is required' });
  }
  if (!author || typeof author !== 'string' || author.trim() === '') {
    return res.status(400).json({ error: 'author is required' });
  }

  const result = db
    .prepare('INSERT INTO books (title, author, year, read) VALUES (?, ?, ?, ?)')
    .run(title.trim(), author.trim(), year ?? null, read ? 1 : 0);

  const book = db.prepare('SELECT * FROM books WHERE id = ?').get(Number(result.lastInsertRowid));
  res.status(201).json(book);
});

// PUT /api/books/:id
app.put('/api/books/:id', (req, res) => {
  const id = Number(req.params.id);
  const existing = db.prepare('SELECT * FROM books WHERE id = ?').get(id);
  if (!existing) {
    return res.status(404).json({ error: 'Book not found' });
  }

  const { title, author, year, read } = req.body;

  if (!title || typeof title !== 'string' || title.trim() === '') {
    return res.status(400).json({ error: 'title is required' });
  }
  if (!author || typeof author !== 'string' || author.trim() === '') {
    return res.status(400).json({ error: 'author is required' });
  }

  db.prepare('UPDATE books SET title = ?, author = ?, year = ?, read = ? WHERE id = ?')
    .run(title.trim(), author.trim(), year ?? null, read ? 1 : 0, id);

  const book = db.prepare('SELECT * FROM books WHERE id = ?').get(id);
  res.json(book);
});

// DELETE /api/books/:id
app.delete('/api/books/:id', (req, res) => {
  const id = Number(req.params.id);
  const existing = db.prepare('SELECT * FROM books WHERE id = ?').get(id);
  if (!existing) {
    return res.status(404).json({ error: 'Book not found' });
  }
  db.prepare('DELETE FROM books WHERE id = ?').run(id);
  res.json({ message: 'Deleted' });
});

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
  console.log(`Server listening on port ${PORT}`);
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
    "react": "^19.0.0",
    "react-dom": "^19.0.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.3.4",
    "vite": "^6.0.0"
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
import { useEffect, useState } from 'react';

const emptyForm = { title: '', author: '', year: '', read: false };

export default function App() {
  const [books, setBooks] = useState([]);
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState(null);
  const [error, setError] = useState('');

  async function fetchBooks() {
    const res = await fetch('/api/books');
    const data = await res.json();
    setBooks(data);
  }

  useEffect(() => {
    fetchBooks();
  }, []);

  function resetForm() {
    setForm(emptyForm);
    setEditingId(null);
    setError('');
  }

  function handleCreate(e) {
    e.preventDefault();
    const payload = {
      title: form.title,
      author: form.author,
      year: form.year ? Number(form.year) : null,
      read: form.read,
    };
    fetch('/api/books', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
      .then((r) => {
        if (!r.ok) return r.json().then((d) => Promise.reject(d));
        return r.json();
      })
      .then(() => {
        resetForm();
        fetchBooks();
      })
      .catch((d) => setError(d.error || 'Error'));
  }

  function handleEdit(book) {
    setEditingId(book.id);
    setForm({
      title: book.title,
      author: book.author,
      year: book.year ?? '',
      read: Boolean(book.read),
    });
    setError('');
  }

  function handleUpdate(e) {
    e.preventDefault();
    const payload = {
      title: form.title,
      author: form.author,
      year: form.year ? Number(form.year) : null,
      read: form.read,
    };
    fetch(`/api/books/${editingId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
      .then((r) => {
        if (!r.ok) return r.json().then((d) => Promise.reject(d));
        return r.json();
      })
      .then(() => {
        resetForm();
        fetchBooks();
      })
      .catch((d) => setError(d.error || 'Error'));
  }

  function handleToggleRead(book) {
    const payload = {
      title: book.title,
      author: book.author,
      year: book.year,
      read: !book.read,
    };
    fetch(`/api/books/${book.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
      .then((r) => r.json())
      .then(() => fetchBooks())
      .catch(() => setError('Error toggling read'));
  }

  function handleDelete(id) {
    fetch(`/api/books/${id}`, { method: 'DELETE' })
      .then((r) => {
        if (!r.ok) return r.json().then((d) => Promise.reject(d));
        return r.json();
      })
      .then(() => {
        if (editingId === id) resetForm();
        fetchBooks();
      })
      .catch((d) => setError(d.error || 'Error deleting'));
  }

  return (
    <div style={{ maxWidth: 800, margin: '2rem auto', fontFamily: 'system-ui, sans-serif' }}>
      <h1>Books</h1>

      {error && (
        <p style={{ color: 'red' }}>{error}</p>
      )}

      <form
        onSubmit={editingId ? handleUpdate : handleCreate}
        style={{ display: 'flex', gap: 8, marginBottom: '1.5rem', flexWrap: 'wrap' }}
      >
        <input
          placeholder="Title *"
          value={form.title}
          onChange={(e) => setForm({ ...form, title: e.target.value })}
          style={{ flex: 1, minWidth: 150 }}
        />
        <input
          placeholder="Author *"
          value={form.author}
          onChange={(e) => setForm({ ...form, author: e.target.value })}
          style={{ flex: 1, minWidth: 150 }}
        />
        <input
          placeholder="Year"
          type="number"
          value={form.year}
          onChange={(e) => setForm({ ...form, year: e.target.value })}
          style={{ width: 100 }}
        />
        <label style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <input
            type="checkbox"
            checked={form.read}
            onChange={(e) => setForm({ ...form, read: e.target.checked })}
          />
          Read
        </label>
        <button type="submit">{editingId ? 'Update' : 'Add'}</button>
        {editingId && (
          <button type="button" onClick={resetForm}>
            Cancel
          </button>
        )}
      </form>

      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            <th style={thStyle}>ID</th>
            <th style={thStyle}>Title</th>
            <th style={thStyle}>Author</th>
            <th style={thStyle}>Year</th>
            <th style={thStyle}>Read</th>
            <th style={thStyle}>Actions</th>
          </tr>
        </thead>
        <tbody>
          {books.map((book) => (
            <tr key={book.id}>
              <td style={tdStyle}>{book.id}</td>
              <td style={tdStyle}>{book.title}</td>
              <td style={tdStyle}>{book.author}</td>
              <td style={tdStyle}>{book.year ?? ''}</td>
              <td style={tdStyle}>{book.read ? '✓' : ''}</td>
              <td style={tdStyle}>
                <button onClick={() => handleEdit(book)} style={btnStyle}>
                  Edit
                </button>{' '}
                <button onClick={() => handleToggleRead(book)} style={btnStyle}>
                  Toggle Read
                </button>{' '}
                <button onClick={() => handleDelete(book.id)} style={{ ...btnStyle, color: 'red' }}>
                  Delete
                </button>
              </td>
            </tr>
          ))}
          {books.length === 0 && (
            <tr>
              <td colSpan={6} style={tdStyle}>
                No books yet.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

const thStyle = {
  textAlign: 'left',
  borderBottom: '2px solid #ccc',
  padding: '8px 6px',
};

const tdStyle = {
  borderBottom: '1px solid #eee',
  padding: '8px 6px',
};

const btnStyle = {
  margin: '0 2px',
  cursor: 'pointer',
};
```

### README.md
```markdown
# Books CRUD App

A full-stack CRUD app for managing a list of books.

## Prerequisites

- Node.js 26+
- npm

## Running

### 1. Start the API server

```bash
cd server
npm install
npm start
```

The API listens on port **3001** (override with the `PORT` env variable).

### 2. Start the frontend (dev)

In a second terminal:

```bash
cd client
npm install
npm run dev
```

Open the URL Vite prints (typically `http://localhost:5173`).

### 3. Production build of the frontend

```bash
cd client
npm run build
```

This outputs static assets to `client/dist/`.

## API Endpoints

| Method | Path             | Description           |
|--------|------------------|-----------------------|
| GET    | /api/books       | List all books        |
| GET    | /api/books/:id   | Get one book          |
| POST   | /api/books       | Create a book         |
| PUT    | /api/books/:id   | Update a book         |
| DELETE | /api/books/:id   | Delete a book         |

`title` and `author` are required on POST/PUT (400 if missing/empty). Unknown ids return 404.
```