

### server/package.json
```json
{
  "name": "books-api",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "start": "node index.js"
  },
  "dependencies": {
    "better-sqlite3": "^11.2.0",
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
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    read INTEGER NOT NULL DEFAULT 0
  );
`);

const app = express();
app.use(express.json());

// GET /api/books
app.get('/api/books', (req, res) => {
  const rows = db.prepare('SELECT * FROM books ORDER BY id').all();
  res.json(rows.map(r => ({ ...r, read: Boolean(r.read) })));
});

// GET /api/books/:id
app.get('/api/books/:id', (req, res) => {
  const row = db.prepare('SELECT * FROM books WHERE id = ?').get(Number(req.params.id));
  if (!row) return res.status(404).json({ error: 'Not found' });
  res.json({ ...row, read: Boolean(row.read) });
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
  const row = db.prepare('SELECT * FROM books WHERE id = ?').get(info.lastInsertRowid);
  res.status(201).json({ ...row, read: Boolean(row.read) });
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
  res.json({ ...row, read: Boolean(row.read) });
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

### client/package.json
```json
{
  "name": "books-ui",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "vite",
    "build": "vite build"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.3.4",
    "vite": "^5.4.19"
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
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Books CRUD</title>
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
import { createRoot } from 'react-dom/client';
import App from './App.jsx';

createRoot(document.getElementById('root')).render(<App />);
```

### client/src/index.css
```css
* {
  box-sizing: border-box;
}

body {
  font-family: system-ui, sans-serif;
  margin: 0;
  padding: 2rem;
  background: #f5f5f5;
}

h1 {
  margin-bottom: 1rem;
}

table {
  width: 100%;
  border-collapse: collapse;
  background: #fff;
  border: 1px solid #ccc;
}

th, td {
  padding: 0.6rem 0.8rem;
  text-align: left;
  border: 1px solid #ddd;
}

th {
  background: #f0f0f0;
}

button {
  cursor: pointer;
  padding: 0.35rem 0.6rem;
  margin: 0 0.15rem;
}

.form {
  background: #fff;
  border: 1px solid #ccc;
  padding: 1.5rem;
  margin-top: 1.5rem;
  max-width: 480px;
}

.form label {
  display: block;
  margin-bottom: 0.5rem;
}

.form input {
  display: block;
  width: 100%;
  padding: 0.35rem;
  margin-top: 0.15rem;
}

.form button[type="submit"] {
  margin-top: 0.75rem;
}
```

### client/src/App.jsx
```jsx
import { useState, useEffect } from 'react';
import './index.css';

const EMPTY = { title: '', author: '', year: '', read: false };

function App() {
  const [books, setBooks] = useState([]);
  const [form, setForm] = useState(null); // null | { ...EMPTY, editingId?: number }

  const fetchBooks = () => {
    fetch('/api/books')
      .then(r => r.json())
      .then(setBooks);
  };

  useEffect(() => { fetchBooks(); }, []);

  const openCreate = () => setForm({ ...EMPTY });

  const openEdit = (b) =>
    setForm({ title: b.title, author: b.author, year: b.year ?? '', read: b.read, editingId: b.id });

  const toggleRead = async (id, currentValue) => {
    await fetch(`/api/books/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...getBook(id), read: !currentValue })
    });
    fetchBooks();
  };

  const deleteBook = async (id) => {
    if (!confirm('Delete this book?')) return;
    await fetch(`/api/books/${id}`, { method: 'DELETE' });
    fetchBooks();
  };

  const getBook = (id) => {
    const b = books.find(x => x.id === id);
    return b ? { title: b.title, author: b.author, year: b.year, read: b.read } : {};
  };

  const submit = async (e) => {
    e.preventDefault();
    const { editingId, ...data } = form;
    const body = { ...data };
    if (body.year === '') body.year = null;
    else body.year = Number(body.year);

    if (editingId) {
      await fetch(`/api/books/${editingId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
    } else {
      await fetch('/api/books', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
    }
    setForm(null);
    fetchBooks();
  };

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  return (
    <div>
      <h1>Books</h1>
      <button onClick={openCreate}>+ Add Book</button>

      {form && (
        <form className="form" onSubmit={submit}>
          <h3>{form.editingId ? 'Edit' : 'Add'} Book</h3>
          <label>
            Title *
            <input value={form.title} onChange={e => set('title', e.target.value)} required />
          </label>
          <label>
            Author *
            <input value={form.author} onChange={e => set('author', e.target.value)} required />
          </label>
          <label>
            Year
            <input type="number" value={form.year} onChange={e => set('year', e.target.value)} />
          </label>
          <label>
            <input type="checkbox" checked={form.read} onChange={e => set('read', e.target.checked)} />
            {' '}Read
          </label>
          <button type="submit">{form.editingId ? 'Update' : 'Create'}</button>{' '}
          <button type="button" onClick={() => setForm(null)}>Cancel</button>
        </form>
      )}

      <table>
        <thead>
          <tr><th>Title</th><th>Author</th><th>Year</th><th>Read</th><th>Actions</th></tr>
        </thead>
        <tbody>
          {books.map(b => (
            <tr key={b.id}>
              <td>{b.title}</td>
              <td>{b.author}</td>
              <td>{b.year ?? '—'}</td>
              <td>{b.read ? '✅' : '⬜'}</td>
              <td>
                <button onClick={() => openEdit(b)}>Edit</button>
                <button onClick={() => toggleRead(b.id, b.read)}>Toggle Read</button>
                <button onClick={() => deleteBook(b.id)}>Delete</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default App;
```

### README.md
```md
# Books CRUD

## Prerequisites

- Node.js 26+

## Run the API

```bash
cd server
npm install
npm start          # starts on PORT (default 3001)
```

## Run the UI

```bash
cd client
npm install
npm run dev        # Vite dev server on http://localhost:5173 (proxies /api → :3001)
```

## Build the UI (production bundle)

```bash
cd client
npm run build
```
```