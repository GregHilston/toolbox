

### server/package.json
```json
{
  "name": "book-manager-server",
  "version": "1.0.0",
  "description": "REST API for book management",
  "main": "index.js",
  "scripts": {
    "start": "node index.js"
  },
  "dependencies": {
    "cors": "^2.8.5",
    "express": "^4.21.2",
    "sqlite": "^5.0.0"
  }
}
```

### server/index.js
```javascript
const express = require('express');
const cors = require('cors');
const sqlite = require('sqlite');
const sqlite3 = require('sqlite3');
const path = require('path');
const fs = require('fs');

const app = express();
const port = process.env.PORT || 3001;

app.use(cors());
app.use(express.json());

let db;

async function init() {
  const dbPath = path.join(__dirname, 'data.db');
  
  // Initialize database
  db = await sqlite.open({
    filename: dbPath,
    driver: sqlite3.Database
  });
  
  await db.exec(`
    CREATE TABLE IF NOT EXISTS books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      author TEXT NOT NULL,
      year INTEGER,
      read BOOLEAN DEFAULT 0
    )
  `);

  app.get('/api/books', async (req, res) => {
    try {
      const books = await db.all('SELECT * FROM books');
      res.json(books.map(b => ({ id: b.id, title: b.title, author: b.author, year: b.year, read: !!b.read })));
    } catch (err) {
      res.status(500).json({ error: err.message });
    }
  });

  app.get('/api/books/:id', async (req, res) => {
    try {
      const book = await db.get('SELECT * FROM books WHERE id = ?', [req.params.id]);
      if (!book) return res.status(404).json({ error: 'Book not found' });
      res.json({ id: book.id, title: book.title, author: book.author, year: book.year, read: !!book.read });
    } catch (err) {
      res.status(500).json({ error: err.message });
    }
  });

  app.post('/api/books', async (req, res) => {
    try {
      const { title, author, year, read } = req.body;
      if (!title || !author || title.trim() === '' || author.trim() === '') {
        return res.status(400).json({ error: 'Title and author are required' });
      }
      const result = await db.run('INSERT INTO books (title, author, year, read) VALUES (?, ?, ?, ?)', 
        [title, author, year || null, read ? 1 : 0]);
      const book = await db.get('SELECT * FROM books WHERE id = ?', [result.lastID]);
      res.status(201).json({ id: book.id, title: book.title, author: book.author, year: book.year, read: !!book.read });
    } catch (err) {
      res.status(500).json({ error: err.message });
    }
  });

  app.put('/api/books/:id', async (req, res) => {
    try {
      const { title, author, year, read } = req.body;
      if (!title || !author || title.trim() === '' || author.trim() === '') {
        return res.status(400).json({ error: 'Title and author are required' });
      }
      const existing = await db.get('SELECT * FROM books WHERE id = ?', [req.params.id]);
      if (!existing) return res.status(404).json({ error: 'Book not found' });
      
      await db.run('UPDATE books SET title = ?, author = ?, year = ?, read = ? WHERE id = ?', 
        [title, author, year || null, read ? 1 : 0, req.params.id]);
      const updated = await db.get('SELECT * FROM books WHERE id = ?', [req.params.id]);
      res.json({ id: updated.id, title: updated.title, author: updated.author, year: updated.year, read: !!updated.read });
    } catch (err) {
      res.status(500).json({ error: err.message });
    }
  });

  app.delete('/api/books/:id', async (req, res) => {
    try {
      const existing = await db.get('SELECT * FROM books WHERE id = ?', [req.params.id]);
      if (!existing) return res.status(404).json({ error: 'Book not found' });
      
      await db.run('DELETE FROM books WHERE id = ?', [req.params.id]);
      res.json({ success: true });
    } catch (err) {
      res.status(500).json({ error: err.message });
    }
  });

  app.listen(port, () => {
    console.log(`Server running on port ${port}`);
  });
}

init().catch(err => {
  console.error('Failed to initialize server:', err);
  process.exit(1);
});
```