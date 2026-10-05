

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
    "express": "^4.21.2",
    "better-sqlite3": "^11.7.0"
  }
}
```

### server/index.js
```js
const express = require("express");
const Database = require("better-sqlite3");
const path = require("path");

const app = express();
const PORT = process.env.PORT || 3001;

const db = new Database(path.join(__dirname, "data.db"));

db.pragma("journal_mode = WAL");

db.exec(`
  CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    read INTEGER DEFAULT 0
  )
`);

// ---------- GET all books ----------
app.get("/api/books", (req, res) => {
  const rows = db.prepare("SELECT * FROM books ORDER BY id").all();
  res.json(rows.map(mapRow));
});

// ---------- GET one book ----------
app.get("/api/books/:id", (req, res) => {
  const row = db.prepare("SELECT * FROM books WHERE id = ?").get(Number(req.params.id));
  if (!row) return res.status(404).json({ error: "Book not found" });
  res.json(mapRow(row));
});

// ---------- CREATE ----------
app.post("/api/books", (req, res) => {
  const { title, author, year, read } = req.body || {};

  if (!title || !author) {
    return res.status(400).json({ error: "title and author are required" });
  }

  const info = db
    .prepare("INSERT INTO books (title, author, year, read) VALUES (?, ?, ?, ?)")
    .run(title.trim(), author.trim(), year ?? null, read ? 1 : 0);

  const row = db.prepare("SELECT * FROM books WHERE id = ?").get(info.lastInsertRowid);
  res.status(201).json(mapRow(row));
});

// ---------- UPDATE ----------
app.put("/api/books/:id", (req, res) => {
  const id = Number(req.params.id);
  const existing = db.prepare("SELECT * FROM books WHERE id = ?").get(id);
  if (!existing) return res.status(404).json({ error: "Book not found" });

  const { title, author, year, read } = req.body || {};

  if (!title || !author) {
    return res.status(400).json({ error: "title and author are required" });
  }

  db.prepare("UPDATE books SET title = ?, author = ?, year = ?, read = ? WHERE id = ?").run(
    title.trim(),
    author.trim(),
    year ?? null,
    read ? 1 : 0,
    id
  );

  const row = db.prepare("SELECT * FROM books WHERE id = ?").get(id);
  res.json(mapRow(row));
});

// ---------- DELETE ----------
app.delete("/api/books/:id", (req, res) => {
  const id = Number(req.params.id);
  const existing = db.prepare("SELECT * FROM books WHERE id = ?").get(id);
  if (!existing) return res.status(404).json({ error: "Book not found" });

  db.prepare("DELETE FROM books WHERE id = ?").run(id);
  res.json({ ok: true });
});

// ---------- helpers ----------
function mapRow(row) {
  return { ...row, read: Boolean(row.read) };
}

app.listen(PORT, () => {
  console.log(`Books API listening on http://localhost:${PORT}`);
});
```

### client/package.json
```json
{
  "name": "books-client",
  "private": true,
  "version": "1.0.0",
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
    "vite": "^6.2.0"
  }
}
```

### client/vite.config.js
```js
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://localhost:3001",
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
import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import "./index.css";

createRoot(document.getElementById("root")).render(<App />);
```

### client/src/index.css
```css
* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
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
  margin-bottom: 2rem;
}

th, td {
  padding: 0.75rem 1rem;
  text-align: left;
  border-bottom: 1px solid #eee;
}

th {
  background: #4a90d9;
  color: #fff;
}

tr:last-child td {
  border-bottom: none;
}

button {
  padding: 0.35rem 0.75rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.85rem;
  margin-right: 0.4rem;
}

button.edit {
  background: #f0ad4e;
  color: #fff;
}

button.delete {
  background: #d9534f;
  color: #fff;
}

button.toggle {
  background: #5cb85c;
  color: #fff;
}

button:hover {
  opacity: 0.85;
}

.form-card {
  background: #fff;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  margin-bottom: 2rem;
  max-width: 500px;
}

.form-card h2 {
  margin-bottom: 1rem;
}

.form-card label {
  display: block;
  margin-bottom: 0.75rem;
}

.form-card input {
  width: 100%;
  padding: 0.4rem 0.6rem;
  margin-top: 0.25rem;
  border: 1px solid #ccc;
  border-radius: 4px;
}

.form-card .actions {
  margin-top: 1rem;
}

.form-card .actions button {
  padding: 0.5rem 1rem;
}

.error {
  color: #d9534f;
  margin-top: 0.5rem;
}
```

### client/src/App.jsx
```jsx
import { useState, useEffect } from "react";

const API = "/api/books";

