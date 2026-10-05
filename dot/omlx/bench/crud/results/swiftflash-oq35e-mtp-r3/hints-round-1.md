I installed and ran your app. These checks failed: create, get_one, update, validation_400, delete, persists_restart, ui_list, ui_create, ui_toggle, ui_edit, ui_delete.

validation statuses (empty title POST, missing author POST, empty author PUT):
```
(400, 400, 404)
```

unknown-id statuses (GET, PUT, DELETE):
```
(404, 404, 404)
```

ui errors:
```
toggle: TypeError: Cannot read properties of undefined (reading 'read')
edit: TimeoutError: locator.click: Timeout 30000ms exceeded.
delete: TimeoutError: locator.click: Timeout 30000ms exceeded.
```

Fix the problems. Output only the files you change, in full, in the same format as before.