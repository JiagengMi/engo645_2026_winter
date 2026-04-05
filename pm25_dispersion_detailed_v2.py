"""
Advanced PM2.5 Smoke Dispersion Map - Version 2
Focus on 2 major events with detailed visualization
风向/风速用箭头表示，扩散范围用颜色填充的椭圆表示
"""

import argparse
from datetime import datetime, timedelta
from pathlib import Path
import math

import folium
import numpy as np
import pandas as pd
from folium import plugins


CALGARY_LAT = 51.0447
CALGARY_LON = -114.0719
PM25_THRESHOLD = 25.0


def create_wind_arrow(lat, lon, wind_direction, wind_speed, map_obj):
    """
    创建风向箭头（风吹来的方向指向）

    Args:
        wind_direction: 风从哪个方向来 (0-360°)
        wind_speed: 风速 (m/s)
    """
    # 计算箭头长度（基于风速）
    arrow_length = min(0.3, 0.05 + wind_speed * 0.04)  # 0.05-0.3度

    # 风向反向（风吹来的方向反向就是风去的方向）
    arrow_direction = (wind_direction + 180) % 360
    arrow_rad = math.radians(arrow_direction)

    # 箭头终点
    end_lat = lat + arrow_length * np.cos(arrow_rad)
    end_lon = lon + arrow_length * np.sin(arrow_rad) / np.cos(math.radians(lat))

    # 颜色基于风速
    if wind_speed < 2:
        color = "blue"
        weight = 2
    elif wind_speed < 3:
        color = "green"
        weight = 3
    elif wind_speed < 4:
        color = "orange"
        weight = 4
    else:
        color = "red"
        weight = 5

    # 绘制箭头线
    folium.PolyLine(
        [[lat, lon], [end_lat, end_lon]],
        color=color,
        weight=weight,
        opacity=0.8,
        popup=f"Wind: {wind_speed:.2f} m/s from {wind_direction:.0f}°",
        tooltip=f"Wind: {wind_speed:.2f} m/s"
    ).add_to(map_obj)

    # 绘制箭头头
    arrow_head_size = 0.08
    left_rad = arrow_rad + math.radians(150)
    right_rad = arrow_rad - math.radians(150)

    left_lat = end_lat + arrow_head_size * np.cos(left_rad)
    left_lon = end_lon + arrow_head_size * np.sin(left_rad) / np.cos(math.radians(end_lat))

    right_lat = end_lat + arrow_head_size * np.cos(right_rad)
    right_lon = end_lon + arrow_head_size * np.sin(right_rad) / np.cos(math.radians(end_lat))

    folium.PolyLine(
        [[end_lat, end_lon], [left_lat, left_lon]],
        color=color,
        weight=weight,
        opacity=0.8
    ).add_to(map_obj)

    folium.PolyLine(
        [[end_lat, end_lon], [right_lat, right_lon]],
        color=color,
        weight=weight,
        opacity=0.8
    ).add_to(map_obj)


def create_dispersion_ellipse(lat, lon, major_axis_km, minor_axis_km,
                            direction_deg, color, opacity, map_obj):
    """
    创建扩散椭圆多边形
    """
    direction_rad = np.radians(direction_deg)
    angles = np.linspace(0, 2*np.pi, 64)

    x = major_axis_km * np.cos(angles)
    y = minor_axis_km * np.sin(angles)

    x_rotated = x * np.cos(direction_rad) - y * np.sin(direction_rad)
    y_rotated = x * np.sin(direction_rad) + y * np.cos(direction_rad)

    lat_offset = y_rotated / 111.0
    lon_offset = x_rotated / (111.0 * np.cos(np.radians(lat)))

    coords = [
        [lat + lat_offset[i], lon + lon_offset[i]]
        for i in range(len(angles))
    ]
    coords.append(coords[0])

    folium.Polygon(
        coords,
        color=color,
        weight=2,
        fillColor=color,
        fillOpacity=opacity,
        popup=f"Impact Radius: {major_axis_km:.0f} km",
        tooltip="Smoke impact area"
    ).add_to(map_obj)


