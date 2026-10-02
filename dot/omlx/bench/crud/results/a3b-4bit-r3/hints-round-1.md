I installed and ran your app. These checks failed: not_found_404, ui_toggle.

validation statuses (empty title POST, missing author POST, empty author PUT):
```
(400, 400, 400)
```

unknown-id statuses (GET, PUT, DELETE):
```
(404, 200, 404)
```

ui errors:
```
toggle: TimeoutError: locator.click: Timeout 30000ms exceeded.
```

Fix the problems. Output only the files you change, in full, in the same format as before.