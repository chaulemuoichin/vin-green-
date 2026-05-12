"""Smart action recommendations: citizen and government, in Vietnamese.

Triggered by a single ``DistrictForecast`` row plus a numeric
``downwind_risk`` (typically the row's own ``downwind_risk`` field,
exposed as a separate argument so the function is callable both inside
the forecast loop and in tests with synthetic data).

Rules are keyed off:
    - AQI band (US-EPA or VN_AQI — caller chooses which key to pass)
    - Local hour (Hanoi rush hours: 7–9 and 17–19)
    - ``source_breakdown`` shares (which sector to actually target)
    - ``downwind_risk`` (whether industrial sources to the west are the
      proximate cause this hour)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

HANOI_TZ = timezone(timedelta(hours=7))

DOMINANT_SHARE_THRESHOLD: float = 0.35
DOWNWIND_RISK_THRESHOLD: float = 0.4


def _hanoi_hour(row: Mapping[str, Any]) -> int:
    timestamp = row.get("timestamp")
    if isinstance(timestamp, str):
        try:
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            return dt.astimezone(HANOI_TZ).hour
        except ValueError:
            pass
    # Fall back to hour_offset relative to "now" — coarse but never crashes.
    return int(row.get("hour_offset", 0)) % 24


def _is_rush_hour(hour: int) -> bool:
    return 7 <= hour <= 9 or 17 <= hour <= 19


def _dominant_share(shares: Mapping[str, float] | None) -> tuple[str, float]:
    if not shares:
        return ("other", 0.0)
    key = max(shares, key=lambda k: shares.get(k, 0.0))
    return (key, float(shares.get(key, 0.0)))


def citizen_actions(row: Mapping[str, Any]) -> list[str]:
    """Return concrete advice strings for residents."""
    aqi = int(row.get("aqi", 0))
    pm25 = float(row.get("pm25", 0.0))
    hour = _hanoi_hour(row)
    shares = row.get("source_breakdown") or {}
    out: list[str] = []

    if aqi <= 50:
        out.append("Chất lượng không khí tốt — có thể hoạt động ngoài trời bình thường.")
        return out

    if aqi <= 100:
        out.append("Người nhạy cảm (trẻ em, người già, bệnh hô hấp) nên theo dõi triệu chứng.")
        if _is_rush_hour(hour):
            out.append("Hạn chế đi bộ/đạp xe sát mặt đường giờ cao điểm.")
        return out

    if aqi <= 150:
        out.append("Đeo khẩu trang khi ra ngoài trên 30 phút.")
        out.append("Người nhạy cảm hạn chế tập thể dục ngoài trời.")
        if _is_rush_hour(hour):
            out.append(f"Tránh giờ cao điểm {hour:02d}h — đi sớm/muộn 30 phút.")
    elif aqi <= 200:
        out.append("Đeo khẩu trang N95/KF94 khi ra ngoài, đặc biệt sáng và chiều.")
        out.append("Đóng cửa sổ, dùng máy lọc không khí nếu có.")
        if pm25 >= 80:
            out.append("Trẻ em và người cao tuổi nên ở trong nhà.")
        if _is_rush_hour(hour):
            out.append("Ưu tiên đi xe buýt/metro thay xe máy giờ cao điểm.")
    elif aqi <= 300:
        out.append("Hạn chế tối đa hoạt động ngoài trời.")
        out.append("Bắt buộc đeo khẩu trang N95 nếu phải ra ngoài.")
        out.append("Dùng máy lọc không khí trong nhà, đóng kín cửa.")
    else:
        out.append("Ở trong nhà, đóng kín cửa sổ và lỗ thông gió.")
        out.append("Người có bệnh hô hấp/tim mạch hạn chế cử động mạnh.")
        out.append("Nếu phải ra ngoài: khẩu trang N95 + kính bảo hộ.")

    # Source-specific nuance for moderate-to-bad days.
    if aqi >= 120:
        top_key, top_share = _dominant_share(shares)
        if top_key == "traffic" and top_share >= DOMINANT_SHARE_THRESHOLD:
            out.append("Nguồn chính là giao thông — tránh đi bộ dọc trục đường lớn.")
        elif top_key == "industry" and top_share >= DOMINANT_SHARE_THRESHOLD:
            out.append("Đóng cửa sổ phía hướng nhà máy, theo dõi bản tin trạm gần nhất.")
        elif top_key == "agriculture" and top_share >= DOMINANT_SHARE_THRESHOLD:
            out.append("Đốt rơm rạ ngoại thành — không phơi quần áo, đóng cửa ban đêm.")
        elif top_key == "fire" and top_share >= 0.1:
            out.append("Khói cháy rừng từ xa — kiểm tra hướng gió trước khi ra ngoài.")
    return out


def government_actions(
    row: Mapping[str, Any],
    downwind_risk: float = 0.0,
) -> list[str]:
    """Return concrete intervention bullets for city authorities."""
    aqi = int(row.get("aqi", 0))
    shares = row.get("source_breakdown") or {}
    hour = _hanoi_hour(row)
    district_name = str(row.get("district_name", "khu vực"))
    out: list[str] = []

    if aqi <= 100:
        return out

    traffic_share = float(shares.get("traffic", 0.0))
    industry_share = float(shares.get("industry", 0.0))
    agriculture_share = float(shares.get("agriculture", 0.0))
    fire_share = float(shares.get("fire", 0.0))

    if aqi > 150 and traffic_share >= DOMINANT_SHARE_THRESHOLD:
        if _is_rush_hour(hour):
            out.append(f"Cấm xe tải qua {district_name} 6–10h và 16–20h.")
        out.append("Khuyến cáo phân luồng xe cá nhân, ưu tiên vận tải công cộng.")

    if aqi > 150 and industry_share >= 0.18 and downwind_risk >= DOWNWIND_RISK_THRESHOLD:
        out.append(
            f"Kiểm tra/tạm dừng các nhà máy xuôi gió về {district_name} "
            f"(điểm xuôi gió {downwind_risk:.2f})."
        )
    if agriculture_share >= 0.15 and aqi > 130:
        out.append("Tăng cường giám sát đốt rơm rạ ngoại thành; phối hợp xã/phường.")
    if fire_share >= 0.10 or (aqi > 200 and downwind_risk >= 0.3):
        out.append("Cảnh báo cộng đồng về khói cháy, mở trung tâm tránh ô nhiễm.")

    if aqi > 200:
        out.append(f"Khuyến cáo trường học tại {district_name} giảm hoạt động ngoài trời.")
    if aqi > 250:
        out.append("Kích hoạt kế hoạch khẩn cấp ô nhiễm cấp thành phố.")

    return out


def recommendations(
    row: Mapping[str, Any],
    downwind_risk: float = 0.0,
) -> dict[str, list[str]]:
    """Bundle citizen + government recommendations for one forecast row."""
    return {
        "citizen": citizen_actions(row),
        "government": government_actions(row, downwind_risk=downwind_risk),
    }
