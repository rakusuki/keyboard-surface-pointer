# keyboard-surface-pointer

[日本語](#日本語) | [English](#english)

## 日本語

既存のキーボードで、順番に押されたキーの物理的な位置からマウスポインターを動かす、Windows向け試作版 **v0.2.0** です。追加機器・外部Pythonライブラリは不要です。

通常のキーボードには接触位置センサーがないため、**触れるだけでは動きません。キーが入力される深さまで押す必要があります。** トラックパッドと同じ精度・操作感を保証するものではなく、押しながらなぞる操作の実用性を検証する段階です。

## 対応環境

- Windows 10 / 11のデスクトップ、ネイティブ版Python 3.10以上。
- 標準的なJIS / USキーボードの数字・文字・記号キー領域。
- WSL、macOS、Linuxでの実マウス操作には未対応。計算部分のテストはLinuxでも実行できます。
- Fnキー、テンキー、分割・特殊配列の座標対応は対象外です。キーボード全体への拡張は今後の課題です。

## 起動

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
| `J → K → L` を繰り返す | LからJへ戻る際は移動せず、右移動を繰り返す |
| 最後の移動キーを押し続ける | 0.25秒後から直前の方向へ連続移動。離すと停止 |
| `F → R` | 上へ移動。行の横ずれも反映 |
| Shiftを併用 | 精密移動 |
| スペースを押して離す | 左クリック |
| スペースを押したまま移動 | ドラッグ |
| Enterを押して離す | 右クリック |
| 上 / 下矢印を押す | 上 / 下へスクロール。長押しリピートは無効 |
| Caps Lockを離す | モード終了、押下中のマウスボタンも解放 |
| モード中にEsc | モードをキャンセル。再開にはモードキーを離して押し直す |

**すべてのキーを離してからモードを開始してください。** 他のキーが先に押されている場合、その回のモード起動を無効にします。先に押されたCtrlなどがマウス操作に影響するのを防ぎます。

最初は指一本で `F → G → H` と順番に押す方法を試してください。複数の指は識別できません。指の戻し移動が逆向きの入力にならないよう、モードキーをいったん離し、指を戻してから再開します。Shiftはモード開始後に押してください。

繰り返し操作では各キーを離しながら `J → K → L → J → K → L` と押します。LからJへの戻りは、直前の方向に逆らう2キー間隔の移動なので、次のストロークの基準点として扱います。この判定は実際の指を識別するものではなく、意図的な長い逆方向移動も同じ扱いになります。隣接キーへ戻る `L → K → J` なら左へ動かせます。

連続移動には少なくとも2つの異なる移動キーが必要です。`J → K → L` のLを保持すると、直前のKからLへの方向に進み続けます。Lを離す、モードキーを離す、またはEscで停止します。Shiftで連続速度も下げられます。クリックやスクロールを挟むと方向をリセットするため、もう一度キーの移動順を入力してください。

## 感度・配列の設定

`config.json` が標準設定です。個人用設定は次のように作れます。

```powershell
Copy-Item config.json config.local.json
notepad config.local.json
py -3 pointer.py --config config.local.json
```

| 設定 | 標準値 | 意味 |
|---|---|---|
| `layout` | `"jis"` | `"jis"` または `"us"`。物理座標を切り替え |
| `mode_scan` | `58` | Caps Lock。`66` にするとF8。ほかの値は受け付けません |
| `gain` | `32.0` | キー間隔1単位あたりの相対移動指示量 |
| `precision_gain` | `4.0` | Shift中の移動指示量 |
| `stroke_timeout` | `0.45` | この秒数以上の間隔が空くと次のキーは基準点になります |
| `max_step` | `3.0` | 1イベントでこれを超えるキー間距離は移動せず基準点を更新 |
| `restart_distance` | `2.0` | 直前の方向と逆向きにこの距離以上戻ったら、新しいストロークとして扱う |
| `hold_delay` | `0.25` | 最後の移動キーを保持してから連続移動が始まるまでの秒数 |
| `hold_speed` | `320.0` | 連続移動の相対移動指示量／秒 |
| `precision_hold_speed` | `40.0` | Shift中の連続移動速度 |

実際の画面上の移動量はWindowsのマウス速度・加速設定にも影響されます。離れたキーへの移動は別の指や位置の戻しと区別できないため、初版では大きな移動を抑制します。低感度にするとタイムアウト前に押せる速度も含めて調整が必要です。

スキャンコードで扱うため、入力文字やIMEの状態ではなく物理キー位置が基準です。JISの「ろ」「¥」も座標を定義しています。特殊なキーボードでは実機で一致を確認してください。

## 実装と入力の扱い

- `core.py`: 配列座標、相対移動、押下状態、モードとボタン管理。OSから独立。
- `pointer.py`: `WH_KEYBOARD_LL` と `SendInput` を使うWindows常駐処理。
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

GitHub ActionsではWindows / Ubuntu、Python 3.10 / 3.13でテストし、WindowsではAPIのロードとINPUT構造体のサイズも確認します。**自動テストは実際の指操作、IME、アプリ切り替え、マウスの操作感を検証しません。** 初回実装時はLinuxで計算テストを実施しており、Windows実機での操作は未確認です。

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

**v0.2.0** is a Windows prototype that moves the mouse pointer using the physical positions of keys pressed in sequence on an ordinary keyboard. No additional hardware or third-party Python libraries are required.

**Touch alone cannot be detected: each key must be pressed far enough to register.** This prototype evaluates the practicality of moving across keycaps while pressing them; it does not promise trackpad-level precision or comfort.

### Requirements

- Windows 10 / 11 desktop with native Python 3.10 or later.
- Standard JIS or US number, letter, and symbol key areas.
- Actual pointer control is not supported on WSL, macOS, or Linux. The engine tests can run on Linux.
- Fn keys, numeric keypads, split keyboards, and custom physical layouts are not mapped. Whole-keyboard coverage is future work.

### Getting started

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
| Repeat `J → K → L` | The return from L to J re-anchors without moving backward |
| Hold the final movement key | Continue in the preceding direction after 0.25 seconds; release to stop |
| `F → R` | Move upward, including the physical row offset |
| Hold Shift in pointing mode | Use precision movement |
| Press and release Space | Left click |
| Hold Space while moving | Drag |
| Press and release Enter | Right click |
| Press Up / Down arrow | Scroll up / down; auto-repeat is ignored |
| Release Caps Lock | Exit pointing mode and release mouse buttons held by the application |
| Press Esc in pointing mode | Cancel the mode; release and press the mode key again to reactivate |

**Release all other keys before starting pointing mode.** If another key is already held, that activation is disabled to prevent previously held modifiers such as Ctrl from affecting mouse actions.

Start with one finger and press `F → G → H` in sequence. Individual fingers cannot be distinguished. To reposition without moving backward, release the mode key, move your finger back, and activate the mode again. Press Shift after activating the mode.

Release each movement key between presses when repeating `J → K → L → J → K → L`. A return of at least two key pitches against the previous direction is treated as repositioning. This is a heuristic, not finger identification; an intentional long reversal is also treated as a new stroke. Use adjacent reversals such as `L → K → J` to move left.

Continuous motion requires at least two different movement keys. Hold L after `J → K → L` to continue in the direction from K to L. Release L, release the mode key, or press Esc to stop. Shift also reduces continuous speed. Clicking or scrolling resets the direction, so enter another key sequence afterward.

### Configuration

The default settings are in `config.json`. Create a personal configuration:

```powershell
Copy-Item config.json config.local.json
notepad config.local.json
py -3 pointer.py --config config.local.json
```

| Setting | Default | Meaning |
|---|---|---|
| `layout` | `"jis"` | Physical layout: `"jis"` or `"us"` |
| `mode_scan` | `58` | Caps Lock; use `66` for F8. Other values are rejected |
| `gain` | `32.0` | Relative movement units per standard key pitch |
| `precision_gain` | `4.0` | Movement units while Shift is held |
| `stroke_timeout` | `0.45` | A gap longer than this many seconds makes the next key a new anchor |
| `max_step` | `3.0` | A key-to-key distance exceeding this threshold re-anchors instead of moving |
| `restart_distance` | `2.0` | A return against the previous direction at or above this distance starts a new stroke |
| `hold_delay` | `0.25` | Seconds before holding the final movement key starts continuous motion |
| `hold_speed` | `320.0` | Continuous relative movement units per second |
| `precision_hold_speed` | `40.0` | Continuous movement speed while Shift is held |

Windows mouse speed and acceleration settings also affect the resulting pointer movement. Distant key presses may come from another finger or repositioning, so large jumps are suppressed. Adjust sensitivity and timeout together to suit your pressing speed.

The engine uses physical scan codes rather than typed characters or IME state. JIS `ろ` and `¥` positions are included. Verify position mappings on unusual keyboards.

### Architecture and input handling

- `core.py`: OS-independent physical coordinates, relative movement, held-key ownership, mode state, and mouse-button state.
- `pointer.py`: Windows backend using `WH_KEYBOARD_LL` and `SendInput`.
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

GitHub Actions is configured for Windows and Ubuntu with Python 3.10 and 3.13. Windows jobs also check API loading and the INPUT structure size. **Automated tests do not verify physical gestures, IME interactions, application switching, or pointer comfort.** Initial engine verification was performed on Linux; interactive operation on a physical Windows machine has not been verified.

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
