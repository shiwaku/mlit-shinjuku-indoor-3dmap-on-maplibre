#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
新宿駅 屋内地図R2（Shapefile群）→ フロアごとにZを付与した3D GeoJSONを一括生成。
- ./ShinjukuTerminal 配下の .shp を全て処理
- WGS84(EPSG:4326) へ再投影
- ファイル名からフロアを推定し、BASE_Z + FLOOR_OFFSETS[階] で絶対Zを付与
- 出力は ./geojson に *.3d.geojson
"""

import json, re, sys
from pathlib import Path
import geopandas as gpd
from shapely.geometry import (
    Point, LineString, Polygon, MultiPoint, MultiLineString,
    MultiPolygon, GeometryCollection, mapping
)

# ====== ここだけ触ればOK（わかりやすく最低限） ==========================
BASE_Z = 40.6  # 新宿駅の基準標高 (m, AMSL)。必要に応じて修正

# フロアごとの相対オフセット (m)。BASE_Z に加算して絶対高さにします。
# 地下はマイナス、屋外通路(out)は該当階と同じに設定。
'''
FLOOR_OFFSETS = {
    "B3": -10.5,
    "B2": -7.0,
    "B1": -3.5,
    "0F":  0.0,
    "1F": +4.0,
    "2F": +8.0,  "2out": +8.0,
    "3F": +12.0, "3out": +12.0,
    "4F": +16.0, "4out": +16.0,
}
'''
# 10倍協調
FLOOR_OFFSETS = {
    "B3": -63.0,
    "B2": -42.0,
    "B1": -21.0,
    "0F":  0.0,
    "1F": +24.0,
    "2F": +48.0,  "2out": +48.0,
    "3F": +72.0, "3out": +72.0,
    "4F": +96.0, "4out": +96.0,
}
# 入出力ディレクトリ
INPUT_DIR  = Path("./shape")
OUTPUT_DIR = Path("./geojson")
# ======================================================================

# 代表的なファイル名パターン（ShinjukuTerminal_X_*）
PATTERNS = [
    (re.compile(r"_b3[_\.]", re.I), "B3"),
    (re.compile(r"_b2[_\.]", re.I), "B2"),
    (re.compile(r"_b1[_\.]", re.I), "B1"),
    (re.compile(r"_0[_\.]",  re.I), "0F"),
    (re.compile(r"_1[_\.]",  re.I), "1F"),
    (re.compile(r"_2out[_\.]", re.I), "2out"),
    (re.compile(r"_3out[_\.]", re.I), "3out"),
    (re.compile(r"_4out[_\.]", re.I), "4out"),
    (re.compile(r"_2[_\.]",  re.I), "2F"),
    (re.compile(r"_3[_\.]",  re.I), "3F"),
    (re.compile(r"_4[_\.]",  re.I), "4F"),
]

def infer_floor_label(filename: str) -> str:
    """ファイル名からフロアラベルを推定（デフォルト0F）"""
    for pat, label in PATTERNS:
        if pat.search(filename):
            return label
    return "0F"

def add_z_to_geom(geom, z: float):
    """2D Geometry → 3D（全頂点に同一Z）"""
    if geom is None or geom.is_empty: return geom
    gt = geom.geom_type
    if gt == "Point":
        return Point(geom.x, geom.y, z)
    if gt == "MultiPoint":
        return MultiPoint([Point(p.x, p.y, z) for p in geom.geoms])
    if gt == "LineString":
        return LineString([(x, y, z) for x, y in geom.coords])
    if gt == "MultiLineString":
        return MultiLineString([LineString([(x, y, z) for x, y in ls.coords]) for ls in geom.geoms])
    if gt == "Polygon":
        ext = [(x, y, z) for x, y in geom.exterior.coords]
        ints = [[(x, y, z) for x, y in r.coords] for r in geom.interiors]
        return Polygon(ext, ints)
    if gt == "MultiPolygon":
        polys = []
        for p in geom.geoms:
            ext = [(x, y, z) for x, y in p.exterior.coords]
            ints = [[(x, y, z) for x, y in r.coords] for r in p.interiors]
            polys.append(Polygon(ext, ints))
        return MultiPolygon(polys)
    if gt == "GeometryCollection":
        return GeometryCollection([add_z_to_geom(g, z) for g in geom.geoms])
    return geom

def process_shp(shp: Path):
    label = infer_floor_label(shp.name)
    if label not in FLOOR_OFFSETS:
        print(f"[WARN] {shp.name}: 未定義のフロア '{label}' → 0F扱い")
        label = "0F"
    z_abs = BASE_Z + FLOOR_OFFSETS[label]

    gdf = gpd.read_file(shp)
    if gdf.crs:
        gdf = gdf.to_crs(epsg=4326)

    gdf3d = gdf.copy()
    gdf3d["geometry"] = gdf3d["geometry"].apply(lambda g: add_z_to_geom(g, z_abs))
    gdf3d["__floor"] = label
    gdf3d["__z_abs"] = float(z_abs)

    outname = shp.with_suffix("").name + ".3d.geojson"
    outpath = OUTPUT_DIR / outname
    outpath.parent.mkdir(parents=True, exist_ok=True)

    fc = {"type": "FeatureCollection", "features": []}
    for _, row in gdf3d.iterrows():
        fc["features"].append({
            "type": "Feature",
            "geometry": mapping(row.geometry),
            "properties": {k: v for k, v in row.items() if k != "geometry"}
        })
    with outpath.open("w", encoding="utf-8") as f:
        json.dump(fc, f, ensure_ascii=False)
    print(f"[OK] {shp.name} -> {outpath.name}  floor={label} z={z_abs:.2f}")

def main():
    shps = list(INPUT_DIR.rglob("*.shp"))
    if not shps:
        print(f"[ERR] {INPUT_DIR} に .shp が見つかりません")
        sys.exit(1)
    print(f"[INFO] BASE_Z={BASE_Z}, floors={sorted(FLOOR_OFFSETS.items())}")
    for shp in sorted(shps):
        try:
            process_shp(shp)
        except Exception as e:
            print(f"[ERR] {shp}: {e}")

if __name__ == "__main__":
    main()
