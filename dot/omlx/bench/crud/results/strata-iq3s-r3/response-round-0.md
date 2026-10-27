### README.md
```markdown
# Books CRUD App

A small full-stack CRUD application managing a `books` table in SQLite.

## Run the backend

```bash
cd server
npm install
npm start
```

The API listens on `http://localhost:3001` (override with `PORT` env var).

## Run the frontend (dev)

```bash
cd client
npm install
npm run dev
```

Vite dev server proxies `/api` to `http://localhost:3001`.

## Build the frontend

```bash
cd client
npm run build
```
```

### server/package.json
```json
{
  "name": "books-server",
  "version": "1.0.0",
  "type": "module",
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
import express from "express";
import { DatabaseSync } from "node:sqlite";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const dbPath = path.join(__dirname, "data.db");

const db = new DatabaseSync(dbPath);

db.exec(`
  CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    read INTEGER DEFAULT 0
  )
`);

const app = express();
app.use(express.json());

// GET all books
app.get("/api/books", (req, res) => {
  const rows = db.prepare("SELECT * FROM books ORDER BY id").all();
  res.json(rows.map(mapRow));
});

// GET one book
app.get("/api/books/:id", (req, res) => {
  const row = db.prepare("SELECT * FROM books WHERE id = ?").get(Number(req.params.id));
  if (!row) return res.status(404).json({ error: "Book not found" });
  res.json(mapRow(row));
});

// POST create book
app.post("/api/books", (req, res) => {
  const { title, author, year, read } = req.body;
  if (!title || !title.trim()) {
    return res.status(400).json({ error: "title is required" });
  }
  if (!author || !author.trim()) {
    return res.status(400).json({ error: "author is required" });
  }
  const info = db
    .prepare("INSERT INTO books (title, author, year, read) VALUES (?, ?, ?, ?)")
    .run(title.trim(), author.trim(), year ?? null, read ? 1 : 0);
  const row = db.prepare("SELECT * FROM books WHERE id = ?").get(info.lastInsertRowid);
  res.status(201).json(mapRow(row));
});

// PUT update book
app.put("/api/books/:id", (req, res) => {
  const id = Number(req.params.id);
  const existing = db.prepare("SELECT * FROM books WHERE id = ?").get(id);
  if (!existing) return res.status(404).json({ error: "Book not found" });

  const { title, author, year, read } = req.body;
  if (title === undefined || title === null || !title.trim()) {
    return res.status(400).json({ error: "title is required" });
  }
  if (author === undefined || author === null || !author.trim()) {
    return res.status(400).json({ error: "author is required" });
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

// DELETE book
app.delete("/api/books/:id", (req, res) => {
  const id = Number(req.params.id);
  const existing = db.prepare("SELECT * FROM books WHERE id = ?").get(id);
  if (!existing) return res.status(404).json({ error: "Book not found" });
  db.prepare("DELETE FROM books WHERE id = ?").run(id);
  res.json({ ok: true });
});

function mapRow(row) {
  return {
    id: row.id,
    title: row.title,
    author: row.author,
    year: row.year,
    read: Boolean(row.read),
  };
}

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
  console.log(`API listening on http://localhost:${PORT}`);
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
    "vite": "^6.0.0"
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
      "/api": {
        target: "http://localhost:3001",
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
import ReactDOM from "react-dom/client";
import App from "./App.jsx";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

### client/src/index.css
```css
* {
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  margin: 0;
  padding: 2rem;
  background: #f5f5f5;
  color: #222;
}

h1 {
  margin-bottom: 1rem;
}

table {
  width: 100%;
  border-collapse: collapse;
  background: #fff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  margin-bottom: 2rem;
}

th, td {
  padding: 0.6rem 0.8rem;
  text-align: left;
  border-bottom: 1px solid #ddd;
}

th {
  background: #333;
  color: #fff;
}

tr:hover {
  background: #f0f0f0;
}

button {
  padding: 0.35rem 0.7rem;
  margin: 0 0.15rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.85rem;
}

.btn-edit {
  background: #2563eb;
  color: #fff;
}

.btn-delete {
  background: #dc2626;
  color: #fff;
}

.btn-toggle {
  background: #16a34a;
  color: #fff;
}

.btn-submit {
  background: #2563eb;
  color: #fff;
  padding: 0.5rem 1.2rem;
}

.btn-cancel {
  background: #6b7280;
  color: #fff;
  padding: 0.5rem 1.2rem;
}

form {
  background: #fff;
  padding: 1.5rem;
  border-radius: 6px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  max-width: 500px;
}

form h2 {
  margin-top: 0;
}

label {
  display: block;
  margin-bottom: 0.75rem;
}

label span {
  display: block;
  font-weight: 600;
  margin-bottom: 0.25rem;
}

input[type="text"],
input[type="number"] {
  width: 100%;
  padding: 0.4rem 0.6rem;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 0.95rem;
}

.error {
  color: #dc2626;
  margin-bottom: 0.75rem;
  font-weight: 600;
}

.read-yes {
  color: #16a34a;
  font-weight: bold;
}

.read-no {
  color: #999;
}
```

### client/src/App.jsx
```jsx
import { useState, useEffect } from "react";

const emptyForm = { title: "", author: "", year: "", read: false };

export default function App() {
  const [books, setBooks] = useState([]);
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchBooks();
  }, []);

  async function fetchBooks() {
    const res = await fetch("/api/books");
    const data = await res.json();
    setBooks(data);
  }

  function handleChange(e) {
    const { name, value, type, checked } = e.target;
    setForm((f) => ({ ...f, [name]: type === "checkbox" ? checked : value }));
  }

  function startEdit(book) {
    setEditingId(book.id);
    setForm({
      title: book.title,
      author: book.author,
      year: book.year ?? "",
      read: book.read,
    });
    setError("");
  }

  function cancelEdit() {
    setEditingId(null);
    setForm(emptyForm);
    setError("");
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");

    const payload = {
      title: form.title,
      author: form.author,
      year: form.year === "" ? null : Number(form.year),
      read: form.read,
    };

    const url = editingId ? `/api/books/${editingId}` : "/api/books";
    const method = editingId ? "PUT" : "POST";

    const res = await fetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const data = await res.json();
      setError(data.error || "Request failed");
      return;
    }

    setEditingId(null);
    setForm(emptyForm);
    fetchBooks();
  }

  async function handleDelete(id) {
    await fetch(`/api/books/${id}`, { method: "DELETE" });
    fetchBooks();
  }

  async function handleToggleRead(book) {
    await fetch(`/api/books/${book.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: book.title,
        author: book.author,
        year: book.year,
        read: !book.read,
      }),
    });
    fetchBooks();
  }

  return (
    <div>
      <h1>Books</h1>

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
              <td>{book.year ?? "—"}</td>
              <td className={book.read ? "read-yes" : "read-no"}>
                {book.read ? "Yes" : "No"}
              </td>
              <td>
                <button className="btn-toggle" onClick={() => handleToggleRead(book)}>
                  {book.read ? "Unread" : "Read"}
                </button>
                <button className="btn-edit" onClick={() => startEdit(book)}>
                  Edit
                </button>
                <button className="btn-delete" onClick={() => handleDelete(book.id)}>
                  Delete
                </button>
              </td>
            </tr>
          ))}
          {books.length === 0 && (
            <tr>
              <td colSpan={6}>No books yet.</td>
            </tr>
          )}
        </tbody>
      </table>

      <form onSubmit={handleSubmit}>
        <h2>{editingId ? "Edit Book" : "Add Book"}</h2>
        {error && <p className="error">{error}</p>}

        <label>
          <span>Title *</span>
          <input type="text" name="title" value={form.title} onChange={handleChange} required />
        </label>

        <label>
          <span>Author *</span>
          <input type="text" name="author" value={form.author} onChange={handleChange} required />
        </label>

        <label>
          <span>Year</span>
          <input type="number" name="year" value={form.year} onChange={handleChange} />
        </label>

        <label>
          <input type="checkbox" name="read" checked={form.read} onChange={handleChange} /> Read
        </label>

        <button type="submit" className="btn-submit">
          {editingId ? "Update" : "Create"}
        </button>
        {editingId && (
          <button type="button" className="btn-cancel" onClick={cancelEdit}>
            Cancel
          </button>
        )}
      </form>
    </div>
  );
}
```