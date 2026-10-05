

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
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT NOT NULL,
    author TEXT NOT NULL,
    year   INTEGER,
    read   BOOLEAN DEFAULT 0
  );
`);

// GET all books
app.get("/api/books", (req, res) => {
  const books = db.prepare("SELECT * FROM books ORDER BY id").all();
  res.json(books);
});

// GET one book
app.get("/api/books/:id", (req, res) => {
  const book = db.prepare("SELECT * FROM books WHERE id = ?").get(Number(req.params.id));
  if (!book) return res.status(404).json({ error: "Book not found" });
  res.json(book);
});

// POST create book
app.post("/api/books", (req, res) => {
  const { title, author, year, read } = req.body || {};

  if (!title || !title.trim()) {
    return res.status(400).json({ error: "Title is required" });
  }
  if (!author || !author.trim()) {
    return res.status(400).json({ error: "Author is required" });
  }

  const info = db
    .prepare("INSERT INTO books (title, author, year, read) VALUES (?, ?, ?, ?)")
    .run(title.trim(), author.trim(), year ?? null, read ? 1 : 0);

  const book = db.prepare("SELECT * FROM books WHERE id = ?").get(info.lastInsertRowid);
  res.status(201).json(book);
});

// PUT update book
app.put("/api/books/:id", (req, res) => {
  const id = Number(req.params.id);
  const existing = db.prepare("SELECT * FROM books WHERE id = ?").get(id);
  if (!existing) return res.status(404).json({ error: "Book not found" });

  const { title, author, year, read } = req.body || {};

  if (title !== undefined && (!title || !title.trim())) {
    return res.status(400).json({ error: "Title cannot be empty" });
  }
  if (author !== undefined && (!author || !author.trim())) {
    return res.status(400).json({ error: "Author cannot be empty" });
  }

  const updated = db
    .prepare("UPDATE books SET title = ?, author = ?, year = ?, read = ? WHERE id = ?")
    .run(
      title !== undefined ? title.trim() : existing.title,
      author !== undefined ? author.trim() : existing.author,
      year !== undefined ? (year === "" ? null : Number(year)) : existing.year,
      read !== undefined ? (read ? 1 : 0) : existing.read,
      id
    );

  if (updated.changes === 0) return res.status(404).json({ error: "Book not found" });
  const book = db.prepare("SELECT * FROM books WHERE id = ?").get(id);
  res.json(book);
});

// DELETE book
app.delete("/api/books/:id", (req, res) => {
  const id = Number(req.params.id);
  const existing = db.prepare("SELECT * FROM books WHERE id = ?").get(id);
  if (!existing) return res.status(404).json({ error: "Book not found" });

  db.prepare("DELETE FROM books WHERE id = ?").run(id);
  res.json({ message: "Book deleted" });
});

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
    "react": "^19.1.0",
    "react-dom": "^19.1.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.3.4",
    "vite": "^6.2.4"
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
    <title>Bookshelf</title>
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
import "./App.css";

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

### client/src/App.jsx
```jsx
import { useEffect, useState } from "react";

const API = "/api/books";

function EmptyForm({ onClear }) {
  return (
    <tr>
      <td colSpan="5">
        <div className="form-inline">
          <input id="c-title" placeholder="Title" />
          <input id="c-author" placeholder="Author" />
          <input id="c-year" placeholder="Year" type="number" style={{ width: 70 }} />
          <button
            onClick={() => {
              const t = document.getElementById("c-title").value;
              const a = document.getElementById("c-author").value;
              const y = document.getElementById("c-year").value;
              onClear();
            }}
          >
            Add
          </button>
        </div>
      </td>
    </tr>
  );
}

