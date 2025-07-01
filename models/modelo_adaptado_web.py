#!/usr/bin/env python3
"""
Adaptador para integrar el modelo de optimización existente con la aplicación web
Convierte el formato de datos y resultados para compatibilidad
"""

import json
import time
import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Optional

# Importar el modelo existente
try:
    from .work_assignment_model_past import solve_work_assignment, analyze_solution
except ImportError as e:
    print(f"Error importando modelo: {e}")
    sys.exit(1)

# Importar el modelo lexicográfico
try:
    from .lexicographicv1 import solve_work_assignment_lexicographic
except ImportError as e:
    print(f"Error importando modelo lexicográfico: {e}")
    print("El modelo lexicográfico no estará disponible")
    solve_work_assignment_lexicographic = None

def convertir_instancia_web_a_modelo(instancia_web: Dict) -> Dict:
    """
    Convierte el formato de instancia de la web al formato que espera el modelo
    """
    # Extraer datos básicos
    empleados = instancia_web['empleados']
    escritorios = instancia_web['escritorios']
    grupos = instancia_web['grupos']
    dias = instancia_web['dias']
    zonas = instancia_web['zonas']

    # Convertir días a formato del modelo (L, Ma, Mi, J, V)
    dias_modelo = {1: 'L', 2: 'Ma', 3: 'Mi', 4: 'J', 5: 'V'}

    # Crear estructura para el modelo
    instancia_modelo = {
        'Employees': [f"E{i}" for i in range(0, empleados)],
        'Days': [dias_modelo[i] for i in range(1, dias + 1)],
        'Groups': [f"G{i}" for i in range(0, grupos)],
        'Zones': zonas,

        # Escritorios por zona
        'Desks_Z': {},
        # Escritorios aptos para empleado (todos pueden usar todos)
        'Desks_E': {},
        # Empleados por grupo
        'Employees_G': {},
        # Días preferidos por empleado
        'Days_E': {}
    }

    print(f"    [DEBUG] Grupos creados: {instancia_modelo['Groups']}")
    print(f"    [DEBUG] Empleados creados: {len(instancia_modelo['Employees'])}")
    print(f"    [DEBUG] Días creados: {instancia_modelo['Days']}")

    # CORRECCIÓN: Usar los IDs de escritorios originales si están disponibles
    if 'escritorios_detalle' in instancia_web and instancia_web['escritorios_detalle']:
        # Si hay detalles de escritorios, usar los IDs originales
        instancia_modelo['Desks'] = [esc['id'] for esc in instancia_web['escritorios_detalle']]
    else:
        # Si no hay detalles, generar IDs simples (D0, D1, D2, ...) en lugar de D001, D002, ...
        instancia_modelo['Desks'] = [f"D{i}" for i in range(0, escritorios)]

    # Procesar escritorios por zona
    for escritorio in instancia_web.get('escritorios_detalle', []):
        zona = escritorio['zona']
        if zona not in instancia_modelo['Desks_Z']:
            instancia_modelo['Desks_Z'][zona] = []
        instancia_modelo['Desks_Z'][zona].append(escritorio['id'])

    # Si no hay escritorios_detalle, crear distribución automática usando IDs originales
    if not instancia_web.get('escritorios_detalle'):
        escritorios_por_zona = escritorios // len(zonas)
        resto = escritorios % len(zonas)

        contador = 0
        for i, zona in enumerate(zonas):
            escritorios_en_zona = escritorios_por_zona + (1 if i < resto else 0)
            # Usar IDs simples D0, D1, D2, ... en lugar de D001, D002, ...
            instancia_modelo['Desks_Z'][zona] = [f"D{j}" for j in range(contador, contador + escritorios_en_zona)]
            contador += escritorios_en_zona

    # Procesar empleados por grupo
    for empleado in instancia_web.get('empleados_detalle', []):
        emp_id = f"E{empleado['id']}"
        grupo_id = f"G{empleado['grupo']}"  # CORRECCIÓN: No restar 1

        if grupo_id not in instancia_modelo['Employees_G']:
            instancia_modelo['Employees_G'][grupo_id] = []
        instancia_modelo['Employees_G'][grupo_id].append(emp_id)

        # Días preferidos
        dias_preferidos = [dias_modelo[d] for d in empleado['dias_preferidos']]
        instancia_modelo['Days_E'][emp_id] = dias_preferidos

    # Si no hay empleados_detalle, crear distribución automática
    if not instancia_web.get('empleados_detalle'):
        empleados_por_grupo = empleados // grupos
        resto = empleados % grupos

        contador = 0
        for i in range(grupos):
            grupo_id = f"G{i}"
            empleados_en_grupo = empleados_por_grupo + (1 if i < resto else 0)
            instancia_modelo['Employees_G'][grupo_id] = [f"E{j}" for j in range(contador, contador + empleados_en_grupo)]
            contador += empleados_en_grupo

            # Asignar días preferidos aleatorios
            for emp_id in instancia_modelo['Employees_G'][grupo_id]:
                dias_disponibles = list(instancia_modelo['Days'])
                dias_preferidos = dias_disponibles[:2]  # 2 días preferidos por defecto
                instancia_modelo['Days_E'][emp_id] = dias_preferidos

    # Todos los empleados pueden usar todos los escritorios
    for emp_id in instancia_modelo['Employees']:
        instancia_modelo['Desks_E'][emp_id] = instancia_modelo['Desks']

    return instancia_modelo

