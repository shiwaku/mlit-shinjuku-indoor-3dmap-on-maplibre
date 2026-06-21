# 新宿駅周辺 屋内3Dマップ on MapLibre

新宿駅周辺の屋内地図オープンデータ（国土交通省）をもとに、フロアごとに標高（Z値）を付与した3次元 GeoJSON を生成し、**MapLibre GL JS** と **deck.gl** で立体的な屋内3Dマップとして可視化するプロジェクトです。

- **デモ**: https://shiwaku.github.io/mlit-shinjuku-indoor-3dmap-on-maplibre/
- **解説記事**: [屋内地図3次元データの作成とMapLibre GL JSとdeck.glでの屋内3Dマップの表示 - Qiita](https://qiita.com/shi-works/items/f50343df20d503653433)

## データ出典

- [新宿駅周辺屋内地図データ（国土交通省）](https://www.geospatial.jp/ckan/dataset/mlit-indoor-shinjuku-r2) を加工して作成
- [3D都市モデル（Project PLATEAU）豊島区（2023年度）土地利用モデル](https://www.geospatial.jp/ckan/dataset/plateau-13116-toshima-ku-2023)

## 特徴

- 国土交通省の屋内地図 Shapefile を、フロア別・ジオメトリ種別に整理した3D GeoJSON へ変換
- 基準標高にフロアごとの相対オフセットを加算し、地下〜地上の各階を立体的に分離して表示
- 歩行者ネットワーク（ノード／リンク）を、始点・終点の標高で線形補間して3D化
- 地下フロアは加算合成（glow）で発光表現
- 背景に 3D都市モデル（Project PLATEAU）豊島区の土地利用モデルを重畳

## 技術スタック

- [MapLibre GL JS](https://maplibre.org/) 5.6.0 — ベースの地図描画
- [deck.gl](https://deck.gl/) 8.9.0（`MapboxOverlay` / `GeoJsonLayer` / `TerrainLayer`）— 3Dレイヤー描画
- [PMTiles](https://github.com/protomaps/PMTiles) 3.2.0
- Python（[GeoPandas](https://geopandas.org/) / [Shapely](https://shapely.readthedocs.io/) / [pyproj](https://pyproj4.github.io/pyproj/)）— データ処理

## ディレクトリ構成

```
.
├── docs/                           # 配信用の静的サイト（GitHub Pages の公開元）
│   ├── index.html                  #   MapLibre + deck.gl による可視化ページ
│   └── data/                       #   ブラウザが読み込む GeoJSON
│       ├── geojson_merged/         #     フロア×ジオメトリ種別の GeoJSON
│       ├── shinjuku_link_3d.geojson #     3D 歩行者ネットワーク
│       ├── toshima-ku-landuse-2023-3d.geojson # 背景：豊島区 土地利用モデル（PLATEAU）
│       └── Road.geojson            #     道路データ（現在は未使用）
├── scripts/                        # データ処理パイプライン（Python）
│   ├── 01_make_3d_geojson.py       #   Shapefile → フロア別 3D GeoJSON 生成
│   ├── 02_merge_floors.py          #   フロア×ジオメトリ種別にマージ
│   ├── 03_add_z.py                 #   GeoJSON 全頂点へ Z 値を付与（背景データ用）
│   └── 04_network_3d.py            #   歩行者ネットワークの 3D 化
├── data/
│   ├── raw/                        # 入力 Shapefile（屋内地図・歩行者ネットワーク）
│   │   ├── ShinjukuTerminal/       #   屋内地図（フロア×種別の Shapefile 群）
│   │   └── nw/                     #   歩行者ネットワーク（node / link）
│   └── intermediate/               # 01 の中間出力（*.3d.geojson）
├── requirements.txt                # Python 依存パッケージ
└── README.md
```

## 入力データ（屋内地図 Shapefile）

`data/raw/ShinjukuTerminal/` に格納されている屋内地図 Shapefile は、国土交通省「高精度測位社会プロジェクト」で作成された新宿駅周辺屋内地図オープンデータで、国土地理院「階層別屋内地理空間情報データ仕様書（案）」（平成30年3月）に準拠しています。

- **作成**: 国土交通省 国土政策局 国土情報課（2020年8月）
- **原座標系**: 地理座標系 JGD2011（緯度経度。EPSG:6668）— 処理時に WGS 84（EPSG:4326）へ再投影
- **ファイル名規則**: `ShinjukuTerminal_<フロア>_<レイヤ種別>.shp`

### レイヤ種別

仕様書の定義に基づく地物用図形データです。

| レイヤ種別 | ジオメトリ | 仕様書上の名称 | 定義 |
|------------|------------|----------------|------|
| `Floor`     | ポリゴン | 階層データ | 建物内の各階の範囲。施設範囲内の建物躯体外側（屋外グランドレベル）も1つの階とする |
| `Space`     | ポリゴン | 物理的な空間データ | 階層内に存在する部屋、階段、エスカレーター、スロープ等の範囲 |
| `Fixture`   | ポリゴン | 固定設置物データ | 柱、家具、自動販売機、障害物、植栽、壁、水面等、移動の障害となる固定設置物の範囲 |
| `Facility`  | ポイント | 設備POI データ | トイレ、ATM、インフォメーション、ポスト、Wi-Fi、喫煙所等、移動の目印となる設備の代表点 |
| `Opening`   | ライン   | 出入口データ | 部屋の出入口、スロープ・エスカレーター・階段の乗降口、駅の改札、施設境界線等の出入口（線） |
| `Drawing`   | ライン   | 描画用地物データ | 階段の踏み段の線、段差の線、線路、回転ドアの形等、線で描画する地物 |
| `TWSILine`  | ライン   | 視覚障害者誘導用ブロック等（線） | 線状ブロック（歩行方向を指示）、プラットホーム縁端警告用内方表示ブロック等 |
| `TWSIPoint` | ポイント | 視覚障害者誘導用ブロック等（点） | 視覚障害者誘導用ブロック等を点で表したもの |

> **TWSI** = Tactile Walking Surface Indicator（視覚障害者誘導用ブロック、いわゆる点字ブロック）

### フロアとレイヤの対応

フロアは `B3`〜`4out` の 11 区分です。`out` が付くフロアは建物躯体外側の屋外グランドレベル（屋外通路・デッキ）を表します。レイヤ種別はフロアによって過不足があり、実データの有無は次のとおりです。

| フロア | Floor | Space | Fixture | Facility | Opening | Drawing | TWSILine | TWSIPoint |
|--------|-------|-------|---------|----------|---------|---------|----------|-----------|
| B3   | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| B2   | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| B1   | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 0F   | ✓ | ✓ | ✓ | ✓ | – | ✓ | ✓ | ✓ |
| 1F   | ✓ | ✓ | – | ✓ | ✓ | ✓ | – | – |
| 2F   | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | – | – |
| 2out | ✓ | ✓ | ✓ | ✓ | – | ✓ | ✓ | ✓ |
| 3F   | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | – | – |
| 3out | ✓ | ✓ | ✓ | ✓ | – | ✓ | – | – |
| 4F   | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | – | – |
| 4out | ✓ | ✓ | ✓ | ✓ | – | – | – | – |

### 歩行者ネットワーク

`data/raw/nw/` の `Shinjuku_node.shp`（ノード）と `Shinjuku_link.shp`（リンク）からなり、ノードの `ordinal`（階層数）により各階へ対応づけられます。

## データ処理パイプライン

```
data/raw/  Shapefile（屋内地図 / 歩行者ネットワーク）
        │
        ▼
scripts/01_make_3d_geojson.py
   ファイル名からフロアを推定し、BASE_Z(=37.5m) + フロアオフセットで
   全頂点に絶対標高 Z を付与 → data/intermediate/*.3d.geojson
        │
        ▼
scripts/02_merge_floors.py
   フロア × ジオメトリ種別（polygons / lines / points）でマージ
   → docs/data/geojson_merged/Shinjuku_<floor>.<geom>.geojson
        │
        ▼
scripts/04_network_3d.py
   node の ordinal から階を判定し Z を計算、link を始点〜終点で
   線形補間して 3D 化 → docs/data/shinjuku_link_3d.geojson
        │
        ▼
docs/index.html（MapLibre GL JS + deck.gl）で可視化
```

`scripts/03_add_z.py` は背景データ（土地利用モデル等）の全座標へ一律の Z 値を付与する補助スクリプトです。各スクリプトのパスはリポジトリルート基準で解決されるため、どのディレクトリから実行しても動作します。

### フロアごとの標高オフセット

各フロアは基準標高 `BASE_Z` に以下の相対オフセット（m）を加算した絶対標高で配置されます（見やすさ優先で強調）。

| フロア | B3 | B2 | B1 | 0F | 1F | 2F | 3F | 4F |
|--------|----|----|----|----|----|----|----|----|
| オフセット | -35 | -25 | -15 | 0 | +15 | +25 | +35 | +45 |

## 使い方

### 1. データの3D化（Python）

```bash
pip install -r requirements.txt

# Shapefile → フロア別 3D GeoJSON
python scripts/01_make_3d_geojson.py

# フロア × ジオメトリ種別にマージ
python scripts/02_merge_floors.py

# 歩行者ネットワークの 3D 化
python scripts/04_network_3d.py
```

### 2. 可視化（ブラウザ）

`fetch` でローカルの GeoJSON を読み込むため、`docs/` をルートにローカルサーバ経由で開きます。

```bash
python -m http.server 8000 --directory docs
# ブラウザで http://localhost:8000/ を開く
```

> **GitHub Pages**: 公開元を「`main` ブランチ / `/docs` フォルダ」に設定してください（Settings → Pages → Source: Deploy from a branch → Branch: `main` `/docs`）。
