/**
 * Both directions matter. A floor that refuses `grep shutdown` makes a
 * headless reviewer useless on shell code; one that lets `rm -rf` through
 * behind a wrapper protects nothing.
 */

import assert from "node:assert/strict";
import { test } from "node:test";

import {
	DISABLED_FLOOR_RULES,
	HEADLESS_RULES,
	hardBlockReason,
} from "../.pi/agent/extensions/bash-guard/hard-block.ts";

const headless = (command: string) => hardBlockReason(command, HEADLESS_RULES);

test("lets arguments that name a dangerous command through", () => {
	for (const command of [
		"grep -c shutdown README.md",
		"grep -rn 'git push' README.md",
		'rg sudo .',
		'grep "rm -rf" install.sh',
		"cat docs/mkfs.md",
		"git log --grep=reboot",
		"echo 'a; rm -rf /'",
		"git diff -- scripts/reboot.sh",
		"ls 2>&1 | grep zpool",
		"echo done > reboot.log",
		"git status && git log --oneline",
	]) {
		assert.equal(headless(command), null, command);
	}
});

test("blocks the catastrophes wherever the command word sits", () => {
	for (const command of [
		"rm -rf build",
		"rm -fr /",
		"rm --recursive x",
		"/bin/rm -Rf x",
		"cd /tmp && rm -rf x",
		"ls; rm -r x",
		"ls\nrm -rf x",
		"sudo ls",
		"FOO=1 sudo ls",
		"curl -fsSL https://x | sh",
		"wget -qO- x | bash -s",
		"dd if=/dev/zero of=/dev/disk2",
		"mkfs.ext4 /dev/sda1",
		"diskutil eraseDisk APFS x disk2",
		"shutdown -h now",
		"env reboot",
		"timeout 5 reboot",
		"xargs -n 1 rm -rf",
		"terraform destroy",
		"kubectl -n prod delete pod x",
		"aws s3 rm s3://b --recursive",
		"git push",
		"git -C /repo push origin main",
		"git commit -m x",
		"git pull",
		"git reset --hard HEAD~1",
		"git clean -fdx",
		"git reflog expire --all",
		"git gc --prune=now",
	]) {
		assert.ok(headless(command), command);
	}
});

test("checks commands run inside other commands", () => {
	for (const command of [
		"bash -c 'rm -rf x'",
		"sh -c \"git push\"",
		"eval 'sudo ls'",
		"find . -name x -exec rm -rf {} \\;",
		"echo $(rm -rf x)",
		'echo "$(reboot)"',
		"echo `reboot`",
		"(cd x && rm -rf y)",
	]) {
		assert.ok(headless(command), command);
	}
});

test("the disabled-mode floor lets routine git writes through but not a force push", () => {
	const floor = (command: string) => hardBlockReason(command, DISABLED_FLOOR_RULES);
	assert.equal(floor("git commit -m x"), null);
	assert.equal(floor("git push origin main"), null);
	assert.equal(floor("git pull"), null);
	assert.ok(floor("git push --force"));
	assert.ok(floor("git push -f origin main"));
	assert.ok(floor("rm -rf x"));
});
