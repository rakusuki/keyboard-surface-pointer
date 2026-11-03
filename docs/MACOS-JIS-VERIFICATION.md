# macOS JIS v0.4.0 regression verification

## 実施範囲（2026-11-03）

対象基準: `32acfeef899e8d0ab1d4c304b06d83707afb2f66`。
Linux / Python 3.12の模擬Quartzイベントで既存45件＋追加6件＝51件成功。
macOS / Windows / Ubuntuデスクトップの実操作は今回実施していません。

既存 `test_dual_mode.py` は左右キー、両モードキーの解放順序、ドラッグ解放、Esc、左Command+Tabを共通エンジンで検証します。
追加 `test_macos_backend.py` は実際の `run()` を偽Quartz/CoreFoundationで動かし、イベントコード・フラグ・抑制・マウス送信を照合します。

- 右Commandの素早い押下・解放、左手A→S、ドラッグ中解除、遅れたSpace/S解放、左Command+C/Tabへの復帰。
- 左手の保持移動、Shift精密移動、移動キー解放後の停止。
- 左Option/J→Kのdry-runでマウスを送信しないこと。
- 起動前から押下されていた右Commandのフラグと解放をOSへ渡すこと。
- Command/Option/Shift/Controlの左右別判定と、反対側保持中の解放。

旧バックエンドへ差し戻す比較では、HID照会が既に解放状態の模擬ケースで3件失敗しました（新しい判定ヘルパーを残して比較）。これはイベント配送時点と後続のHID照会時点のずれへの回帰テストであり、実機での発生頻度を示すものではありません。

## 修正点と制約

`flagsChanged` の押下・解放はイベント自身の左右別device-dependentフラグを使用します。Command全体のフラグだけでは、左Command保持中の右Command解放を判別できません。起動時のHID照会は初期状態を取得する目的で残します。

フラグ除去では、起動前からOSに渡っていた予約キーを保持します。予約キーの新しい押下は引き続きモード専用です。

左右別フラグが実キーボード・リマップ環境で想定どおり届くか、JIS配列、IME、権限、Secure Input、ポインターの操作感は実機確認が必要です。

## 安全な実機手順

作業を保存し、他のリマップソフトと本アプリの別プロセスを停止してください。
Terminalと空のTextEdit書類を使用し、トラックパッド/マウスを手元に置きます。
ドラッグはTextEditの選択だけで試し、ファイル移動や削除ボタン上では行いません。
全キーを離して起動します。sudoは不要です。

```bash
git fetch origin
git switch fix/macos-jis-mode-regressions
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-macos.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python pointer.py --check-backend
.venv/bin/python pointer.py --dry-run
```

入力監視・アクセシビリティの許可が必要なら、READMEどおり起動アプリに付与して再起動してください。
dry-run中もモード中のキーは抑制されます。マウスは動きません。
異常時は全キーを離し、トラックパッドでTerminalを選びCtrl+C。
停止できない場合はアクティビティモニタで対象Pythonプロセスを終了します。
停止後に物理Space/Returnを押して離し、マウスボタンの状態を確認してください。強制終了時の自動復旧は保証されません。

| 順序 | 入力 | 期待結果 |
|---|---|---|
| 1 | 右Command保持→Aを押して離す→Sを保持 | 右向きmove、約0.25秒後から連続move。A/Sが書類に入らない |
| 2 | Sを離す。右Commandも離す | moveが停止。次の通常文字入力は通る |
| 3 | モードを押し直しS→A、Aを保持 | 左向き連続move |
| 4 | 右Commandの短い押下・解放を10回。毎回その後に通常文字入力 | モードやCommandが残らない |
| 5 | 左Option保持→J→K、Kを保持・解放 | 同様に右移動と停止 |
| 6 | 両モードキーを保持→一方だけ離す→残りを離す。順序を逆にして再試行 | 一方保持中は継続、最後の解放で停止 |
| 7 | 左Commandを先に保持→右Commandを押して離す→左Command+C/Tab | 誤ってモード開始せず、左Command操作が使える |
| 8 | 全モードキー解放後に左Command+C/V、左Command+Tab | 通常のコピー・貼り付け・アプリ切り替えが可能 |

次にCtrl+Cで停止し、実出力で起動します。

```bash
.venv/bin/python pointer.py
```

1. 表の1〜8を再試行します。最初は一指で、画面中央の空の書類上で行います。
2. 右Command保持→Space保持→A→Sでテキストを選択します。Spaceを保持したまま右Commandを離します。選択が終了し、その後のポインター移動で選択が伸びないことを確認。最後にSpace/Sを離します。
3. 両モードキーで同じドラッグを行い、一方の解放では継続、最後の解放で終了することを両順序で確認します。
4. ドラッグ中Escで即座に終了することを確認。全モードキーを離すまでは再開しないことを確認します。
5. 最後の移動キー保持中にShiftを押すと低速になり、Shift解放で通常速度へ戻ることを確認します。
6. 日本語IMEのオン/オフで再試行し、モード終了後に日本語・英字を通常入力できることを確認します。
7. アプリ停止後は右Command+C/Tabと左Option本来の操作も戻ることを確認します。

**起動中の右Commandは、モードを離した後も通常ショートカット用には戻りません。次の押下で再びモードになります。通常ショートカットには左Commandを使用します。** 右Commandを通常用途に戻すには停止、または `extra_mode_keys: []` へ設定変更して再起動します。

記録: macOS版、Mac機種、内蔵/外付けJISと型番、Python版、コミット、IME、リマップ有無、上記各項目の合否、異常時の入力順を残してください。未実施項目は「未実施」と記録します。
