

### README.md
```markdown
# Books CRUD App

A small full-stack CRUD application for managing a `books` table.

## Run

### Backend (API)

```bash
cd server
npm install
npm start        # listens on http://localhost:3001
```

### Frontend (UI)

In a second terminal:

```bash
cd client
npm install
npm run dev     # opens on http://localhost:5173, proxies /api → :3001
```

Build production bundle:

```bash
cd client
npm run build
```

## API Endpoints

| Method | Path            | Description            |
|--------|-----------------|----------------------|
| GET    | /api/books      | List all books       |
| GET    | /api/books/:id  | Get one book         |
| POST   | /api/books      | Create a book        |
| PUT    | /api/books/:id  | Update a book        |
| DELETE | /api/books/:id  | Delete a book        |

Title and author are required (non-empty) on POST and PUT; missing/empty values return 400.
An unknown id returns 404.
```

### server/package.json
```json
{
  "name": "books-api",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "start": "node index.js"
  },
  "dependencies": {
    "better-sqlite3": "^11.7.0",
    "express": "^4.21.2"
  }
}
```

### server/index.js
```js
const express = require('express');
const Database = require('better-sqlite3');
const path = require('path');

const app = express();
const PORT = parseInt(process.env.PORT, 10) || 3001;

const db = new Database(path.join(__dirname, 'data.db'));

// Enable WAL mode for better concurrent reads
db.pragma('journal_mode = WAL');

// Create table if it doesn't exist
db.exec(`
  CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT    NOT NULL,
    author TEXT    NOT NULL,
    year   INTEGER,
    read   BOOLEAN NOT NULL DEFAULT 0
  )
`);

// Prepare statements
const stmts = {
  list:    db.prepare('SELECT * FROM books ORDER BY id'),
  getById: db.prepare('SELECT * FROM books WHERE id = ?'),
  insert:  db.prepare('INSERT INTO books (title, author, year, read) VALUES (?, ?, ?, ?)'),
  update:  db.prepare('UPDATE books SET title = ?, author = ?, year = ?, read = ? WHERE id = ?'),
  delete:  db.prepare('DELETE FROM books WHERE id = ?'),
};

// Middleware
app.use(express.json());

// ---------- Routes ----------

// GET all books
app.get('/api/books', (req, res) => {
  const books = stmts.list.all();
  res.json(books);
});

// GET one book
app.get('/api/books/:id', (req, res) => {
  const book = stmts.getById.get(req.params.id);
  if (!book) {
    return res.status(404).json({ error: 'Book not found' });
  }
  res.json(book);
});

// POST (create)
app.post('/api/books', (req, res) => {
  const { title, author, year, read } = req.body;

  if (!title || typeof title !== 'string' || title.trim() === '') {
    return res.status(400).json({ error: 'title is required and must not be empty' });
  }
  if (!author || typeof author !== 'string' || author.trim() === '') {
    return res.status(400).json({ error: 'author is required and must not be empty' });
  }

  const info = stmts.insert.run(title.trim(), author.trim(), year || null, read ? 1 : 0);
  const created = stmts.getById.get(info.lastInsertRowid);
  res.status(201).json(created);
});

// PUT (update)
app.put('/api/books/:id', (req, res) => {
  const existing = stmts.getById.get(req.params.id);
  if (!existing) {
    return res.status(404).json({ error: 'Book not found' });
  }

  const { title, author, year, read } = req.body;

  if (!title || typeof title !== 'string' || title.trim() === '') {
    return res.status(400).json({ error: 'title is required and must not be empty' });
  }
  if (!author || typeof author !== 'string' || author.trim() === '') {
    return res.status(400).json({ error: 'author is required and must not be empty' });
  }

  stmts.update.run(title.trim(), author.trim(), year || null, read ? 1 : 0, req.params.id);
  const updated = stmts.getById.get(req.params.id);
  res.json(updated);
});

// DELETE
app.delete('/api/books/:id', (req, res) => {
  const existing = stmts.getById.get(req.params.id);
  if (!existing) {
    return res.status(404).json({ error: 'Book not found' });
  }
  stmts.delete.run(req.params.id);
  res.json({ ok: true });
});

// Start
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
import './App.css';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

### client/src/App.css
```css
* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: #f5f5f5;
  color: #333;
  padding: 2rem;
}

h1 {
  margin-bottom: 1.5rem;
}

