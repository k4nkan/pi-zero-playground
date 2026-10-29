# 開発の制約

Pi Peace Camera を作るうえでの前提と制約。数値は **実測** と **目安（未検証）** を区別して書く。実測した値が変わったらここを更新する。

## デバイス

| 項目 | 内容 | 開発への影響 |
| --- | --- | --- |
| 本体 | Raspberry Pi Zero 2 W | — |
| CPU | Cortex-A53 4コア 1GHz（BCM2710A1）。**AES などの暗号命令なし** | AES 前提でビルドされた wheel は `Illegal instruction` で落ちる（MediaPipe 1.x など） |
| RAM | 512MB（OS から見えるのは 415MB）＋ swap 414MB | 大きいモデルやブラウザは載らない。メモリ確保は控えめに |
| GPU | VideoCore IV | WebGL / TF.js / MediaPipe の GPU 高速化は使えない。推論は CPU のみ |
| ストレージ | microSD（ルート領域 57GB、使用 約 3GB） | 容量は十分。急な電源断で壊れることがある |
| 通信 | 2.4GHz Wi-Fi のみ（5GHz 不可） | WPA2-Enterprise（eduroam など）は Imager の設定では入れない |
| カメラ端子 | mini CSI × 1 | Zero 用の細いケーブルが要る |
| 映像出力 | mini HDMI | — |
| 電源 | micro USB（PWR 側）5V | モバイルバッテリーは低電流で自動オフすることがある |

### カメラ（OV5647）

| モード | fps |
| --- | --- |
| 640×480 | 62.5 |
| 1296×972 | 46.3 |
| 1920×1080 | 32.8 |
| 2592×1944（撮影に使用） | 15.6 |

- **同時に使えるのは1プロセスだけ**。ライブ映像（`rpicam-vid`）を止めないと撮影（`rpicam-still`）できない。
- カメラの抜き差しは電源を切ってから。起動時にしか認識されない。

### 画面

- HDMI のコンソール。`/dev/fb0` は 1024×600 / 16bit（RGB565）。
- GUI（デスクトップ、X、Wayland）はない。アプリは `/dev/fb0` に直接描く。
- `rpicam-hello` のプレビューは fb0 とは別の層（DRM プレーン）に出るので、fb0 を読んでも映らない。

## OS とシステム

| 項目 | 内容 |
| --- | --- |
| OS | Raspberry Pi OS Lite **64bit**（Debian 13 trixie、aarch64） |
| 起動モード | `multi-user.target`（GUI なし） |
| システムの Python | 3.13（picamera2 などの apt パッケージはこれ用） |
| カメラのツール | rpicam-apps 1.14.0 / libcamera 0.7.2 |
| 追加した apt パッケージ | `python3-picamera2`、`libegl1`、`libgles2` |
| ユーザー | `raspi`（2026-10-30 に `kanta` から改名、ホスト名も `kanta` → `ddse`。`.venv` などに旧パスが入っているので `/home/kanta` → `/home/raspi` のリンクを残している）。video グループ（fb0 に書ける）。sudo はパスワード必須（コンソールが使うコマンドだけ例外、`/etc/sudoers.d/99-raspi-require-password`） |
| 追加した設定 | Wi-Fi の省電力オフ（`/etc/NetworkManager/conf.d/wifi-powersave-off.conf`）、ログを再起動後も残す（`/etc/systemd/journald.conf.d/50-persistent.conf`、上限 50MB）、SSH は鍵認証だけ（`/etc/ssh/sshd_config.d/10-key-only.conf`） |

- apt で libcamera だけが上がると、rpicam-apps と合わなくなって `rpicam-*` が起動しなくなる。上げるときは両方そろえる。
- `/tmp` は再起動で消える。PID ファイルとログはここに置いている。

## 言語とランタイム

| 場所 | 言語 | バージョン | 依存 |
| --- | --- | --- | --- |
| Pi（`raspi/`） | Python | **3.12**（uv で導入。OS の 3.13 とは別） | `raspi/requirements.txt`。`mediapipe==0.10.18` 固定 |
| Mac（`console/`） | JavaScript（Node.js） | 22 以上（作者の環境は 24） | なし（標準モジュールだけ） |