function App() {
  const [books, setBooks] = useState([]);
  const [form, setForm] = useState({ title: "", author: "", year: "", read: false });
  const [editingId, setEditingId] = useState(null);
  const [error, setError] = useState("");

  // ---------- fetch ----------
  async function fetchBooks() {
    const res = await fetch(API);
    setBooks(await res.json());
  }

  useEffect(() => {
    fetchBooks();
  }, []);

  // ---------- form ----------
  function handleInput(e) {
    const { name, value, type, checked } = e.target;
    setForm((f) => ({ ...f, [name]: type === "checkbox" ? checked : value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    const payload = {
      title: form.title,
      author: form.author,
      year: form.year ? Number(form.year) : null,
      read: form.read,
    };

    const url = editingId ? `${API}/${editingId}` : API;
    const res = await fetch(url, {
      method: editingId ? "PUT" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const data = await res.json();
      setError(data.error || "Request failed");
      return;
    }

    setForm({ title: "", author: "", year: "", read: false });
    setEditingId(null);
    fetchBooks();
  }

  function startEdit(book) {
    setEditingId(book.id);
    setForm({
      title: book.title,
      author: book.author,
      year: book.year != null ? String(book.year) : "",
      read: book.read,
    });
    setError("");
  }

  function cancelEdit() {
    setEditingId(null);
    setForm({ title: "", author: "", year: "", read: false });
    setError("");
  }

  async function handleToggleRead(book) {
    const res = await fetch(`${API}/${book.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: book.title,
        author: book.author,
        year: book.year,
        read: !book.read,
      }),
    });
    if (res.ok) fetchBooks();
  }

  async function handleDelete(id) {
    if (!window.confirm("Delete this book?")) return;
    await fetch(`${API}/${id}`, { method: "DELETE" });
    fetchBooks();
  }

  // ---------- render ----------
  return (
    <div>
      <h1>📚 Book Collection</h1>

      {/* Create / Edit form */}
      <div className="form-card">
        <h2>{editingId ? "Edit Book" : "Add Book"}</h2>
        <form onSubmit={handleSubmit}>
          <label>
            Title
            <input
              name="title"
              value={form.title}
              onChange={handleInput}
              required
            />
          </label>
          <label>
            Author
            <input
              name="author"
              value={form.author}
              onChange={handleInput}
              required
            />
          </label>
          <label>
            Year
            <input
              name="year"
              type="number"
              value={form.year}
              onChange={handleInput}
            />
          </label>
          <label>
            <input
              name="read"
              type="checkbox"
              checked={form.read}
              onChange={handleInput}
            />{" "}
            Read
          </label>

          {error && <p className="error">{error}</p>}

          <div className="actions">
            <button type="submit">{editingId ? "Update" : "Add"}</button>
            {editingId && (
              <button type="button" onClick={cancelEdit}>
                Cancel
              </button>
            )}
          </div>
        </form>
      </div>

      {/* Books table */}
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
          {books.length === 0 && (
            <tr>
              <td colSpan={6}>No books yet. Add one above!</td>
            </tr>
          )}
          {books.map((book) => (
            <tr key={book.id}>
              <td>{book.id}</td>
              <td>{book.title}</td>
              <td>{book.author}</td>
              <td>{book.year ?? "—"}</td>
              <td>{book.read ? "✅" : "⬜"}</td>
              <td>
                <button className="toggle" onClick={() => handleToggleRead(book)}>
                  Toggle Read
                </button>
                <button className="edit" onClick={() => startEdit(book)}>
                  Edit
                </button>
                <button className="delete" onClick={() => handleDelete(book.id)}>
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

export default App;
```

### README.md
```markdown
# Book Collection – Full-Stack CRUD

A small CRUD app for managing a `books` table.

## Prerequisites

- Node.js ≥ 20 (tested against Node.js 26)
- npm ≥ 10

## Run the backend (API)

```bash
cd server
npm install
npm start
```

The API listens on `http://localhost:3001` (override with `PORT=… npm start`).
SQLite data is persisted in `server/data.db`.

## Run the frontend (UI)

In a second terminal:

```bash
cd client
npm install
npm run dev
```

Vite dev server proxies `/api/*` → `http://localhost:3001`.
Open **http://localhost:5173** in your browser.

## Production build

```bash
cd client
npm run build
npm run preview   # serves dist/ on http://localhost:4173
```

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/books | List all books |
| GET | /api/books/:id | Get one book (404 if not found) |
| POST | /api/books | Create (400 if title/author missing) |
| PUT | /api/books/:id | Update (400 if title/author missing) |
| DELETE | /api/books/:id | Delete (404 if not found) |
```