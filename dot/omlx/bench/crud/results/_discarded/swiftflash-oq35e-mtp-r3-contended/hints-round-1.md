I installed and ran your app. These checks failed: ui_create, ui_toggle.

validation statuses (empty title POST, missing author POST, empty author PUT):
```
(400, 400, 400)
```

unknown-id statuses (GET, PUT, DELETE):
```
(404, 404, 404)
```

ui errors:
```
create: Error: no title/author inputs found
toggle: TimeoutError: locator.click: Timeout 30000ms exceeded.
```

Fix the problems. Output only the files you change, in full, in the same format as before.