### Python 3.12 + MediaPipe 0.10.18 に固定している理由

- MediaPipe 1.x（2026年〜）の aarch64 wheel は AES 命令前提で、この CPU では起動直後に落ちる。
- 0.10.x 系の aarch64 wheel は Python 3.12 までしかない。
- そのため、OS の Python 3.13 ではなく、uv で入れた 3.12 の venv（`~/hand-landmarker/.venv`）で動かす。

### 使えないもの・避けるもの

| もの | 理由 |
| --- | --- |
| MediaPipe 1.x | AES 命令がなく落ちる |
| picamera2（3.12 の venv から） | OS の 3.13 用なので import できない。`rpicam-vid` / `rpicam-still` を subprocess で使う |
| ブラウザ（Chromium）、p5.js、ml5.js | 重すぎる。Chromium だけで 150MB 前後、GPU も使えない |
| OpenCV の `imshow` | GUI がないので表示できない。`/dev/fb0` に書く |
| `curl \| sh` での導入 | 素性の分からないスクリプトは実行しない。PyPI / apt を使う |

## 性能の予算（実測）

ピース認識（`pi_peace.py`）を動かしている間の値。ケース・ヒートシンクなし。30 秒平均。

### 今の構成（2026-10-27）

表示は `rpicam-vid` の DRM プレビュー（GPU）に任せ、同じ `rpicam-vid` の stdout（640×480 YUV420）から認識する。手が写っていないときは推論を1秒に1回に間引く。Python は画面右の余白に状態を描くだけ。

| 項目 | 値 | 残りの余裕 |
| --- | --- | --- |
| CPU（4コア全体） | 平均 19.5% | 約3コア |
| └ Python（ほぼ MediaPipe の推論） | 約 0.65 コア | — |
| └ `rpicam-vid`（プレビュー＋640×480 出力） | 約 0.08 コア | — |
| メモリ（available） | 168〜179MB（Python 86MB） | Slack 通知くらいは足せる。ブラウザは無理 |
| swap | 91MB 使用 | — |
| 温度 | 46〜48℃（性能制限は 80℃ 超から） | 長時間での推移は未計測 |
| CPU 周波数 | 600〜1000MHz（暇なときは下がる） | — |
| 認識の回数 | 1秒に 1.0〜1.9 回（1回 約 500〜800ms） | — |

計測中にカメラの前に手があった時間は記録していないので、待機中だけ・認識中だけの値は未計測。

### 前の構成（2026-10-26、参考）

320×240 を受け取り、Python が 800×600 に拡大して `/dev/fb0` に 15fps で描いていた。

| 項目 | 値 |
| --- | --- |
| CPU（4コア全体） | 平均 48% |
| └ MediaPipe の推論 | 約 1.0 コア |
| └ 表示（拡大・RGB565 変換・fb0 への書き込み） | 約 0.8 コア |
| └ `rpicam-vid` とカメラ読み取り | 約 0.1 コア |
| メモリ（available） | 約 167MB（Python 109MB）、swap 88MB |
| 温度 | 62〜63℃ |

### Tailscale（2026-10-29）

`tailscale` 1.104.4。何も動かしていない（コンソールだけつながっている）ときに測った。「見守り」と同時の値は未計測。

| 項目 | 値 |
| --- | --- |
| `tailscaled` の RSS | 約 38MB（導入直後）、約 42MB（Tailscale SSH を有効にした後） |
| `tailscaled` の CPU | 起動から 6 分の平均で 1 コアの 1.4%（起動時の処理を含む） |
| Tailscale SSH の接続 1 本 | 補助プロセス（`tailscaled be-child`）が 1〜2 個増え、それぞれ RSS 約 24MB。`tailscaled` 本体と共有している分を含むので、実際の増え方はこれより小さい（root でないと測れず未計測） |
| メモリ（available） | 271MB（導入前）→ 264MB（導入後）→ 約 230MB（Tailscale SSH の接続が 1〜2 本） |

