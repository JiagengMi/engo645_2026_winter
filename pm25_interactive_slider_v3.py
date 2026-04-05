"""
Advanced PM2.5 Smoke Dispersion Map - Version 3 with Time Slider
逐日显示扩散过程，可通过时间滑块切换
"""

import argparse
from datetime import timedelta
from pathlib import Path
import math
import json

import folium
import numpy as np
import pandas as pd


CALGARY_LAT = 51.0447
CALGARY_LON = -114.0719
PM25_THRESHOLD = 25.0


def create_wind_arrow(lat, lon, wind_direction, wind_speed):
    """创建风向箭头的GeoJSON特征"""
    # 计算箭头长度
    arrow_length = min(0.3, 0.05 + wind_speed * 0.04)
    arrow_direction = (wind_direction + 180) % 360
    arrow_rad = math.radians(arrow_direction)

    # 箭头终点
    end_lat = lat + arrow_length * np.cos(arrow_rad)
    end_lon = lon + arrow_length * np.sin(arrow_rad) / np.cos(math.radians(lat))

    # 颜色基于风速
    if wind_speed < 2:
        color = "blue"
    elif wind_speed < 3:
        color = "green"
    elif wind_speed < 4:
        color = "orange"
    else:
        color = "red"

    return {
        "type": "LineString",
        "coordinates": [[lon, lat], [end_lon, end_lat]],
        "color": color,
        "weight": 3 if wind_speed < 3 else (4 if wind_speed < 4 else 5),
        "popup": f"Wind: {wind_speed:.2f} m/s from {wind_direction:.0f}°"
    }


def create_dispersion_ellipse(lat, lon, major_axis_km, minor_axis_km,
                             direction_deg, color, opacity):
    """创建扩散椭圆的GeoJSON特征"""
    direction_rad = np.radians(direction_deg)
    angles = np.linspace(0, 2*np.pi, 64)

    x = major_axis_km * np.cos(angles)
    y = minor_axis_km * np.sin(angles)

    x_rotated = x * np.cos(direction_rad) - y * np.sin(direction_rad)
    y_rotated = x * np.sin(direction_rad) + y * np.cos(direction_rad)

    lat_offset = y_rotated / 111.0
    lon_offset = x_rotated / (111.0 * np.cos(np.radians(lat)))

    coords = [
        [lon + lon_offset[i], lat + lat_offset[i]]
        for i in range(len(angles))
    ]
    coords.append(coords[0])

    return {
        "type": "Polygon",
        "coordinates": [coords],
        "color": color,
        "fillColor": color,
        "fillOpacity": opacity
    }


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


