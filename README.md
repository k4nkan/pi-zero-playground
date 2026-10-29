# Pi Peace Camera

Raspberry Pi Zero 2 W で両手のピースを認識し、3秒のカウントダウン後に写真を撮影するカメラ。Mac 上のローカルコンソールから起動・停止・状態確認・最新写真の取得ができる。

## 構成

```text
raspi/
  pi_peace.py       # Pi で動く認識・撮影処理
  requirements.txt  # Pi 実機の Python 依存関係
console/
  index.html        # 操作画面
  server.mjs        # SSH 経由で Pi を操作するローカルサーバー
  package.json
```

## 動作

- ライブ映像: 640×480 / 15fps。`rpicam-vid` の GPU プレビューで画面左に出し、カウントダウンなどは右の余白に出す
- 手の認識: 1回 約 0.5 秒。手が写っていないときは1秒に1回に間引く
- 両手ピースを3秒間維持すると2592×1944で撮影
- 写真は Pi の `~/hand-landmarker/photos/` に保存
- 一度撮影したら、手を下ろすまで再撮影しない
- コンソールの「カメラ」モードでは Python を使わず、`rpicam-hello` でカメラ映像をそのまま Pi のディスプレイに出す（画角の確認用）。露出補正・明るさ・コントラスト・彩度・シャープネスは「カメラの設定」を開いて調整する
- コンソールの「待機」モードではカメラを使わず、Pi のディスプレイにドットの目を出して数秒おきにまばたきさせる（`raspi/pi_eyes.py`）。ほかのモードとは同時に使えない

## Pi の準備

Raspberry Pi OS Lite 64-bit、Python 3.12、`rpicam-apps`、framebuffer (`/dev/fb0`) を使う。

```sh
sudo apt install --no-install-recommends libegl1 libgles2

python3 -m venv ~/.local/uv-venv
~/.local/uv-venv/bin/pip install uv
~/.local/uv-venv/bin/uv python install 3.12

mkdir -p ~/hand-landmarker/models
cd ~/hand-landmarker
~/.local/uv-venv/bin/uv venv --python 3.12 .venv
```

Mac からコードと依存関係を送る。`PI_HOST` は自分のPiに合わせる。

```sh
export PI_HOST=pi@raspberrypi.local
rsync -a raspi/pi_peace.py raspi/requirements.txt "$PI_HOST":hand-landmarker/
ssh "$PI_HOST" '~/.local/uv-venv/bin/uv pip install --python ~/hand-landmarker/.venv/bin/python -r ~/hand-landmarker/requirements.txt'

curl -L -o /tmp/hand_landmarker.task \
  https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task
scp /tmp/hand_landmarker.task "$PI_HOST":hand-landmarker/models/
```

モデルのSHA-256:

```text
fbc2a30080c3c557093b5ddfc334698132eb341044ccee322ccf8bcf3607cde1
```

## コンソール

Node.js 22以上と、PiへのSSH鍵認証が必要。

```sh
cd console
cp .env.example .env
# .env の PI_HOST を自分のPiに合わせる
npm run dev
```

コンソールは `http://127.0.0.1:8765` だけで待ち受ける。Pi の再起動・電源オフができるため、LANやインターネットへ公開しない。

## 確認コマンド

```sh
python3 -m py_compile raspi/pi_peace.py
node --check console/server.mjs
```