table {
  width: 100%;
  border-collapse: collapse;
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

th, td {
  padding: 0.75rem 1rem;
  text-align: left;
  border-bottom: 1px solid #eee;
}

th {
  background: #2c3e50;
  color: #fff;
}

tr:hover td {
  background: #f9f9f9;
}

button {
  padding: 0.4rem 0.8rem;
  margin: 0 0.25rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.85rem;
}

button.toggle {
  background: #27ae60;
  color: #fff;
}

button.toggle.is-read {
  background: #f39c12;
}

button.edit {
  background: #2980b9;
  color: #fff;
}

button.delete {
  background: #e74c3c;
  color: #fff;
}

form {
  margin-top: 2rem;
  background: #fff;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

form h2 {
  margin-bottom: 1rem;
}

label {
  display: block;
  margin-bottom: 0.75rem;
}

label span {
  display: block;
  margin-bottom: 0.25rem;
  font-weight: 600;
}

input[type="text"],
input[type="number"] {
  width: 100%;
  max-width: 400px;
  padding: 0.5rem;
  border: 1px solid #ccc;
  border-radius: 4px;
}

.form-actions {
  margin-top: 1rem;
}

.form-actions button {
  padding: 0.5rem 1.2rem;
}

.error {
  color: #e74c3c;
  margin-top: 0.5rem;
  font-weight: 600;
}
```

### client/src/App.jsx
```jsx
import { useState, useEffect } from 'react';

const API = '/api/books';

function App() {
  const [books, setBooks] = useState([]);
  const [editing, setEditing] = useState(null);   // book being edited, or null
  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState('');
  const [author, setAuthor] = useState('');
  const [year, setYear] = useState('');
  const [read, setRead] = useState(false);
  const [error, setError] = useState('');

  // Fetch all books
  const fetchBooks = async () => {
    const res = await fetch(API);
    const data = await res.json();
    setBooks(data);
  };

  useEffect(() => {
    fetchBooks();
  }, []);

  // Open form for creating a new book
  const openCreate = () => {
    setTitle('');
    setAuthor('');
    setYear('');
    setRead(false);
    setEditing(null);
    setShowForm(true);
    setError('');
  };

  // Open form for editing
  const openEdit = (book) => {
    setTitle(book.title);
    setAuthor(book.author);
    setYear(book.year != null ? String(book.year) : '');
    setRead(!!book.read);
    setEditing(book);
    setShowForm(true);
    setError('');
  };

  // Close form
  const closeForm = () => {
    setShowForm(false);
    setEditing(null);
    setError('');
  };

  // Submit (create or update)
  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    const body = {
      title,
      author,
      year: year !== '' ? parseInt(year, 10) : null,
      read,
    };

    const url = editing ? `${API}/${editing.id}` : API;
    const method = editing ? 'PUT' : 'POST';

    const res = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    if (!res.ok) {
      const err = await res.json();
      setError(err.error || 'An error occurred');
      return;
    }

    await fetchBooks();
    closeForm();
  };

  // Toggle read
  const toggleRead = async (book) => {
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
    if (res.ok) fetchBooks();
  };

  // Delete
  const handleDelete = async (book) => {
    if (!window.confirm(`Delete "${book.title}"?`)) return;
    const res = await fetch(`${API}/${book.id}`, { method: 'DELETE' });
    if (res.ok) fetchBooks();
  };

  return (
    <div>
      <h1>📚 Books</h1>
      <button onClick={openCreate}>+ Add Book</button>

      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Title</th>
            <th>Author</th>
            <th>Year</th>
            <th>Read</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {books.map((book) => (
            <tr key={book.id}>
              <td>{book.id}</td>
              <td>{book.title}</td>
              <td>{book.author}</td>
              <td>{book.year ?? '—'}</td>
              <td>{book.read ? '✅' : '📖'}</td>
              <td>
                <button
                  className={`toggle ${book.read ? 'is-read' : ''}`}
                  onClick={() => toggleRead(book)}
                >
                  {book.read ? 'Unread' : 'Read'}
                </button>
                <button className="edit" onClick={() => openEdit(book)}>
                  Edit
                </button>
                <button className="delete" onClick={() => handleDelete(book)}>
                  Delete
                </button>
              </td>
            </tr>
          ))}
          {books.length === 0 && (
            <tr>
              <td colSpan="6" style={{ textAlign: 'center', color: '#999' }}>
                No books yet. Add one!
              </td>
            </tr>
          )}
        </tbody>
      </table>

      {showForm && (
        <form onSubmit={handleSubmit}>
          <h2>{editing ? `Edit Book #${editing.id}` : 'Add Book'}</h2>

          <label>
            <span>Title *</span>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
            />
          </label>

          <label>
            <span>Author *</span>
            <input
              type="text"
              value={author}
              onChange={(e) => setAuthor(e.target.value)}
              required
            />
          </label>

          <label>
            <span>Year</span>
            <input
              type="number"
              value={year}
              onChange={(e) => setYear(e.target.value)}
            />
          </label>

          <label>
            <input
              type="checkbox"
              checked={read}
              onChange={(e) => setRead(e.target.checked)}
            />{' '}
            Read
          </label>

          {error && <p className="error">{error}</p>}

          <div className="form-actions">
            <button type="submit">{editing ? 'Update' : 'Create'}</button>
            <button type="button" onClick={closeForm}>Cancel</button>
          </div>
        </form>
      )}
    </div>
  );
}

export default App;
```