def create_event_interactive_map(test_data: pd.DataFrame, start_date, end_date,
                                event_name: str, out_dir: Path):
    """创建交互式时间滑块地图"""

    period_data = test_data[
        (test_data["date"] >= start_date) &
        (test_data["date"] <= end_date)
    ].copy()

    peak_date = period_data.loc[period_data["pm25"].idxmax(), "date"]
    peak_pm25 = period_data["pm25"].max()

    # 创建基础地图
    m = folium.Map(
        location=[CALGARY_LAT, CALGARY_LON],
        zoom_start=7,
        tiles="CartoDB positron",
        prefer_canvas=True
    )

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

    # 为每一天准备数据
    daily_features = []
    daily_info = []

    for idx, (_, row) in enumerate(period_data.iterrows()):
        date_str = row["date"].strftime("%Y-%m-%d")
        day_num = idx + 1
        pm25 = row["pm25"]
        wind_speed = row.get("era5_wind_speed_mean_ms", 2.5)
        wind_direction = row.get("era5_wind_from_deg", 180)
        fire_count = row.get("fire_count", 0)
        is_peak = (row["date"].date() == peak_date.date())

        # 计算扩散椭圆
        base_radius = 50
        intensity_factor = max(0.3, min(2.0, pm25 / PM25_THRESHOLD))
        influence_radius = base_radius * intensity_factor

        wind_speed_normalized = min(wind_speed / 5.0, 1.0)
        major_axis = influence_radius * (1.0 + 0.5 * wind_speed_normalized)
        minor_axis = influence_radius * (1.0 - 0.3 * wind_speed_normalized)

        dispersion_direction = (wind_direction + 180) % 360
        color = get_color_by_pm25(pm25)

        # 创建椭圆和风向特征
        ellipse = create_dispersion_ellipse(
            CALGARY_LAT, CALGARY_LON,
            major_axis, minor_axis,
            dispersion_direction,
            color, 0.5
        )

        wind_arrow = create_wind_arrow(
            CALGARY_LAT, CALGARY_LON,
            wind_direction, wind_speed
        )

        daily_features.append({
            "date": date_str,
            "day_num": day_num,
            "ellipse": ellipse,
            "arrow": wind_arrow,
            "pm25": pm25,
            "wind_speed": wind_speed,
            "wind_direction": wind_direction,
            "is_peak": is_peak,
            "fire": "Yes" if fire_count > 0 else "No"
        })

        daily_info.append({
            "date": date_str,
            "pm25": pm25,
            "wind_speed": wind_speed,
            "wind_direction": wind_direction,
            "is_peak": is_peak
        })

    # 使用JavaScript创建时间滑块交互
    # 初始显示第一天
    first_day = daily_features[0]

    # 添加初始椭圆
    folium.GeoJson(
        {
            "type": "Feature",
            "geometry": first_day["ellipse"],
            "properties": {"name": f"{first_day['date']} PM2.5: {first_day['pm25']:.1f}"}
        },
        style_function=lambda x: {
            "color": first_day["arrow"]["color"] if isinstance(first_day["arrow"], dict) else "#000",
            "weight": 2,
            "fillColor": first_day["ellipse"]["fillColor"],
            "fillOpacity": 0.5
        }
    ).add_to(m)

    # 添加风向箭头
    folium.PolyLine(
        [[first_day["arrow"]["coordinates"][0][1], first_day["arrow"]["coordinates"][0][0]],
         [first_day["arrow"]["coordinates"][1][1], first_day["arrow"]["coordinates"][1][0]]],
        color=first_day["arrow"]["color"],
        weight=first_day["arrow"]["weight"],
        opacity=0.8
    ).add_to(m)

    # 添加标题面板
    title_html = f"""
    <div id="title-panel" style="position: fixed;
                top: 10px; left: 50px; width: 380px; height: auto;
                background-color: white; border: 3px solid darkred; z-index:9999;
                font-size: 12px; padding: 15px; border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.3);">
    <p style="margin: 0; font-weight: bold; color: darkred; font-size: 16px;">
    {event_name}</p>
    <p style="margin: 8px 0; font-size: 13px;">
    <span style="font-weight: bold;">Peak:</span> {peak_pm25:.1f} ug/m3 on {peak_date.strftime("%B %d, %Y")}</p>
    <p style="margin: 5px 0; font-size: 13px;">
    <span style="font-weight: bold;">Period:</span> {start_date.strftime("%b %d")} to {end_date.strftime("%b %d, %Y")}</p>
    <p id="day-info" style="margin: 8px 0; font-size: 12px; background: #f0f0f0; padding: 8px; border-left: 3px solid #FF8C00;">
    Day 1/8: {daily_info[0]['date']}<br>
    PM2.5: {daily_info[0]['pm25']:.1f} ug/m3<br>
    Wind: {daily_info[0]['wind_speed']:.1f} m/s from {daily_info[0]['wind_direction']:.0f}°
    </p>
    </div>

    <div style="position: fixed;
                top: 200px; left: 50px; width: 350px; height: auto;
                background-color: white; border: 2px solid #333; z-index:9998;
                font-size: 12px; padding: 15px; border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.2);">
    <p style="margin: 0 0 10px 0; font-weight: bold;">Time Slider</p>
    <input id="day-slider" type="range" min="1" max="{len(daily_features)}" value="1"
           style="width: 100%; cursor: pointer;" title="Drag to select day">
    <p id="slider-label" style="margin: 8px 0 0 0; text-align: center; font-size: 11px; color: #666;">
    Day <span id="day-num">1</span> of {len(daily_features)}
    </p>
    </div>
    """
    m.get_root().html.add_child(folium.Element(title_html))

    # 添加图例
    legend_html = """
    <div style="position: fixed;
                bottom: 50px; right: 50px; width: 280px; height: auto;
                background-color: white; border: 2px solid grey; z-index:9999;
                font-size: 10px; padding: 10px; border-radius: 5px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.2);">
    <p style="margin: 0 0 8px 0; font-weight: bold;">Legend</p>
    <p style="margin: 3px 0; font-weight: bold; color: #666;">Ellipse:</p>
    <div style="margin: 2px 0;"><span style="display:inline-block; width:10px; height:10px; background:#90EE90; border:1px solid #333; margin-right:3px;"></span>Low</div>
    <div style="margin: 2px 0;"><span style="display:inline-block; width:10px; height:10px; background:#FF8C00; border:1px solid #333; margin-right:3px;"></span>Moderate</div>
    <div style="margin: 2px 0;"><span style="display:inline-block; width:10px; height:10px; background:#FF4500; border:1px solid #333; margin-right:3px;"></span>High</div>
    <div style="margin: 2px 0;"><span style="display:inline-block; width:10px; height:10px; background:#DC143C; border:1px solid #333; margin-right:3px;"></span>Severe</div>
    <div style="margin: 2px 0;"><span style="display:inline-block; width:10px; height:10px; background:#8B0000; border:1px solid #333; margin-right:3px;"></span>Critical</div>
    <hr style="margin: 5px 0;">
    <p style="margin: 3px 0; font-weight: bold; color: #666;">Wind Arrow:</p>
    <div style="margin: 2px 0; font-size: 9px;">
    Blue=Weak, Green=Light, Orange=Moderate, Red=Strong
    </div>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    # 添加JavaScript来处理时间滑块交互
    script = f"""
    <script>
    var dailyFeatures = {json.dumps(daily_features)};

    function updateMap(dayIndex) {{
        // 移除所有先前的椭圆和箭头
        var layers = document.querySelectorAll('.leaflet-interactive');

        // 这里我们需要重新渲染
        // 因为folium限制，我们使用一个简单的方法：刷新页面参数
        // 更好的方法是使用leaflet的图层管理

        var day = dailyFeatures[dayIndex - 1];
        document.getElementById('day-info').innerHTML =
            'Day ' + dayIndex + '/{len(daily_features)}: ' + day['date'] + '<br>' +
            'PM2.5: ' + day['pm25'].toFixed(1) + ' ug/m3<br>' +
            'Wind: ' + day['wind_speed'].toFixed(1) + ' m/s from ' + day['wind_direction'].toFixed(0) + '°' +
            (day['is_peak'] ? '<br><span style="color: red; font-weight: bold;">PEAK DAY</span>' : '');

        document.getElementById('day-num').textContent = dayIndex;
    }}

    document.getElementById('day-slider').addEventListener('input', function(e) {{
        updateMap(parseInt(e.target.value));
    }});
    </script>
    """

    # 由于Folium的限制，我们需要使用一个更简单的方法
    # 创建一个单纯图层切换的地图

    return m, daily_features, daily_info, peak_pm25


def create_simple_time_slider_map(test_data: pd.DataFrame, start_date, end_date,
                                 event_name: str, out_dir: Path):
    """
    创建一个简化版本，用户可以通过重新加载来查看不同日期
    实际上，我们将创建一个HTML文件，嵌入所有日期的数据和JavaScript交互
    """

    period_data = test_data[
        (test_data["date"] >= start_date) &
        (test_data["date"] <= end_date)
    ].copy()

    peak_date = period_data.loc[period_data["pm25"].idxmax(), "date"]
    peak_pm25 = period_data["pm25"].max()

    # 准备所有日期的数据
    all_days_data = []

    for idx, (_, row) in enumerate(period_data.iterrows()):
        date_str = row["date"].strftime("%Y-%m-%d")
        day_num = idx + 1
        pm25 = row["pm25"]
        wind_speed = row.get("era5_wind_speed_mean_ms", 2.5)
        wind_direction = row.get("era5_wind_from_deg", 180)
        fire_count = row.get("fire_count", 0)
        is_peak = (row["date"].date() == peak_date.date())

        # 计算椭圆参数
        base_radius = 50
        intensity_factor = max(0.3, min(2.0, pm25 / PM25_THRESHOLD))
        influence_radius = base_radius * intensity_factor

        wind_speed_normalized = min(wind_speed / 5.0, 1.0)
        major_axis = influence_radius * (1.0 + 0.5 * wind_speed_normalized)
        minor_axis = influence_radius * (1.0 - 0.3 * wind_speed_normalized)

        dispersion_direction = (wind_direction + 180) % 360
        color = get_color_by_pm25(pm25)

        # 风速颜色
        if wind_speed < 2:
            wind_color = "blue"
        elif wind_speed < 3:
            wind_color = "green"
        elif wind_speed < 4:
            wind_color = "orange"
        else:
            wind_color = "red"

        all_days_data.append({
            "date": date_str,
            "day_num": day_num,
            "pm25": pm25,
            "wind_speed": wind_speed,
            "wind_direction": wind_direction,
            "is_peak": is_peak,
            "major_axis": major_axis,
            "minor_axis": minor_axis,
            "direction": dispersion_direction,
            "color": color,
            "wind_color": wind_color,
            "fire": "Yes" if fire_count > 0 else "No"
        })

    # 生成完整的HTML文件
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{event_name}</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>
    <style>
        body {{ margin: 0; padding: 0; font-family: Arial, sans-serif; }}
        #map {{ position: absolute; top: 0; bottom: 0; width: 100%; }}
        .panel {{ position: fixed; background: white; padding: 15px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.3); z-index: 1000; }}
        #title-panel {{ top: 10px; left: 50px; width: 360px; border: 3px solid darkred; }}
        #control-panel {{ top: 250px; left: 50px; width: 350px; border: 2px solid #333; }}
        #legend-panel {{ bottom: 50px; right: 50px; width: 280px; border: 2px solid grey; }}
        input[type="range"] {{ width: 100%; cursor: pointer; }}
        .day-info {{ margin: 8px 0; padding: 8px; background: #f0f0f0; border-left: 3px solid #FF8C00; font-size: 12px; }}
        table {{ font-size: 11px; border-collapse: collapse; margin-top: 10px; width: 100%; }}
        table td {{ padding: 3px; border: 1px solid #ddd; }}
        .peak {{ background-color: #ffe6e6; font-weight: bold; }}
        button {{ padding: 8px 15px; margin: 5px; cursor: pointer; background: #FF8C00; color: white; border: none; border-radius: 4px; font-weight: bold; }}
        button:hover {{ background: #DC143C; }}
        button.active {{ background: #DC143C; }}
    </style>
</head>
<body>
    <div id="map"></div>

    <div id="title-panel" class="panel">
        <p style="margin: 0; font-weight: bold; color: darkred; font-size: 16px;">{event_name}</p>
        <p style="margin: 8px 0; font-size: 13px;">
            <span style="font-weight: bold;">Peak:</span> {peak_pm25:.1f} ug/m3 on {peak_date.strftime("%B %d, %Y")}</p>
        <p style="margin: 5px 0; font-size: 13px;">
            <span style="font-weight: bold;">Period:</span> {start_date.strftime("%b %d")} to {end_date.strftime("%b %d, %Y")}</p>
        <div id="current-day-info" class="day-info">
            Loading...
        </div>
    </div>

    <div id="control-panel" class="panel">
        <p style="margin: 0 0 10px 0; font-weight: bold;">Time Slider: Day <span id="day-num">1</span>/{len(all_days_data)}</p>
        <input id="day-slider" type="range" min="1" max="{len(all_days_data)}" value="1">
        <div style="text-align: center; margin-top: 10px;">
            <button onclick="previousDay()">← Previous</button>
            <button onclick="nextDay()">Next →</button>
        </div>
    </div>

    <div id="legend-panel" class="panel">
        <p style="margin: 0 0 8px 0; font-weight: bold;">Legend</p>
        <p style="margin: 2px 0; font-weight: bold; font-size: 11px;">Color = PM2.5 Level:</p>
        <div style="font-size: 10px;">
            <div><span style="display:inline-block; width:10px; height:10px; background:#90EE90; margin-right:3px;"></span>Low (<25)</div>
            <div><span style="display:inline-block; width:10px; height:10px; background:#FF8C00; margin-right:3px;"></span>Moderate (25-35)</div>
            <div><span style="display:inline-block; width:10px; height:10px; background:#FF4500; margin-right:3px;"></span>High (35-50)</div>
            <div><span style="display:inline-block; width:10px; height:10px; background:#DC143C; margin-right:3px;"></span>Severe (50-100)</div>
            <div><span style="display:inline-block; width:10px; height:10px; background:#8B0000; margin-right:3px;"></span>Critical (≥100)</div>
        </div>
        <hr style="margin: 5px 0;">
        <p style="margin: 2px 0; font-weight: bold; font-size: 11px;">Wind Arrow:</p>
        <div style="font-size: 10px;">
            Blue = Weak | Green = Light<br>
            Orange = Moderate | Red = Strong
        </div>
    </div>

    <script>
    var allDaysData = {json.dumps(all_days_data)};
    var map = L.map('map').setView([{CALGARY_LAT}, {CALGARY_LON}], 7);

    // 使用 CartoDB light_all 底图（与 pm25_detailed_event_1_extended.html 相同）
    L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
        attribution: '&copy; CartoDB',
        maxZoom: 18
    }}).addTo(map);

    var drawnLayers = L.featureGroup();
    map.addLayer(drawnLayers);

    // 添加Calgary标记
    L.circleMarker([{CALGARY_LAT}, {CALGARY_LON}], {{
        radius: 12,
        color: 'blue',
        fillColor: 'blue',
        fillOpacity: 0.9,
        weight: 3
    }}).bindPopup('<b>Calgary City Center</b>').addTo(map);

    // 加载Calgary实际城市边界 GeoJSON
    fetch('./City_Boundary_20260404.geojson')
        .then(response => response.json())
        .then(data => {{
            L.geoJSON(data, {{
                style: {{
                    color: '#FF0000',
                    weight: 1.5,
                    opacity: 0.8,
                    fill: false
                }},
                onEachFeature: function(feature, layer) {{
                    layer.bindPopup('<b>Calgary City Boundary</b>');
                }}
            }}).addTo(map);
        }})
        .catch(error => console.error('Error loading boundary:', error));

    function drawEllipse(day) {{
        drawnLayers.clearLayers();

        // 椭圆参数
        var majorAxis = day.major_axis;
        var minorAxis = day.minor_axis;
        var direction = day.direction * Math.PI / 180;

        // 生成椭圆点
        var points = [];
        for (var i = 0; i < 65; i++) {{
            var angle = (i / 64) * 2 * Math.PI;
            var x = majorAxis * Math.cos(angle);
            var y = minorAxis * Math.sin(angle);

            var xRot = x * Math.cos(direction) - y * Math.sin(direction);
            var yRot = x * Math.sin(direction) + y * Math.cos(direction);

            var latOff = yRot / 111.0;
            var lonOff = xRot / (111.0 * Math.cos({CALGARY_LAT} * Math.PI / 180));

            points.push([{CALGARY_LAT} + latOff, {CALGARY_LON} + lonOff]);
        }}

        // 绘制椭圆多边形
        L.polygon(points, {{
            color: day.color,
            weight: 2,
            fillColor: day.color,
            fillOpacity: 0.5
        }}).addTo(drawnLayers);

        // 绘制风向箭头
        var windDir = (day.wind_direction + 180) * Math.PI / 180;
        var arrowLen = 0.05 + day.wind_speed * 0.04;
        var endLat = {CALGARY_LAT} + arrowLen * Math.cos(windDir);
        var endLon = {CALGARY_LON} + arrowLen * Math.sin(windDir) / Math.cos({CALGARY_LAT} * Math.PI / 180);

        // 箭头杆
        L.polyline([[{CALGARY_LAT}, {CALGARY_LON}], [endLat, endLon]], {{
            color: day.wind_color,
            weight: day.wind_speed < 3 ? 2 : (day.wind_speed < 4 ? 3 : 4),
            opacity: 0.8
        }}).addTo(drawnLayers);

        // 更新信息
        var status = day.is_peak ? '<span style="color: red; font-weight: bold;">★ PEAK DAY ★</span>' : '';
        document.getElementById('current-day-info').innerHTML =
            'Day ' + day.day_num + '/{len(all_days_data)}: ' + day.date + '<br>' +
            'PM2.5: ' + day.pm25.toFixed(1) + ' ug/m3  ' + status + '<br>' +
            'Wind: ' + day.wind_speed.toFixed(1) + ' m/s from ' + day.wind_direction.toFixed(0) + '°<br>' +
            'Impact Radius: ' + day.major_axis.toFixed(0) + ' km';
    }}

    function updateDay() {{
        var slider = document.getElementById('day-slider');
        var day = allDaysData[parseInt(slider.value) - 1];
        document.getElementById('day-num').textContent = slider.value;
        drawEllipse(day);
    }}

    function previousDay() {{
        var slider = document.getElementById('day-slider');
        if (parseInt(slider.value) > 1) {{
            slider.value = parseInt(slider.value) - 1;
            updateDay();
        }}
    }}

    function nextDay() {{
        var slider = document.getElementById('day-slider');
        if (parseInt(slider.value) < {len(all_days_data)}) {{
            slider.value = parseInt(slider.value) + 1;
            updateDay();
        }}
    }}

    document.getElementById('day-slider').addEventListener('input', updateDay);

    // 初始化
    updateDay();
    </script>
</body>
</html>"""

    return html_content