def convertir_solucion_modelo_a_web(solucion_modelo: Dict, instancia_web: Dict, tiempo_resolucion: float) -> Dict:
    """
    Convierte la solución del modelo al formato requerido por la web
    """
    # Mapeo de días del modelo a números
    dias_mapping = {'L': 1, 'Ma': 2, 'Mi': 3, 'J': 4, 'V': 5}

    # Convertir instancia web a modelo para acceder a Desks_Z
    instancia_modelo = convertir_instancia_web_a_modelo(instancia_web)

    # Convertir horarios de empleados
    horarios_empleados = []
    for emp_id, dias in solucion_modelo['employee_schedule'].items():
        if dias:  # Solo incluir empleados con asignación
            dias_numericos = [dias_mapping[dia] for dia in dias]
            horarios_empleados.append({
                "empleado_id": int(emp_id.replace('E', '')),
                "dias_presenciales": sorted(dias_numericos)
            })

    # Convertir asignación de escritorios
    asignacion_escritorios = []
    for emp_id, asignaciones in solucion_modelo['desk_assignments'].items():
        for dia, escritorio in asignaciones.items():
            asignacion_escritorios.append({
                "empleado_id": int(emp_id.replace('E', '')),
                "dia": dias_mapping[dia],
                "escritorio_id": escritorio,
                "zona": determinar_zona_escritorio(escritorio, instancia_web, instancia_modelo)
            })

    # Convertir reuniones de equipo
    reuniones_equipo = []
    for grupo_id, dias in solucion_modelo['team_meetings'].items():
        if dias:  # Solo incluir grupos con reuniones
            # Validar que el grupo existe en Employees_G antes de procesarlo
            if grupo_id not in instancia_modelo['Employees_G']:
                print(f"    [WARN] Grupo {grupo_id} en team_meetings no existe en Employees_G")
                print(f"    [WARN] Grupos disponibles: {list(instancia_modelo['Employees_G'].keys())}")
                continue

            dias_numericos = [dias_mapping[dia] for dia in dias]
            reuniones_equipo.append({
                "grupo_id": int(grupo_id.replace('G', '')),  # Esto ya maneja G0, G1, G2, G3 correctamente
                "dias_reunion": sorted(dias_numericos)
            })

    # Generar análisis de proximidad
    analisis_proximidad = generar_analisis_proximidad(solucion_modelo, instancia_web, instancia_modelo)

    # Calcular métricas
    empleados_asignados = len([emp for emp, dias in solucion_modelo['employee_schedule'].items() if dias])
    total_empleados = len(solucion_modelo['employee_schedule'])
    tasa_satisfaccion = calcular_tasa_satisfaccion(solucion_modelo, instancia_web)

    # Calcular métrica de cohesión de equipos
    # Inspirado en el ejemplo proporcionado por el usuario
    total = 0
    cohesion = 0
    for grupo_id, dias_reunion in solucion_modelo['team_meetings'].items():
        if grupo_id not in instancia_modelo['Employees_G']:
            continue
        empleados_grupo = instancia_modelo['Employees_G'][grupo_id]
        for dia in dias_reunion:
            # dia es string tipo 'L', 'Ma', ... pero en la web lo convertimos a número
            if isinstance(dia, int):
                dia_str = dias_mapping.get(dia, str(dia))
            else:
                dia_str = dia
            zonas_count = {}
            members_present = []
            for emp_id in empleados_grupo:
                if emp_id in solucion_modelo['desk_assignments'] and dia_str in solucion_modelo['desk_assignments'][emp_id]:
                    escritorio = solucion_modelo['desk_assignments'][emp_id][dia_str]
                    zona = determinar_zona_escritorio(escritorio, instancia_web, instancia_modelo)
                    if zona not in zonas_count:
                        zonas_count[zona] = []
                    zonas_count[zona].append(emp_id)
                    members_present.append(emp_id)
            for zone, emps in zonas_count.items():
                total += 1
                if len(emps) >= 2:
                    cohesion += 1
    tasa_cohesion = (cohesion / total) if total > 0 else 0.0

    # Determinar estado
    estado = "Optimo" if solucion_modelo['status'] == 'Optimal' else "Factible"

    # Calcular valor objetivo real: suma de días preferidos asignados
    dias_preferidos_asignados = 0
    days_e = instancia_modelo.get('Days_E', {})
    for emp_id, dias in solucion_modelo['employee_schedule'].items():
        if dias:
            dias_pref = set(days_e.get(emp_id, []))
            for dia in dias:
                if dia in dias_pref:
                    dias_preferidos_asignados += 1

    # Generar colores por grupo
    colores_grupos = [
        "#1A237E",  # Azul oscuro - Grupo 0
        "#00B8F4",  # Azul claro - Grupo 1
        "#43A047",  # Verde - Grupo 2
        "#FBC02D",  # Amarillo - Grupo 3
        "#E53935",  # Rojo - Grupo 4
        "#8E24AA",  # Púrpura - Grupo 5
        "#3949AB",  # Índigo - Grupo 6
        "#00897B",  # Verde azulado - Grupo 7
        "#F4511E",  # Naranja - Grupo 8
        "#6D4C41",  # Marrón - Grupo 9
    ]

    # Crear mapeo de colores por grupo
    mapeo_colores_grupos = {}
    for grupo_id in instancia_modelo['Employees_G'].keys():
        grupo_num = int(grupo_id.replace('G', ''))
        mapeo_colores_grupos[grupo_num] = colores_grupos[grupo_num % len(colores_grupos)]

    return {
        "estado": estado,
        "tiempo_resolucion": round(tiempo_resolucion, 2),
        "valor_objetivo": dias_preferidos_asignados,
        "empleados_asignados": empleados_asignados,
        "total_empleados": total_empleados,
        "tasa_satisfaccion": round(tasa_satisfaccion, 3),
        "tasa_cohesion": round(tasa_cohesion, 3),
        "horarios_empleados": horarios_empleados,
        "asignacion_escritorios": asignacion_escritorios,
        "reuniones_equipo": reuniones_equipo,
        "analisis_proximidad": analisis_proximidad,
        "validacion": {
            "errores": 0,
            "advertencias": 0,
            "detalles": [
                "Solución generada por modelo de optimización",
                f"Estado del solver: {solucion_modelo['status']}",
                f"Empleados asignados: {empleados_asignados}/{total_empleados}"
            ]
        },
        "zonas": instancia_web.get("zonas") or instancia_web.get("Zones", []),
        "escritorios_detalle": instancia_web.get("escritorios_detalle", []),
        "empleados_detalle": instancia_web.get("empleados_detalle", []),  # AÑADIDO: Información de empleados y grupos
        "mapeo_colores_grupos": mapeo_colores_grupos,  # AÑADIDO: Colores por grupo
    }

