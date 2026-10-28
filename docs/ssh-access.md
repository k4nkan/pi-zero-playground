# Pi に SSH で入る（メンバー向け）

メンバーが自分の鍵を作り、公開鍵を管理者に送り、管理者が Pi に登録すると、研究室の LAN から `ssh kanta@kanta.local` で入れる。

- ログインするユーザーは全員 `kanta` を共有する。誰の鍵かは、鍵に付けた名前（`taro@lab` など）で見分ける
- 入り方は鍵認証だけ。パスワードでは SSH できない。登録されていない PC からは入れない
- 研究室の LAN（Wi-Fi か有線）につないでいる必要がある
- 接続先は `kanta.local`。届かない PC だけ IP を使う（IP は DHCP なので変わることがある。管理者に聞く）
- `sudo` には `kanta` のパスワードが要る（パスワードは管理者だけが知っている）

## 流れ

| # | 誰が | やること |
| --- | --- | --- |
| 1 | メンバー | 鍵を作る（最初の 1 回だけ） |
| 2 | メンバー | 公開鍵（`.pub`）を管理者に送る |
| 3 | 管理者 | Pi の `~/.ssh/authorized_keys` に登録する |
| 4 | メンバー | `ssh kanta@kanta.local` でつなぐ |

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
ssh kanta@kanta.local 'K="ssh-ed25519 AAAA... taro@lab"; grep -qxF "$K" ~/.ssh/authorized_keys || echo "$K" >> ~/.ssh/authorized_keys'
```

- `>>`（追加）を `>`（上書き）と間違えない。`>` にすると、管理者を含む全員の鍵が消える
- 行の末尾の名前で、誰の鍵か分かるようにしておく

登録済みの鍵の一覧（指紋と名前だけで、鍵そのものは出ない）:

```sh
ssh kanta@kanta.local 'ssh-keygen -lf ~/.ssh/authorized_keys'
```

## 4. つなぐ（メンバー）

```sh
ssh kanta@kanta.local
```

- 初回は「このホストを信用するか」と聞かれるので `yes`
- `Enter passphrase for key` と聞かれたら、1 で自分が決めた**鍵のパスフレーズ**を入れる（Pi のパスワードではない）
- `kanta@kanta:~ $` が出れば成功

`kanta@kanta.local` の `@` の前は Pi のユーザー名（全員 `kanta`）、後ろは接続先（Pi のホスト名 `kanta` に `.local` を付けたもの）。自分の名前（`taro` や `taro@lab`）はログインには使わない。

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
  HostName kanta.local
  User kanta
```

## 抜けるとき（管理者）

その人の名前が付いた行を消す。

```sh
ssh kanta@kanta.local 'sed -i "/taro@lab$/d" ~/.ssh/authorized_keys'
```

## つながらないとき

| 症状 | よくある原因 |
| --- | --- |
| `Could not resolve hostname` | `@` の後ろが接続先になっていない（`kanta@taro` など）、または `.local` の名前が引けていない。後者は管理者に IP を聞いて `ssh kanta@<IP>` |
| `Connection timed out` | 研究室の LAN にいない、Pi が落ちている |
| `Permission denied (publickey)` | 鍵が登録されていない、別の鍵を使っている、または Pi に入った状態の中から `ssh` している。Mac / Windows のターミナルから `ssh -v kanta@kanta.local` で使われた鍵を見て管理者に伝える |
| `Enter passphrase for key` が通らない | 自分の鍵のパスフレーズを間違えている（Pi 側の問題ではない） |
| `REMOTE HOST IDENTIFICATION HAS CHANGED` | Pi を焼き直した、または同じ IP に別の機器が来た。管理者に確認してから `ssh-keygen -R kanta.local` |

## 使うときのルール

- **`sudo` にはパスワードが要る**。設定変更・パッケージの導入・ファイル削除などは管理者に頼む。コンソールが使う LED・再起動・電源オフ・ログイン画面の再表示だけはパスワードなしで動く（`/etc/sudoers.d/99-kanta-require-password`）
- **カメラは同時に 1 プロセスだけ**。ピースカメラ・映像だけモード・配信のどれかが動いていると、ほかは使えない。コンソールの状態表示で確かめてから使う
- **メモリは 512MB しかない**。MediaPipe などの重い処理を 2 人が同時に動かすと Pi が固まり、SSH も届かなくなる。重い処理は 1 人ずつ
- **コードは Pi 上で直接編集しない**。このリポジトリで変更して、Mac から `rsync` で送る
- `kanta` を共有しているので、`sudo` なしでできること（`~/hand-landmarker` のファイル削除、動いているプログラムの停止など）は誰でもできてしまう。触る前にほかのメンバーに声をかける
