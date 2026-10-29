// モニタースタンド: 前の足と後ろの三角のあいだの溝にモニターの下の縁を差し込む。
// 前の足は、座ったクマのぬいぐるみが前に投げ出した足の形
// （角を丸めた正方形の断面を前に伸ばした棒を寝かせたもの。正面に角丸の四角い足の裏と、肉球の輪郭のような溝）。
// 全体の角は丸めてある（モニターを差し込む溝の縁だけは、幅を正確に保つため角のまま）。
// モニターの左右に1個ずつ置く。足のつま先は少し外側を向くので、左用と右用がある。単位は mm。
//
//   横から見た形
//    ______
//   (      |  |\   ← 後ろの三角（低い）
//   (______|溝| \
//           ‾‾‾‾‾‾‾  ← 土台（溝の下でつながっている）

part = "both";    // "left"（モニターの左に置く）/ "right" / "both"（印刷用に並べる）

$fn = 64;
width = 30;       // 横幅（モニターの縁に沿う方向）
slot_w = 5.1;     // 溝の幅（傾きに垂直な向き）。モニターの厚さ + すき間
tilt = 10;        // モニターを後ろに傾ける角度（度）。0 で垂直
base_t = 4;       // 溝の下の土台の厚さ（足と後ろ側をつなぐ部分なので薄くしすぎない）
base_overlap = 6; // 土台を足の中まで食い込ませる長さ。足と後ろ側を面でつなぐ（外からは見えない）
toe_out = 8;      // 足のつま先を外側に向ける角度（度、上から見て）。足の中心は後ろ側の中心とそろえる
foot_size = 30;   // 足の断面（角を丸めた正方形）の一辺。正面から見た足の大きさ
foot_corner = 9;  // 足の断面の角の丸み
foot_len = 12;    // 足の長さ（溝から足の裏まで）
fillet = 4;       // 足の裏の縁の丸み
foot_flat = 1.5;  // 足の底を平らに切る量（印刷で台に付く面を作る）
pad = false;      // 足の裏に溝（肉球の輪郭のような線）を彫るか。細い溝は印刷で潰れやすいので今は無し
pad_inset = 2;    // 足の裏の溝を、足の裏の平らな面の縁からどれだけ内側に彫るか
pad_groove = 2;   // 足の裏の溝の幅
pad_depth = 1.5;  // 足の裏の溝の深さ
pad_corner = 4;   // 足の裏の溝の角の丸み
back_len = 24;    // 後ろの三角の奥行き
back_h = 10;      // 後ろの三角の高さ（土台の上から）
hide_margin = 1;  // 正面から見て後ろ側が足に隠れるよう、足の輪郭よりどれだけ内側に収めるか

half = slot_w / 2 / cos(tilt);  // 傾けても溝の幅が slot_w になる、底での前後のずれ
lean = [sin(tilt), cos(tilt)];  // 溝の向き（後ろへ傾く）

// 後ろ側を横から見た形（y が前後、z が上下）: 土台と後ろの三角。正面から見えないので角は丸めない
// （丸めると下向きの面ができて印刷で垂れやすい）。
// 三角の溝側の面は溝の傾きに合わせる（溝を後から削ると、角が溝の手前に残るため）
module back_profile() {
  translate([-half - base_overlap, 0]) square([half + base_overlap + back_len, base_t]);  // 前は足の中まで伸ばす
  slot_back_bottom = [half, base_t];
  polygon([slot_back_bottom, [back_len, base_t], slot_back_bottom + lean * back_h / cos(tilt)]);
}

module back_part() {
  rotate([90, 0, 90]) linear_extrude(height = width) back_profile();
}

// 足の断面（角を丸めた正方形）を、y = at の位置に、縁から inset だけ細らせて置いた薄い板
module foot_slice(at, inset) {
  side = foot_size - 2 * inset;
  r = max(foot_corner - inset, 0.01);
  translate([0, at, foot_size / 2 - foot_flat]) rotate([90, 0, 0])
    linear_extrude(height = 0.01, center = true)
      offset(r = r) square(side - 2 * r, center = true);
}

// 足の裏（y = -len の面）に彫る、角丸の四角い輪の溝
module pad_groove_cut(len) {
  outer = foot_size - 2 * fillet - 2 * pad_inset;  // 足の裏の平らな面より pad_inset 内側
  translate([0, -len + pad_depth, foot_size / 2 - foot_flat]) rotate([90, 0, 0])
    linear_extrude(height = pad_depth + 1)
      difference() {
        offset(r = pad_corner) square(outer - 2 * pad_corner, center = true);
        offset(r = pad_corner) square(outer - 2 * pad_corner - 2 * pad_groove, center = true);
      }
}

// 前の足: 角丸の正方形の断面を前に伸ばした棒を寝かせたもの。足の裏の縁だけ fillet で丸め、底を平らに切る。
// つま先を toe（度）だけ外へ回し、溝側の面で切りそろえてから、溝の傾きに合わせて斜めにずらす
module front_foot(toe) {
  // 回した分だけ足の裏の角が前に出るので、その分短くして足の長さを foot_len にそろえる
  len = foot_len - foot_size / 2 * sin(abs(toe));
  // 傾きは後ろの三角と同じく土台の上（z = base_t）を基準にする。地面を基準にすると、
  // 溝が base_t * sin(tilt)（約 0.7mm）だけ slot_w より狭くなる
  translate([width / 2, -half - base_t * tan(tilt), 0])
    multmatrix([[1, 0, 0, 0], [0, 1, tan(tilt), 0], [0, 0, 1, 0], [0, 0, 0, 1]])
      intersection() {
        rotate([0, 0, toe])
          difference() {
            hull() {
              foot_slice(len, 0);       // 溝の後ろまで伸ばしておき、あとで溝の面で切る
              for (a = [0 : 15 : 90])   // 足の裏の縁を 1/4 円で丸める
                foot_slice(-(len - fillet) - fillet * sin(a), fillet * (1 - cos(a)));
            }
            if (pad) pad_groove_cut(len);
          }
        // 溝より前・地面より上だけ残す
        translate([-width, -2 * foot_len, 0]) cube([2 * width, 2 * foot_len, foot_size]);
      }
}

// 正面から見た足の輪郭（角丸の正方形）を hide_margin だけ細らせ、前後に長く伸ばした立体。
// 後ろ側をこの中に収めると、正面から見て足の陰に隠れる
module behind_foot() {
  side = foot_size - 2 * hide_margin;
  r = max(foot_corner - hide_margin, 0.01);
  translate([width / 2, 0, foot_size / 2 - foot_flat]) rotate([90, 0, 0])
    linear_extrude(height = 4 * (back_len + foot_len), center = true)
      offset(r = r) square(side - 2 * r, center = true);
}

// 左用。つま先は左（-x）へ向く
module stand_left() {
  intersection() {
    back_part();
    behind_foot();
  }
  front_foot(-toe_out);
}

// 土台を下にした向きで出力する
if (part == "left") {
  stand_left();
} else if (part == "right") {
  translate([width, 0, 0]) mirror([1, 0, 0]) stand_left();
} else {
  stand_left();
  translate([2 * width + 10, 0, 0]) mirror([1, 0, 0]) stand_left();
}