def determinar_zona_escritorio(escritorio_id: str, instancia_web: Dict, instancia_modelo: Dict = None) -> str:
    """
    Determina la zona de un escritorio basado en su ID
    """
    print(f"    [DEBUG] Determinando zona para escritorio: {escritorio_id}")

    # 1. Buscar en escritorios_detalle (formato web)
    for escritorio in instancia_web.get('escritorios_detalle', []):
        if escritorio['id'] == escritorio_id:
            print(f"    [DEBUG] Encontrado en escritorios_detalle: {escritorio_id} -> {escritorio['zona']}")
            return escritorio['zona']

    # 2. Buscar en Desks_Z de la instancia del modelo
    if instancia_modelo and 'Desks_Z' in instancia_modelo:
        for zona, escritorios in instancia_modelo['Desks_Z'].items():
            if escritorio_id in escritorios:
                print(f"    [DEBUG] Encontrado en Desks_Z: {escritorio_id} -> {zona}")
                return zona

    # 3. Buscar en Desks_Z de la instancia web (si existe)
    if 'Desks_Z' in instancia_web:
        for zona, escritorios in instancia_web['Desks_Z'].items():
            if escritorio_id in escritorios:
                print(f"    [DEBUG] Encontrado en Desks_Z (web): {escritorio_id} -> {zona}")
                return zona

    # 4. Lógica por defecto: asignar a la primera zona disponible
    zonas = instancia_web.get('zonas') or instancia_web.get('Zones') or []
    if zonas:
        print(f"    [DEBUG] Zona asignada por defecto: {escritorio_id} -> {zonas[0]}")
        return zonas[0]
    print(f"    [WARN] No se pudo determinar la zona para {escritorio_id}, devolviendo 'Z0'")
    return 'Z0'

