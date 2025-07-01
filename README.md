# ASOCIOAPP - Sistema de Optimización de Asignación Híbrida

Una aplicación web completa desarrollada en Flask para resolver problemas de optimización de asignación de empleados a escritorios en un entorno híbrido.

## 🚀 Características

- **Optimización Híbrida**: Sistema que combina trabajo presencial y remoto, utilizando un modelo lexicográfico.
- **Asignación Inteligente**: Algoritmo de optimización para asignar empleados a escritorios
- **Gestión de Grupos**: Coordinación de reuniones de equipo
- **Análisis de Proximidad**: Distribución óptima por zonas
- **API REST**: Endpoints para integración con frontend
- **Interfaz Web**: Dashboard interactivo para visualizar resultados

## 📋 Requisitos

- Flask
- PuLP (para optimización)
- Flask-CORS

## 🛠️ Instalación

1. **Clonar el repositorio**
   ```bash
   git clone https://github.com/sricog/ASOCIO-FLASK.git
   cd ASOCIO-FLASK
   ```

2. **Crear entorno virtual**
   ```bash
   python -m venv venv
   ```

3. **Activar entorno virtual**
   - Windows:
     ```bash
     venv\Scripts\activate
     ```
   - Linux/Mac:
     ```bash
     source venv/bin/activate
     ```

4. **Instalar dependencias**
   ```bash
   pip install -r requirements.txt
   ```

## 🚀 Uso

### Ejecutar la aplicación

```bash
python app.py
```

La aplicación estará disponible en: `http://localhost:5000`

### Endpoints disponibles

- `GET /` - Interfaz web principal
- `GET /health` - Verificar estado de la API
- `POST /resolver-instancia` - Resolver problema de optimización


## 📁 Estructura del Proyecto

```
FlaskDeploy/
├── app.py                 # Aplicación principal Flask
├── requirements.txt       # Dependencias de Python
├── README.md              # Documentación
├── .gitignore             # Archivos a ignorar por Git
├── models/                # Modelos de optimización
│   ├── __init__.py
│   ├── modelo_adaptado_web.py
│   ├── lexicographicv1.py
│   └── work_assignment_model_past.py
├── templates/             # Plantillas HTML
│   └── index.html
└── __init__.py
```
