

### client/src/App.jsx
```jsx
import React, { useState, useEffect } from 'react';
import './App.css';

function App() {
  const [books, setBooks] = useState([]);
  const [formData, setFormData] = useState({ title: '', author: '', year: '', read: false });
  const [editingId, setEditingId] = useState(null);

  useEffect(() => {
    fetchBooks();
  }, []);

  const fetchBooks = async () => {
    try {
      const res = await fetch('/api/books');
      const data = await res.json();
      setBooks(data);
    } catch (err) {
      console.error('Failed to fetch books', err);
    }
  };

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch(`/api/books${editingId ? `/${editingId}` : ''}`, {
        method: editingId ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...formData, year: formData.year ? Number(formData.year) : null, read: formData.read }),
      });
      
      if (res.ok) {
        fetchBooks();
        setFormData({ title: '', author: '', year: '', read: false });
        setEditingId(null);
      } else {
        const errData = await res.json();
        alert(errData.error || 'Error');
      }
    } catch (err) {
      console.error('Failed to save book', err);
    }
  };

  const handleDelete = async (id) => {
    if (!confirm('Are you sure?')) return;
    try {
      const res = await fetch(`/api/books/${id}`, { method: 'DELETE' });
      if (res.ok) fetchBooks();
      else alert('Failed to delete');
    } catch (err) {
      console.error('Failed to delete book', err);
    }
  };

  const handleEdit = (book) => {
    setFormData({ title: book.title, author: book.author, year: book.year, read: book.read });
    setEditingId(book.id);
  };

  const handleToggleRead = async (book) => {
    const newReadState = !book.read;
    
    try {
      const res = await fetch(`/api/books/${book.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ read: newReadState }),
      });
      
      if (res.ok) {
        fetchBooks();
      } else {
        const errData = await res.json();
        alert(errData.error || 'Failed to toggle read');
      }
    } catch (err) {
      console.error('Failed to toggle read', err);
    }
  };

  return (
    <div className="container">
      <h1>Book Manager</h1>
      
      <form onSubmit={handleSubmit} className="form">
        <input name="title" placeholder="Title" value={formData.title} onChange={handleChange} required />
        <input name="author" placeholder="Author" value={formData.author} onChange={handleChange} required />
        <input name="year" type="number" placeholder="Year" value={formData.year} onChange={handleChange} />
        <label>
          <input type="checkbox" name="read" checked={formData.read} onChange={handleChange} /> Read
        </label>
        <button type="submit">{editingId ? 'Update' : 'Add Book'}</button>
        {editingId && <button type="button" onClick={() => { setEditingId(null); setFormData({ title: '', author: '', year: '', read: false }); }}>Cancel</button>}
      </form>

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
          {books.map(book => (
            <tr key={book.id}>
              <td>{book.title}</td>
              <td>{book.author}</td>
              <td>{book.year || '-'}</td>
              <td>
                <input type="checkbox" checked={book.read} onChange={() => handleToggleRead(book)} />
              </td>
              <td>
                <button onClick={() => handleEdit(book)}>Edit</button>
                <button onClick={() => handleDelete(book.id)}>Delete</button>
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