def generar_analisis_proximidad(solucion_modelo: Dict, instancia_web: Dict, instancia_modelo: Dict) -> List[Dict]:
    """
    Genera el análisis de proximidad por zonas (diferenciador clave)
    """
    analisis = []
    dias_mapping = {'L': 1, 'Ma': 2, 'Mi': 3, 'J': 4, 'V': 5}

    print("\n--- Análisis de Proximidad ---")
    print(f"Zonas disponibles: {instancia_web['zonas']}")
    print(f"Team meetings: {list(solucion_modelo['team_meetings'].keys())}")
    print(f"Employees_G disponibles: {list(instancia_modelo['Employees_G'].keys())}")

    # Para cada grupo y día de reunión
    for grupo_id, dias_reunion in solucion_modelo['team_meetings'].items():
        # Validar que el grupo existe en Employees_G
        if grupo_id not in instancia_modelo['Employees_G']:
            print(f"\n[WARN] Grupo {grupo_id} en team_meetings no existe en Employees_G, saltando...")
            continue

        print(f"\nGrupo {grupo_id}:")
        for dia in dias_reunion:
            dia_num = dias_mapping[dia]
            print(f"  Día {dia} ({dia_num}):")

            # Contar empleados del grupo por zona en ese día
            distribucion_zonas = {zona: 0 for zona in instancia_web['zonas']}

            # Obtener empleados del grupo
            empleados_grupo = instancia_modelo['Employees_G'][grupo_id]  # Ya validamos que existe arriba
            print(f"    Empleados del grupo {grupo_id}: {empleados_grupo}")

            # Contar por zona
            for emp_id in empleados_grupo:
                if emp_id in solucion_modelo['desk_assignments'] and dia in solucion_modelo['desk_assignments'][emp_id]:
                    escritorio = solucion_modelo['desk_assignments'][emp_id][dia]
                    zona = determinar_zona_escritorio(escritorio, instancia_web, instancia_modelo)
                    distribucion_zonas[zona] += 1
                    print(f"      {emp_id} -> {escritorio} -> {zona}")
                else:
                    print(f"      {emp_id} -> No asignado en día {dia}")

            print(f"    Distribución final: {distribucion_zonas}")

            analisis.append({
                "grupo_id": int(grupo_id.replace('G', '')),  # Esto ya maneja G0, G1, G2, G3 correctamente
                "dia": dia_num,
                "distribucion_zonas": distribucion_zonas
            })

    print(f"\nAnálisis generado: {len(analisis)} registros")
    return analisis

