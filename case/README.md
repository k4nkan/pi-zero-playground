# case（3D プリント用ケース）

Raspberry Pi Zero 2 W とカメラモジュールを入れる、装飾なしの箱型ケース。モニター（7 インチ HDMI）は別置きで、mini HDMI ケーブルでつなぐ。設計は OpenSCAD（[case.scad](case.scad)）で、寸法はすべて変数になっている。

## 形

- 底（base）とふた（lid）の2パーツ。外形 約 71 × 36 × 22mm
- Pi は底の柱に M2.5 のネジで固定。カメラはふたの裏の柱に M2 のネジで固定し、レンズをふたの四角い穴から出す
- ふたは縁を底の内側にはめ込むだけ（接着・ネジなし）
- 手前の長い辺に mini HDMI・micro USB 2つの穴、左の短い辺に microSD の切り欠き、底とふたに通気口

## 印刷前に実物を測る（★）

カメラ（RasTech 500 万画素）は商品ページに寸法が書かれていなかったので、Camera Module v1（25 × 24mm）と同じ形を仮定している。次の値を測って `case.scad` の先頭で直す。

| 変数 | 測るところ | 仮の値 |
| --- | --- | --- |
| `cam_w`, `cam_h` | カメラ基板の幅・高さ | 25, 24 |
| `cam_hole_dx`, `cam_hole_dy` | 取り付け穴の中心どうしの間隔（左右・上下） | 21, 12.5 |
| `cam_lens_offset` | 穴4つの中心から、レンズの中心までのずれ | 1.25 |
| `cam_lens_box` | レンズの四角い台座の幅 | 8.5 |
| `cam_lens_h` | 基板の表面からレンズの先端までの高さ | 5.5 |

Pi Zero 2 W の寸法は公式の図面どおりなので、そのままでよい。

## プレビューのしかた

### 1. OpenSCAD を入れる（初回だけ）

```sh
brew install --cask openscad
```

または [openscad.org](https://openscad.org/downloads.html) から Mac 版をダウンロードする。

### 2. 開いて見る

```sh
open case/case.scad
```

- `F5`: プレビュー（速い）。マウスで回せる
- `F6`: 本番の形を計算（遅いが正確。STL を書き出す前に必要）
- 先頭の `part = "both";` を書き換えると表示が変わる
  - `"assembled"`: 組み立てた状態。半透明の板が Pi とカメラの位置
  - `"base"` / `"lid"`: パーツ単体
  - `"both"`: 印刷用に並べた状態
- 右側の「Customizer」パネルからも数値を変えられる

### 3. STL を書き出す（印刷用）

GUI なら `F6` のあと「File → Export → Export as STL」。コマンドなら:

```sh
openscad -D 'part="base"' -o case/base.stl case/case.scad
openscad -D 'part="lid"'  -o case/lid.stl  case/case.scad
openscad -D 'part="assembled"' --render --imgsize=1200,900 -o case/preview.png case/case.scad  # 画像で確認
```

STL と PNG は生成物なのでコミットしない（`.gitignore` 済み）。

## 印刷のメモ

- 底はそのまま、ふたは裏返して（表面を下に）置く。`"both"` はその向きで並べてある
- 熱がこもるので、PLA より PETG がおすすめ
- ふたがきつい・ゆるいときは `tol`（初期値 0.2）を変える
- ネジ: M2.5 × 6mm 程度 ×4（Pi）、M2 × 4〜5mm 程度 ×4（カメラ）。柱の穴は下穴なので、直接ねじ込む

## モニタースタンド（`monitor_stand.scad`）

前の足と後ろの低い三角（高さ 10mm）のあいだの溝（`slot_w` = 4mm）にモニターの下の縁を差し込む。横幅 30mm（`width`）。溝は `tilt`（初期値 10°）だけ後ろに傾いている。

前の足は、座ったクマのぬいぐるみが前に投げ出した足の形。一辺 30mm（`foot_size`）の角を丸めた正方形（角の丸み `foot_corner` = 9mm）の断面を前に伸ばした棒で、正面に角丸の四角い足の裏がある（縁は `fillet` で丸める）。足の裏の溝（肉球の輪郭のような線）は、細い溝が印刷で潰れやすいので今は彫っていない（`pad = true` で彫れる）。足の長さは溝から 12mm（`foot_len`）。

足と後ろ側は、溝の下の土台（厚さ `base_t` = 4mm）でつながっている。土台は足の中まで `base_overlap`（6mm）食い込ませてあり、足と面でつながるので折れにくい。後ろの土台と三角は、正面から見えないので角を丸めていない（丸めると下向きの面ができて印刷で垂れやすいため）。後ろ側は、正面から見た足の輪郭より `hide_margin`（1mm）内側に収めてあるので、正面からは足の陰に隠れてつなぎ目が見えない。

モニターの左右に1個ずつ置く。足のつま先が少し外側を向く（`toe_out` = 8°。足の中心は後ろ側の中心とそろえてある）ので、**左用と右用を1個ずつ印刷する**。

```sh
openscad -D 'part="left"'  -o case/monitor_stand_left.stl  case/monitor_stand.scad
openscad -D 'part="right"' -o case/monitor_stand_right.stl case/monitor_stand.scad
```

`part = "both"` にすると、OpenSCAD のプレビューで左右を並べて見られる。STL は土台を下にした向きで出る。溝がきつい・ゆるいときは `slot_w` を 0.2mm ずつ変える。
