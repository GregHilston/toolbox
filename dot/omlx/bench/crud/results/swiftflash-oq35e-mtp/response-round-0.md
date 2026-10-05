

### README.md
```markdown
# Books CRUD App

A simple full-stack CRUD application for managing a `books` table.

## Structure

- `server/` – Node.js + Express + SQLite (better-sqlite3) REST API
- `client/` – React + Vite single-page UI

## Run the API

```bash
cd server
npm install
npm start
```

The API listens on `http://localhost:3001` (override with `PORT`).

## Run the UI (dev)

```bash
cd client
npm install
npm run dev
```

Vite dev server (http://localhost:5173) proxies `/api` → `:3001`.

## Build the UI

```bash
cd client
npm run build
```

Static output lands in `client/dist/`.
```

### server/package.json
```json
{
  "name": "books-api",
  "version": "1.0.0",
  "private": true,
  "type": "module",
  "scripts": {
    "start": "node index.js"
  },
  "dependencies": {
    "express": "^4.21.2",
    "better-sqlite3": "^12.2.0"
  }
}
```

### server/index.js
```js
import express from "express";
import Database from "better-sqlite3";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DB_PATH = path.join(__dirname, "data.db");

const db = new Database(DB_PATH);

db.pragma("journal_mode = WAL");

db.exec(`
  CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT    NOT NULL,
    author TEXT    NOT NULL,
    year   INTEGER,
    "read" BOOLEAN NOT NULL DEFAULT 0
  );
`);

const app = express();
app.use(express.json());

/* ---------- GET all ---------- */
app.get("/api/books", (req, res) => {
  const rows = db.prepare("SELECT * FROM books ORDER BY id").all();
  res.json(rows);
});

/* ---------- GET one ---------- */
app.get("/api/books/:id", (req, res) => {
  const id = Number(req.params.id);
  const row = db.prepare("SELECT * FROM books WHERE id = ?").get(id);
  if (!row) return res.status(404).json({ error: "Book not found" });
  res.json(row);
});

/* ---------- POST ---------- */
app.post("/api/books", (req, res) => {
  const { title, author, year, read } = req.body ?? {};

  if (!title || String(title).trim() === "") {
    return res.status(400).json({ error: "title is required" });
  }
  if (!author || String(author).trim() === "") {
    return res.status(400).json({ error: "author is required" });
  }

  const info = db
    .prepare(
      `INSERT INTO books (title, author, year, "read") VALUES (?, ?, ?, ?)`
    )
    .run(String(title).trim(), String(author).trim(), year ?? null, read ? 1 : 0);

  const row = db
    .prepare("SELECT * FROM books WHERE id = ?")
    .get(info.lastInsertRowid);
  res.status(201).json(row);
});

/* ---------- PUT ---------- */
app.put("/api/books/:id", (req, res) => {
  const id = Number(req.params.id);
  const existing = db.prepare("SELECT * FROM books WHERE id = ?").get(id);
  if (!existing) return res.status(404).json({ error: "Book not found" });

  const { title, author, year, read } = req.body ?? {};

  if (title !== undefined && (!title || String(title).trim() === "")) {
    return res.status(400).json({ error: "title cannot be empty" });
  }
  if (author !== undefined && (!author || String(author).trim() === "")) {
    return res.status(400).json({ error: "author cannot be empty" });
  }

  db.prepare(
    `UPDATE books SET title = ?, author = ?, year = ?, "read" = ? WHERE id = ?`
  ).run(
    title !== undefined ? String(title).trim() : existing.title,
    author !== undefined ? String(author).trim() : existing.author,
    year !== undefined ? year : existing.year,
    read !== undefined ? (read ? 1 : 0) : existing.read,
    id
  );

  const row = db.prepare("SELECT * FROM books WHERE id = ?").get(id);
  res.json(row);
});

/* ---------- DELETE ---------- */
app.delete("/api/books/:id", (req, res) => {
  const id = Number(req.params.id);
  const existing = db.prepare("SELECT * FROM books WHERE id = ?").get(id);
  if (!existing) return res.status(404).json({ error: "Book not found" });

  db.prepare("DELETE FROM books WHERE id = ?").run(id);
  res.json({ ok: true });
});

/* ---------- start ---------- */
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

const emptyForm = { title: "", author: "", year: "", read: false };

export default function App() {
  const [books, setBooks] = useState([]);
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState(null); // null = create mode
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  /* --- data fetching --- */
  const fetchBooks = useCallback(async () => {
    try {
      const res = await fetch("/api/books");
      if (!res.ok) throw new Error("Failed to fetch");
      setBooks(await res.json());
      setError("");
    } catch (e) {
      setError(e.message);
    }
  }, []);

  useEffect(() => {
    fetchBooks();
  }, [fetchBooks]);

  /* --- form helpers --- */
  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setForm((f) => ({ ...f, [name]: type === "checkbox" ? checked : value }));
  };

  const startEdit = (book) => {
    setEditingId(book.id);
    setForm({
      title: book.title,
      author: book.author,
      year: book.year != null ? String(book.year) : "",
      read: !!book.read,
    });
  };

  const cancelEdit = () => {
    setEditingId(null);
    setForm(emptyForm);
  };

  /* --- submit (create / update) --- */
  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const payload = {
        title: form.title.trim(),
        author: form.author.trim(),
        year: form.year ? Number(form.year) : null,
        read: form.read,
      };
      const url =
        editingId != null ? `/api/books/${editingId}` : "/api/books";
      const method = editingId != null ? "PUT" : "POST";
      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const body = await res.json();
        alert(body.error || "Request failed");
        return;
      }
      await fetchBooks();
      cancelEdit();
    } catch (e) {
      alert(e.message);
    } finally {
      setLoading(false);
    }
  };

  /* --- toggle read --- */
  const toggleRead = async (book) => {
    try {
      const res = await fetch(`/api/books/${book.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ read: !book.read }),
      });
      if (res.ok) await fetchBooks();
    } catch (_) {}
  };

  /* --- delete --- */
  const handleDelete = async (id) => {
    if (!confirm("Delete this book?")) return;
    try {
      const res = await fetch(`/api/books/${id}`, { method: "DELETE" });
      if (res.ok) await fetchBooks();
    } catch (_) {}
  };

  return (
    <div className="container">
      <h1>📚 Books</h1>
      {error && <p className="error">{error}</p>}

      {/* ---- form ---- */}
      <form onSubmit={handleSubmit} className="book-form">
        <h2>{editingId != null ? "Edit Book" : "Add Book"}</h2>
        <div className="form-row">
          <label>
            Title <span className="req">*</span>
            <input
              name="title"
              value={form.title}
              onChange={handleChange}
              required
            />
          </label>
          <label>
            Author <span className="req">*</span>
            <input
              name="author"
              value={form.author}
              onChange={handleChange}
              required
            />
          </label>
        </div>
        <div className="form-row">
          <label>
            Year
            <input
              name="year"
              type="number"
              value={form.year}
              onChange={handleChange}
            />
          </label>
          <label className="check-label">
            <input
              type="checkbox"
              name="read"
              checked={form.read}
              onChange={handleChange}
            />{" "}
            Read
          </label>
        </div>
        <div className="form-actions">
          <button type="submit" disabled={loading}>
            {editingId != null ? "Update" : "Create"}
          </button>
          {editingId != null && (
            <button type="button" onClick={cancelEdit}>
              Cancel
            </button>
          )}
        </div>
      </form>

      {/* ---- table ---- */}
      <table className="book-table">
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
              <td colSpan={6} className="empty">
                No books yet — add one above!
              </td>
            </tr>
          )}
          {books.map((b) => (
            <tr key={b.id} className={b.read ? "read-row" : ""}>
              <td>{b.id}</td>
              <td>{b.title}</td>
              <td>{b.author}</td>
              <td>{b.year ?? "—"}</td>
              <td>
                <button
                  className="toggle-btn"
                  onClick={() => toggleRead(b)}
                  title="Toggle read"
                >
                  {b.read ? "✔" : "☐"}
                </button>
              </td>
              <td>
                <button className="edit-btn" onClick={() => startEdit(b)}>
                  Edit
                </button>{" "}
                <button
                  className="delete-btn"
                  onClick={() => handleDelete(b.id)}
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

### client/src/App.css
```css
* {
  box-sizing: border-box;
}

body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  background: #f5f5f5;
  color: #333;
}

.container {
  max-width: 900px;
  margin: 2rem auto;
  padding: 0 1rem;
}

h1 {
  margin-bottom: 1rem;
}

.error {
  color: #c0392b;
  font-weight: 600;
}

/* ---- form ---- */
.book-form {
  background: #fff;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 1.25rem 1.5rem;
  margin-bottom: 1.5rem;
}

.book-form h2 {
  margin-top: 0;
  font-size: 1.1rem;
}

.form-row {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
  margin-bottom: 0.75rem;
}

.form-row label {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  flex: 1;
  min-width: 140px;
  font-size: 0.9rem;
}

.check-label {
  flex-direction: row !important;
  align-items: center;
  gap: 0.4rem !important;
}

.req {
  color: #c0392b;
}

.form-actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

.form-actions button {
  padding: 0.4rem 1rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
}

.form-actions button[type="submit"] {
  background: #2980b9;
  color: #fff;
}

.form-actions button[type="submit"]:disabled {
  opacity: 0.6;
  cursor: default;
}

.form-actions button[type="button"] {
  background: #ecf0f1;
}

/* ---- table ---- */
.book-table {
  width: 100%;
  border-collapse: collapse;
  background: #fff;
  border: 1px solid #ddd;
  border-radius: 8px;
  overflow: hidden;
}

.book-table th,
.book-table td {
  padding: 0.6rem 0.75rem;
  text-align: left;
  border-bottom: 1px solid #eee;
}

.book-table th {
  background: #2c3e50;
  color: #fff;
  font-weight: 600;
}

.book-table tbody tr:hover {
  background: #f9f9f9;
}

.read-row {
  opacity: 0.55;
}

.empty {
  text-align: center !important;
  padding: 1.5rem !important;
  color: #999;
}

/* ---- action buttons ---- */
.toggle-btn {
  cursor: pointer;
  font-size: 1rem;
  border: 1px solid #ccc;
  background: #fff;
  border-radius: 4px;
  padding: 0.15rem 0.45rem;
}

.edit-btn {
  background: #27ae60;
  color: #fff;
  border: none;
  border-radius: 4px;
  padding: 0.3rem 0.6rem;
  cursor: pointer;
}

.delete-btn {
  background: #c0392b;
  color: #fff;
  border: none;
  border-radius: 4px;
  padding: 0.3rem 0.6rem;
  cursor: pointer;
}
```