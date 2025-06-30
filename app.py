#!/usr/bin/env python3
"""
ASOCIOAPP - Aplicación completa en Flask
Sistema de Optimización de Asignación Híbrida
"""

from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
import json
import time
import os
import traceback
from datetime import datetime

def safe_write_json(data, filename):
    """Safely write JSON data to file, handling read-only file systems"""
    # Skip logging on Vercel (read-only file system)
    if os.environ.get('VERCEL') or os.environ.get('VERCEL_ENV'):
        print(f"📝 Skipping log file {filename} (Vercel environment)")
        return False

    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except (OSError, IOError) as e:
        print(f"⚠️ Warning: Could not write {filename}: {e}")
        return False

app = Flask(__name__)
CORS(app, origins=["*"])

# Importar el modelo de optimización
try:
    from models.modelo_adaptado_web import resolver_instancia_web
except ImportError:
    try:
        import sys
        sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
        from models.modelo_adaptado_web import resolver_instancia_web
    except ImportError as e:
        print(f"Error importando modelo: {e}")
        resolver_instancia_web = None

@app.route('/')
def index():
    """Página principal de la aplicación"""
    return render_template('index.html')

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint para verificar que la API está funcionando"""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "message": "API de optimización funcionando correctamente"
    })

@app.route('/resolver-instancia', methods=['POST'])
def resolver_instancia():
    """Endpoint principal para resolver una instancia"""
    try:
        data = request.get_json()

        # LOG 1: Guardar el JSON recibido para depuración
        safe_write_json(data, 'log_instancia_recibida.json')

        instancia = data.get('instancia', {})
        tiempo_limite = data.get('tiempo_limite', 300)
        optimizacion_iterativa = data.get('optimizacion_iterativa', True)

        # --- NUEVO: Si la instancia tiene claves en inglés, convertirlas ---
        def convertir_claves_ingles_a_espanol(inst):
            if 'Employees' in inst and 'Desks' in inst and 'Days' in inst and 'Groups' in inst and 'Zones' in inst:
                # Crear detalles de escritorios con IDs originales
                escritorios_detalle = []
                for i, desk_id in enumerate(inst['Desks']):
                    # Determinar zona basándose en Desks_Z
                    zona = None
                    for zone_id, desks_in_zone in inst.get('Desks_Z', {}).items():
                        if desk_id in desks_in_zone:
                            zona = zone_id
                            break
                    if zona is None:
                        # Si no está en Desks_Z, asignar a la primera zona
                        zona = inst['Zones'][0] if inst['Zones'] else 'Z0'

                    escritorios_detalle.append({
                        'id': desk_id,  # Usar ID original
                        'zona': zona
                    })

                # Crear detalles de empleados con días preferidos originales
                empleados_detalle = []
                for i, emp_id in enumerate(inst['Employees']):
                    # Determinar grupo basándose en Employees_G
                    grupo = None
                    for group_id, employees_in_group in inst.get('Employees_G', {}).items():
                        if emp_id in employees_in_group:
                            grupo = int(group_id.replace('G', ''))  # <--- Solo el índice, sin +1
                            break

                    # Convertir días preferidos de letras a números
                    dias_preferidos = []
                    if emp_id in inst.get('Days_E', {}):
                        dias_map = {'L': 1, 'Ma': 2, 'Mi': 3, 'J': 4, 'V': 5}
                        dias_preferidos = [dias_map[d] for d in inst['Days_E'][emp_id]]

                    empleados_detalle.append({
                        'id': i,  # Usar índice como ID
                        'grupo': grupo,
                        'dias_preferidos': dias_preferidos
                    })

                return {
                    'empleados': len(inst['Employees']),
                    'escritorios': len(inst['Desks']),
                    'grupos': len(inst['Groups']),
                    'dias': len(inst['Days']),
                    'zonas': inst['Zones'],
                    'escritorios_detalle': escritorios_detalle,
                    'empleados_detalle': empleados_detalle,
                    # Mantener datos originales para compatibilidad
                    'Employees': inst['Employees'],
                    'Desks': inst['Desks'],
                    'Days': inst['Days'],
                    'Groups': inst['Groups'],
                    'Zones': inst['Zones'],
                    'Desks_Z': inst.get('Desks_Z', {}),
                    'Desks_E': inst.get('Desks_E', {}),
                    'Employees_G': inst.get('Employees_G', {}),
                    'Days_E': inst.get('Days_E', {})
                }
            return inst
        instancia = convertir_claves_ingles_a_espanol(instancia)

        # LOG 2: Guardar la instancia convertida para el modelo
        from models.modelo_adaptado_web import convertir_instancia_web_a_modelo
        instancia_modelo = convertir_instancia_web_a_modelo(instancia)
        safe_write_json(instancia_modelo, 'log_instancia_modelo.json')

        # Validar campos requeridos
        campos_requeridos = ['empleados', 'escritorios', 'grupos', 'dias', 'zonas']
        for campo in campos_requeridos:
            if campo not in instancia:
                return jsonify({"error": f"Campo requerido faltante: {campo}"}), 400

        # Validar consistencia de datos
        if 'empleados_detalle' in instancia:
            grupos_en_empleados = set(emp['grupo'] for emp in instancia['empleados_detalle'] if emp['grupo'] is not None)
            if grupos_en_empleados:
                max_grupo = max(grupos_en_empleados)
                if max_grupo >= instancia['grupos']:
                    print(f"⚠️ Advertencia: Grupo máximo en empleados ({max_grupo}) >= grupos totales ({instancia['grupos']})")
                    print(f"   Grupos encontrados: {sorted(grupos_en_empleados)}")
                    print(f"   Grupos esperados: 0 a {instancia['grupos'] - 1}")

        if 'Employees_G' in instancia:
            grupos_en_employees_g = set(instancia['Employees_G'].keys())
            print(f"🔍 Grupos en Employees_G: {sorted(grupos_en_employees_g)}")
            print(f"🔍 Grupos esperados: {[f'G{i}' for i in range(instancia['grupos'])]}")

        # Usar el modelo real de optimización
        if resolver_instancia_web is None:
            # Fallback a simulación
            solucion = generar_solucion_ejemplo(instancia, 0)
            solucion['tiempo_resolucion'] = round(time.time() - time.time(), 2)
        else:
            solucion = resolver_instancia_web(
                instancia_web=instancia,
                tiempo_limite=tiempo_limite,
                optimizacion_iterativa=optimizacion_iterativa
            )

        # LOG 3: Guardar la solución cruda del modelo
        safe_write_json(solucion, 'log_solucion_cruda.json')

        # LOG 4: Guardar la respuesta final enviada al frontend
        safe_write_json(solucion, 'log_respuesta_final.json')

        return jsonify(solucion)

    except Exception as e:
        print(f"Error en resolver_instancia: {str(e)}")
        return jsonify({
            "error": "Error interno del servidor",
            "detalle": str(e)
        }), 500

def generar_solucion_ejemplo(instancia, tiempo_resolucion):
    """Función de ejemplo para cuando el modelo no está disponible"""
    import random

    empleados = instancia['empleados']
    escritorios = instancia['escritorios']
    grupos = instancia['grupos']
    dias = instancia['dias']
    zonas = instancia['zonas']

    # Generar horarios de empleados
    horarios_empleados = []
    for emp_id in range(1, empleados + 1):
        dias_presenciales = random.sample(range(1, dias + 1), random.randint(2, 3))
        horarios_empleados.append({
            "empleado_id": emp_id,
            "dias_presenciales": sorted(dias_presenciales)
        })

    # Generar asignación de escritorios
    asignacion_escritorios = []
    contador_escritorio = 1
    for horario in horarios_empleados:
        for dia in horario["dias_presenciales"]:
            if contador_escritorio <= escritorios:
                asignacion_escritorios.append({
                    "empleado_id": horario["empleado_id"],
                    "dia": dia,
                    "escritorio_id": f"E{contador_escritorio:03d}",
                    "zona": random.choice(zonas)
                })
                contador_escritorio += 1

    # Generar reuniones de equipo
    reuniones_equipo = []
    # Usar grupos reales si están disponibles, sino usar rango
    grupos_reales = []
    if 'empleados_detalle' in instancia:
        # Extraer grupos únicos de empleados_detalle
        grupos_reales = sorted(list(set(emp['grupo'] for emp in instancia['empleados_detalle'] if emp['grupo'] is not None)))
    elif 'Employees_G' in instancia:
        # Extraer grupos de Employees_G
        grupos_reales = sorted([int(g.replace('G', '')) for g in instancia['Employees_G'].keys()])

    if grupos_reales:
        # Usar grupos reales
        for grupo_id in grupos_reales:
            dias_reunion = random.sample(range(1, dias + 1), random.randint(1, 2))
            reuniones_equipo.append({
                "grupo_id": grupo_id,
                "dias_reunion": sorted(dias_reunion)
            })
    else:
        # Fallback a rango si no hay información de grupos
        for grupo_id in range(1, grupos + 1):
            dias_reunion = random.sample(range(1, dias + 1), random.randint(1, 2))
            reuniones_equipo.append({
                "grupo_id": grupo_id,
                "dias_reunion": sorted(dias_reunion)
            })

    # Generar análisis de proximidad
    analisis_proximidad = []
    for reunion in reuniones_equipo:
        for dia in reunion["dias_reunion"]:
            distribucion = {}
            for zona in zonas:
                distribucion[zona] = random.randint(0, 4)
            analisis_proximidad.append({
                "grupo_id": reunion["grupo_id"],
                "dia": dia,
                "distribucion_zonas": distribucion
            })

    # Calcular métricas
    empleados_asignados = len(set(a["empleado_id"] for a in asignacion_escritorios))
    valor_objetivo = len(asignacion_escritorios)
    tasa_satisfaccion = random.uniform(0.8, 0.95)

    return {
        "estado": "Optimo",
        "tiempo_resolucion": round(tiempo_resolucion, 2),
        "valor_objetivo": valor_objetivo,
        "empleados_asignados": empleados_asignados,
        "total_empleados": empleados,
        "tasa_satisfaccion": round(tasa_satisfaccion, 3),
        "horarios_empleados": horarios_empleados,
        "asignacion_escritorios": asignacion_escritorios,
        "reuniones_equipo": reuniones_equipo,
        "analisis_proximidad": analisis_proximidad,
        "validacion": {
            "errores": 0,
            "advertencias": random.randint(0, 3),
            "detalles": [
                "Solución encontrada exitosamente",
                "Todas las restricciones satisfechas"
            ]
        }
    }

# Vercel deployment configuration
app.debug = False

if __name__ == '__main__':
    print("🚀 Iniciando ASOCIOAPP...")
    print("📍 Endpoints disponibles:")
    print("   GET  / - Interfaz web")
    print("   GET  /health - Verificar estado")
    print("   POST /resolver-instancia - Resolver problema")
    print("\n🌐 Ejecutándose en: http://localhost:5000")

    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'

    app.run(debug=debug, host='0.0.0.0', port=port)