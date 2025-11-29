import pandas as pd
import numpy as np
import os

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import confusion_matrix, classification_report

import matplotlib.pyplot as plt
import seaborn as sns

from keras.models import Sequential
from keras.layers import Dense, Dropout
from keras.optimizers import Adam
from keras.utils import to_categorical

# Global artifacts for reuse
_model = None
_scaler = None
_encoder = None
_training_columns = None # To store the exact column order and names after one-hot encoding

def train_model(file_path="Base de datos para el PP (actualizada).xlsx"):
    global _model, _scaler, _encoder, _training_columns
    
    if not os.path.exists(file_path):
        print(f"Advertencia: No se encontró el archivo {file_path}. El modelo no se entrenará.")
        return None

    print(f"Entrenando modelo con {file_path}...")
    df = pd.read_excel(file_path, header=1)

    # Limpiar los nombres de las columnas para que coincidan con las características esperadas
    df.columns = df.columns.str.replace(' ', '_').str.replace('(', '').str.replace(')', '')
    
    # Normalizar nombres de columna (quitar espacios y minúsculas para evitar errores)
    df.columns = df.columns.str.strip().str.replace(" ", "_").str.replace("á","a").str.replace("é","e").str.replace("í","i").str.replace("ó","o").str.replace("ú","u")

    # Nombres esperados (ajustados a la normalización anterior)
    expected_features = ["Experiencia_años", "Nivel_Educativo", "Campo_Estudio"]
    # Aplica la misma normalizacion a los nombres esperados para comparación robusta
    expected_features_norm = [c.strip().replace(" ", "_").replace("á","a").replace("é","e").replace("í","i").replace("ó","o").replace("ú","u") for c in expected_features]
    target_col = "Nivel"
    target_col_norm = target_col.strip().replace(" ", "_")

    # Verificar existencia de columnas
    missing = [c for c in expected_features_norm + [target_col_norm] if c not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas en el Excel: {missing}")

    # Usar columnas normalizadas
    features = expected_features_norm
    target = target_col_norm

    df = df[features + [target]].copy()

    df["Experiencia_años"] = pd.to_numeric(df["Experiencia_años"], errors='coerce')

    # Categorías a texto seguro
    df["Nivel_Educativo"] = df["Nivel_Educativo"].fillna("Desconocido").astype(str)
    df["Campo_Estudio"] = df["Campo_Estudio"].fillna("Desconocido").astype(str)

    df[target] = df[target].astype(str)

    # Eliminar filas con datos faltantes
    df = df.dropna(subset=["Experiencia_años", "Nivel_Educativo", "Campo_Estudio", target])

    df_cat = pd.get_dummies(
        df[["Nivel_Educativo", "Campo_Estudio"]],
        prefix=["NivelEd", "Campo"]
    )

    # Dataset final de entrada X
    X_df = pd.concat(
        [df[["Experiencia_años"]].reset_index(drop=True),
         df_cat.reset_index(drop=True)],
        axis=1
    )
    
    # Guardar las columnas de entrenamiento para alinear en predicción
    _training_columns = X_df.columns.tolist()

    X = X_df.values

    # Codificación del target
    encoder = LabelEncoder()
    y_encoded = encoder.fit_transform(df[target])
    y = to_categorical(y_encoded)
    
    _encoder = encoder # Store the encoder globally

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42
    )

    scaler = StandardScaler()
    scaler.fit(X_train)
    _scaler = scaler # Store the scaler globally

    X_train = scaler.transform(X_train)
    X_test = scaler.transform(X_test)

    model = Sequential()
    model.add(Dense(64, activation='relu', input_shape=(X_train.shape[1],)))
    model.add(Dropout(0.2))
    model.add(Dense(32, activation='relu'))
    model.add(Dense(16, activation='relu'))
    model.add(Dense(y.shape[1], activation='softmax'))

    model.compile(
        optimizer=Adam(learning_rate=0.001),
        loss='categorical_crossentropy',
        metrics=['accuracy']
    )

    history = model.fit(
        X_train, y_train,
        epochs=60,
        batch_size=16,
        validation_data=(X_test, y_test),
        verbose=0 # Silencioso
    )
    
    _model = model # Store the trained model globally
    
    print("Modelo entrenado exitosamente.")
    return model

def predict_candidate(candidate_data):
    """
    Realiza una predicción para un candidato dado.
    
    Args:
        candidate_data (dict): Un diccionario con los datos del candidato.
                               Ej: {"Experiencia (años)": 5, "Nivel Educativo": "Maestría", "Campo Estudio": "Ingeniería"}
    
    Returns:
        str: El nivel predicho para el candidato.
        str: "Modelo no cargado" si el modelo no ha sido entrenado.
    """
    global _model, _scaler, _encoder, _training_columns
    
    if _model is None or _scaler is None or _encoder is None or _training_columns is None:
        return "Modelo no cargado. Por favor, entrena el modelo primero."

    # Mapeo de claves del JSON a las esperadas por el modelo (normalizadas)
    # JSON: "Experiencia (años)", "Nivel Educativo", "Campo Estudio"
    # Modelo espera normalizado: "Experiencia_años", "Nivel_Educativo", "Campo_Estudio"
    
    # Crear un DF de una sola fila
    data = {
        "Experiencia_años": [float(candidate_data.get("Experiencia (años)", 0))],
        "Nivel_Educativo": [str(candidate_data.get("Nivel Educativo", "Desconocido"))],
        "Campo_Estudio": [str(candidate_data.get("Campo Estudio", "Desconocido"))]
    }
    
    df_input = pd.DataFrame(data)
    
    # One-Hot Encoding para categóricas
    df_cat = pd.get_dummies(
        df_input[["Nivel_Educativo", "Campo_Estudio"]],
        prefix=["NivelEd", "Campo"]
    )
    
    X_input_df = pd.concat(
        [df_input[["Experiencia_años"]].reset_index(drop=True),
         df_cat.reset_index(drop=True)],
        axis=1
    )
    
    # Alinear columnas con las del entrenamiento
    # Agregar columnas faltantes con 0
    for col in _training_columns:
        if col not in X_input_df.columns:
            X_input_df[col] = 0
            
    # Reordenar y seleccionar solo las columnas de entrenamiento
    X_input_df = X_input_df[_training_columns]
    
    X_input = X_input_df.values
    X_input = _scaler.transform(X_input)
    
    prediction = _model.predict(X_input, verbose=0)
    predicted_class_idx = np.argmax(prediction, axis=1)[0]
    predicted_label = _encoder.inverse_transform([predicted_class_idx])[0]
    
    return predicted_label

if __name__ == "__main__":
    # Test local
    trained_model = train_model()

    if trained_model:
        print("\nRealizando una predicción de prueba:")
        test_candidate = {
            "Experiencia (años)": 7,
            "Nivel Educativo": "Licenciatura",
            "Campo Estudio": "Informática"
        }
        predicted_level = predict_candidate(test_candidate)
        print(f"Para el candidato {test_candidate}, el nivel predicho es: {predicted_level}")

        test_candidate_2 = {
            "Experiencia (años)": 15,
            "Nivel Educativo": "Maestría",
            "Campo Estudio": "Administración"
        }
        predicted_level_2 = predict_candidate(test_candidate_2)
        print(f"Para el candidato {test_candidate_2}, el nivel predicho es: {predicted_level_2}")
    else:
        print("No se pudo entrenar el modelo, no se realizarán predicciones de prueba.")