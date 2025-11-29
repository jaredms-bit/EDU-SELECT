import json

DB_FILE = 'base_del_proto.json'

def normalize_text(text):
    if isinstance(text, str):
        # Title Case and strip
        return text.strip().title()
    return text

def migrate():
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        updated_count = 0
        for record in data:
            # 1. Update Jornada
            jornada = record.get('Jornada')
            if jornada in ['Tiempo Completo', 'Medio Tiempo']:
                record['Jornada'] = 'Asignatura'
                updated_count += 1
            
            # 2. Normalize other fields
            for key, value in record.items():
                if key in ['Nombre', 'Apellidos', 'Procedencia', 'Entidad Federativa', 'Zona Geográfica', 'Nivel Educativo', 'Campo Estudio', 'Tipo Institución', 'Institución', 'Jornada', 'Nivel']:
                    record[key] = normalize_text(value)
            
            # Specific fix for "CDMX" if we want to standardize it to "Ciudad De México" or vice versa.
            # The user said "normalize", usually implies standard format.
            # Let's check what's common. "Ciudad De México" is Title Case of "Ciudad de México".
            # "Cdmx" would be Title Case of "CDMX".
            # Let's keep "CDMX" as "CDMX" if it exists, or map it?
            # The file has "CDMX" in "Entidad Federativa".
            # normalize_text("CDMX") -> "Cdmx". This might be undesirable.
            # Let's add an exception for CDMX.
            
            if record.get('Entidad Federativa') == 'Cdmx':
                 record['Entidad Federativa'] = 'CDMX'

        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
            
        print(f"Migration complete. Updated {updated_count} records to 'Asignatura'. Normalized text.")

    except Exception as e:
        print(f"Error during migration: {e}")

if __name__ == "__main__":
    migrate()
