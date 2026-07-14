import json
import math
import os
import xml.etree.ElementTree as ET


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


def parse_kml(kml_path):
    """Extrai placemarks do KML: [{'nome','descricao','lat','lon'}]."""
    tree = ET.parse(kml_path)
    root = tree.getroot()
    ns = root.tag.split("}")[0] + "}" if root.tag.startswith("{") else ""

    caixas = []
    for pm in root.iter(f"{ns}Placemark"):
        name_el = pm.find(f"{ns}name")
        nome = name_el.text.strip() if name_el is not None and name_el.text else "Sem nome"

        desc_el = pm.find(f".//{ns}description")
        descricao = desc_el.text.strip() if desc_el is not None and desc_el.text else ""

        coord_el = pm.find(f".//{ns}coordinates")
        if coord_el is None or not coord_el.text:
            continue
        first = coord_el.text.strip().split()[0]
        parts = first.split(",")
        if len(parts) < 2:
            continue
        try:
            lon = float(parts[0])
            lat = float(parts[1])
        except ValueError:
            continue
        caixas.append({"nome": nome, "descricao": descricao, "lat": lat, "lon": lon})
    return caixas


def save_cache(cache_file, caixas):
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(caixas, f, ensure_ascii=False)


def load_caixas(cache_file, kml_file):
    if os.path.exists(cache_file):
        with open(cache_file, "r", encoding="utf-8") as f:
            return json.load(f)
    if os.path.exists(kml_file):
        caixas = parse_kml(kml_file)
        save_cache(cache_file, caixas)
        return caixas
    return []


def load_config(config_file, default_raio):
    if os.path.exists(config_file):
        with open(config_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {"raio_metros": float(data.get("raio_metros", default_raio))}
    return {"raio_metros": float(default_raio)}


def save_config(config_file, config):
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump({"raio_metros": float(config["raio_metros"])}, f)
