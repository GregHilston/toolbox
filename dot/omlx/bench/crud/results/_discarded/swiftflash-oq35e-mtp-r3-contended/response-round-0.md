

### README.md
```markdown
# Books CRUD App

## Prerequisites
- Node.js (v18+ recommended, tested with v26)

## Run the Backend

```bash
cd server
npm install
npm start
```

The API listens on `http://localhost:3001` (or set `PORT`).

## Run the Frontend (in a second terminal)

```bash
cd client
npm install
npm run dev
```

Open the URL Vite prints (default `http://localhost:5173`).

## Build the Frontend

```bash
cd client
npm run build
```

The production bundle is emitted to `client/dist/`.
```

### server/package.json
```json
{
  "name": "books-api",
  "version": "1.0.0",
  "private": true,
  "type": "module",
  "main": "index.js",
  "scripts": {
    "start": "node index.js"
  },
  "dependencies": {
    "better-sqlite3": "^11.7.0",
    "express": "^4.21.0"
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
const dbPath = path.join(__dirname, "data.db");

const db = new Database(dbPath);

db.exec(`
  CREATE TABLE IF NOT EXISTS books (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year  INTEGER,
    read  INTEGER NOT NULL DEFAULT 0
  );
`);

const app = express();
app.use(express.json());

// ── GET /api/books ──────────────────────────────────────────
app.get("/api/books", (_req, res) => {
  const rows = db.prepare("SELECT * FROM books ORDER BY id").all();
  res.json(rows.map(row => ({ ...row, read: !!row.read })));
});

// ── GET /api/books/:id ─────────────────────────────────────
app.get("/api/books/:id", (req, res) => {
  const id = Number(req.params.id);
  const row = db.prepare("SELECT * FROM books WHERE id = ?").get(id);
  if (!row) return res.status(404).json({ error: "Book not found" });
  res.json({ ...row, read: !!row.read });
});

// ── POST /api/books ─────────────────────────────────────────
app.post("/api/books", (req, res) => {
  const { title, author, year, read } = req.body;

  if (!title || String(title).trim() === "") {
    return res.status(400).json({ error: "title is required" });
  }
  if (!author || String(author).trim() === "") {
    return res.status(400).json({ error: "author is required" });
  }

  const yearVal = year === undefined || year === null ? null : Number(year);
  const readVal = read ? 1 : 0;

  const info = db
    .prepare("INSERT INTO books (title, author, year, read) VALUES (?, ?, ?, ?)")
    .run(String(title).trim(), String(author).trim(), yearVal, readVal);

  const row = db.prepare("SELECT * FROM books WHERE id = ?").get(info.lastInsertRowid);
  res.status(201).json({ ...row, read: !!row.read });
});

// ── PUT /api/books/:id ─────────────────────────────────────
app.put("/api/books/:id", (req, res) => {
  const id = Number(req.params.id);
  const existing = db.prepare("SELECT * FROM books WHERE id = ?").get(id);
  if (!existing) return res.status(404).json({ error: "Book not found" });

  const { title, author, year, read } = req.body;

  if (!title || String(title).trim() === "") {
    return res.status(400).json({ error: "title is required" });
  }
  if (!author || String(author).trim() === "") {
    return res.status(400).json({ error: "author is required" });
  }

  const yearVal = year === undefined || year === null ? null : Number(year);
  const readVal = read ? 1 : 0;

  db.prepare("UPDATE books SET title=?, author=?, year=?, read=? WHERE id=?").run(
    String(title).trim(),
    String(author).trim(),
    yearVal,
    readVal,
    id
  );

  const row = db.prepare("SELECT * FROM books WHERE id = ?").get(id);
  res.json({ ...row, read: !!row.read });
});

// ── DELETE /api/books/:id ──────────────────────────────────
app.delete("/api/books/:id", (req, res) => {
  const id = Number(req.params.id);
  const existing = db.prepare("SELECT * FROM books WHERE id = ?").get(id);
  if (!existing) return res.status(404).json({ error: "Book not found" });

  db.prepare("DELETE FROM books WHERE id = ?").run(id);
  res.json({ ok: true });
});

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
  console.log(`API running on http://localhost:${PORT}`);
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
*,
*::before,
*::after {
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
    "Helvetica Neue", Arial, sans-serif;
  margin: 0;
  background: #f5f5f5;
  color: #222;
}

h1 {
  margin: 0;
}

button {
  cursor: pointer;
  border: none;
  border-radius: 4px;
  padding: 6px 14px;
  font-size: 0.85rem;
  font-weight: 600;
  transition: background 0.15s, opacity 0.15s;
}
button:hover {
  opacity: 0.85;
}

.btn-primary {
  background: #2563eb;
  color: #fff;
}

.btn-danger {
  background: #dc2626;
  color: #fff;
}

.btn-secondary {
  background: #e5e7eb;
  color: #333;
}

.btn-toggle {
  background: #16a34a;
  color: #fff;
}
.btn-toggle.unread {
  background: #9ca3af;
}

input[type="text"],
input[type="number"] {
  border: 1px solid #ccc;
  border-radius: 4px;
  padding: 6px 10px;
  font-size: 0.9rem;
  width: 100%;
}

table {
  width: 100%;
  border-collapse: collapse;
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
}

th,
td {
  padding: 10px 14px;
  text-align: left;
}

th {
  background: #1e293b;
  color: #fff;
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

tr:not(:last-child) td {
  border-bottom: 1px solid #f0f0f0;
}

.container {
  max-width: 920px;
  margin: 32px auto;
  padding: 0 16px;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.form-card {
  background: #fff;
  padding: 20px 24px;
  border-radius: 8px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
  margin-bottom: 24px;
}

.form-card h2 {
  margin: 0 0 16px;
  font-size: 1.15rem;
}

.form-row {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.form-row label {
  flex: 1 1 180px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 0.85rem;
  font-weight: 600;
  color: #555;
}

.form-actions {
  display: flex;
  gap: 8px;
  margin-top: 4px;
}

.read-cell {
  text-align: center;
}
```

### client/src/App.jsx
```jsx
import { useEffect, useState, useCallback } from "react";

const API = "/api/books";

function BookForm({ book, onSubmit, onCancel }) {
  const isEdit = !!book;
  const [title, setTitle] = useState(book?.title ?? "");
  const [author, setAuthor] = useState(book?.author ?? "");
  const [year, setYear] = useState(book?.year ?? "");
  const [read, setRead] = useState(book?.read ?? false);
  const [saving, setSaving] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    if (saving) return;
    setSaving(true);
    const payload = {
      title,
      author,
      year: year === "" ? null : Number(year),
      read,
    };
    try {
      await onSubmit(payload);
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="form-card" onSubmit={handleSubmit}>
      <h2>{isEdit ? "Edit Book" : "Add Book"}</h2>
      <div className="form-row">
        <label>
          Title *
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
          />
        </label>
        <label>
          Author *
          <input
            type="text"
            value={author}
            onChange={(e) => setAuthor(e.target.value)}
            required
          />
        </label>
      </div>
      <div className="form-row">
        <label>
          Year
          <input
            type="number"
            value={year}
            onChange={(e) => setYear(e.target.value)}
            placeholder="e.g. 2024"
          />
        </label>
        <label>
          Read
          <input
            type="checkbox"
            checked={read}
            onChange={(e) => setRead(e.target.checked)}
          />
        </label>
      </div>
      <div className="form-actions">
        <button type="submit" className="btn-primary" disabled={saving}>
          {isEdit ? "Update" : "Add"}
        </button>
        <button type="button" className="btn-secondary" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}

export default function App() {
  const [books, setBooks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [showForm, setShowForm] = useState(false);
  const [editingBook, setEditingBook] = useState(null);

  const fetchBooks = useCallback(async () => {
    try {
      const res = await fetch(API);
      const data = await res.json();
      setBooks(data);
      setError("");
    } catch (err) {
      setError("Failed to load books.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchBooks();
  }, [fetchBooks]);

  async function handleCreate(payload) {
    const res = await fetch(API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) {
      alert(data.error || "Create failed");
      return;
    }
    setShowForm(false);
    fetchBooks();
  }

  async function handleUpdate(payload) {
    const res = await fetch(`${API}/${editingBook.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) {
      alert(data.error || "Update failed");
      return;
    }
    setEditingBook(null);
    setShowForm(false);
    fetchBooks();
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

  async function handleDelete(book) {
    if (!confirm(`Delete "${book.title}"?`)) return;
    const res = await fetch(`${API}/${book.id}`, { method: "DELETE" });
    if (res.ok) fetchBooks();
  }

  if (loading) return <div className="container">Loading…</div>;

  return (
    <div className="container">
      <div className="header">
        <h1>📚 Books</h1>
        {!showForm && (
          <button className="btn-primary" onClick={() => setShowForm(true)}>
            + Add Book
          </button>
        )}
      </div>

      {error && <p style={{ color: "#dc2626" }}>{error}</p>}

      {showForm && (
        <BookForm
          book={editingBook}
          onSubmit={editingBook ? handleUpdate : handleCreate}
          onCancel={() => {
            setShowForm(false);
            setEditingBook(null);
          }}
        />
      )}

      <table>
        <thead>
          <tr>
            <th>Title</th>
            <th>Author</th>
            <th>Year</th>
            <th className="read-cell">Read</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {books.length === 0 && (
            <tr>
              <td colSpan={5} style={{ textAlign: "center", padding: 24 }}>
                No books yet. Click <strong>+ Add Book</strong> to create one.
              </td>
            </tr>
          )}
          {books.map((book) => (
            <tr key={book.id}>
              <td>{book.title}</td>
              <td>{book.author}</td>
              <td>{book.year ?? "—"}</td>
              <td className="read-cell">
                <button
                  className={`btn-toggle ${book.read ? "" : "unread"}`}
                  onClick={() => handleToggleRead(book)}
                >
                  {book.read ? "✓" : "—"}
                </button>
              </td>
              <td>
                <button
                  className="btn-secondary"
                  onClick={() => {
                    setEditingBook(book);
                    setShowForm(true);
                  }}
                >
                  Edit
                </button>{" "}
                <button
                  className="btn-danger"
                  onClick={() => handleDelete(book)}
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

That's every file. The project tree is:

```
README.md
server/
  package.json
  index.js
client/
  package.json
  vite.config.js
  index.html
  src/
    main.jsx
    App.jsx
    index.css
```

**Quick run:**

| Terminal 1 | Terminal 2 |
|---|---|
| `cd server && npm install && npm start` | `cd client && npm install && npm run dev` |

Open the Vite URL (default `http://localhost:5173`). The `/api` proxy forwards to the Express server on `:3001`. The SQLite file `server/data.db` is created automatically on first start.