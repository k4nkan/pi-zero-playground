# Pi Peace Camera

Raspberry Pi Zero 2 W で両手のピースを認識し、3秒カウントダウン後に撮影するカメラ。Mac のローカルコンソール（ブラウザ）から SSH 経由で起動・停止・状態確認・最新写真の取得をする。使い方と Pi の初期準備は [README.md](README.md)。

デバイスのスペック、言語とバージョン、使えないもの、CPU・メモリの予算（実測）は [docs/constraints.md](docs/constraints.md) にまとめてある。機能を足す・ライブラリを変える前に読む。

## 構成

| パス | 動く場所 | 中身 |
| --- | --- | --- |
| `raspi/pi_peace.py` | Pi | カメラ取得・手の認識・カウントダウン撮影・`/dev/fb0` への描画 |
| `raspi/requirements.txt` | Pi | Pi の venv（Python 3.12）に入れる依存。`mediapipe==0.10.18` 固定 |
| `console/server.mjs` | Mac | `127.0.0.1` だけで待ち受けるローカルサーバー。ブラウザ → server → SSH → Pi |
| `console/index.html` | Mac | 操作画面（状態・カメラ・LED・コマンド実行・電源） |

Pi 上の配置: `~/hand-landmarker/`（`pi_peace.py`、`.venv/`、`models/hand_landmarker.task`、`photos/`）。

## デバイスの前提

- Raspberry Pi Zero 2 W（Cortex-A53 4コア / RAM 512MB / 2.4GHz Wi-Fi のみ）
- OS: Raspberry Pi OS Lite **64bit**（Debian 13 trixie）。デスクトップなし、`multi-user.target`
- 画面: HDMI のコンソール。`/dev/fb0` は 1024×600 / 16bit（RGB565）。`kanta` は video グループなので sudo なしで書ける
- カメラ: OV5647（640×480 62fps 〜 2592×1944 15fps）
- 接続先は `console/.env` の `PI_HOST`（作者の環境は `kanta@kanta.local`）。SSH は鍵認証、Pi の sudo はパスワードなし

## ハマりどころ（変えるときは必ず踏まえる）

- **MediaPipe 1.x は Pi Zero 2 W で起動直後に `Illegal instruction`**。wheel が AES 命令前提で、この CPU にはない。→ Python 3.12（uv で導入、`~/.local/uv-venv/bin/uv`）＋ `mediapipe==0.10.18` を使う。安易に mediapipe を上げない。
- **picamera2 は使えない**。apt の picamera2 は OS の Python 3.13 用で、3.12 の venv からは import できない。カメラは `rpicam-vid`（YUV420 を stdout）と `rpicam-still` を subprocess で呼ぶ。
- **カメラは同時に1プロセスだけ**。ライブ映像中に撮るときは `rpicam-vid` を止めてから `rpicam-still` し、再開する（`Camera.capture_photo`）。
- mediapipe は `libEGL.so.1` が要る（`apt install libegl1 libgles2`）。`import` からモデル生成まで約 30 秒かかるので、先に `LOADING...` を描いている。
- apt で libcamera だけ上がると `rpicam-*` が `undefined symbol` で起動しなくなる。libcamera を上げたら rpicam-apps も揃えて上げる。
- コンソールの SSH コマンドで裏起動するときは `setsid nohup ... </dev/null &` を単独の文で書く。`cd x && setsid ... &` とつなぐと、残ったサブシェルが SSH の出力を握って返ってこない。停止は PID ファイルからプロセスグループごと（`kill -- -PID`）。
- `pi_peace.py` が `/dev/fb0` に直接描くので、停止後は `systemctl restart getty@tty1` でログイン画面を戻している。

## 性能の目安（実測、詳細は docs/constraints.md）

- ライブ映像 320×240 / 15fps、手の認識は両手で約 2fps（VIDEO モード 1回 約 500ms）
- 動作中は CPU 4コア中 約2コア使用（推論 約1コア＋表示 約0.8コア）、空きメモリ 約 165MB
- 認識の速さは CPU の空きでは上がらない。速くするなら認識の解像度を下げる・毎フレーム認識しない
- 実測値を docs/constraints.md に書くときは、推測値と混ぜない

## Claude が Pi を操作するときのルール

- Pi への操作は Mac から `ssh "$PI_HOST" '<command>'` を **1コマンドずつ**。対話シェルに入りっぱなしにしない。
- 状態確認（`systemctl status`、`journalctl`、`free`、`vcgencmd`、`rpicam-hello --list-cameras`、`pgrep` など）は自由に実行してよい。
- `sudo`・ファイル削除・パッケージ導入/更新・再起動・`/etc` の編集は、実行前に内容を説明して確認を取る。apt で何かを入れたら、ほかのパッケージが巻き添えで上がっていないか確認する。
- `.env` の中身は読まない・表示しない・コミットしない（`.env.example` は見てよい）。パスワードや Wi-Fi の鍵も同様。必要なときはユーザー自身に入力してもらう。
- コードは Mac で編集して `rsync` で送る。Pi 上で直接編集しない。
- インターネット上のスクリプトを `curl | sh` で実行しない。ツールは PyPI / apt など素性の分かる経路で入れる。

## Mac 側で作業するときのルール

- プロセスを止めるときは **PID 指定だけ**。`pkill -f <パターン>` や `killall` は使わない（macOS の pkill は引数の順で意図しないプロセスまで止める）。
- 動作確認でコンソールを起動するときは、ユーザーが 8765 番で動かしている可能性があるので別ポート（例 `PORT=8766`）で起動し、終わったらそのプロセスだけ止める。
- Mac の Python は pyenv（3.13）。実験用の venv は各フォルダの `.venv/` に作る。

## 確認コマンド

```sh
python3 -m py_compile raspi/pi_peace.py
node --check console/server.mjs
```

実機での確認は、コンソールの「ピース認識を起動」→ 約 30 秒待つ → Pi の画面を見る。画面の中身は `ssh "$PI_HOST" 'head -c 1228800 /dev/fb0'` で RGB565 の生データとして取れる。

## 規約

- ドキュメントとコメントは日本語。コミットメッセージは Conventional Commits（`feat:` / `fix:` / `docs:` …）で英語。
- Pi 側は Python、Mac 側のコンソールは Node.js（標準モジュールだけ、依存パッケージなし）。
- 撮影画像は人が写るので、`*.jpg` / `photos/` / `captures/` はコミットしない（`.gitignore` 済み）。モデル（`*.task`）もコミットしない。
- 推論速度・メモリなど実測した値を書くときは、推測値と混ぜない。
