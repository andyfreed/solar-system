"""
TRMNL Solar System Viewer — Vercel Serverless Function

Shows real-time planet positions around the Sun using Keplerian orbital mechanics.
No external API needed — positions computed from NASA/JPL orbital elements.
"""

from http.server import BaseHTTPRequestHandler
import json
import math
from datetime import datetime, timezone

# NASA/JPL Keplerian elements for approximate planetary positions
# Source: https://ssd.jpl.nasa.gov/planets/approx_pos.html
# Format: [value_at_J2000, rate_per_century]
PLANETS = {
    "Mercury": {
        "a": [0.38709927, 0.00000037],
        "e": [0.20563593, 0.00001906],
        "L": [252.25032350, 149472.67411175],
        "w_bar": [77.45779628, 0.16047689],
        "Omega": [48.33076593, -0.12534081],
    },
    "Venus": {
        "a": [0.72333566, 0.00000390],
        "e": [0.00677672, -0.00004107],
        "L": [181.97909950, 58517.81538729],
        "w_bar": [131.60246718, 0.00268329],
        "Omega": [76.67984255, -0.27769418],
    },
    "Earth": {
        "a": [1.00000261, 0.00000562],
        "e": [0.01671123, -0.00004392],
        "L": [100.46457166, 35999.37244981],
        "w_bar": [102.93768193, 0.32327364],
        "Omega": [0.0, 0.0],
    },
    "Mars": {
        "a": [1.52371034, 0.00001847],
        "e": [0.09339410, 0.00007882],
        "L": [-4.55343205, 19140.30268499],
        "w_bar": [-23.94362959, 0.44441088],
        "Omega": [49.55953891, -0.29257343],
    },
    "Jupiter": {
        "a": [5.20288700, -0.00011607],
        "e": [0.04838624, -0.00013253],
        "L": [34.39644051, 3034.74612775],
        "w_bar": [14.72847983, 0.21252668],
        "Omega": [100.47390909, 0.20469106],
    },
    "Saturn": {
        "a": [9.53667594, -0.00125060],
        "e": [0.05386179, -0.00050991],
        "L": [49.95424423, 1222.49362201],
        "w_bar": [92.59887831, -0.41897216],
        "Omega": [113.66242448, -0.28867794],
    },
    "Uranus": {
        "a": [19.18916464, -0.00196176],
        "e": [0.04725744, -0.00004397],
        "L": [313.23810451, 428.48202785],
        "w_bar": [170.95427630, 0.40805281],
        "Omega": [74.01692503, 0.04240589],
    },
    "Neptune": {
        "a": [30.06992276, 0.00026291],
        "e": [0.00859048, 0.00005105],
        "L": [-55.12002969, 218.45945325],
        "w_bar": [44.96476227, -0.32241464],
        "Omega": [131.78422574, -0.00508664],
    },
}

PLANET_ABBREV = {
    "Mercury": "Me", "Venus": "Ve", "Earth": "Ea", "Mars": "Ma",
    "Jupiter": "Ju", "Saturn": "Sa", "Uranus": "Ur", "Neptune": "Ne",
}

PLANET_DOT_SIZE = {
    "Mercury": 4, "Venus": 6, "Earth": 7, "Mars": 5,
    "Jupiter": 10, "Saturn": 9, "Uranus": 8, "Neptune": 8,
}


