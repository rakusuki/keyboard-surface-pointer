# keyboard-surface-pointer

[日本語](#日本語) | [English](#english)

## 日本語

既存のキーボードで、順番に押されたキーの物理的な位置からマウスポインターを動かす、Windows・Ubuntu・macOS向け試作版 **v0.4.0** です。追加機器は不要です。Windows版はPython標準ライブラリのみ、Ubuntu/macOS版はOS別の依存ライブラリを使用します。

通常のキーボードには接触位置センサーがないため、**触れるだけでは動きません。キーが入力される深さまで押す必要があります。** トラックパッドと同じ精度・操作感を保証するものではなく、押しながらなぞる操作の実用性を検証する段階です。

## 対応環境

- Windows 10 / 11のデスクトップ、ネイティブ版Python 3.10以上。
- 標準的なJIS / USキーボードの数字・文字・記号キー領域。
- Ubuntu版はevdev/uinput、macOS版はQuartzで操作します。下記のOS別手順を参照してください。WSLは対象外です。
- Fnキー、テンキー、分割・特殊配列の座標対応は対象外です。キーボード全体への拡張は今後の課題です。

## 起動（Windows）

PowerShellで次を実行します。Pythonが未導入の場合は https://www.python.org/downloads/windows/ から導入してください。

```powershell
git clone https://github.com/rakusuki/keyboard-surface-pointer.git
cd keyboard-surface-pointer
py -3 pointer.py --check-backend
py -3 pointer.py --dry-run
```

`--check-backend` はWindows APIと構造体サイズを確認し、入力を捕捉しません。`--dry-run` は移動やクリックを送信せず、生成したマウス操作だけをコンソールに表示します。**dry-runでもモード中のキー入力は抑制されます。**

確認後、通常起動します。

```powershell
py -3 pointer.py
```

停止は、モードキーを離してコンソールを選択し、`Ctrl+C` を押してください。

## 操作

| 操作 | 動作 |
|---|---|
| Caps Lockを押している間 | マウス操作モード。Caps Lock自体の通常機能は起動中に抑制されます |
| 最初の文字・数字・記号キー | 基準点を設定。ポインターは動きません |
| 次のキーを押す | 前のキーとの物理座標差で相対移動 |
| `F → G → H` | 右へ移動 |
| `J → K` または `J → K → L` を繰り返す | 逆方向への戻りは移動せず、右移動を繰り返す |
| 最後の移動キーを押し続ける | 0.25秒後から直前の方向へ連続移動。離すと停止 |
| `F → R` | 上へ移動。行の横ずれも反映 |
| Shiftを併用 | 精密移動 |
| スペースを押して離す | 左クリック |
| スペースを押したまま移動 | ドラッグ |
| Enterを押して離す | 右クリック |
| 上 / 下矢印を押す | 上 / 下へスクロール。長押しリピートは無効 |
| すべてのモードキーを離す | モード終了、押下中のマウスボタンも解放 |
| モード中にEsc | モードをキャンセル。再開にはモードキーを離して押し直す |

Caps Lock（または設定したモードキー）を離した後、新たに押すキーは通常のキーボード入力として通します。`Alt+Tab`、`Ctrl+C`、`Win+D`などを使えます。モード中に抑制したキーの遅れた解放だけは対応する押下と対にして抑制し、キー状態が残らないようにします。

**すべてのキーを離してからモードを開始してください。** 他のキーが先に押されている場合、その回のモード起動を無効にします。先に押されたCtrlなどがマウス操作に影響するのを防ぎます。

最初は指一本で `F → G → H` と順番に押す方法を試してください。複数の指は識別できません。指の戻し移動が逆向きの入力にならないよう、モードキーをいったん離し、指を戻してから再開します。Shiftはモード開始後に押してください。

2キーなら `J → K → J → K` で右へ、`K → J → K → J` で左へ動き続けます。繰り返し操作では各キーを離しながら `J → K → L → J → K → L` と押します。LからJへの戻りは、直前の方向に逆らう1キー間隔の移動なので、次のストロークの基準点として扱います。この判定は実際の指を識別するものではなく、意図的な長い逆方向移動も同じ扱いになります。方向を切り替える場合、最初の逆向き入力は基準点の更新のみで、次の同方向入力から動きます。確実に切り替えるにはモードキーを離して押し直し、`K → J` と入力してください。

連続移動には少なくとも2つの異なる移動キーが必要です。`J → K → L` のLを保持すると、直前のKからLへの方向に進み続けます。Lを離す、モードキーを離す、またはEscで停止します。Shiftで連続速度も下げられます。クリックやスクロールを挟むと方向をリセットするため、もう一度キーの移動順を入力してください。

## 感度・配列の設定

`config.json` が標準設定です。既存の個人設定に `"restart_distance": 2.0` がある場合、2キー繰り返しには `1.0` に変更してください。個人用設定は次のように作れます。

```powershell
Copy-Item config.json config.local.json
notepad config.local.json
py -3 pointer.py --config config.local.json
```

| 設定 | 標準値 | 意味 |
|---|---|---|
| `layout` | `"jis"` | `"jis"` または `"us"`。物理座標を切り替え |
| `mode_scan` | `58` | 主モードキー。58=Caps Lock、66=F8、56=Alt/Option、92=右Command（extended=true） |
| `gain` | `32.0` | キー間隔1単位あたりの相対移動指示量 |
| `precision_gain` | `4.0` | Shift中の移動指示量 |
| `stroke_timeout` | `0.45` | この秒数以上の間隔が空くと次のキーは基準点になります |
| `max_step` | `3.0` | 1イベントでこれを超えるキー間距離は移動せず基準点を更新 |
| `restart_distance` | `1.0` | 直前の方向と逆向きにこの距離以上戻ったら、新しいストロークとして扱う |
| `hold_delay` | `0.25` | 最後の移動キーを保持してから連続移動が始まるまでの秒数 |
| `hold_speed` | `320.0` | 連続移動の相対移動指示量／秒 |
| `precision_hold_speed` | `40.0` | Shift中の連続移動速度 |

実際の画面上の移動量はWindowsのマウス速度・加速設定にも影響されます。離れたキーへの移動は別の指や位置の戻しと区別できないため、初版では大きな移動を抑制します。低感度にするとタイムアウト前に押せる速度も含めて調整が必要です。

スキャンコードで扱うため、入力文字やIMEの状態ではなく物理キー位置が基準です。JISの「ろ」「¥」も座標を定義しています。特殊なキーボードでは実機で一致を確認してください。

## 実装と入力の扱い

- `core.py`: 配列座標、相対移動、押下状態、モードとボタン管理。OSから独立。
- `pointer.py`: OS別バックエンドへの起動処理。
- `windows_backend.py`: `WH_KEYBOARD_LL` と `SendInput` を使うWindows処理。
- `ubuntu_backend.py` / `macos_backend.py`: Ubuntu / macOSの入力と出力。
- `keycodes.py`: 各OSの物理キーコードを共通形式に変換。
- `config.json`: 配列・感度の設定。
- `tests/test_core.py`: 入力切り替え、方向、精密操作、クリックなどの回帰テスト。

キー押下と解放を対応づけ、モード終了後に解放されたキーも正しく抑制します。自動リピートは指の移動として扱いません。終了時にはアプリが送信したマウスボタンの解放を試みます。

キー入力履歴のファイル保存・外部送信・ネットワーク通信は実装していません。dry-runでも表示するのは生成したマウス操作のみです。

フックのコールバックでI/Oを行わず、計算と入力送信を短く処理します。ただしWindowsはコールバックのタイムアウトでフックを無通知に解除する場合があります。動かなくなったらプロセスを終了して再起動してください。ハング・強制終了時の完全な復旧は保証できません。

## 検証

```powershell
py -3 -m unittest discover -s tests -v
py -3 -m compileall -q core.py pointer.py
py -3 pointer.py --check-backend
```

GitHub ActionsではWindows / Ubuntu / macOS、Python 3.10 / 3.13でテストし、WindowsではAPIのロードとINPUT構造体のサイズも確認します。**自動テストは実際の指操作、IME、アプリ切り替え、マウスの操作感を検証しません。** 初回実装時はLinuxで計算テストを実施しており、Windows実機での操作は未確認です。

実機で、次の順に確認してください。

1. メモ帳で通常入力ができること。
2. Caps Lockを押しながら `F → G → H`。文字が混入せず右へ移動すること。
3. `F → R`、Shift併用、ゆっくり入力した場合の再基準点化。
4. スペースでクリック、スペースを押したまま移動してドラッグ。
5. ドラッグ中のCaps Lock解放 / Escでマウスボタンが解放されること。
6. モードを離して文字入力へ戻り、Shift・Ctrlなどの押下が残らないこと。
7. 日本語IMEオン、別のアプリ、複数画面でも同じ確認を行うこと。
8. `J → K → L` を3回繰り返し、戻りで左へ動かないこと。
9. 最後のLを保持して連続移動、L解放で停止すること。ShiftとEscも確認すること。
10. `J → K` の繰り返しで右移動、モードを押し直して `K → J` の繰り返しで左移動すること。
11. モードキーを離してからAlt+Tabでアプリ切り替えできること。

## 制約・トラブル

- 通常権限から管理者権限のアプリへの入力送信はUIPIにより制限されます。初版は通常権限のアプリで検証してください。
- UAC画面、ロック画面、ログイン画面は対象外です。
- 同時押しを認識できる組み合わせはキーボードに依存します。まず1本指で試してください。
- 複数起動や他のキーリマップソフトとの併用は避けてください。
- コンソールの選択によるプロセス停止は避けてください。停止するとフックがタイムアウトする可能性があります。
- 接触検出、キー内部の細かい位置、複数指識別、連続的な高解像度追跡はできません。
- 移動キーを保持している間だけ連続移動します。解放後の慣性移動は行いません。キー間の接触位置の補間は未実装です。

## 先行研究・技術資料

- [KeySlide: Using Directional Gestures on Keyboard for Cursor Positioning](https://arihantparsoya.github.io/portfolio/files/papers/keyslide.pdf) (2019): 物理キー上のジェスチャによる主にテキストカーソルの操作。本実装は論文のコードを流用せず、OSのマウスポインターを対象とする独立した試作です。
- [LowLevelKeyboardProc](https://learn.microsoft.com/en-us/windows/win32/winmsg/lowlevelkeyboardproc)
- [SendInput](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-sendinput)

## ライセンス

本プロジェクトは [MIT License](LICENSE) のOSSです。

**Copyright (c) 2026 rakusuki。著作権は保持しており、パブリックドメインへの放棄ではありません。**

利用・改変・再配布・商用利用を認めます。ソフトウェアのすべての複製または重要な部分には、著作権表示と許諾表示を含める必要があります。無保証で提供します。正式な条件は [LICENSE](LICENSE) の全文を参照してください。


## English

### Overview

**v0.4.0** is a Windows, Ubuntu, and macOS prototype that moves the mouse pointer using the physical positions of keys pressed in sequence on an ordinary keyboard. No additional hardware is required. Windows uses the Python standard library; Ubuntu and macOS require platform-specific dependencies.

**Touch alone cannot be detected: each key must be pressed far enough to register.** This prototype evaluates the practicality of moving across keycaps while pressing them; it does not promise trackpad-level precision or comfort.

### Requirements

- Windows 10 / 11 desktop with native Python 3.10 or later.
- Standard JIS or US number, letter, and symbol key areas.
- Ubuntu uses evdev/uinput; macOS uses Quartz. See the platform-specific instructions below. WSL is unsupported.
- Fn keys, numeric keypads, split keyboards, and custom physical layouts are not mapped. Whole-keyboard coverage is future work.

### Getting started (Windows)

Run in PowerShell. Install Python from [python.org](https://www.python.org/downloads/windows/) if needed.

```powershell
git clone https://github.com/rakusuki/keyboard-surface-pointer.git
cd keyboard-surface-pointer
py -3 pointer.py --check-backend
py -3 pointer.py --dry-run
```

`--check-backend` validates Windows API bindings and structure size without capturing input. `--dry-run` prints generated mouse actions without sending mouse events. **Keys are still suppressed while pointing mode is active in dry-run.**

Then start normal operation:

```powershell
py -3 pointer.py
```

To stop, release the mode key, focus the console, and press `Ctrl+C`.

### Controls

| Action | Behavior |
|---|---|
| Hold Caps Lock | Activate pointing mode. Its normal Caps Lock function is suppressed while the application runs |
| Press the first mapped key | Set an anchor without moving the pointer |
| Press the next mapped key | Move relative to the physical position of the previous key |
| `F → G → H` | Move right |
| Repeat `J → K` or `J → K → L` | The return against the preceding direction re-anchors without moving backward |
| Hold the final movement key | Continue in the preceding direction after 0.25 seconds; release to stop |
| `F → R` | Move upward, including the physical row offset |
| Hold Shift in pointing mode | Use precision movement |
| Press and release Space | Left click |
| Hold Space while moving | Drag |
| Press and release Enter | Right click |
| Press Up / Down arrow | Scroll up / down; auto-repeat is ignored |
| Release all mode keys | Exit pointing mode and release mouse buttons held by the application |
| Press Esc in pointing mode | Cancel the mode; release and press the mode key again to reactivate |

After releasing Caps Lock (or the configured mode key), newly pressed keys pass through as normal keyboard input, including `Alt+Tab`, `Ctrl+C`, and `Win+D`. Late releases of keys consumed during pointing remain paired with their consumed presses.

**Release all other keys before starting pointing mode.** If another key is already held, that activation is disabled to prevent previously held modifiers such as Ctrl from affecting mouse actions.

Start with one finger and press `F → G → H` in sequence. Individual fingers cannot be distinguished. To reposition without moving backward, release the mode key, move your finger back, and activate the mode again. Press Shift after activating the mode.

Two-key strokes work as `J → K → J → K` for rightward movement or `K → J → K → J` for leftward movement. Release each movement key between presses when repeating `J → K → L → J → K → L`. A return of at least one key pitch against the previous direction is treated as repositioning. This is a heuristic, not finger identification; an intentional long reversal is also treated as a new stroke. The first reversed step re-anchors; a second step in that direction moves the pointer. To switch direction explicitly, release and reactivate the mode, then press `K → J` to move left.

Continuous motion requires at least two different movement keys. Hold L after `J → K → L` to continue in the direction from K to L. Release L, release the mode key, or press Esc to stop. Shift also reduces continuous speed. Clicking or scrolling resets the direction, so enter another key sequence afterward.

### Configuration

The default settings are in `config.json`. If an existing personal configuration contains `"restart_distance": 2.0`, change it to `1.0` to enable two-key repetition. Create a personal configuration:

```powershell
Copy-Item config.json config.local.json
notepad config.local.json
py -3 pointer.py --config config.local.json
```

| Setting | Default | Meaning |
|---|---|---|
| `layout` | `"jis"` | Physical layout: `"jis"` or `"us"` |
| `mode_scan` | `58` | Primary mode: 58=Caps Lock, 66=F8, 56=Alt/Option, 92=right Command (extended=true) |
| `gain` | `32.0` | Relative movement units per standard key pitch |
| `precision_gain` | `4.0` | Movement units while Shift is held |
| `stroke_timeout` | `0.45` | A gap longer than this many seconds makes the next key a new anchor |
| `max_step` | `3.0` | A key-to-key distance exceeding this threshold re-anchors instead of moving |
| `restart_distance` | `1.0` | A return against the previous direction at or above this distance starts a new stroke |
| `hold_delay` | `0.25` | Seconds before holding the final movement key starts continuous motion |
| `hold_speed` | `320.0` | Continuous relative movement units per second |
| `precision_hold_speed` | `40.0` | Continuous movement speed while Shift is held |

Windows mouse speed and acceleration settings also affect the resulting pointer movement. Distant key presses may come from another finger or repositioning, so large jumps are suppressed. Adjust sensitivity and timeout together to suit your pressing speed.

The engine uses physical scan codes rather than typed characters or IME state. JIS `ろ` and `¥` positions are included. Verify position mappings on unusual keyboards.

### Architecture and input handling

- `core.py`: OS-independent physical coordinates, relative movement, held-key ownership, mode state, and mouse-button state.
- `pointer.py`: Cross-platform entry point.
- `windows_backend.py`: Windows backend using `WH_KEYBOARD_LL` and `SendInput`.
- `ubuntu_backend.py` / `macos_backend.py`: Ubuntu / macOS input and output.
- `keycodes.py`: Physical-key normalization for the shared engine.
- `config.json`: Layout and sensitivity settings.
- `tests/test_core.py`: Regression tests for mode switching, movement, precision, and clicks.

Key-down and key-up events are paired so that releases of consumed keys remain suppressed after the mode ends. Auto-repeat does not count as finger movement. On shutdown, the application attempts to release mouse buttons it pressed.

No key-history file logging, external transmission, or network communication is implemented. Dry-run prints generated mouse actions only.

The hook callback avoids console/file I/O and keeps processing short. Windows can silently remove a hook if its callback times out. If control stops working, stop and restart the process. Complete recovery from hangs or forced termination is not guaranteed.

### Verification

```powershell
py -3 -m unittest discover -s tests -v
py -3 -m compileall -q core.py pointer.py
py -3 pointer.py --check-backend
```

GitHub Actions is configured for Windows, Ubuntu, and macOS with Python 3.10 and 3.13. Windows jobs also check API loading and the INPUT structure size. **Automated tests do not verify physical gestures, IME interactions, application switching, or pointer comfort.** Initial engine verification was performed on Linux; interactive operation on a physical Windows machine has not been verified.

Manual checklist:

1. Confirm normal typing in Notepad.
2. Hold Caps Lock and press `F → G → H`; verify rightward movement without typed characters.
3. Try `F → R`, Shift precision, and slow presses that trigger re-anchoring.
4. Click with Space and drag while holding Space.
5. Release Caps Lock or press Esc during a drag; verify mouse-button release.
6. Return to typing and confirm Shift/Ctrl do not remain logically held.
7. Repeat with Japanese IME enabled, other applications, and multiple monitors.
8. Repeat `J → K → L` three times and verify that returns do not move left.
9. Hold the final L to continue moving, release to stop, and test Shift and Esc.
10. Repeat `J → K` to move right, reactivate the mode, and repeat `K → J` to move left.
11. Release the mode key and verify normal Alt+Tab application switching.

### Limitations and troubleshooting

- UIPI restricts input injection from a normal-privilege application into an elevated application. Test with normal-privilege applications first.
- UAC prompts, lock screens, and sign-in screens are outside the supported scope.
- Supported simultaneous key combinations depend on the keyboard. Start with one finger.
- Avoid multiple instances and other keyboard remapping tools during testing.
- Avoid console selection that pauses the process; it may cause the hook to time out.
- Touch detection, sub-key position tracking, finger identification, and continuous high-resolution tracking are unavailable.
- Continuous motion operates only while the final movement key is held. There is no inertia after release or interpolation of contact positions between keys.

### Prior work and technical references

- [KeySlide: Using Directional Gestures on Keyboard for Cursor Positioning](https://arihantparsoya.github.io/portfolio/files/papers/keyslide.pdf) (2019): Physical-keyboard gestures primarily for text-cursor positioning. This project is an independent prototype for the OS mouse pointer and does not reuse the paper's code.
- [LowLevelKeyboardProc](https://learn.microsoft.com/en-us/windows/win32/winmsg/lowlevelkeyboardproc)
- [SendInput](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-sendinput)

### License and copyright

This project is open-source software under the [MIT License](LICENSE).

**Copyright (c) 2026 rakusuki. Copyright is retained; the code is not dedicated to the public domain.**

The license permits use, modification, redistribution, and commercial use, provided its copyright notice and permission notice are included in all copies or substantial portions of the software. The software is provided without warranty. See [LICENSE](LICENSE) for the full terms.


## Ubuntu版の導入 / Ubuntu setup

UbuntuデスクトップでPython 3.10以上を使用します。X11/WaylandのアプリAPIではなく、evdev/uinputのデバイス層で入出力する構成です。実デスクトップでの操作は未検証です。選択した1台のキーボードのみを対象とします。

Use Python 3.10+ on an Ubuntu desktop. Input/output uses evdev/uinput rather than X11/Wayland application APIs. Interactive desktop operation has not been verified. Only one explicitly selected keyboard is handled.

```bash
git pull --ff-only
sudo apt update
sudo apt install python3-venv python3-dev build-essential linux-libc-dev
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-ubuntu.txt
.venv/bin/python pointer.py --check-backend
sudo modprobe uinput
sudo .venv/bin/python pointer.py --list-devices
```

一覧の実キーボードを選び、下記の `/dev/input/eventN` をそのパスに置き換えてください。イベント番号は再起動や抜き差しで変わる場合があります。

Select the physical keyboard from the list and replace `/dev/input/eventN` below with its path. Event numbers may change after reboot or reconnection.

```bash
sudo .venv/bin/python pointer.py --device /dev/input/eventN --dry-run
# Stop with Ctrl+C, then start normally:
sudo .venv/bin/python pointer.py --device /dev/input/eventN
```

- Caps Lockを保持して操作。解放後は通常入力を仮想デバイス経由で転送し、Alt+Tabなどを使えます。
- Hold Caps Lock to point. Outside the mode, keyboard events are forwarded through a virtual input device, including Alt+Tab.
- 選択キーボードを排他的に取得します。入力デバイスと `/dev/uinput` へのアクセスが必要なため、試作段階では `sudo` で実行します。sudoでpipのインストールは行いません。
- The selected keyboard is grabbed exclusively. The prototype uses `sudo` for input-device and `/dev/uinput` access; dependency installation runs without sudo.
- 停止はモード解除後に端末でCtrl+C、または選択キーボードで **左Ctrl+Alt+Esc**。端末を閉じる前に停止してください。キーボード切断・入力欠落時は終了して再起動します。正常終了時は仮想キーを解放し、grabを解除します。
- Stop with Ctrl+C in the terminal after leaving pointing mode, or **left Ctrl+Alt+Esc** on the selected keyboard. Stop before closing the terminal. Restart after disconnection or dropped events. Cleanup releases virtual keys and the exclusive grab.
- 仮想入力デバイスのCaps Lock LED同期、複数キーボードの一体処理は未実装です。別のキーボードで押す修飾キーは追跡しません。他キーボードの修飾キーも離して試してください。
- Caps Lock LED synchronization and combined handling of multiple keyboards are not implemented. Modifiers held on other keyboards are not tracked; release them during testing.

## v0.4.0：左右の手で操作 / Point with either hand

| OS | 右手で移動 / Right-hand pointing | 左手で移動 / Left-hand pointing |
|---|---|---|
| Windows / Ubuntu | Caps Lock保持 / Hold Caps Lock | 右Alt保持 / Hold right Alt |
| macOS（JIS / US） | 左Option保持 / Hold left Option | 右Command保持 / Hold right Command |

モードキーはトグルではなく保持式です。いずれかを保持している間は操作を継続し、すべて離すと停止します。Escで解除した場合は、すべてのモードキーを離してから押し直してください。文字キーを含め、ほかのキーを先に押している場合は誤操作防止のため開始しません。

Mode keys are hold-to-use, not toggles. Either key keeps the mode active; releasing all stops movement and releases mouse buttons. After Escape, release all mode keys before starting again. Pre-held non-mode keys prevent activation.

主キーは `mode_scan` と `mode_extended`、追加キーは `extra_mode_keys` の `[scan, extended]` 配列で指定します。既存のカスタム設定はそのまま読み込めますが、追加キーは自動追加されません。

Set the primary key with `mode_scan` and `mode_extended`, and additional keys with `extra_mode_keys`, a list of `[scan, extended]` pairs. Legacy custom configs still load; additional keys are not inserted automatically.

```json
{"mode_scan": 56, "mode_extended": false, "extra_mode_keys": [[92, true]]}
```

上記はMacの左Option＋右Commandです。Windows/Ubuntuは `mode_scan: 58`、`mode_extended: false`、`extra_mode_keys: [[56, true]]` が標準です。追加キーを無効にするには `extra_mode_keys: []` にします。AltGr配列では右AltがCtrl併用として通知される場合があるため、右Altを無効化しF8 `[66, false]` などに変更してください。予約したキー本来のショートカットは起動中使えません。通常のAlt+Tabは左Altを使います。

The example reserves Mac left Option and right Command. Windows/Ubuntu ship with primary scan 58, extended false, and extra keys `[[56, true]]`. Use `extra_mode_keys: []` to disable extra keys. On AltGr layouts, right Alt may generate a companion Ctrl event; disable it and choose F8 `[66, false]` instead. Reserved keys lose their normal shortcuts while running. Use left Alt for normal Alt+Tab.

共通処理・キー変換・修飾フラグの自動テストは45件成功しました。今回の追加機能は各OSの実機では未検証です。

45 automated tests pass for shared logic, key mappings and modifier flags. This update has not been verified on physical desktops.

## macOS版の導入 / macOS setup

macOSの標準モードキーは **左Optionと右Command** です。左Optionを保持して右手で操作、右Commandを保持して左手で操作できます。F8も右Optionも不要です。`config.macos.json` はmacOSで自動選択されます。Caps Lockの物理的な押下・解放には対応しません。

macOS defaults to **left Option and right Command**: hold left Option for right-hand pointing, or right Command for left-hand pointing. Neither F8 nor right Option is required. `config.macos.json` is selected automatically. Caps Lock is not supported as a physical hold key.

```bash
git pull --ff-only
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-macos.txt
.venv/bin/python pointer.py --check-backend
.venv/bin/python pointer.py --dry-run
```

「システム設定 → プライバシーとセキュリティ」の **入力監視** と **アクセシビリティ** で、起動に使うTerminal/iTerm/VSCodeなど、macOSが対象として表示するアプリへ権限を付与してください。許可後はそのアプリを再起動し、再実行します。sudoは使いません。

Grant **Input Monitoring** and **Accessibility** in System Settings → Privacy & Security to the terminal/IDE or Python application identified by macOS. Restart that application after granting access, then rerun. Do not use sudo.

```bash
.venv/bin/python pointer.py
```

- 左Option保持中に `J → K → J → K`、または右Command保持中に `A → S → A → S` で右へ移動します。逆順なら左へ移動します。最後のキーを保持すると連続移動します。
- Hold left Option and repeat `J → K`, or hold right Command and repeat `A → S`, to move right. Reverse the order for leftward motion; hold the final key for continuous motion.
- すべてのモードキーを離すと通常入力へ戻ります。Shiftは精密操作、Spaceは左クリック/ドラッグ、Returnは右クリック、上下矢印はスクロールです。
- Release all mode keys to return to typing. Shift: precision; Space: left click/drag; Return: right click; Up/Down: scroll.
- 起動中は左Optionと右Commandがモード専用です。通常のCommand+Tab/Command+Cなどには **左Command** を使用してください。Option入力が必要なら設定変更またはアプリ停止を行ってください。
- While running, left Option and right Command are reserved. Use **left Command** for normal Command+Tab/Command+C shortcuts. Reconfigure or stop the application to restore reserved Option input.
- Secure Input、ログイン画面、権限がないアプリでは入力取得・操作できない場合があります。入力タップが無効化された場合は終了して再起動します。
- Secure Input, sign-in screens, and missing permissions can prevent capture or control. Restart if macOS disables the event tap.

## OS別の検証範囲 / Platform verification scope

共通エンジンとOS別キー変換は自動テスト対象です。CIは各OSの依存ライブラリの読み込みも確認する構成です。Ubuntuのgrab/uinput経路やmacOSの権限付きイベントタップの実操作はCIでは検証しません。Ubuntu/macOSは新規バックエンドの試作で、実機動作を確認済みとはしていません。

Automated tests cover the shared engine and key mappings. CI is configured to check platform dependency imports too. It does not exercise an Ubuntu keyboard grab/uinput path or an authorized interactive macOS event tap. These are new prototype backends; physical desktop operation is not claimed as verified.

参考 / References:
- [python-evdev tutorial](https://python-evdev.readthedocs.io/en/stable/tutorial.html)
- [PyObjC Quartz notes](https://pyobjc.readthedocs.io/en/latest/apinotes/Quartz.html)
- [Apple Quartz Event Services](https://developer.apple.com/documentation/coregraphics/quartz-event-services)