def main():
    parser = argparse.ArgumentParser(description="Create interactive time-slider PM2.5 dispersion maps")
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

    # 创建完整时间线
    date_range = pd.date_range(
        start=high_pollution["date"].min() - timedelta(days=3),
        end=high_pollution["date"].max() + timedelta(days=3),
        freq="D"
    )

    full_timeline = pd.DataFrame({
        "date": date_range,
        "pm25": 15.0,
        "era5_wind_speed_mean_ms": 2.5,
        "era5_wind_from_deg": 180.0,
        "fire_count": 0.0,
        "upwind_fire_count": 0.0
    })

    # 合并高污染数据
    for idx, row in high_pollution.iterrows():
        match = full_timeline["date"].dt.date == row["date"].date()
        if match.any():
            full_timeline.loc[match, "pm25"] = row["pm25"]
            full_timeline.loc[match, "era5_wind_speed_mean_ms"] = row["era5_wind_speed_mean_ms"]
            full_timeline.loc[match, "era5_wind_from_deg"] = row["era5_wind_from_deg"]
            full_timeline.loc[match, "fire_count"] = row.get("fire_count", 0)
            full_timeline.loc[match, "upwind_fire_count"] = row.get("upwind_fire_count", 0)

    # 为每个顶级事件创建地图
    for event_num, (_, event) in enumerate(top_2_events.iterrows(), 1):
        event_date = event["date"]
        start_date = event_date - timedelta(days=3)
        end_date = event_date + timedelta(days=4)

        print(f"\n[STEP {event_num+1}] Creating interactive map for Event {event_num}...")
        print(f"  Date range: {start_date.date()} to {end_date.date()} (8 days)")

        html_content = create_simple_time_slider_map(
            full_timeline,
            start_date, end_date,
            f"Event #{event_num} - PM2.5 Peak: {event['pm25']:.1f} ug/m3",
            out_dir
        )

        filename = f"pm25_event_{event_num}_interactive.html"
        with open(out_dir / filename, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"  [CREATED] {filename}")

    print("\n" + "="*80)
    print("SUCCESS! Interactive Time-Slider Maps Created")
    print("="*80)
    print(f"\nOpen these files in a web browser:")
    print(f"  - pm25_event_1_interactive.html")
    print(f"  - pm25_event_2_interactive.html")
    print(f"\nFeatures:")
    print(f"  - Drag slider to see each day's pollution")
    print(f"  - Use Previous/Next buttons for stepping")
    print(f"  - Ellipse and wind arrow update in real-time")
    print(f"  - See daily PM2.5, wind speed, wind direction")


if __name__ == "__main__":
    main()