def get_color_by_pm25(pm25_value: float):
    """根据PM2.5返回颜色"""
    if pm25_value >= 100:
        return "#8B0000"
    elif pm25_value >= 50:
        return "#DC143C"
    elif pm25_value >= 35:
        return "#FF4500"
    elif pm25_value >= 25:
        return "#FF8C00"
    else:
        return "#90EE90"


def create_event_detailed_map(test_data: pd.DataFrame, start_date, end_date,
                             event_name: str, out_dir: Path):
    """
    创建详细的事件地图（可以是任意长度的时间窗口）
    """
    period_data = test_data[
        (test_data["date"] >= start_date) &
        (test_data["date"] <= end_date)
    ].copy()

    peak_date = period_data.loc[period_data["pm25"].idxmax(), "date"]
    peak_pm25 = period_data["pm25"].max()

    # 创建地图
    m = folium.Map(
        location=[CALGARY_LAT, CALGARY_LON],
        zoom_start=7,
        tiles="CartoDB positron",
        prefer_canvas=True
    )

    # 添加标题面板
    title_html = f"""
    <div style="position: fixed;
                top: 10px; left: 50px; width: 380px; height: auto;
                background-color: white; border: 3px solid darkred; z-index:9999;
                font-size: 12px; padding: 15px; border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.3);">
    <p style="margin: 0; font-weight: bold; color: darkred; font-size: 16px;">
    {event_name}</p>
    <p style="margin: 8px 0; font-size: 13px;">
    <span style="font-weight: bold;">Peak:</span> {peak_pm25:.1f} µg/m³ on {peak_date.strftime("%B %d, %Y")}</p>
    <p style="margin: 5px 0; font-size: 13px;">
    <span style="font-weight: bold;">Period:</span> {start_date.strftime("%b %d")} to {end_date.strftime("%b %d, %Y")}</p>
    <p style="margin: 5px 0; font-size: 11px; color: #666;">
    <strong>Daily Details:</strong> Hover over elements for info<br>
    <strong>Arrow:</strong> Wind direction & speed<br>
    <strong>Ellipse:</strong> PM2.5 impact radius</p>
    </div>
    """
    m.get_root().html.add_child(folium.Element(title_html))

    # 为每一天添加图层
    daily_info = []

    for idx, (_, row) in enumerate(period_data.iterrows()):
        date_str = row["date"].strftime("%Y-%m-%d")
        pm25 = row["pm25"]
        wind_speed = row.get("era5_wind_speed_mean_ms", 2.5)
        wind_direction = row.get("era5_wind_from_deg", 180)
        fire_count = row.get("fire_count", 0)

        # 计算扩散椭圆
        base_radius = 50
        intensity_factor = max(0.3, min(2.0, pm25 / PM25_THRESHOLD))
        influence_radius = base_radius * intensity_factor

        wind_speed_normalized = min(wind_speed / 5.0, 1.0)
        major_axis = influence_radius * (1.0 + 0.5 * wind_speed_normalized)
        minor_axis = influence_radius * (1.0 - 0.3 * wind_speed_normalized)

        dispersion_direction = (wind_direction + 180) % 360
        color = get_color_by_pm25(pm25)

        # 添加椭圆
        create_dispersion_ellipse(
            CALGARY_LAT, CALGARY_LON,
            major_axis, minor_axis,
            dispersion_direction,
            color, 0.4, m
        )

        # 添加风向箭头
        create_wind_arrow(
            CALGARY_LAT, CALGARY_LON,
            wind_direction, wind_speed, m
        )

        # 记录日期信息
        is_peak = (row["date"].date() == peak_date.date())
        daily_info.append({
            "date": date_str,
            "pm25": pm25,
            "wind_speed": wind_speed,
            "wind_direction": wind_direction,
            "is_peak": is_peak,
            "fire": "Yes" if fire_count > 0 else "No"
        })

    # 添加Calgary标记
    folium.CircleMarker(
        location=[CALGARY_LAT, CALGARY_LON],
        radius=12,
        color="blue",
        fill=True,
        fillColor="blue",
        fillOpacity=0.9,
        popup="<b>Calgary City Center</b>",
        zIndex=1000,
        weight=3
    ).add_to(m)

    # 添加数据表面板（显示所有天的数据）
    table_html = """
    <div style="position: fixed;
                bottom: 50px; right: 50px; width: 320px; max-height: 350px;
                background-color: white; border: 2px solid #333; z-index:9999;
                font-size: 10px; padding: 10px; border-radius: 5px;
                overflow-y: auto; box-shadow: 0 4px 12px rgba(0,0,0,0.3);">
    <p style="margin: 0; font-weight: bold; margin-bottom: 8px;">Daily Data</p>
    <table style="width: 100%; border-collapse: collapse; font-size: 9px;">
    <tr style="background-color: #f0f0f0;">
        <th style="border: 1px solid #ddd; padding: 3px;">Date</th>
        <th style="border: 1px solid #ddd; padding: 3px;">PM2.5</th>
        <th style="border: 1px solid #ddd; padding: 3px;">Wind</th>
        <th style="border: 1px solid #ddd; padding: 3px;">Dir</th>
    </tr>
    """

    for info in daily_info:
        highlight = "background-color: #ffe6e6;" if info["is_peak"] else ""
        table_html += f"""
    <tr style="{highlight}">
        <td style="border: 1px solid #ddd; padding: 3px;">{info['date']}</td>
        <td style="border: 1px solid #ddd; padding: 3px; text-align: right;"><b>{info['pm25']:.1f}</b></td>
        <td style="border: 1px solid #ddd; padding: 3px; text-align: right;">{info['wind_speed']:.1f}</td>
        <td style="border: 1px solid #ddd; padding: 3px; text-align: right;">{info['wind_direction']:.0f}°</td>
    </tr>
    """

    table_html += """
    </table>
    <p style="margin-top: 8px; font-size: 9px; color: #666;">
    <span style="background-color: #ffe6e6; padding: 2px 4px;">Peak day highlighted</span>
    </p>
    </div>
    """
    m.get_root().html.add_child(folium.Element(table_html))

    # 添加图例
    legend_html = """
    <div style="position: fixed;
                top: 420px; left: 50px; width: 280px; height: auto;
                background-color: white; border: 2px solid grey; z-index:9999;
                font-size: 11px; padding: 10px; border-radius: 5px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.2);">
    <p style="margin: 0 0 8px 0; font-weight: bold;">Legend</p>
    <hr style="margin: 5px 0;">
    <p style="margin: 5px 0; font-weight: bold; color: #666;">Ellipse (Impact Area):</p>
    <div style="margin: 3px 0;"><span style="display:inline-block; width:12px; height:12px; background:#90EE90; border:1px solid #333; margin-right:5px;"></span>Low (<25)</div>
    <div style="margin: 3px 0;"><span style="display:inline-block; width:12px; height:12px; background:#FF8C00; border:1px solid #333; margin-right:5px;"></span>Moderate (25-35)</div>
    <div style="margin: 3px 0;"><span style="display:inline-block; width:12px; height:12px; background:#FF4500; border:1px solid #333; margin-right:5px;"></span>High (35-50)</div>
    <div style="margin: 3px 0;"><span style="display:inline-block; width:12px; height:12px; background:#DC143C; border:1px solid #333; margin-right:5px;"></span>Severe (50-100)</div>
    <div style="margin: 3px 0;"><span style="display:inline-block; width:12px; height:12px; background:#8B0000; border:1px solid #333; margin-right:5px;"></span>Critical (≥100)</div>
    <hr style="margin: 5px 0;">
    <p style="margin: 5px 0; font-weight: bold; color: #666;">Wind Arrow:</p>
    <div style="margin: 3px 0; font-size: 9px;">
    <span style="color: blue;">■</span> Weak
    <span style="color: green;">■</span> Light
    <span style="color: orange;">■</span> Mod<br>
    <span style="color: red;">■</span> Strong
    </div>
    <p style="margin-top: 8px; font-size: 9px; color: #666;">
    Arrow size & color = wind speed<br>
    Arrow direction = wind direction<br>
    Ellipse size = PM2.5 intensity
    </p>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    return m, peak_pm25


def main():
    parser = argparse.ArgumentParser(description="Create detailed 2-event PM2.5 dispersion maps")
    parser.add_argument("--processed-dir", type=Path, default=Path("processed"),
                       help="Path to processed data directory")
    args = parser.parse_args()

    out_dir = args.processed_dir / "model_outputs" / "spatial_temporal_analysis"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("[STEP 1] Loading data...")
    high_pollution = pd.read_csv(out_dir / "high_pollution_events.csv")
    high_pollution["date"] = pd.to_datetime(high_pollution["date"])

    # 找两个最严重的事件
    top_2_events = high_pollution.nlargest(2, "pm25")
    print(f"[INFO] Top 2 events:")
    for idx, (_, event) in enumerate(top_2_events.iterrows(), 1):
        print(f"  Event {idx}: {event['date'].strftime('%Y-%m-%d')} - PM2.5: {event['pm25']:.1f} ug/m3")

    # 创建完整的时间线（用于时间窗口）
    date_range = pd.date_range(
        start=high_pollution["date"].min() - timedelta(days=3),
        end=high_pollution["date"].max() + timedelta(days=3),
        freq="D"
    )

    full_timeline = pd.DataFrame({
        "date": date_range,
        "pm25": 15.0,
        "era5_wind_speed_mean_ms": 2.5,
        "era5_wind_from_deg": 180.0,  # 改为浮点数
        "fire_count": 0.0,
        "upwind_fire_count": 0.0
    })

    # 合并高污染事件数据
    for idx, row in high_pollution.iterrows():
        match = full_timeline["date"].dt.date == row["date"].date()
        if match.any():
            full_timeline.loc[match, "pm25"] = row["pm25"]
            full_timeline.loc[match, "era5_wind_speed_mean_ms"] = row["era5_wind_speed_mean_ms"]
            full_timeline.loc[match, "era5_wind_from_deg"] = row["era5_wind_from_deg"]
            full_timeline.loc[match, "fire_count"] = row.get("fire_count", 0)
            full_timeline.loc[match, "upwind_fire_count"] = row.get("upwind_fire_count", 0)

    # 为每个顶级事件创建详细地图
    for event_num, (_, event) in enumerate(top_2_events.iterrows(), 1):
        event_date = event["date"]

        # 扩展时间窗口：前3天到后4天
        start_date = event_date - timedelta(days=3)
        end_date = event_date + timedelta(days=4)

        print(f"\n[STEP {event_num+1}] Creating detailed map for Event {event_num}...")
        print(f"  Date range: {start_date.date()} to {end_date.date()} (8 days)")

        m, peak = create_event_detailed_map(
            full_timeline,
            start_date, end_date,
            f"Event #{event_num} - PM2.5 Peak: {event['pm25']:.1f} µg/m³",
            out_dir
        )

        filename = f"pm25_detailed_event_{event_num}_extended.html"
        m.save(out_dir / filename)
        print(f"  [CREATED] {filename}")

    # 创建导航索引
    index_html = """<!DOCTYPE html>