export default function App() {
  const [books, setBooks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // form state for create
  const [showCreate, setShowCreate] = useState(false);
  const [createTitle, setCreateTitle] = useState("");
  const [createAuthor, setCreateAuthor] = useState("");
  const [createYear, setCreateYear] = useState("");

  // form state for edit
  const [editing, setEditing] = useState(null); // book being edited
  const [editTitle, setEditTitle] = useState("");
  const [editAuthor, setEditAuthor] = useState("");
  const [editYear, setEditYear] = useState("");
  const [editRead, setEditRead] = useState(false);

  // form state for delete confirm
  const [deleteId, setDeleteId] = useState(null);

  const load = () => {
    setLoading(true);
    fetch(API)
      .then((r) => r.json())
      .then((data) => {
        setBooks(data);
        setError("");
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  /* ---- create ---- */
  const handleCreate = () => {
    if (!createTitle.trim() || !createAuthor.trim()) return;
    fetch(API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: createTitle.trim(),
        author: createAuthor.trim(),
        year: createYear ? Number(createYear) : null,
        read: false,
      }),
    })
      .then((r) => {
        if (!r.ok) return r.json().then((e) => { throw new Error(e.error); });
        return r.json();
      })
      .then(() => {
        setCreateTitle("");
        setCreateAuthor("");
        setCreateYear("");
        setShowCreate(false);
        load();
      })
      .catch((e) => setError(e.message));
  };

  /* ---- edit ---- */
  const openEdit = (book) => {
    setEditing(book);
    setEditTitle(book.title);
    setEditAuthor(book.author);
    setEditYear(book.year != null ? String(book.year) : "");
    setEditRead(!!book.read);
  };

  const handleSaveEdit = () => {
    if (!editing) return;
    if (!editTitle.trim() || !editAuthor.trim()) return;
    fetch(`${API}/${editing.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: editTitle.trim(),
        author: editAuthor.trim(),
        year: editYear ? Number(editYear) : null,
        read: editRead,
      }),
    })
      .then((r) => {
        if (!r.ok) return r.json().then((e) => { throw new Error(e.error); });
        return r.json();
      })
      .then(() => {
        setEditing(null);
        load();
      })
      .catch((e) => setError(e.message));
  };

  /* ---- toggle read ---- */
  const handleToggleRead = (book) => {
    fetch(`${API}/${book.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ read: !book.read }),
    })
      .then((r) => {
        if (!r.ok) return r.json().then((e) => { throw new Error(e.error); });
        return r.json();
      })
      .then(() => load())
      .catch((e) => setError(e.message));
  };

  /* ---- delete ---- */
  const handleDelete = () => {
    if (deleteId == null) return;
    fetch(`${API}/${deleteId}`, { method: "DELETE" })
      .then((r) => {
        if (!r.ok) return r.json().then((e) => { throw new Error(e.error); });
        setDeleteId(null);
        load();
      })
      .catch((e) => setError(e.message));
  };

  if (loading && books.length === 0) return <p className="msg">Loading…</p>;

  return (
    <div className="wrapper">
      <h1>📚 Bookshelf</h1>

      {error && <p className="msg error">{error}</p>}

      {/* Create section */}
      <section className="form-section">
        <button onClick={() => setShowCreate((v) => !v)}>
          {showCreate ? "Cancel" : "+ Add Book"}
        </button>
        {showCreate && (
          <div className="form-inline">
            <input
              placeholder="Title *"
              value={createTitle}
              onChange={(e) => setCreateTitle(e.target.value)}
            />
            <input
              placeholder="Author *"
              value={createAuthor}
              onChange={(e) => setCreateAuthor(e.target.value)}
            />
            <input
              placeholder="Year"
              type="number"
              value={createYear}
              onChange={(e) => setCreateYear(e.target.value)}
              style={{ width: 80 }}
            />
            <button onClick={handleCreate}>Save</button>
          </div>
        )}
      </section>

      {/* Books table */}
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
          {books.length === 0 && (
            <tr>
              <td colSpan="5" className="msg">
                No books yet.
              </td>
            </tr>
          )}
          {books.map((book) => {
            if (editing && editing.id === book.id) {
              return (
                <tr key={book.id}>
                  <td>
                    <input value={editTitle} onChange={(e) => setEditTitle(e.target.value)} />
                  </td>
                  <td>
                    <input value={editAuthor} onChange={(e) => setEditAuthor(e.target.value)} />
                  </td>
                  <td>
                    <input
                      type="number"
                      value={editYear}
                      onChange={(e) => setEditYear(e.target.value)}
                      style={{ width: 70 }}
                    />
                  </td>
                  <td>
                    <input
                      type="checkbox"
                      checked={editRead}
                      onChange={(e) => setEditRead(e.target.checked)}
                    />
                  </td>
                  <td className="actions">
                    <button onClick={handleSaveEdit}>Save</button>{" "}
                    <button onClick={() => setEditing(null)}>Cancel</button>
                  </td>
                </tr>
              );
            }
            if (deleteId === book.id) {
              return (
                <tr key={book.id}>
                  <td colSpan="5" className="confirm">
                    Delete &ldquo;{book.title}&rdquo;?{" "}
                    <button onClick={handleDelete}>Yes</button>{" "}
                    <button onClick={() => setDeleteId(null)}>No</button>
                  </td>
                </tr>
              );
            }
            return (
              <tr key={book.id}>
                <td>{book.title}</td>
                <td>{book.author}</td>
                <td>{book.year ?? ""}</td>
                <td>{book.read ? "✅" : "⬜"}</td>
                <td className="actions">
                  <button onClick={() => handleToggleRead(book)}>
                    {book.read ? "Unread" : "Read"}
                  </button>{" "}
                  <button onClick={() => openEdit(book)}>Edit</button>{" "}
                  <button onClick={() => setDeleteId(book.id)} className="danger">
                    Delete
                  </button>
                </td>
              </tr>
            );
          })}
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
  margin: 0;
  padding: 0;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  background: #f5f5f5;
  color: #1a1a1a;
}

