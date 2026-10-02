

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
  "dependencies": {
    "better-sqlite3": "^11.10.0",
    "express": "^4.21.0"
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

// --- Database setup ---
const db = new Database(path.join(__dirname, "data.db"));
db.exec(`
  CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    read BOOLEAN NOT NULL DEFAULT 0
  )
`);

app.use(express.json());

// --- Validation helper ---
function validate(body) {
  const title = (body.title || "").trim();
  const author = (body.author || "").trim();
  if (!title || !author) return null;
  return { title, author };
}

// --- GET /api/books ---
app.get("/api/books", (req, res) => {
  const rows = db.prepare("SELECT id, title, author, year, read FROM books ORDER BY id").all();
  res.json(rows.map(r => ({ ...r, read: !!r.read })));
});

// --- GET /api/books/:id ---
app.get("/api/books/:id", (req, res) => {
  const row = db.prepare("SELECT id, title, author, year, read FROM books WHERE id = ?").get(req.params.id);
  if (!row) return res.status(404).json({ error: "Book not found" });
  res.json({ ...row, read: !!row.read });
});

// --- POST /api/books ---
app.post("/api/books", (req, res) => {
  const valid = validate(req.body);
  if (!valid) return res.status(400).json({ error: "title and author are required" });

  const year = req.body.year !== undefined && req.body.year !== null && req.body.year !== ""
    ? parseInt(req.body.year, 10)
    : null;
  const read = !!req.body.read;

  const info = db.prepare(
    "INSERT INTO books (title, author, year, read) VALUES (?, ?, ?, ?)"
  ).run(valid.title, valid.author, year, read);

  const created = db.prepare("SELECT id, title, author, year, read FROM books WHERE id = ?").get(info.lastInsertRowid);
  res.status(201).json({ ...created, read: !!created.read });
});

// --- PUT /api/books/:id ---
app.put("/api/books/:id", (req, res) => {
  const existing = db.prepare("SELECT id FROM books WHERE id = ?").get(req.params.id);
  if (!existing) return res.status(404).json({ error: "Book not found" });

  const valid = validate(req.body);
  if (!valid) return res.status(400).json({ error: "title and author are required" });

  const year = req.body.year !== undefined && req.body.year !== null && req.body.year !== ""
    ? parseInt(req.body.year, 10)
    : null;
  const read = !!req.body.read;

  db.prepare(
    "UPDATE books SET title = ?, author = ?, year = ?, read = ? WHERE id = ?"
  ).run(valid.title, valid.author, year, read, req.params.id);

  const updated = db.prepare("SELECT id, title, author, year, read FROM books WHERE id = ?").get(req.params.id);
  res.json({ ...updated, read: !!updated.read });
});

// --- DELETE /api/books/:id ---
app.delete("/api/books/:id", (req, res) => {
  const info = db.prepare("DELETE FROM books WHERE id = ?").run(req.params.id);
  if (info.changes === 0) return res.status(404).json({ error: "Book not found" });
  res.status(204).end();
});

app.listen(PORT, () => {
  console.log(`Books API listening on port ${PORT}`);
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
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Books Manager</title>
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
import ReactDOM from "react-dom/client";
import App from "./App.jsx";
import "./App.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

### client/src/App.jsx
```jsx
import { useState, useEffect, useCallback } from "react";

export default function App() {
  const [books, setBooks] = useState([]);
  const [editingId, setEditingId] = useState(null);
  const [form, setForm] = useState({ title: "", author: "", year: "", read: false });
  const [error, setError] = useState("");

  const fetchBooks = useCallback(async () => {
    const res = await fetch("/api/books");
    const data = await res.json();
    setBooks(data);
  }, []);

  useEffect(() => {
    fetchBooks();
  }, [fetchBooks]);

  const resetForm = () => {
    setForm({ title: "", author: "", year: "", read: false });
    setEditingId(null);
    setError("");
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const payload = {
      title: form.title.trim(),
      author: form.author.trim(),
      year: form.year === "" ? null : parseInt(form.year, 10),
      read: form.read,
    };

    try {
      if (editingId) {
        await fetch(`/api/books/${editingId}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
      } else {
        await fetch("/api/books", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
      }
      resetForm();
      fetchBooks();
    } catch (err) {
      setError("Failed to save book");
    }
  };

  const handleEdit = (book) => {
    setEditingId(book.id);
    setForm({
      title: book.title,
      author: book.author,
      year: book.year ?? "",
      read: book.read,
    });
    setError("");
  };

  const handleDelete = async (id) => {
    await fetch(`/api/books/${id}`, { method: "DELETE" });
    if (editingId === id) resetForm();
    fetchBooks();
  };

  const handleToggleRead = async (book) => {
    const payload = {
      title: book.title,
      author: book.author,
      year: book.year,
      read: !book.read,
    };
    await fetch(`/api/books/${book.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    fetchBooks();
  };

  return (
    <div className="container">
      <h1>📚 Books Manager</h1>

      {error && <p className="error">{error}</p>}

      <form onSubmit={handleSubmit} className="form">
        <h2>{editingId ? "Edit Book" : "Add a Book"}</h2>
        <div className="form-row">
          <input
            type="text"
            placeholder="Title *"
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
            required
          />
          <input
            type="text"
            placeholder="Author *"
            value={form.author}
            onChange={(e) => setForm({ ...form, author: e.target.value })}
            required
          />
          <input
            type="number"
            placeholder="Year (optional)"
            value={form.year}
            onChange={(e) => setForm({ ...form, year: e.target.value })}
          />
          <label className="read-label">
            <input
              type="checkbox"
              checked={form.read}
              onChange={(e) => setForm({ ...form, read: e.target.checked })}
            />
            Read
          </label>
          <button type="submit">{editingId ? "Update" : "Add"}</button>
          {editingId && (
            <button type="button" onClick={resetForm} className="cancel-btn">
              Cancel
            </button>
          )}
        </div>
      </form>

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
            <tr key={book.id} className={book.read ? "read-row" : ""}>
              <td>{book.id}</td>
              <td>{book.title}</td>
              <td>{book.author}</td>
              <td>{book.year ?? "—"}</td>
              <td>
                <input
                  type="checkbox"
                  checked={book.read}
                  onChange={() => handleToggleRead(book)}
                />
              </td>
              <td>
                <button onClick={() => handleEdit(book)} className="edit-btn">
                  Edit
                </button>
                <button onClick={() => handleDelete(book.id)} className="delete-btn">
                  Delete
                </button>
              </td>
            </tr>
          ))}
          {books.length === 0 && (
            <tr>
              <td colSpan={6} className="empty">No books yet. Add one above!</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
```

### client/src/App.css
```css
* {
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  margin: 0;
  background: #f5f5f5;
  color: #222;
}

.container {
  max-width: 860px;
  margin: 2rem auto;
  padding: 0 1rem;
}

h1 {
  text-align: center;
}

.error {
  color: #c0392b;
  text-align: center;
}

.form {
  background: #fff;
  border-radius: 8px;
  padding: 1rem;
  margin-bottom: 1.5rem;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.1);
}

.form h2 {
  margin-top: 0;
  font-size: 1.1rem;
}

.form-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
}

.form-row input[type="text"],
.form-row input[type="number"] {
  padding: 0.5rem;
  border: 1px solid #ccc;
  border-radius: 4px;
  flex: 1;
  min-width: 120px;
}

.read-label {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.9rem;
}

button {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
}

.form button[type="submit"] {
  background: #2980b9;
  color: #fff;
}

.cancel-btn {
  background: #95a5a6;
  color: #fff;
}

table {
  width: 100%;
  border-collapse: collapse;
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.1);
}

th,
td {
  padding: 0.6rem 0.8rem;
  text-align: left;
  border-bottom: 1px solid #eee;
}

th {
  background: #34495e;
  color: #fff;
  font-weight: 600;
}

.read-row td {
  background: #eafaf1;
}

.empty {
  text-align: center;
  color: #888;
  padding: 1.5rem;
}

.edit-btn {
  background: #f39c12;
  color: #fff;
  margin-right: 0.4rem;
  padding: 0.3rem 0.7rem;
}

.delete-btn {
  background: #e74c3c;
  color: #fff;
  padding: 0.3rem 0.7rem;
}
```

### README.md
```markdown
# Books CRUD App

A small full-stack app to manage a list of books (title, author, year, read status).

## Prerequisites

- Node.js 26

## Running the API (server/)

```bash
cd server
npm install
npm start
```

The API listens on `http://localhost:3001` (override with the `PORT` env var).
SQLite database is stored at `server/data.db` (created automatically).

## Running the UI (client/)

```bash
cd client
npm install
npm run dev
```

Open `http://localhost:5173` in your browser. The Vite dev server proxies all
`/api/*` requests to `http://localhost:3001`.

## Production build

```bash
cd client
npm run build
```

Outputs static files to `client/dist/`.
```