<html>
<head>
    <title>PM2.5 Smoke Dispersion - Detailed Events</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; background: #f5f5f5; }
        h1 { color: #8B0000; border-bottom: 3px solid #DC143C; padding-bottom: 10px; }
        .intro { background: white; padding: 20px; border-radius: 8px; border-left: 4px solid #FF4500; margin-bottom: 20px; }
        .event-card { background: white; padding: 20px; border-radius: 8px; margin: 15px 0; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        .event-card h2 { margin-top: 0; color: #DC143C; }
        .event-card a { display: inline-block; margin-top: 10px; padding: 12px 20px; background: #DC143C;
                        color: white; text-decoration: none; border-radius: 5px; font-weight: bold; }
        .event-card a:hover { background: #8B0000; }
        .key-info { background: #ffe6e6; padding: 10px; border-left: 4px solid #DC143C; margin: 10px 0; }
        .wind-info { font-size: 12px; color: #666; margin-top: 10px; }
    </style>
</head>
<body>
    <h1>PM2.5 Smoke Dispersion Analysis</h1>

    <div class="intro">
        <h2>Detailed 2-Event Visualization</h2>
        <p>This analysis focuses on the <strong>2 most severe PM2.5 pollution events</strong> in Calgary.</p>
        <ul>
            <li><strong>Extended Timeline:</strong> ±3-4 days around peak to see full progression</li>
            <li><strong>Wind Arrows:</strong> Direction (arrow direction) and speed (arrow size & color)</li>
            <li><strong>Ellipse Areas:</strong> Impact zone size = PM2.5 intensity</li>
            <li><strong>Daily Data Table:</strong> All wind and pollution metrics for each day</li>
            <li><strong>Color Coding:</strong> Green (safe) → Red (severe) → Dark Red (critical)</li>
        </ul>
    </div>

    <div class="event-card">
        <h2>Event #1 - Most Severe Pollution</h2>
        <p>This is the most severe PM2.5 event in the analysis period.</p>
        <div class="key-info">
            <strong>Peak PM2.5:</strong> See in map<br>
            <strong>Duration:</strong> 8 days visualization (3 days before to 4 days after)<br>
            <strong>Focus:</strong> Watch how ellipse grows to peak, then shrinks as pollution dissipates
        </div>
        <p class="wind-info"><strong>How to use:</strong> Zoom in/out, hover over elements for data, check the data table on right for daily metrics</p>
        <a href="pm25_detailed_event_1_extended.html">Open Event #1 Map</a>
    </div>

    <div class="event-card">
        <h2>Event #2 - Second Most Severe Pollution</h2>
        <p>This is the second most severe PM2.5 event in the analysis period.</p>
        <div class="key-info">
            <strong>Peak PM2.5:</strong> See in map<br>
            <strong>Duration:</strong> 8 days visualization<br>
            <strong>Focus:</strong> Compare with Event #1 to understand pollution patterns
        </div>
        <p class="wind-info"><strong>Key Observation:</strong> Notice differences in wind patterns, recovery time, and spatial extent</p>
        <a href="pm25_detailed_event_2_extended.html">Open Event #2 Map</a>
    </div>

    <div class="event-card" style="background: #f0f0f0; border-left: 4px solid #999;">
        <h2>How to Interpret the Maps</h2>
        <p><strong>Ellipse (Colored Area):</strong></p>
        <ul style="font-size: 13px; margin: 5px 0;">
            <li>Size = PM2.5 impact radius (calculated from concentration)</li>
            <li>Color = PM2.5 intensity (green=safe, red=severe, dark red=critical)</li>
            <li>Shape = Influenced by wind speed (strong wind = elongated, weak wind = round)</li>
            <li>Orientation = Wind direction (ellipse points in direction smoke travels)</li>
        </ul>
        <p><strong>Wind Arrow (From Calgary center):</strong></p>
        <ul style="font-size: 13px; margin: 5px 0;">
            <li>Direction = Where wind is blowing TO (opposite of arrow base)</li>
            <li>Length = Wind speed magnitude</li>
            <li>Color: Blue (weak) → Green (light) → Orange (moderate) → Red (strong)</li>
        </ul>
        <p><strong>Data Table (Bottom Right):</strong></p>
        <ul style="font-size: 13px; margin: 5px 0;">
            <li>Shows PM2.5, wind speed, wind direction for each day</li>
            <li>Pink background = Peak pollution day</li>
        </ul>
    </div>

    <footer style="margin-top: 40px; text-align: center; color: #999; border-top: 1px solid #ddd; padding-top: 20px; font-size: 12px;">
        <p>ENGO645 Data Mining Project - Advanced PM2.5 Dispersion Modeling</p>
        <p>Wind-influenced elliptical smoke plume visualization with temporal progression</p>
    </footer>
</body>
</html>"""

    with open(out_dir / "pm25_dispersion_index.html", "w", encoding="utf-8") as f:
        f.write(index_html)

    print(f"\n[STEP 3] Creating navigation index...")
    print(f"[CREATED] pm25_dispersion_index.html")

    print("\n" + "="*80)
    print("SUCCESS! Detailed 2-Event Dispersion Maps Created")
    print("="*80)
    print(f"\nStart here: pm25_dispersion_index.html")
    print(f"Location: {out_dir}")
    print("\nMaps created:")
    print("  - pm25_detailed_event_1_extended.html (8-day timeline)")
    print("  - pm25_detailed_event_2_extended.html (8-day timeline)")


if __name__ == "__main__":
    main()
