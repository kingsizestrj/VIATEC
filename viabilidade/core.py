import math


def haversine(lat1, lon1, lat2, lon2):
    """Distância em metros entre dois pontos (lat/lon)."""
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def caixas_mais_proximas(caixas, lat, lon, n):
    """As n caixas mais próximas de (lat, lon), ordenadas por distância.
    Cada item é uma cópia com a chave extra 'distancia_metros' (arredondada)."""
    enriquecidas = []
    for c in caixas:
        item = dict(c)
        item["distancia_metros"] = round(haversine(lat, lon, c["lat"], c["lon"]), 1)
        enriquecidas.append(item)
    enriquecidas.sort(key=lambda x: x["distancia_metros"])
    return enriquecidas[:n]
