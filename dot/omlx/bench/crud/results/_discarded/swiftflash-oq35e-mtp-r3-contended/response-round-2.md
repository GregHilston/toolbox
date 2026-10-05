

### client/src/App.jsx
```jsx
import { useEffect, useState, useCallback } from "react";

const API = "/api/books";

export default function App() {
  const [books, setBooks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [title, setTitle] = useState("");
  const [author, setAuthor] = useState("");
  const [year, setYear] = useState("");
  const [read, setRead] = useState(false);
  const [saving, setSaving] = useState(false);

  const fetchBooks = useCallback(async () => {
    try {
      const res = await fetch(API);
      const data = await res.json();
      setBooks(data);
      setError("");
    } catch {
      setError("Failed to load books.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchBooks();
  }, [fetchBooks]);

  async function handleSubmit(e) {
    e.preventDefault();
    if (saving) return;
    if (!title.trim() || !author.trim()) {
      setError("Title and author are required.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      const res = await fetch(API, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: title.trim(),
          author: author.trim(),
          year: year === "" ? null : Number(year),
          read,
        }),
      });
      if (res.ok) {
        setTitle("");
        setAuthor("");
        setYear("");
        setRead(false);
        await fetchBooks();
      } else {
        const data = await res.json().catch(() => ({}));
        setError(data.error || "Failed to create book.");
      }
    } finally {
      setSaving(false);
    }
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

  if (loading) return <div className="container"><p>Loading…</p></div>;

  return (
    <div className="container">
      <h1>📚 Books</h1>

      {error && <p className="error" data-testid="form-error">{error}</p>}

      <form className="form-card" onSubmit={handleSubmit} data-testid="book-form">
        <div className="form-row">
          <div className="field">
            <label htmlFor="title">Title</label>
            <input
              id="title"
              name="title"
              type="text"
              placeholder="Title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              data-testid="title-input"
            />
          </div>
          <div className="field">
            <label htmlFor="author">Author</label>
            <input
              id="author"
              name="author"
              type="text"
              placeholder="Author"
              value={author}
              onChange={(e) => setAuthor(e.target.value)}
              data-testid="author-input"
            />
          </div>
        </div>
        <div className="form-row">
          <div className="field">
            <label htmlFor="year">Year</label>
            <input
              id="year"
              name="year"
              type="number"
              placeholder="Year (optional)"
              value={year}
              onChange={(e) => setYear(e.target.value)}
              data-testid="year-input"
            />
          </div>
          <div className="field">
            <label htmlFor="read">Read</label>
            <input
              id="read"
              name="read"
              type="checkbox"
              checked={read}
              onChange={(e) => setRead(e.target.checked)}
              data-testid="read-checkbox"
            />
          </div>
        </div>
        <div className="form-actions">
          <button type="submit" className="btn-primary" disabled={saving} data-testid="submit-button">
            Add Book
          </button>
        </div>
      </form>

      <table data-testid="books-table">
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
                No books yet.
              </td>
            </tr>
          )}
          {books.map((book) => (
            <tr key={book.id} data-testid={`book-row-${book.id}`}>
              <td data-testid={`book-title-${book.id}`}>{book.title}</td>
              <td data-testid={`book-author-${book.id}`}>{book.author}</td>
              <td>{book.year ?? "—"}</td>
              <td className="read-cell">
                <button
                  type="button"
                  className={`btn-toggle ${book.read ? "read" : "unread"}`}
                  onClick={() => handleToggleRead(book)}
                  data-testid={`toggle-${book.id}`}
                  aria-label={`Toggle read status for ${book.title}`}
                >
                  {book.read ? "Mark as Unread" : "Mark as Read"}
                </button>
              </td>
              <td>
                <button
                  type="button"
                  className="btn-danger"
                  onClick={() => handleDelete(book)}
                  data-testid={`delete-${book.id}`}
                  aria-label={`Delete ${book.title}`}
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
  margin: 0 0 20px;
}

.container {
  max-width: 920px;
  margin: 32px auto;
  padding: 0 16px;
}

.error {
  color: #dc2626;
  font-weight: 600;
}

.form-card {
  background: #fff;
  padding: 20px 24px;
  border-radius: 8px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
  margin-bottom: 24px;
}

.form-row {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.field {
  flex: 1 1 220px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.field label {
  font-size: 0.85rem;
  font-weight: 600;
  color: #555;
}

input[type="text"],
input[type="number"] {
  border: 1px solid #ccc;
  border-radius: 4px;
  padding: 6px 10px;
  font-size: 0.9rem;
  width: 100%;
}

.form-actions {
  display: flex;
  gap: 8px;
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

.read-cell {
  text-align: center;
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

button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background: #2563eb;
  color: #fff;
}

.btn-danger {
  background: #dc2626;
  color: #fff;
}

.btn-toggle {
  color: #fff;
}

.btn-toggle.unread {
  background: #9ca3af;
}

.btn-toggle.read {
  background: #16a34a;
}
```