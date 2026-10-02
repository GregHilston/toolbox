

The issue is that the form is hidden behind a "showForm" toggle, so the test can't find the title/author inputs. The fix is to make the form always visible on the page.

### client/src/App.jsx
```jsx
import { useState, useEffect, useCallback } from 'react';

function App() {
  const [books, setBooks] = useState([]);
  const [loadError, setLoadError] = useState(null);
  const [editingId, setEditingId] = useState(null);
  const [form, setForm] = useState({ title: '', author: '', year: '', read: false });

  const fetchBooks = useCallback(async () => {
    try {
      const res = await fetch('/api/books');
      if (!res.ok) throw new Error('Failed to load books');
      const data = await res.json();
      setBooks(data);
      setLoadError(null);
    } catch (err) {
      setLoadError(err.message);
    }
  }, []);

  useEffect(() => {
    fetchBooks();
  }, [fetchBooks]);

  const resetForm = () => {
    setForm({ title: '', author: '', year: '', read: false });
    setEditingId(null);
  };

  const startEdit = (book) => {
    setEditingId(book.id);
    setForm({
      title: book.title,
      author: book.author,
      year: book.year ?? '',
      read: book.read
    });
  };

  const handleFormChange = (e) => {
    const { name, value, type, checked } = e.target;
    if (type === 'checkbox') {
      setForm((f) => ({ ...f, [name]: checked }));
    } else {
      setForm((f) => ({ ...f, [name]: value }));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const payload = {
      title: form.title,
      author: form.author,
      year: form.year ? Number(form.year) : null,
      read: form.read
    };

    try {
      if (editingId) {
        const res = await fetch(`/api/books/${editingId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        if (!res.ok) throw new Error((await res.json()).error || 'Update failed');
      } else {
        const res = await fetch('/api/books', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        if (!res.ok) throw new Error((await res.json()).error || 'Create failed');
      }
      resetForm();
      fetchBooks();
    } catch (err) {
      alert(err.message);
    }
  };

  const handleToggleRead = async (book) => {
    try {
      const res = await fetch(`/api/books/${book.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: book.title,
          author: book.author,
          year: book.year,
          read: !book.read
        })
      });
      if (!res.ok) throw new Error('Toggle failed');
      fetchBooks();
    } catch (err) {
      alert(err.message);
    }
  };

  const handleDelete = async (id) => {
    if (!confirm('Delete this book?')) return;
    try {
      const res = await fetch(`/api/books/${id}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Delete failed');
      fetchBooks();
    } catch (err) {
      alert(err.message);
    }
  };

  return (
    <div className="container">
      <h1>📚 Books Manager</h1>

      <div className="form-section">
        <h2>{editingId ? 'Edit Book' : 'Add New Book'}</h2>
        <form onSubmit={handleSubmit}>
          <div className="form-row">
            <div className="form-group">
              <label htmlFor="title">Title *</label>
              <input
                id="title"
                type="text"
                name="title"
                value={form.title}
                onChange={handleFormChange}
                required
              />
            </div>
            <div className="form-group">
              <label htmlFor="author">Author *</label>
              <input
                id="author"
                type="text"
                name="author"
                value={form.author}
                onChange={handleFormChange}
                required
              />
            </div>
            <div className="form-group">
              <label htmlFor="year">Year</label>
              <input
                id="year"
                type="number"
                name="year"
                value={form.year}
                onChange={handleFormChange}
                placeholder="Optional"
              />
            </div>
            <div className="form-group" style={{ minWidth: 80 }}>
              <label htmlFor="read">Read</label>
              <input
                id="read"
                type="checkbox"
                name="read"
                checked={form.read}
                onChange={handleFormChange}
              />
            </div>
            <div>
              <button type="submit" className="btn-primary">
                {editingId ? 'Update' : 'Add'}
              </button>
              {editingId && (
                <button type="button" className="btn-secondary" onClick={resetForm}>
                  Cancel
                </button>
              )}
            </div>
          </div>
        </form>
      </div>

      {loadError && <p style={{ color: 'red' }}>Error: {loadError}</p>}

      {books.length === 0 && !loadError ? (
        <p className="empty-msg">No books yet. Use the form above to add one.</p>
      ) : (
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
                <td>
                  <span className={`badge ${book.read ? 'badge-read' : 'badge-unread'}`}>
                    {book.read ? 'Read' : 'Unread'}
                  </span>
                </td>
                <td>
                  <div className="actions">
                    <button
                      className="btn-toggle"
                      onClick={() => handleToggleRead(book)}
                      title={book.read ? 'Mark as unread' : 'Mark as read'}
                    >
                      {book.read ? '↩ Unread' : '✓ Read'}
                    </button>
                    <button className="btn-secondary" onClick={() => startEdit(book)}>
                      Edit
                    </button>
                    <button className="btn-danger" onClick={() => handleDelete(book.id)}>
                      Delete
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export default App;
```