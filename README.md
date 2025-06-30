# ASOCIOAPP - Sistema de Optimización de Asignación Híbrida

Una aplicación web completa desarrollada en Flask para resolver problemas de optimización de asignación de empleados a escritorios en un entorno híbrido.

## 🚀 Características

- **Optimización Híbrida**: Sistema que combina trabajo presencial y remoto
- **Asignación Inteligente**: Algoritmo de optimización para asignar empleados a escritorios
- **Gestión de Grupos**: Coordinación de reuniones de equipo
- **Análisis de Proximidad**: Distribución óptima por zonas
- **API REST**: Endpoints para integración con frontend
- **Interfaz Web**: Dashboard interactivo para visualizar resultados

## 📋 Requisitos

- Python 3.7+
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

### Ejemplo de uso de la API

```bash
curl -X POST http://localhost:5000/resolver-instancia \
  -H "Content-Type: application/json" \
  -d '{
    "instancia": {
      "empleados": 10,
      "escritorios": 8,
      "grupos": 3,
      "dias": 5,
      "zonas": ["Z1", "Z2", "Z3"],
      "empleados_detalle": [...],
      "escritorios_detalle": [...]
    },
    "tiempo_limite": 300,
    "optimizacion_iterativa": true
  }'
```

## 📁 Estructura del Proyecto

```
FlaskDeploy/
├── app.py                 # Aplicación principal Flask
├── requirements.txt       # Dependencias de Python
├── README.md             # Documentación
├── .gitignore           # Archivos a ignorar por Git
├── models/              # Modelos de optimización
│   ├── __init__.py
│   ├── lexicographic.py
│   ├── lexicographicv1.py
│   └── modelo_adaptado_web.py
├── templates/           # Plantillas HTML
│   └── index.html
└── venv/               # Entorno virtual (no incluido en Git)
```

## 🔧 Configuración

### Variables de entorno

- `PORT`: Puerto donde ejecutar la aplicación (default: 5000)
- `FLASK_ENV`: Entorno de Flask (development/production)

### Parámetros de optimización

- `tiempo_limite`: Tiempo máximo de resolución en segundos
- `optimizacion_iterativa`: Habilitar optimización iterativa

## 📊 Formato de Datos

### Instancia de entrada

```json
{
  "empleados": 10,
  "escritorios": 8,
  "grupos": 3,
  "dias": 5,
  "zonas": ["Z1", "Z2", "Z3"],
  "empleados_detalle": [
    {
      "id": 0,
      "grupo": 0,
      "dias_preferidos": [1, 3, 5]
    }
  ],
  "escritorios_detalle": [
    {
      "id": "E001",
      "zona": "Z1"
    }
  ]
}
```

### Respuesta de la API

```json
{
  "estado": "Optimo",
  "tiempo_resolucion": 2.5,
  "valor_objetivo": 25,
  "empleados_asignados": 8,
  "total_empleados": 10,
  "tasa_satisfaccion": 0.85,
  "horarios_empleados": [...],
  "asignacion_escritorios": [...],
  "reuniones_equipo": [...],
  "analisis_proximidad": [...],
  "validacion": {
    "errores": 0,
    "advertencias": 1,
    "detalles": [...]
  }
}
```

## 🤝 Contribuir

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📝 Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

## 👥 Autores

- **Santiago Rico** - *Desarrollo inicial* - [sricog](https://github.com/sricog)

## 🙏 Agradecimientos

- Equipo de optimización por el desarrollo del modelo matemático
- Comunidad Flask por el framework web
- PuLP por las herramientas de optimización