.wrapper {
  max-width: 960px;
  margin: 2rem auto;
  padding: 0 1rem;
}

h1 {
  margin-bottom: 1.5rem;
}

.msg {
  padding: 0.5rem;
  text-align: center;
}

.msg.error {
  color: #d32f2f;
  background: #ffebee;
  border-radius: 4px;
}

/* form */
.form-section {
  margin-bottom: 1.5rem;
}

.form-inline {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.5rem;
  flex-wrap: wrap;
}

.form-inline input {
  padding: 0.4rem 0.6rem;
  border: 1px solid #ccc;
  border-radius: 4px;
}

button {
  padding: 0.4rem 0.8rem;
  border: 1px solid #ccc;
  border-radius: 4px;
  background: #fff;
  cursor: pointer;
}

button:hover {
  background: #e0e0e0;
}

button.danger {
  color: #d32f2f;
  border-color: #d32f2f;
}

button.danger:hover {
  background: #ffebee;
}

/* table */
table {
  width: 100%;
  border-collapse: collapse;
  background: #fff;
  border-radius: 6px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

th,
td {
  padding: 0.6rem 0.8rem;
  border-bottom: 1px solid #eee;
  text-align: left;
}

th {
  background: #fafafa;
  font-weight: 600;
}

td input {
  width: 100%;
  padding: 0.35rem 0.5rem;
  border: 1px solid #ccc;
  border-radius: 3px;
}

td.actions {
  white-space: nowrap;
}

.confirm {
  text-align: center;
  font-style: italic;
}
```

### README.md
```markdown
# Bookshelf – Full-Stack CRUD (SQLite + Express + React)

## Prerequisites

- Node.js (v20+)
- npm

## Run the API (server)

```bash
cd server
npm install
npm start        # listens on http://localhost:3001 (override with PORT)
```

## Run the UI (client)

Open a **second** terminal, then:

```bash
cd client
npm install
npm run dev    # Vite dev server, proxies /api → localhost:3001
```

Open http://localhost:5173 in your browser.

## Production build

```bash
cd client
npm run build   # output in client/dist/
```

## API endpoints

| Method | Path              | Description          |
|--------|-------------------|--------------------|
| GET    | /api/books        | List all books     |
| GET    | /api/books/:id    | Get one book       |
| POST   | /api/books        | Create a book      |
| PUT    | /api/books/:id    | Update a book      |
| DELETE | /api/books/:id    | Delete a book      |
```