available はキャッシュの増減も混ざるので、差は目安。Tailscale SSH はコンソールのように接続を使い回すとその間ずっとメモリを使うので、研究室では `ddse.local`（普通の sshd）を使う。

### 速さ（実測）

| 処理 | 値 |
| --- | --- |
| MediaPipe の読み込み（import 〜 モデル生成） | 約 28 秒 |
| 手の認識 1回（320×240、手なし） | 約 365ms |
| 手の認識 1回（両手あり、VIDEO モード） | 約 500ms → **約 2fps** |
| ライブ映像の表示 | 15fps |
| 静止画 1枚（`rpicam-still`、待ちなし） | 約 1.0 秒 |
| 動画（`rpicam-vid` 640×480） | 約 28fps、CPU は1コアの 38% |

- **認識の速さは CPU の空きでは上がらない**。1回の推論にかかる時間が上限になる。速くするなら、認識に渡す画像を小さくする・毎フレーム認識しない、など仕事を減らす。
- 表示は GPU のプレビューに任せるのが一番効く（Python で描くと約 0.8 コア）。`rpicam-vid` は `-n` を付けなければ、プレビューを出しながら stdout にも映像を出せる（実測で 640×480 / 約 15fps）。
- 未計測: 待機中だけ・認識中だけの CPU、撮影の瞬間のメモリ、長時間動かしたときの温度。

## ネットワークと運用

- 研究室の LAN からは `ddse.local`（mDNS）に SSH の鍵認証で入る（`console/.env` の `PI_HOST`）。`ddse.local` が引けない環境では IP で指定する。
- 外からは Tailscale で入る。Tailscale 経由の SSH は Tailscale SSH が受け持ち、鍵ではなく Tailscale のアカウントで認証する。メンバーは Pi を共有してもらい、`ddse.<tailnet>.ts.net` でつなぐ。学内 Wi-Fi など直接つながらないネットワークでは中継（DERP、東京）を通るので、録画の取り込みなど大きい転送は研究室の LAN でやる。手順は [ssh-access.md](ssh-access.md)。
- tailnet の名前・メンバーの Tailscale の ID はリポジトリに書かない（公開リポジトリのため）。
- Wi-Fi は 2.4GHz だけ。**802.11r（FT / 高速ローミング）が有効な AP にはつながらない**: AP が FT 用の PMKID を 4-way handshake の 3/4 に付けてきて、wpa_supplicant が `IE in 3/4 msg does not match`（reason 17）で切る。ドライバー（brcmfmac）が FT に対応していないので Pi 側の設定では直らず、AP 側で 802.11r を無効にする。
- `nmcli connection up` で認証に失敗すると、NetworkManager が保存済みのパスワードを使わなくなることがある（次の試行が `Secrets were required` で即失敗する）。そのときは `nmtui` でパスワードを入れ直す。
- ネットワークを切り替えるときは、SSH が切れても戻れるよう `systemd-run` で「つなぐ → 結果を記録 → 一定時間後に元の接続へ戻す」を裏で動かしてから実行する。
- Wi-Fi の MAC アドレスは Raspberry Pi の新しい OUI（`88:a2:9e`）。ARP で探すときは `b8:27:eb` などの古い OUI だけで探さない。
- コンソール（`console/server.mjs`）は `127.0.0.1:8765` だけで待ち受ける。Pi の再起動・電源オフができるので外に公開しない。
- コードは Mac で編集して `rsync` で送る。Pi 上で直接編集しない。

## 電源と持ち運び（目安・未検証）

- 動作中の消費電力は 1〜2W 程度の見込み。1200mAh の電池で 2〜3 時間程度。
- 電池切れの急な電源断で SD が壊れることがある。持ち歩くなら電池残量が取れる電源（PiSugar など）で自動シャットダウンを入れたい。
- 起動から使えるまで、OS の起動 20〜30 秒 ＋ MediaPipe の読み込み 約 30 秒。
