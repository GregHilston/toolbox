

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
    "express": "^4.21.2"
  }
}
```

### server/index.js
```js
const path = require('node:path');
const { DatabaseSync } = require('node:sqlite');

const PORT = process.env.PORT || 3001;

const db = new DatabaseSync(path.join(__dirname, 'data.db'));

db.exec(`
  CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    read BOOLEAN DEFAULT 0
  )
`);

const express = require('express');
const app = express();
app.use(express.json());

function toBook(row) {
  return { ...row, read: !!row.read };
}

function validateBook(body) {
  const title = body.title;
  const author = body.author;
  if (title === undefined || title === null || String(title).trim() === '') return false;
  if (author === undefined || author === null || String(author).trim() === '') return false;
  return true;
}

// GET /api/books
app.get('/api/books', (_req, res) => {
  const rows = db.prepare('SELECT id, title, author, year, read FROM books').all();
  res.json(rows.map(toBook));
});

// GET /api/books/:id
app.get('/api/books/:id', (req, res) => {
  const id = Number(req.params.id);
  if (!Number.isInteger(id)) return res.status(404).json({ error: 'Book not found' });
  const row = db.prepare('SELECT id, title, author, year, read FROM books WHERE id = ?').get(id);
  if (!row) return res.status(404).json({ error: 'Book not found' });
  res.json(toBook(row));
});

// POST /api/books
app.post('/api/books', (req, res) => {
  const { title, author, year, read } = req.body;
  if (!validateBook(req.body)) {
    return res.status(400).json({ error: 'Title and author are required' });
  }
  const yearVal = (year === undefined || year === null || year === '') ? null : parseInt(year, 10);
  const readVal = read ? 1 : 0;
  const info = db.prepare(
    'INSERT INTO books (title, author, year, read) VALUES (?, ?, ?, ?)'
  ).run(String(title).trim(), String(author).trim(), yearVal, readVal);
  const row = db.prepare('SELECT id, title, author, year, read FROM books WHERE id = ?').get(Number(info.lastInsertRowid));
  res.status(201).json(toBook(row));
});

// PUT /api/books/:id
app.put('/api/books/:id', (req, res) => {
  const id = Number(req.params.id);
  const { title, author, year, read } = req.body;

  if (!validateBook(req.body)) {
    return res.status(400).json({ error: 'Title and author are required' });
  }

  const existing = db.prepare('SELECT id FROM books WHERE id = ?').get(id);
  if (!existing) return res.status(404).json({ error: 'Book not found' });

  const yearVal = (year === undefined || year === null || year === '') ? null : parseInt(year, 10);
  const readVal = read ? 1 : 0;

  db.prepare(
    'UPDATE books SET title = ?, author = ?, year = ?, read = ? WHERE id = ?'
  ).run(String(title).trim(), String(author).trim(), yearVal, readVal, id);

  const row = db.prepare('SELECT id, title, author, year, read FROM books WHERE id = ?').get(id);
  res.json(toBook(row));
});

// DELETE /api/books/:id
app.delete('/api/books/:id', (req, res) => {
  const id = Number(req.params.id);
  const existing = db.prepare('SELECT id FROM books WHERE id = ?').get(id);
  if (!existing) return res.status(404).json({ error: 'Book not found' });
  db.prepare('DELETE FROM books WHERE id = ?').run(id);
  res.json({ message: 'Deleted' });
});

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
    "build": "vite build"
  },
  "dependencies": {
    "react": "^19.1.0",
    "react-dom": "^19.1.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.4.1",
    "vite": "^6.3.3"
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
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './index.css';
import App from './App';

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>
);
```

### client/src/index.css
```css
*,
*::before,
*::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: system-ui, -apple-system, sans-serif;
  background: #f5f5f5;
  padding: 2rem;
  color: #1a1a1a;
}

h1 {
  margin-bottom: 1rem;
}

form {
  background: #fff;
  padding: 1.25rem;
  border-radius: 8px;
  box-shadow: 0 1px 4px rgba(0,0,0,.1);
  margin-bottom: 1.5rem;
  display: grid;
  gap: .5rem;
  max-width: 600px;
}

form label {
  display: grid;
  gap: .25rem;
  font-size: .85rem;
}

form input[type="text"],
form input[type="number"] {
  padding: .4rem .5rem;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: .9rem;
}

table {
  width: 100%;
  border-collapse: collapse;
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 1px 4px rgba(0,0,0,.1);
}

