

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

  /* --- toggle read (inline checkbox in the table) --- */
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
                {/* Real, clickable checkbox so UI automation can toggle "read". */}
                <input
                  type="checkbox"
                  className="read-checkbox"
                  checked={!!b.read}
                  onChange={() => toggleRead(b)}
                  aria-label={`Toggle read: ${b.title}`}
                />
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