def calcular_tasa_satisfaccion(solucion_modelo: Dict, instancia_web: Dict) -> float:
    """
    Calcula la tasa de satisfacción basada en Days_E (días preferidos por empleado)
    Imprime en el log el cálculo para cada empleado.
    """
    total_dias_trabajados = 0
    dias_preferidos_trabajados = 0

    # Obtener Days_E de la instancia del modelo
    instancia_modelo = convertir_instancia_web_a_modelo(instancia_web)
    days_e = instancia_modelo.get('Days_E', {})
    dias_mapping = {'L': 1, 'Ma': 2, 'Mi': 3, 'J': 4, 'V': 5}

    print("\n--- Cálculo de tasa de satisfacción por empleado ---")
    print(f"Days_E disponible: {list(days_e.keys())}")

    for emp_id, dias in solucion_modelo['employee_schedule'].items():
        if dias:
            # Buscar días preferidos del empleado en Days_E
            dias_preferidos = []
            if emp_id in days_e:
                if all(isinstance(d, str) for d in days_e[emp_id]):
                    dias_preferidos = [dias_mapping[d] for d in days_e[emp_id] if d in dias_mapping]
                else:
                    dias_preferidos = days_e[emp_id]
            else:
                print(f"[WARN] No se encontraron días preferidos para {emp_id} en Days_E")

            dias_trabajados_numericos = [dias_mapping[dia] for dia in dias]
            total = len(dias_trabajados_numericos)
            preferidos = sum(1 for dia in dias_trabajados_numericos if dia in dias_preferidos)
            total_dias_trabajados += total
            dias_preferidos_trabajados += preferidos
            print(f"Empleado {emp_id}: asignados {dias_trabajados_numericos}, preferidos {dias_preferidos} -> {preferidos}/{total}")

    print(f"TOTAL: {dias_preferidos_trabajados}/{total_dias_trabajados} días preferidos sobre días asignados")

    if total_dias_trabajados == 0:
        return 0.0

    return dias_preferidos_trabajados / total_dias_trabajados