def julian_centuries_since_j2000():
    now = datetime.now(timezone.utc)
    a = (14 - now.month) // 12
    y = now.year + 4800 - a
    m = now.month + 12 * a - 3
    jd = (now.day + (153 * m + 2) // 5 + 365 * y
           + y // 4 - y // 100 + y // 400 - 32045)
    jd += (now.hour - 12) / 24.0 + now.minute / 1440.0 + now.second / 86400.0
    return (jd - 2451545.0) / 36525.0


def solve_kepler(M_deg, e):
    M = math.radians(M_deg)
    E = M
    for _ in range(50):
        dE = (E - e * math.sin(E) - M) / (1 - e * math.cos(E))
        E -= dE
        if abs(dE) < 1e-8:
            break
    return E


def compute_planet_position(name, elems, T):
    a = elems["a"][0] + elems["a"][1] * T
    e = elems["e"][0] + elems["e"][1] * T
    L = elems["L"][0] + elems["L"][1] * T
    w_bar = elems["w_bar"][0] + elems["w_bar"][1] * T
    Omega = elems["Omega"][0] + elems["Omega"][1] * T

    M = ((L - w_bar + 180) % 360) - 180
    E = solve_kepler(M, e)

    x_orb = a * (math.cos(E) - e)
    y_orb = a * math.sqrt(1 - e * e) * math.sin(E)

    w = math.radians(w_bar - Omega)
    Omega_rad = math.radians(Omega)

    x_ecl = x_orb * math.cos(w) - y_orb * math.sin(w)
    y_ecl = x_orb * math.sin(w) + y_orb * math.cos(w)

    x = x_ecl * math.cos(Omega_rad) - y_ecl * math.sin(Omega_rad)
    y = x_ecl * math.sin(Omega_rad) + y_ecl * math.cos(Omega_rad)

    dist = math.sqrt(x * x + y * y)
    angle = math.degrees(math.atan2(y, x)) % 360

    return {
        "name": name,
        "abbrev": PLANET_ABBREV[name],
        "x_au": x,
        "y_au": y,
        "distance_au": round(dist, 2),
        "angle_deg": round(angle, 1),
        "semi_major": a,
    }


def compute_all_planets():
    T = julian_centuries_since_j2000()
    return [compute_planet_position(name, elems, T)
            for name, elems in PLANETS.items()]


def scale_distance(au, max_au=32.0, max_px=200):
    return (math.sqrt(au) / math.sqrt(max_au)) * max_px


def compute_layout(planets, width, height):
    """Pre-compute all pixel positions for a given layout size."""
    cx = int(width / 2)
    cy = int(height / 2)
    margin = 25
    max_r = min(cx, cy) - margin

    # Orbital rings
    orbits = []
    for p in planets:
        r = int(scale_distance(p["semi_major"], max_px=max_r))
        orbits.append({
            "left": cx - r,
            "top": cy - r,
            "size": r * 2,
        })

    # Planet positions
    positioned = []
    for p in planets:
        dist = math.sqrt(p["x_au"] ** 2 + p["y_au"] ** 2)
        if dist < 0.001:
            continue
        dist_px = scale_distance(dist, max_px=max_r)
        angle = math.atan2(p["y_au"], p["x_au"])
        px = cx + dist_px * math.cos(angle)
        py = cy - dist_px * math.sin(angle)  # SVG/screen y is inverted

        dot = PLANET_DOT_SIZE.get(p["name"], 6)
        positioned.append({
            "name": p["name"],
            "abbrev": p["abbrev"],
            "distance_au": p["distance_au"],
            "left": int(px - dot / 2),
            "top": int(py - dot / 2),
            "dot": dot,
            "label_left": int(px),
            "label_top": int(py - dot / 2 - 3),
            "is_earth": p["name"] == "Earth",
            "ring_left": int(px - dot / 2 - 2),
            "ring_top": int(py - dot / 2 - 2),
            "ring_size": dot + 4,
        })

    return {
        "width": width,
        "height": height,
        "cx": cx,
        "cy": cy,
        "orbits": orbits,
        "planets": positioned,
    }


def build_response():
    raw_planets = compute_all_planets()
    now = datetime.now(timezone.utc)

    # Pre-compute pixel positions for each layout
    full = compute_layout(raw_planets, 450, 380)
    half = compute_layout(raw_planets, 320, 200)
    quadrant = compute_layout(raw_planets, 280, 200)

    # Simplified planet list for sidebar
    planet_list = [
        {
            "name": p["name"],
            "abbrev": p["abbrev"],
            "distance_au": p["distance_au"],
        }
        for p in raw_planets
    ]

    return {
        "planets": planet_list,
        "full": full,
        "half": half,
        "quadrant": quadrant,
        "date": now.strftime("%b %d, %Y"),
        "time_utc": now.strftime("%H:%M UTC"),
    }


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            data = build_response()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "s-maxage=3600, stale-while-revalidate=600")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode())
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
