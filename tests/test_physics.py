from hanoi_air.dispersion import gaussian_plume_concentration
from hanoi_air.interpolation import idw_interpolate
from hanoi_air.schemas import SourceEmission
from hanoi_air.weather import wind_components


def test_idw_exact_station_value():
    points = [{"lat": 21.0, "lon": 105.8, "value": 88.0}]
    targets = [{"lat": 21.0, "lon": 105.8}]
    assert idw_interpolate(points, targets) == [88.0]


def test_wind_components_meteorological_south_wind():
    u, v = wind_components(10.0, 180.0)
    assert abs(u) < 1e-6
    assert round(v, 3) == 10.0


def test_gaussian_plume_is_downwind_oriented():
    source = SourceEmission(
        source_id="s1",
        name="test",
        lat=21.0,
        lon=105.8,
        district="x",
        height_m=30.0,
        pm25_g_s=1.0,
        no2_g_s=2.0,
    )
    downwind = gaussian_plume_concentration(source, 21.03, 105.8, 2.5, 180.0, "pm25")
    upwind = gaussian_plume_concentration(source, 20.97, 105.8, 2.5, 180.0, "pm25")
    assert downwind > 0
    assert upwind == 0
    assert downwind > upwind
