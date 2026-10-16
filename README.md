# shanhao-experiments
シャンハオ実験専用リポジトリ

AIを活用した小さな実験と、その検証結果を公開するためのリポジトリです。

実験段階の内容を含みます。

## 世界一重たくてクソ怠いファッキンクレイジーな HELLO WORLD 表示 Project

11 文字を出す。それだけのために 11 件の議案を提出し、55 票を集め、11 通の成立証明を発行し、議事録を編纂する。書類が 1 枚でも失われれば表示を拒否する。

第 1 週 `2026-10-03`: **文字議会**。待機や無限ループで遅くしているわけではなく、各段階の成果物が次の段階に必要になる。今週は工程の無駄を増やす低負荷版。高負荷モードはない。

第 2 週 `2026-10-10`: **議案言語局**。提出前に 8 語の独自辞書を生成し、11 件の議案を翻訳、逆翻訳して原案との一致を検査する。文字議会は逆翻訳された議案を採決する。辞書・翻訳・逆翻訳のどれかが欠けても表示を拒否する。前週の 55 票・成立証明・議事録は全部必要なまま。

第 3 週 `2026-10-17`: **履歴監査院**。翻訳担当とも採決担当とも別の検証器が、11 件の原案・翻訳・逆翻訳・55 票を照合し、鎖につないだ 11 枚の履歴証明を発行する。成立証明にこの履歴一式を添付し、議事録係が再監査する。証明が欠けたり変わったりすると表示できない。旧工程と 4 ファイルの上限は維持する。

### 0. 準備委員会

必要環境: Linux、CPython **3.12.14**（検証版）、標準ライブラリだけ。CPU affinity と Unix の `resource` が使えること。依存インストール・API キー・通信・課金は不要。README 以下のコマンドは repo のルートで実行する。

```sh
python3 --version
# 検証版: Python 3.12.14
python3 -B -m hello_world.cli limits --run-id preflight
```

制限の JSON が stderr に出る。機能不足や制限適用失敗なら先へ進まない。

### 1. 議案受理窓口

新しい台帳名 `ceremony` を選ぶ。同名に前回の成果物がある場合は、別名にする。途中の書類を上書きして揉み消す機能はない。

```sh
python3 -B -m hello_world.cli stage proposal --run-id ceremony
```

11 の位置番号、11 の議案番号、11 の文字コードが `.hello-world/runs/ceremony/proposal.json` に提出される。まだ表示できない。

この受付の内部で辞書生成→翻訳→逆翻訳を順に実行する。`proposal.json` の `payload.language` に `dictionary`、`translated`、`backtranslated` を収録し、追加ファイルを作らず 4 成果物の上限を保つ。`s00`〜`s07` は固定文字コード集合を昇順に対応させた小さな人工語で、自然言語翻訳や外部 AI API は使わない。

### 2. 五委員会合同採決

```sh
python3 -B -m hello_world.cli stage ballot --run-id ceremony
```

位置委員・ASCII 委員・議題委員・件数委員・印字委員の 55 票を `ballot.json` に記録する。議案がない、変更された、あるいは余計な書類がある場合は受理しない。

### 3. 成立証明発行局

```sh
python3 -B -m hello_world.cli stage certificate --run-id ceremony
```

この窓口内で独立した履歴検証器を通す。保存済みの原案・投票を先頭から検査した後、固定原案の翻訳記録と投票の対応を別実装で照合し、11 枚の連鎖証明を作る。定足数と過半数を検査し、投票のハッシュと必須の `payload.history` を含む `certificate.json` を発行する。ハッシュは改変検出用で、法的な署名ではない。

### 4. 議事録編纂室

```sh
python3 -B -m hello_world.cli stage minutes --run-id ceremony
```

履歴証明と 55 票を再監査し、成立証明がその投票に対応することを照合して位置順に並べ、`minutes.json` に収録する。ここまで来ても stdout は空である。

### 5. 表示許可の執行

```sh
python3 -B -m hello_world.cli show --run-id ceremony
```

ここで初めて stdout に `HELLO WORLD` と LF、合計 12 バイトが出る。コード 0 が正常終了。進捗・診断は stderr にだけ出る。

### 6. 全工程 smoke と出力監査

独立した新しい台帳で全工程を通す。stdout はファイルに保存せず比較するので、ログを増やす監査委員会は不要。

```sh
python3 -B - <<'PY'
import subprocess, sys
p = subprocess.run(
    [sys.executable, '-B', '-m', 'hello_world.cli', 'run', '--run-id', 'smoke-check'],
    capture_output=True, timeout=12,
)
assert p.returncode == 0, p.stderr.decode()
assert p.stdout == b'HELLO WORLD\n', repr(p.stdout)
print('12-byte audit: OK')
PY
python3 -I -B tools/verify.py . tests -v tests.test_language
python3 -I -B tools/verify.py . tests -v tests.test_history
python3 -I -B tools/verify.py . tests -v tests.test_pipeline
python3 -I -B tools/verify.py . tests -v tests.test_release
python3 -I -B tools/verify.py . tests -v tests.test_sandbox
```

全工程を 1 回で済ませたい場合の正式な受付窓口は `python3 -B -m hello_world.cli run --run-id <fresh-id>`。ファイル不足・改変・工程違いなら非 0 で終了し、最終文字列は出ない。検証失敗の書類は調査用に残す。

試験は `tools/verify.py` 経由で、上記の 5 コマンドをすべて順に実行する（計 44 試験、省略なし）。単発 discover はこの環境で 10 秒上限を超えたため、上限を緩めずモジュール単位に分割した。各コマンドは同じ制限を適用し、同時には実行しない。直接関数を呼ぶ試験にも 1 CPU、192 MiB/8 CPU 秒を適用し、外側の監督に 64 MiB/2 CPU 秒、全体に 10 秒・取得出力計 64 KiB を適用する。Linux のプロセス単位 subreaper で、異常終了した試験の子孫も回収する。生成量はレビュー済み有限書込みの 8 MiB 以内の見積りと、32 MiB 予算の開始前余裕・終了後実測を照合する。OS のディスク quota ではない。機能を確認できなければ実行せず終了する。未レビューのコードを試す汎用 runner として使わない。

### 資源と安全上の限界

- 監督 1 プロセス＋ワーカー 1 プロセスを同じ 1 CPU に固定
- 仮想アドレス空間: 監督 64 MiB、ワーカー 192 MiB。CPU 時間: 監督 2 秒、ワーカー 8 秒
- 1 コマンドの経過時間 deadline は 10 秒。超過時はワーカーを終了・回収する
- 1 ファイル上限 1 MiB、成果物は 4 個×64 KiB 以下、取得 stdout/stderr は計 64 KiB 以下。通常実行の生成内容は最大 320 KiB で、32 MiB の予算内
- OS による通信・領域外書込みの全面隔離ではない。外部通信や追加子プロセスを使わない固定コードをレビューして実行する。任意コードを持ち込む sandbox として使わない
- RLIMIT_AS はプロセス別の仮想メモリ、RLIMIT_FSIZE はファイル別の制限。cgroup の全体 RAM/ディスク制限ではない
- 同じ台帳の同時処理はロックで拒否。別々に起動した実行の合計負荷はこの上限の対象外

動作設計は [docs/DESIGN.md](docs/DESIGN.md)、週次更新は [docs/WEEKLY.md](docs/WEEKLY.md)、実行順は [pipeline.json](pipeline.json)。試験結果は [第 1 週](docs/runs/2026-10-03.json) 、[第 2 週](docs/runs/2026-10-10.json) と [第 3 週](docs/runs/2026-10-17.json) に記録する。