def resolver_instancia_web(instancia_web: Dict, tiempo_limite: int = 300, optimizacion_iterativa: bool = True) -> Dict:
    """
    Función principal que resuelve una instancia en formato web
    """
    print(f"🔄 Convirtiendo instancia web a formato del modelo...")

    # Convertir instancia
    instancia_modelo = convertir_instancia_web_a_modelo(instancia_web)

    # Validar consistencia de datos
    print(f"🔍 Validando consistencia de datos...")
    print(f"   Grupos definidos: {list(instancia_modelo['Employees_G'].keys())}")
    print(f"   Empleados totales: {len(instancia_modelo['Employees'])}")
    print(f"   Escritorios totales: {len(instancia_modelo['Desks'])}")

    # Verificar que todos los empleados están asignados a algún grupo
    empleados_asignados = set()
    for grupo_id, empleados in instancia_modelo['Employees_G'].items():
        empleados_asignados.update(empleados)

    empleados_sin_grupo = set(instancia_modelo['Employees']) - empleados_asignados
    if empleados_sin_grupo:
        print(f"   ⚠️ Empleados sin grupo asignado: {empleados_sin_grupo}")

    # Verificar que todos los escritorios están asignados a alguna zona
    escritorios_asignados = set()
    for zona, escritorios in instancia_modelo['Desks_Z'].items():
        escritorios_asignados.update(escritorios)

    escritorios_sin_zona = set(instancia_modelo['Desks']) - escritorios_asignados
    if escritorios_sin_zona:
        print(f"   ⚠️ Escritorios sin zona asignada: {escritorios_sin_zona}")

    print(f"🚀 Resolviendo con modelo de optimización...")
    print(f"   Empleados: {len(instancia_modelo['Employees'])}")
    print(f"   Escritorios: {len(instancia_modelo['Desks'])}")
    print(f"   Grupos: {len(instancia_modelo['Groups'])}")
    print(f"   Tiempo límite: {tiempo_limite}s")
    print(f"   Optimización iterativa: {optimizacion_iterativa}")

    # Ejecutar modelo
    tiempo_inicio = time.time()

    try:
        if optimizacion_iterativa and solve_work_assignment_lexicographic is not None:
            print(f"🎯 Usando modelo lexicográfico (optimización iterativa)")
            solucion_modelo = solve_work_assignment_lexicographic(
                instancia_modelo,
                verbose=True,
                time_limit=tiempo_limite,
                gap_tolerance=0.01
            )
        else:
            if optimizacion_iterativa:
                print(f"⚠️ Optimización iterativa solicitada pero modelo lexicográfico no disponible")
                print(f"   Usando modelo estándar en su lugar")
            else:
                print(f"🎯 Usando modelo estándar")

            solucion_modelo = solve_work_assignment(
                instancia_modelo,
                verbose=True,
                time_limit=tiempo_limite
            )

        tiempo_fin = time.time()
        tiempo_resolucion = tiempo_fin - tiempo_inicio

        # Validar que la solución es consistente
        if solucion_modelo and 'team_meetings' in solucion_modelo:
            print(f"🔍 Validando solución...")
            print(f"   Grupos en team_meetings: {list(solucion_modelo['team_meetings'].keys())}")
            print(f"   Grupos esperados: {list(instancia_modelo['Employees_G'].keys())}")

            # Verificar que todos los grupos en team_meetings existen en Employees_G
            grupos_invalidos = []
            for grupo_id in solucion_modelo['team_meetings'].keys():
                if grupo_id not in instancia_modelo['Employees_G']:
                    grupos_invalidos.append(grupo_id)

            if grupos_invalidos:
                print(f"   ⚠️ Grupos inválidos en solución: {grupos_invalidos}")
                # Filtrar grupos inválidos
                solucion_modelo['team_meetings'] = {
                    k: v for k, v in solucion_modelo['team_meetings'].items()
                    if k in instancia_modelo['Employees_G']
                }
                print(f"   ✅ Solución filtrada, grupos válidos: {list(solucion_modelo['team_meetings'].keys())}")

        if solucion_modelo is None:
            return {
                "estado": "NoEncontrado",
                "tiempo_resolucion": round(tiempo_resolucion, 2),
                "valor_objetivo": 0,
                "empleados_asignados": 0,
                "total_empleados": instancia_web['empleados'],
                "tasa_satisfaccion": 0.0,
                "horarios_empleados": [],
                "asignacion_escritorios": [],
                "reuniones_equipo": [],
                "analisis_proximidad": [],
                "validacion": {
                    "errores": 1,
                    "advertencias": 0,
                    "detalles": ["No se pudo encontrar solución"]
                }
            }

        # Convertir solución
        print(f"✅ Solución encontrada, convirtiendo a formato web...")
        solucion_web = convertir_solucion_modelo_a_web(solucion_modelo, instancia_web, tiempo_resolucion)

        return solucion_web

    except Exception as e:
        tiempo_fin = time.time()
        tiempo_resolucion = tiempo_fin - tiempo_inicio

        print(f"❌ Error en la resolución: {e}")

        return {
            "estado": "Error",
            "tiempo_resolucion": round(tiempo_resolucion, 2),
            "valor_objetivo": 0,
            "empleados_asignados": 0,
            "total_empleados": instancia_web['empleados'],
            "tasa_satisfaccion": 0.0,
            "horarios_empleados": [],
            "asignacion_escritorios": [],
            "reuniones_equipo": [],
            "analisis_proximidad": [],
            "validacion": {
                "errores": 1,
                "advertencias": 0,
                "detalles": [f"Error en resolución: {str(e)}"]
            }
        }

def main():
    """
    Función principal para testing
    """
    print("🧪 Testing del adaptador de modelo...")

    # Cargar instancia de ejemplo
    with open('ejemplo-instancia-pequena.json', 'r') as f:
        instancia_web = json.load(f)

    # Resolver
    solucion = resolver_instancia_web(instancia_web, tiempo_limite=60, optimizacion_iterativa=True)

    # Guardar resultado
    with open('solucion_adaptada.json', 'w') as f:
        json.dump(solucion, f, indent=2, ensure_ascii=False)

    print(f"✅ Solución guardada en 'solucion_adaptada.json'")
    print(f"📊 Estado: {solucion['estado']}")
    print(f"⏱️  Tiempo: {solucion['tiempo_resolucion']}s")
    print(f"🎯 Objetivo: {solucion['valor_objetivo']}")
    print(f"👥 Empleados: {solucion['empleados_asignados']}/{solucion['total_empleados']}")

if __name__ == "__main__":
    main()