

### server/package.json
```json
{
  "name": "server",
  "version": "1.0.0",
  "description": "Book Manager API",
  "main": "index.js",
  "scripts": {
    "start": "node index.js"
  },
  "dependencies": {
    "express": "^4.18.2",
    "sql.js": "^1.10.1"
  }
}
```

### server/index.js
```javascript
const express = require('express');
const initSqlJs = require('sql.js');
const fs = require('fs');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3001;
const DB_PATH = path.join(__dirname, 'data.db');

app.use(express.json());

async function initDatabase() {
  const SQL = await initSqlJs();
  let db;

  try {
    if (fs.existsSync(DB_PATH)) {
      const fileBuffer = fs.readFileSync(DB_PATH);
      db = new SQL.Database(fileBuffer);
    } else {
      db = new SQL.Database();
    }
  } catch (err) {
    console.error("Failed to load database:", err);
    process.exit(1);
  }

  // Create table
  try {
    db.run(`
      CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        year INTEGER,
        read BOOLEAN DEFAULT 0
      )
    `);
  } catch (err) {
    console.error("Failed to create table:", err);
    process.exit(1);
  }

  function save() {
    const data = db.export();
    const buffer = Buffer.from(data);
    fs.writeFileSync(DB_PATH, buffer);
  }

  // GET /api/books
  app.get('/api/books', (req, res) => {
    try {
      const result = db.exec("SELECT * FROM books");
      if (result.length === 0) {
        return res.json([]);
      }
      const columns = result[0].columns;
      const values = result[0].values;
      const books = values.map(row => {
        const book = {};
        columns.forEach((col, index) => {
          let val = row[index];
          if (col === 'id') book.id = val;
          else if (col === 'title') book.title = val;
          else if (col === 'author') book.author = val;
          else if (col === 'year') book.year = val;
          else if (col === 'read') book.read = val === 1;
        });
        return book;
      });
      res.json(books);
    } catch (err) {
      res.status(500).json({ error: err.message });
    }
  });

  // GET /api/books/:id
  app.get('/api/books/:id', (req, res) => {
    try {
      const result = db.exec("SELECT * FROM books WHERE id = ?", [req.params.id]);
      if (result.length === 0 || result[0].values.length === 0) {
        return res.status(404).json({ error: 'Book not found' });
      }
      const columns = result[0].columns;
      const row = result[0].values[0];
      const book = {};
      columns.forEach((col, index) => {
        let val = row[index];
        if (col === 'id') book.id = val;
        else if (col === 'title') book.title = val;
        else if (col === 'author') book.author = val;
        else if (col === 'year') book.year = val;
        else if (col === 'read') book.read = val === 1;
      });
      res.json(book);
    } catch (err) {
      res.status(500).json({ error: err.message });
    }
  });

  // POST /api/books
  app.post('/api/books', (req, res) => {
    try {
      const { title, author, year, read } = req.body;
      if (!title || !author) {
        return res.status(400).json({ error: 'Title and Author are required' });
      }
      
      const resRun = db.run("INSERT INTO books (title, author, year, read) VALUES (?, ?, ?, ?)", 
                            [title, author, year || null, read ? 1 : 0]);
      const newId = resRun.lastID;
      
      const result = db.exec("SELECT * FROM books WHERE id = ?", [newId]);
      if (result.length === 0 || result[0].values.length === 0) {
         return res.status(500).json({ error: 'Failed to retrieve new book' });
      }
      const columns = result[0].columns;
      const row = result[0].values[0];
      const book = {};
      columns.forEach((col, index) => {
        let val = row[index];
        if (col === 'id') book.id = val;
        else if (col === 'title') book.title = val;
        else if (col === 'author') book.author = val;
        else if (col === 'year') book.year = val;
        else if (col === 'read') book.read = val === 1;
      });
      save();
      res.status(201).json(book);
    } catch (err) {
      res.status(500).json({ error: err.message });
    }
  });

  // PUT /api/books/:id
  app.put('/api/books/:id', (req, res) => {
    try {
      const { title, author, year, read } = req.body;
      const id = req.params.id;
      
      // Check existence
      const checkRes = db.exec("SELECT * FROM books WHERE id = ?", [id]);
      if (checkRes.length === 0 || checkRes[0].values.length === 0) {
        return res.status(404).json({ error: 'Book not found' });
      }

      if (!title || !author) {
        return res.status(400).json({ error: 'Title and Author are required' });
      }

      db.run("UPDATE books SET title = ?, author = ?, year = ?, read = ? WHERE id = ?", 
             [title, author, year || null, read ? 1 : 0, id]);
      
      const result = db.exec("SELECT * FROM books WHERE id = ?", [id]);
      const columns = result[0].columns;
      const row = result[0].values[0];
      const book = {};
      columns.forEach((col, index) => {
        let val = row[index];
        if (col === 'id') book.id = val;
        else if (col === 'title') book.title = val;
        else if (col === 'author') book.author = val;
        else if (col === 'year') book.year = val;
        else if (col === 'read') book.read = val === 1;
      });
      save();
      res.json(book);
    } catch (err) {
      res.status(500).json({ error: err.message });
    }
  });

  // DELETE /api/books/:id
  app.delete('/api/books/:id', (req, res) => {
    try {
      const id = req.params.id;
      const resRun = db.run("DELETE FROM books WHERE id = ?", [id]);
      if (resRun.changes === 0) {
        return res.status(404).json({ error: 'Book not found' });
      }
      save();
      res.json({ message: 'Book deleted' });
    } catch (err) {
      res.status(500).json({ error: err.message });
    }
  });

  app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
  });
}

initDatabase().catch(err => {
  console.error("Failed to start server:", err);
  process.exit(1);
});
```