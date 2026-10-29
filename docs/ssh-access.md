# Pi に SSH で入る（メンバー向け）

入り方は 2 つある。

| 場所 | 接続先 | 認証 | 準備 |
| --- | --- | --- | --- |
| 研究室の LAN | `raspi@ddse.local` | SSH の鍵 | 鍵を作って管理者に登録してもらう（この下の手順） |
| どこからでも（家など） | `raspi@ddse.<tailnet>.ts.net` | Tailscale のアカウント | Tailscale を入れて、Pi を共有してもらう（[家から入る（Tailscale）](#家から入るtailscale)） |

研究室の LAN から鍵で入る場合は、メンバーが自分の鍵を作り、公開鍵を管理者に送り、管理者が Pi に登録すると `ssh raspi@ddse.local` で入れる。

- ログインするユーザーは全員 `raspi` を共有する。誰の鍵かは、鍵に付けた名前（`taro@lab` など）で見分ける
- 入り方は鍵認証だけ。パスワードでは SSH できない。登録されていない PC からは入れない
- 研究室の LAN（Wi-Fi か有線）につないでいる必要がある。外からは Tailscale を使う
- 接続先は `ddse.local`。届かない PC だけ IP を使う（IP は DHCP なので変わることがある。管理者に聞く）
- `sudo` には `raspi` のパスワードが要る（パスワードは管理者だけが知っている）

## 流れ

| # | 誰が | やること |
| --- | --- | --- |
| 1 | メンバー | 鍵を作る（最初の 1 回だけ） |
| 2 | メンバー | 公開鍵（`.pub`）を管理者に送る |
| 3 | 管理者 | Pi の `~/.ssh/authorized_keys` に登録する |
| 4 | メンバー | `ssh raspi@ddse.local` でつなぐ |

## 1. 鍵を作る（メンバー）

Mac はターミナル、Windows 10 / 11 は PowerShell で実行する（どちらも `ssh` は最初から入っている）。`taro` は自分の名前に置き換える。

```sh
ssh-keygen -t ed25519 -C "taro@lab"
```

1. 保存場所を聞かれたら、そのまま Enter
2. パスフレーズを入れる（PC をなくしても鍵を使われにくくなるので、付けるのがおすすめ）
3. 秘密鍵 `id_ed25519` と公開鍵 `id_ed25519.pub` ができる（Mac は `~/.ssh/`、Windows は `C:\Users\<自分の名前>\.ssh\`）

すでに `id_ed25519` がある人は、作り直さずにそれを使う。上書きすると、その鍵で入っていた他のサーバーに入れなくなる。

Windows で `ssh` が見つからないと言われたら、「設定 → システム → オプション機能」から「OpenSSH クライアント」を追加する。

## 2. 公開鍵を送る（メンバー）

```sh
# Mac
cat ~/.ssh/id_ed25519.pub
```

```powershell
# Windows（PowerShell）
Get-Content $env:USERPROFILE\.ssh\id_ed25519.pub
```

出てきた `ssh-ed25519 AAAA... taro@lab` の 1 行を、Slack などで管理者に送る。

- 送ってよいのは `.pub` が付いたほうだけ
- `.pub` が付いていない `id_ed25519` は秘密鍵。誰にも渡さない・どこにも貼らない

## 3. Pi に登録する（管理者）

受け取った 1 行を、**Mac のターミナルから**（Pi に入った状態ではなく）`authorized_keys` に足す。すでに同じ行があれば足さない。

```sh
ssh raspi@ddse.local 'K="ssh-ed25519 AAAA... taro@lab"; grep -qxF "$K" ~/.ssh/authorized_keys || echo "$K" >> ~/.ssh/authorized_keys'
```

- `>>`（追加）を `>`（上書き）と間違えない。`>` にすると、管理者を含む全員の鍵が消える
- 行の末尾の名前で、誰の鍵か分かるようにしておく

登録済みの鍵の一覧（指紋と名前だけで、鍵そのものは出ない）:

```sh
ssh raspi@ddse.local 'ssh-keygen -lf ~/.ssh/authorized_keys'
```

## 4. つなぐ（メンバー）

```sh
ssh raspi@ddse.local
```

- 初回は「このホストを信用するか」と聞かれるので `yes`
- `Enter passphrase for key` と聞かれたら、1 で自分が決めた**鍵のパスフレーズ**を入れる（Pi のパスワードではない）
- `raspi@ddse:~ $` が出れば成功

`raspi@ddse.local` の `@` の前は Pi のユーザー名（全員 `raspi`）、後ろは接続先（Pi のホスト名 `ddse` に `.local` を付けたもの）。自分の名前（`taro` や `taro@lab`）はログインには使わない。

### パスフレーズを毎回聞かれないようにする（任意）

Mac:

```sh
ssh-add --apple-use-keychain ~/.ssh/id_ed25519
```

Windows: 管理者として開いた PowerShell で 1 回だけ ssh-agent を有効にしてから、普通の PowerShell で鍵を登録する。

```powershell
# 管理者の PowerShell
Get-Service ssh-agent | Set-Service -StartupType Automatic
Start-Service ssh-agent
```

```powershell
# 普通の PowerShell
ssh-add $env:USERPROFILE\.ssh\id_ed25519
```

### 短い名前でつなぐ（任意）

`~/.ssh/config`（Windows は `C:\Users\<自分の名前>\.ssh\config`）に書いておくと `ssh peace-cam` だけでつながる。

```
Host peace-cam
  HostName ddse.local
  User raspi
```

### コンソール（`console/`）を自分の PC で使うとき

- コンソールはパスフレーズを聞かずに SSH する（`BatchMode=yes`）。パスフレーズ付きの鍵は、上の手順で ssh-agent / キーチェーンに登録しておかないと「オフライン」になる
- `console/.env` の `PI_HOST` は `raspi@ddse.local`
- Windows では「録画を Mac に取り込む」は使えない（`rsync` が入っていないため）

## 家から入る（Tailscale）

Pi には [Tailscale](https://tailscale.com/) が入っていて、Tailscale 経由の SSH は Tailscale SSH が受け持つ。Tailscale のアカウントで認証するので、**SSH の鍵の登録はいらない**。研究室の LAN の `ddse.local` は今までどおり鍵認証のまま。

- 中身の通信は端末どうしで暗号化して流れる。直接つながらないネットワーク（大学の Wi-Fi など）では Tailscale の中継サーバーを通るので、少し遅い
- Pi の tailnet の名前（`ddse.<tailnet>.ts.net` の `<tailnet>`）はリポジトリに書かない。管理者に聞く
- 管理者の tailnet に入るのではなく、Pi だけを共有してもらう形。ほかのメンバーの端末や管理者の PC は見えない

### メンバー

1. Tailscale を入れる（Mac は App Store、Windows は https://tailscale.com/download ）
2. GitHub か Google のアカウントでログインする
3. 自分の **Tailscale の ID** を管理者に送る。管理画面（https://login.tailscale.com/admin ）の右上に出る名前で、GitHub でログインした人は `ユーザー名@github`、Google の人はメールアドレスになる
4. 管理者から届いた共有リンクを開き、Pi（`ddse`）を受け取る
5. Tailscale を ON にして、つなぐ

```sh
ssh raspi@ddse.<tailnet>.ts.net
```

初回はホストを信用するか聞かれるので、指紋が `SHA256:kFm2JDVhYXtGY6BWkaa/H6lanQi4C+xZiLJ3BiB4rl4` なのを見てから `yes`。共有された Pi は短い名前（`ddse`）では引けないので、長い名前を使う。毎回打つのが面倒なら `~/.ssh/config` に書く。

```
Host peace-cam
  HostName ddse.<tailnet>.ts.net
  User raspi
```

コンソールを家から使うときは、`console/.env` の `PI_HOST` を `raspi@ddse.<tailnet>.ts.net` にする。Tailscale SSH は鍵を使わないので、ssh-agent の登録もいらない。

### 管理者

1. メンバーの Tailscale の ID を、管理画面の Access controls の `ssh` ルールの `src` に足す。**メールアドレスではなく Tailscale の ID**（GitHub ログインなら `ユーザー名@github`）を書く。違うと `tailnet policy does not permit you to SSH to this node` で断られる

```jsonc
{
	"action": "accept",
	"src":    ["autogroup:member", "taro@github"],
	"dst":    ["tag:peace-cam"],
	"users":  ["raspi"],
},
```

2. Machines → `ddse` の「…」→ **Share...** で共有リンクを作り、メンバーに送る

`src` に `autogroup:shared`（共有した相手全員）は書けないので、1 人ずつ足す。入れるユーザーは `raspi` だけで、root では入れない。

抜けるときは、`src` からその人の ID を消し、Machines → `ddse` → Share... から共有を外す。

### Pi 側の設定（済み、作り直すとき用）

- 公式の apt リポジトリ（`pkgs.tailscale.com/stable/debian` の trixie）から `tailscale` を入れた。依存で `iptables`・`libip4tc2`・`libip6tc2` が入る
- `sudo tailscale up` で tailnet に参加 → 管理画面で `tag:peace-cam` を付ける（タグを付けると鍵の期限が切れなくなる）→ `sudo tailscale set --ssh`
- ポリシーには `"tagOwners": {"tag:peace-cam": ["autogroup:admin"]}` と、上の `ssh` ルールを書いてある
- `tailscale set --ssh` を Tailscale 経由の SSH で実行すると、その接続は切れる。研究室の LAN の `ddse.local` から実行すると切れない

## 抜けるとき（管理者）

その人の名前が付いた行を消す。

```sh
ssh raspi@ddse.local 'sed -i "/taro@lab$/d" ~/.ssh/authorized_keys'
```

## つながらないとき

| 症状 | よくある原因 |
| --- | --- |
| `Could not resolve hostname` | `@` の後ろが接続先になっていない（`raspi@taro` など）、または `.local` の名前が引けていない。後者は管理者に IP を聞いて `ssh raspi@<IP>` |
| `Connection timed out` | 研究室の LAN にいない、Pi が落ちている。外からは Tailscale を ON にして `ddse.<tailnet>.ts.net` を使う |
| `tailnet policy does not permit you to SSH to this node` | 管理者のポリシーの `src` に自分の Tailscale の ID が入っていない（メールアドレスで書かれている、など） |
| `Permission denied (publickey)` | 鍵が登録されていない、別の鍵を使っている、または Pi に入った状態の中から `ssh` している。Mac / Windows のターミナルから `ssh -v raspi@ddse.local` で使われた鍵を見て管理者に伝える |
| `Enter passphrase for key` が通らない | 自分の鍵のパスフレーズを間違えている（Pi 側の問題ではない） |
| `REMOTE HOST IDENTIFICATION HAS CHANGED` | Pi を焼き直した、または同じ IP に別の機器が来た。管理者に確認してから `ssh-keygen -R ddse.local` |

## 使うときのルール

- **`sudo` にはパスワードが要る**。設定変更・パッケージの導入・ファイル削除などは管理者に頼む。コンソールが使う再起動・電源オフ・ログイン画面の再表示だけはパスワードなしで動く（`/etc/sudoers.d/99-raspi-require-password`）
- **カメラは同時に 1 プロセスだけ**。コンソールの「カメラ」「見守り」「録画」・配信のどれかが動いていると、ほかは使えない。コンソールの状態表示で確かめてから使う
- **メモリは 512MB しかない**。MediaPipe などの重い処理を 2 人が同時に動かすと Pi が固まり、SSH も届かなくなる。重い処理は 1 人ずつ
- **Tailscale 経由の SSH は 1 本ごとに Pi のメモリを使う**（[constraints.md](constraints.md#tailscale2026-10-29)）。コンソールは接続をつなぎっぱなしにするので、「見守り」を動かしている間に家からコンソールを開くのは 1 人まで。研究室にいるときは `ddse.local` を使う
- **コードは Pi 上で直接編集しない**。このリポジトリで変更して、Mac から `rsync` で送る
- `raspi` を共有しているので、`sudo` なしでできること（`~/hand-landmarker` のファイル削除、動いているプログラムの停止など）は誰でもできてしまう。触る前にほかのメンバーに声をかける