th, td {
  padding: .6rem .75rem;
  text-align: left;
  border-bottom: 1px solid #eee;
}

th {
  background: #f0f0f0;
  font-size: .8rem;
  text-transform: uppercase;
}

td button {
  margin-right: .35rem;
  cursor: pointer;
}

button {
  padding: .35rem .65rem;
  border-radius: 4px;
  border: 1px solid #ccc;
  background: #fff;
  font-size: .8rem;
}

button:hover {
  background: #eee;
}

button.danger {
  color: #c0392b;
  border-color: #e8b0b0;
}

form button[type="submit"] {
  justify-self: start;
  background: #2563eb;
  color: #fff;
  border-color: #2563eb;
  font-weight: 600;
}

form button[type="submit"]:hover {
  background: #1d4ed8;
}
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
  const [editingId, setEditingId] = useState(null);
  const [error, setError] = useState('');

  const fetchBooks = useCallback(() => {
    fetch(API)
      .then(r => r.json())
      .then(setBooks)
      .catch(console.error);
  }, []);

  useEffect(() => { fetchBooks(); }, [fetchBooks]);

  function change(field, value) {
    setForm(f => ({ ...f, [field]: value }));
  }

  function handleSubmit(e) {
    e.preventDefault();
    setError('');
    const body = { ...form, year: form.year !== '' ? Number(form.year) : null };
    const method = editingId !== null ? 'PUT' : 'POST';
    const url = editingId !== null ? `${API}/${editingId}` : API;

    fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
      .then(r => r.json().then(d => ({ ok: r.ok, body: d })))
      .then(({ ok, body }) => {
        if (!ok) { setError(body.error || 'Unknown error'); return; }
        setForm(emptyForm());
        setEditingId(null);
        fetchBooks();
      })
      .catch(err => setError(err.message));
  }

  function handleEdit(book) {
    setEditingId(book.id);
    setForm({
      title: book.title,
      author: book.author,
      year: book.year !== null && book.year !== undefined ? String(book.year) : '',
      read: book.read,
    });
  }

  function handleToggleRead(book) {
    const body = { ...book, read: !book.read };
    fetch(`${API}/${book.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(fetchBooks);
  }

  function handleDelete(id) {
    if (!window.confirm('Delete this book?')) return;
    fetch(`${API}/${id}`, { method: 'DELETE' }).then(fetchBooks);
  }

  function cancelEdit() {
    setEditingId(null);
    setForm(emptyForm());
  }

  return (
    <>
      <h1>Books</h1>

      <form onSubmit={handleSubmit}>
        <h2>{editingId !== null ? 'Edit book' : 'Add book'}</h2>
        {error && <p style={{ color: '#c0392b' }}>{error}</p>}

        <label>
          Title *
          <input type="text" value={form.title} onChange={e => change('title', e.target.value)} required />
        </label>

        <label>
          Author *
          <input type="text" value={form.author} onChange={e => change('author', e.target.value)} required />
        </label>

        <label>
          Year (optional)
          <input type="number" value={form.year} onChange={e => change('year', e.target.value)} />
        </label>

        <label>
          <input type="checkbox" checked={form.read} onChange={e => change('read', e.target.checked)} />
          {' '}Read
        </label>

        <button type="submit">{editingId !== null ? 'Update' : 'Create'}</button>
        {editingId !== null && (
          <button type="button" onClick={cancelEdit}>Cancel</button>
        )}
      </form>

      <table>
        <thead>
          <tr>
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
              <td>{b.title}</td>
              <td>{b.author}</td>
              <td>{b.year ?? ''}</td>
              <td>{b.read ? 'Yes' : 'No'}</td>
              <td>
                <button onClick={() => handleEdit(b)}>Edit</button>
                <button onClick={() => handleToggleRead(b)}>Toggle Read</button>
                <button className="danger" onClick={() => handleDelete(b.id)}>Delete</button>
              </td>
            </tr>
          ))}
          {books.length === 0 && <tr><td colSpan={5}>No books yet.</td></tr>}
        </tbody>
      </table>
    </>
  );
}
```

### README.md
```md
# Books CRUD App

## Prerequisites

- Node.js 26+

## Run the API server

```bash
cd server
npm install
npm start
# → Books API listening on http://localhost:3001
# (override with PORT env var if needed)
```

## Run the React UI

```bash
cd client
npm install
npm run dev
# → Open http://localhost:5173
```

## Build the UI for production

```bash
cd client
npm run build
```
```