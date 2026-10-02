# shanhao-experiments
シャンハオ実験専用リポジトリ

AIを活用した小さな実験と、その検証結果を公開するためのリポジトリです。

実験段階の内容を含みます。

## 世界一重たくてクソ怠いファッキンクレイジーな HELLO WORLD 表示 Project

11 文字を出す。それだけのために 11 件の議案を提出し、55 票を集め、11 通の成立証明を発行し、議事録を編纂する。書類が 1 枚でも失われれば表示を拒否する。

第 1 週 `2026-10-03`: **文字議会**。待機や無限ループで遅くしているわけではなく、各段階の成果物が次の段階に必要になる。今週は工程の無駄を増やす低負荷版。高負荷モードはない。

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

### 2. 五委員会合同採決

```sh
python3 -B -m hello_world.cli stage ballot --run-id ceremony
```

位置委員・ASCII 委員・議題委員・件数委員・印字委員の 55 票を `ballot.json` に記録する。議案がない、変更された、あるいは余計な書類がある場合は受理しない。

### 3. 成立証明発行局

```sh
python3 -B -m hello_world.cli stage certificate --run-id ceremony
```

定足数と過半数を検査し、投票のハッシュを含む `certificate.json` を発行する。ハッシュは改変検出用で、法的な署名ではない。

### 4. 議事録編纂室

```sh
python3 -B -m hello_world.cli stage minutes --run-id ceremony
```

成立証明を照合して位置順に並べ、`minutes.json` に収録する。ここまで来ても stdout は空である。

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
python3 -B -m unittest discover -s tests -v
```

全工程を 1 回で済ませたい場合の正式な受付窓口は `python3 -B -m hello_world.cli run --run-id <fresh-id>`。ファイル不足・改変・工程違いなら非 0 で終了し、最終文字列は出ない。検証失敗の書類は調査用に残す。

### 資源と安全上の限界

- 監督 1 プロセス＋ワーカー 1 プロセスを同じ 1 CPU に固定
- 仮想アドレス空間: 監督 64 MiB、ワーカー 192 MiB。CPU 時間: 監督 2 秒、ワーカー 8 秒
- 1 コマンドの経過時間 deadline は 10 秒。超過時はワーカーを終了・回収する
- 1 ファイル上限 1 MiB、成果物は 4 個×64 KiB 以下、取得 stdout/stderr は計 64 KiB 以下。通常実行の生成内容は最大 320 KiB で、32 MiB の予算内
- OS による通信・領域外書込みの全面隔離ではない。外部通信や追加子プロセスを使わない固定コードをレビューして実行する。任意コードを持ち込む sandbox として使わない
- RLIMIT_AS はプロセス別の仮想メモリ、RLIMIT_FSIZE はファイル別の制限。cgroup の全体 RAM/ディスク制限ではない
- 同じ台帳の同時処理はロックで拒否。別々に起動した実行の合計負荷はこの上限の対象外

動作設計は [docs/DESIGN.md](docs/DESIGN.md)、週次更新は [docs/WEEKLY.md](docs/WEEKLY.md)、実行順は [pipeline.json](pipeline.json)。試験結果は [docs/runs/2026-10-03.json](docs/runs/2026-10-03.json) に記録する。
