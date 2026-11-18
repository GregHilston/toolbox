// Ctrl+B prefix, matching dot/zellij's tmux mode.
import { View, div } from "gpui-kit";
import { v_flex, h_flex } from "gpui-base";
import { run, hc, focused, props, closeOverlay, theme, checking, nextCommand } from "herdr";

const go = (direction) => ["pane.go", { direction }];
const KEYS = {
  c: ["tab.new"],
  n: ["tab.next"],
  p: ["tab.prev"],
  "&": ["tab.close"],
  ",": ["tab.rename"],
  "%": ["pane.split", { direction: "right" }],
  "|": ["pane.split", { direction: "right" }],
  '"': ["pane.split", { direction: "down" }],
  "-": ["pane.split", { direction: "down" }],
  x: ["pane.close"],
  z: ["pane.zoom"],
  h: go("left"), j: go("down"), k: go("up"), l: go("right"),
  left: go("left"), down: go("down"), up: go("up"), right: go("right"),
  "{": ["pane.swap", { direction: "left" }],
  "}": ["pane.swap", { direction: "right" }],
  "(": ["space.prev"],
  ")": ["space.next"],
  $: ["space.rename"],
  s: ["mod.open", { name: "picker" }],
  w: ["mod.open", { name: "picker" }],
  "[": ["terminal.search"],
  "?": ["app.help"],
};
for (let i = 1; i <= 9; i++) KEYS[String(i)] = ["tab.select", { index: i }];

const HINT = [
  ["Tabs", [["c", "new"], ["n p", "next, prev"], ["1-9", "go to"], ["&", "close"], [",", "rename"]]],
  ["Panes", [["% |", "split right"], ["\" -", "split down"], ["h j k l", "move"], ["x", "close"], ["z", "zoom"], ["{ }", "swap"]]],
  ["Spaces", [["( )", "prev, next space"], ["$", "rename space"], ["s w", "find a space, tab or agent"]]],
  ["Other", [["[", "find in scrollback"], ["?", "all keys"], ["Ctrl+B", "send Ctrl+B"], ["Esc", "cancel"]]],
];
const TIP = "No prefix: Cmd+P finds, Ctrl+1-9 picks a space, Cmd+Opt+[ ] steps.";

export default class TmuxPrefix extends View {
  init(_props, cx) {
    this.handle = cx.focus_handle();
    if (checking()) return;
    this.handle.focus();
    cx.timer.after(50, () => this.handle.focus());
    // keys.json may claim Ctrl+B before on_key_down.
    cx.spawn(async () => {
      for (;;) {
        if ((await nextCommand()) !== "literal") continue;
        this.done();
        this.sendPrefix();
      }
    });
  }

  done() {
    closeOverlay(props().overlay);
  }

  sendPrefix() {
    const t = focused()?.terminal;
    if (t) hc(["keys", t, "ctrl+b"]);
  }

  onKey(e, cx) {
    cx.stop_propagation();
    if (e.keystroke === "ctrl-b") {
      this.done();
      return this.sendPrefix();
    }
    const action = KEYS[e.key_char ?? ""] ?? KEYS[e.key];
    this.done();
    if (action && !e.modifiers.control && !e.modifiers.platform) run(...action);
  }

  render() {
    const t = theme();
    const key = (k) => div().w(64).flex_none().font_semibold().text_color(t.foreground).child(k);
    const row = ([k, what]) => h_flex().gap(8).child(key(k)).child(div().text_color(t.dim).child(what));
    const group = ([title, rows]) =>
      v_flex().gap(3).child(div().text_size(11).text_color(t.accent).child(title)).children(rows.map(row));
    return v_flex()
      .id("tmux-prefix")
      .track_focus(this.handle)
      .on_key_down((e, cx) => this.onKey(e, cx))
      .size_full().p(16).gap(12).bg(t.popover).text_size(12)
      .child(div().text_size(14).font_semibold().text_color(t.foreground).child("Ctrl+B, then…"))
      .child(h_flex().gap(24).items_start()
        .child(v_flex().flex_1().gap(12).child(group(HINT[0])).child(group(HINT[2])))
        .child(v_flex().flex_1().gap(12).child(group(HINT[1])).child(group(HINT[3]))))
      .child(div().text_size(11).text_color(t.dim).child(TIP));
  }
}
