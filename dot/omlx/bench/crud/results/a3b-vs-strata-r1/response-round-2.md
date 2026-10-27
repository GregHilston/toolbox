

### client/src/App.jsx
```jsx
import React, { useState, useEffect } from 'react';

function App() {
  const [books, setBooks] = useState([]);
  const [editing, setEditing] = useState(null);
  const [formData, setFormData] = useState({ title: '', author: '', year: '', read: false });
  const [error, setError] = useState('');

  const fetchBooks = async () => {
    try {
      const res = await fetch('/api/books');
      if (!res.ok) {
        throw new Error('Failed to fetch');
      }
      const data = await res.json();
      if (Array.isArray(data)) {
        setBooks(data);
      } else {
        setBooks([]);
      }
    } catch (e) {
      console.error('Fetch error:', e);
      setError('Failed to fetch books');
    }
  };

  useEffect(() => {
    fetchBooks();
  }, []);

  const handleCreate = async () => {
    try {
      const res = await fetch('/api/books', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });
      if (res.status === 400) {
        const err = await res.json();
        setError(err.error);
        return;
      }
      setError('');
      setFormData({ title: '', author: '', year: '', read: false });
      await fetchBooks();
    } catch (e) {
      setError('Failed to create book');
    }
  };

  const handleUpdate = async () => {
    try {
      const res = await fetch(`/api/books/${editing.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });
      if (res.status === 400) {
        const err = await res.json();
        setError(err.error);
        return;
      }
      if (res.status === 404) {
        setError('Book not found');
        return;
      }
      setError('');
      setEditing(null);
      setFormData({ title: '', author: '', year: '', read: false });
      await fetchBooks();
    } catch (e) {
      setError('Failed to update book');
    }
  };

  const handleDelete = async (id) => {
    try {
      await fetch(`/api/books/${id}`, { method: 'DELETE' });
      await fetchBooks();
    } catch (e) {
      setError('Failed to delete book');
    }
  };

  const handleToggleRead = async (book) => {
    if (!book || !book.id) return;
    try {
      const updated = { ...book, read: !book.read };
      await fetch(`/api/books/${book.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updated),
      });
      await fetchBooks();
    } catch (e) {
      setError('Failed to update book');
    }
  };

  const startEdit = (book) => {
    if (!book) return;
    setEditing(book);
    setFormData({
      title: book.title,
      author: book.author,
      year: book.year !== null && book.year !== undefined ? String(book.year) : '',
      read: book.read
    });
  };

  const cancelEdit = () => {
    setEditing(null);
    setFormData({ title: '', author: '', year: '', read: false });
  };

  return (
    <div style={{ maxWidth: '800px', margin: '0 auto', padding: '20px', fontFamily: 'sans-serif' }}>
      <h1>Book Manager</h1>

      {error && <div style={{ color: 'red', marginBottom: '10px', padding: '10px', backgroundColor: '#ffe0e0', borderRadius: '4px' }}>{error}</div>}

      <div style={{ marginBottom: '20px', padding: '15px', border: '1px solid #ccc', borderRadius: '5px' }}>
        <h3>{editing ? 'Edit Book' : 'Add New Book'}</h3>
        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', marginBottom: '10px' }}>
          <input
            placeholder="Title"
            value={formData.title}
            onChange={(e) => setFormData({ ...formData, title: e.target.value })}
            style={{ flex: 2, padding: '8px', minWidth: '150px' }}
          />
          <input
            placeholder="Author"
            value={formData.author}
            onChange={(e) => setFormData({ ...formData, author: e.target.value })}
            style={{ flex: 2, padding: '8px', minWidth: '150px' }}
          />
          <input
            type="number"
            placeholder="Year"
            value={formData.year}
            onChange={(e) => setFormData({ ...formData, year: e.target.value })}
            style={{ flex: 1, padding: '8px', minWidth: '80px' }}
          />
          <label style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <input
              type="checkbox"
              checked={formData.read}
              onChange={(e) => setFormData({ ...formData, read: e.target.checked })}
            />
            <span>Read</span>
          </label>
        </div>
        <button onClick={editing ? handleUpdate : handleCreate} style={{ padding: '8px 16px', marginRight: '10px', cursor: 'pointer' }}>
          {editing ? 'Update' : 'Add Book'}
        </button>
        {editing && <button onClick={cancelEdit} style={{ padding: '8px 16px', cursor: 'pointer' }}>Cancel</button>}
      </div>

      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ backgroundColor: '#f0f0f0' }}>
            <th style={{ padding: '10px', border: '1px solid #ccc', textAlign: 'center' }}>Read</th>
            <th style={{ padding: '10px', border: '1px solid #ccc' }}>Title</th>
            <th style={{ padding: '10px', border: '1px solid #ccc' }}>Author</th>
            <th style={{ padding: '10px', border: '1px solid #ccc' }}>Year</th>
            <th style={{ padding: '10px', border: '1px solid #ccc' }}>Actions</th>
          </tr>
        </thead>
        <tbody>
          {books.length === 0 ? (
            <tr>
              <td colSpan="5" style={{ padding: '20px', textAlign: 'center', color: '#666' }}>
                No books yet. Add one above!
              </td>
            </tr>
          ) : (
            books.map((book) => (
              <tr key={book.id}>
                <td style={{ padding: '10px', border: '1px solid #ccc', textAlign: 'center' }}>
                  <input
                    type="checkbox"
                    checked={book.read}
                    onChange={() => handleToggleRead(book)}
                  />
                </td>
                <td style={{ padding: '10px', border: '1px solid #ccc' }}>{book.title}</td>
                <td style={{ padding: '10px', border: '1px solid #ccc' }}>{book.author}</td>
                <td style={{ padding: '10px', border: '1px solid #ccc' }}>{book.year || ''}</td>
                <td style={{ padding: '10px', border: '1px solid #ccc' }}>
                  <button onClick={() => startEdit(book)} style={{ marginRight: '5px', padding: '4px 8px', cursor: 'pointer' }}>Edit</button>
                  <button onClick={() => handleDelete(book.id)} style={{ padding: '4px 8px', cursor: 'pointer' }}>Delete</button>
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

export default App;
```