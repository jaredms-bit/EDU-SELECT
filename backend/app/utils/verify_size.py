import json

data = {
    "Nombre": "Miguel",
    "Apellidos": "Lopez",
    "Edad": 27,
    "Procedencia": "Nuevo León",
    "Entidad Federativa": "CDMX",
    "Zona Geográfica": "Norte",
    "Nivel Educativo": "Licenciatura",
    "Campo Estudio": "Tecnologías de la Información",
    "Tipo Institución": "Pública",
    "Institución": "Universidad Nacional Autonoma de Mexico",
    "Rango Ingreso": 32903,
    "Experiencia (años)": 6,
    "Jornada": "Tiempo Completo",
    "Nivel": "A"
}

json_str = json.dumps(data)
print(f"JSON string: {json_str}")
print(f"Length: {len(json_str.encode('utf-8'))} bytes")
print(f"Max RSA 2048 PKCS1v1.5 size: {256 - 11} bytes")
