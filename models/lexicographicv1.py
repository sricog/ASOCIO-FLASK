import pulp
import json
from collections import defaultdict
import multiprocessing

def solve_work_assignment_lexicographic(data_file, verbose=True, time_limit=300, gap_tolerance=0.01):
    """
    Resuelve el problema de asignación de puestos de trabajo usando método lexicográfico.
    
    Restricciones fuertes:
    1. Cada empleado debe tener el escritorio que necesite
    2. Cada equipo debe ir una vez a la semana
    3. Cada empleado debe ir al menos dos días a la semana
    
    Funciones objetivo (en orden lexicográfico):
    1. Maximizar preferencia de días de los empleados
    2. Maximizar cohesión de equipos en la misma zona
    
    Args:
        data_file: Archivo JSON con los datos o diccionario con los datos
        verbose: Si mostrar información durante la resolución
        time_limit: Límite de tiempo en segundos para cada etapa
        gap_tolerance: Tolerancia para considerar óptima una solución
    """
    
    # Cargar datos
    if isinstance(data_file, str):
        with open(data_file, 'r') as f:
            data = json.load(f)
    else:
        data = data_file
    
    # Conjuntos
    E = data['Employees']
    D = data['Desks']
    T = data['Days']
    G = data['Groups']
    Z = data['Zones']
    
    # Indexados
    D_z = data['Desks_Z']
    D_e = data['Desks_E']
    E_g = data['Employees_G']
    T_e = data['Days_E']
    
    if verbose:
        print(f"Instancia: {len(E)} empleados, {len(D)} escritorios, {len(G)} grupos")
        print(f"Promedio escritorios por empleado: {sum(len(desks) for desks in D_e.values()) / len(E):.1f}")
        print(f"Promedio días disponibles por empleado: {sum(len(days) for days in T_e.values()) / len(E):.1f}")
    
    # =====================================================
    # ETAPA 1: Maximizar preferencia de días
    # =====================================================
    if verbose:
        print("\n" + "="*60)
        print("ETAPA 1: Maximizar preferencia de días de empleados")
        print("="*60)
    
    # Crear modelo para etapa 1
    model1 = pulp.LpProblem("Work_Assignment_Stage1", pulp.LpMaximize)
    
    # Variables de decisión (estas se reutilizarán)
    X = {}
    for i in E:
        for j in T:
            X[i, j] = pulp.LpVariable(f"X_{i}_{j}", cat='Binary')
    
    Y = {}
    for i in E:
        for k in D:
            for j in T:
                Y[i, k, j] = pulp.LpVariable(f"Y_{i}_{k}_{j}", cat='Binary')
    
    Z_var = {}
    for g in G:
        for j in T:
            Z_var[g, j] = pulp.LpVariable(f"Z_{g}_{j}", cat='Binary')
    
    # Función objetivo 1: Maximizar días trabajados en días preferidos
    model1 += pulp.lpSum(X[i, j] for i in E for j in T if j in T_e.get(i, T))
    
    # RESTRICCIONES FUERTES
    # RF1: Cada empleado debe tener el escritorio que necesite
    # Un empleado debe estar en un escritorio si va en un día
    for i in E:
        for j in T:
            model1 += pulp.lpSum(Y[i, k, j] for k in D_e[i]) == X[i, j], f"Desk_Assignment_{i}_{j}"
    
    # Un escritorio no puede ser usado por más de un empleado en un día
    for k in D:
        for j in T:
            model1 += pulp.lpSum(Y[i, k, j] for i in E if k in D_e[i]) <= 1, f"Desk_Capacity_{k}_{j}"
    
    # Solo puede usar escritorios compatibles
    for i in E:
        for k in D:
            if k not in D_e[i]:
                for j in T:
                    model1 += Y[i, k, j] == 0, f"Compatible_Desk_{i}_{k}_{j}"
    
    # RF2: Cada equipo debe ir una vez a la semana
    for g in G:
        model1 += pulp.lpSum(Z_var[g, j] for j in T) >= 1, f"Team_Meeting_{g}"
    
    # Z_gj <= X_ij para todo i en E_g, todo j en T
    for g in G:
        for j in T:
            for i in E_g[g]:
                model1 += Z_var[g, j] <= X[i, j], f"Team_Consistency_{g}_{i}_{j}"
    
    # RF3: Cada empleado debe ir al menos dos días a la semana
    for i in E:
        model1 += pulp.lpSum(X[i, j] for j in T) >= 2, f"Min_Days_{i}"
    
    # Resolver etapa 1
    solver = pulp.GUROBI_CMD(
        msg=1 if verbose else 0,
        timeLimit=time_limit,
        gapRel=gap_tolerance,
        threads=max(1, multiprocessing.cpu_count()),
    )
    
    model1.solve(solver)
    
    if model1.status != 1:
        print(f"Error: La etapa 1 no pudo encontrar solución factible. Estado: {pulp.LpStatus[model1.status]}")
        return None
    
    optimal_preference = pulp.value(model1.objective)
    
    if verbose:
        print(f"Valor óptimo etapa 1 (preferencia de días): {optimal_preference}")
    
    # =====================================================
    # ETAPA 2: Maximizar cohesión de equipos
    # =====================================================
    if verbose:
        print("\n" + "="*60)
        print("ETAPA 2: Maximizar cohesión de equipos en la misma zona")
        print("="*60)
    
    # Crear modelo para etapa 2
    model2 = pulp.LpProblem("Work_Assignment_Stage2", pulp.LpMaximize)
    
    # Variable de decisión adicional para tracking de zonas
    W = {}
    for i in E:
        for j in T:
            for z in Z:
                W[i, z, j] = pulp.LpVariable(f"W_{i}_{z}_{j}", cat='Binary')

    # FUNCIÓN OBJETIVO: Combinación ponderada de objetivos blandos
    
    # Maximizar el número de empleados que están con su equipo en la misma zona
    cohesion_vars = {}
    for g in G:
        for j in T:
            for z in Z:
                for i in E_g[g]:
                    # Variable que indica si el empleado i está con su equipo en zona z día j
                    cohesion_vars[g, j, z, i] = pulp.LpVariable(f"Cohesion_{g}_{j}_{z}_{i}", cat='Binary')
                    
                    # El empleado está cohesionado si está en la zona y su equipo se reúne y hay al menos otro del equipo
                    # Simplificación: está cohesionado si está en una zona donde hay al menos 2 del equipo
                    team_in_zone = pulp.lpSum(W[i2, z, j] for i2 in E_g[g])
                    
                    # Si hay al menos 2 del equipo en la zona y este empleado está ahí, cuenta como cohesión
                    model1 += cohesion_vars[g, j, z, i] <= W[i, z, j], f"Cohesion_1_{g}_{j}_{z}_{i}"
                    model1 += cohesion_vars[g, j, z, i] <= (team_in_zone - 1) / len(E_g[g]), f"Cohesion_2_{g}_{j}_{z}_{i}"

    # Tracking de zonas
    for i in E:
        for j in T:
            for z in Z:
                model1 += pulp.lpSum(Y[i, k, j] for k in D_z[z] if k in D_e[i]) == W[i, z, j], f"Zone_Track2_{i}_{z}_{j}"
    
    cohesion_score = pulp.lpSum(cohesion_vars.values())
    model1 += cohesion_score
    
    # Restricción de optimalidad de etapa 1
    model1 += pulp.lpSum(X[i, j] for i in E for j in T if j in T_e.get(i, T)) >= optimal_preference - 0.5, "Maintain_Stage1_Optimality"
    
    # Resolver etapa 2
    model1.solve(solver)
    
    if verbose:
        print(f"Estado etapa 2: {pulp.LpStatus[model1.status]}")
        print(f"Valor objetivo etapa 2 (grupos cohesionados): {pulp.value(model1.objective)}")
    
    # Extraer solución final
    solution = {
        'status': pulp.LpStatus[model1.status],
        'stage1_value': optimal_preference,
        'stage2_value': pulp.value(model1.objective),
        'objective_value': optimal_preference,  # Para compatibilidad con main_solver
        'employee_schedule': {},
        'desk_assignments': {},
        'team_meetings': {},
        'team_zones': {},
        'data': data  # Incluir datos para la función de impresión
    }
    
    # Horario de empleados
    for i in E:
        solution['employee_schedule'][i] = []
        for j in T:
            if pulp.value(X[i, j]) == 1:
                solution['employee_schedule'][i].append(j)
    
    # Asignación de escritorios
    for i in E:
        solution['desk_assignments'][i] = {}
        for j in T:
            for k in D:
                if k in D_e[i] and pulp.value(Y[i, k, j]) == 1:
                    solution['desk_assignments'][i][j] = k
    
    # Reuniones de equipo
    for g in G:
        solution['team_meetings'][g] = []
        for j in T:
            if pulp.value(Z_var[g, j]) == 1:
                solution['team_meetings'][g].append(j)
    
    return solution


def print_lexicographic_solution(solution):
    """Imprime la solución del método lexicográfico"""
    # Extraer datos de la solución
    data = solution.get('data', {})
    
    print("\n" + "="*60)
    print("SOLUCIÓN LEXICOGRÁFICA DEL PROBLEMA DE ASIGNACIÓN")
    print("="*60)
    
    print(f"\nEstado: {solution['status']}")
    print(f"Valor Etapa 1 (días preferidos): {solution['stage1_value']}")
    print(f"Valor Etapa 2 (equipos cohesionados): {solution['stage2_value']}")
    
    print("\n" + "-"*40)
    print("HORARIOS DE EMPLEADOS")
    print("-"*40)
    for emp, days in solution['employee_schedule'].items():
        if days:
            preferred = data.get('Days_E', {}).get(emp, data.get('Days', []))
            days_str = []
            for d in days:
                if d in preferred:
                    days_str.append(f"{d}✓")
                else:
                    days_str.append(d)
            print(f"{emp}: {', '.join(days_str)} (✓ = día preferido)")
    
    print("\n" + "-"*40)
    print("ASIGNACIÓN DE ESCRITORIOS")
    print("-"*40)
    
    # Crear mapeo de escritorio a zona
    desk_to_zone = {}
    for zone, desks in data.get('Desks_Z', {}).items():
        for desk in desks:
            desk_to_zone[desk] = zone
    
    for emp, assignments in solution['desk_assignments'].items():
        if assignments:
            for day, desk in assignments.items():
                zone = desk_to_zone.get(desk, "?")
                print(f"{emp} - {day}: {desk} (Zona {zone})")
    
    print("\n" + "-"*40)
    print("REUNIONES DE EQUIPO Y COHESIÓN")
    print("-"*40)
    
    for group, days in solution['team_meetings'].items():
        if days:
            print(f"\nEquipo {group}:")
            print(f"  Días de reunión: {', '.join(days)}")
            
            # Analizar cohesión por día
            for day in days:
                zones_count = defaultdict(int)
                members_present = []
                
                for emp in data.get('Employees_G', {}).get(group, []):
                    if day in solution['desk_assignments'].get(emp, {}):
                        desk = solution['desk_assignments'][emp][day]
                        zone = desk_to_zone[desk]
                        zones_count[zone] += 1
                        members_present.append(emp)
                
                total_members = len(data.get('Employees_G', {}).get(group, []))
                print(f"  {day}: {len(members_present)}/{total_members} miembros presentes")
                for zone, count in zones_count.items():
                    print(f"    Zona {zone}: {count} empleados")
                
                if len(zones_count) == 1:
                    print(f"    ✅ Equipo cohesionado en zona {list(zones_count.keys())[0]}")
                else:
                    print(f"    ⚠️ Equipo disperso en {len(zones_count)} zonas")
    
    # Resumen de métricas
    print("\n" + "="*60)
    print("RESUMEN DE MÉTRICAS")
    print("="*60)
    
    # Satisfacción de empleados
    total_days = 0
    preferred_days = 0
    for emp, days in solution['employee_schedule'].items():
        total_days += len(days)
        pref = data.get('Days_E', {}).get(emp, data.get('Days', []))
        for d in days:
            if d in pref:
                preferred_days += 1
    
    if total_days > 0:
        print(f"📊 Satisfacción de días: {preferred_days}/{total_days} ({100*preferred_days/total_days:.1f}%)")
    
    # Equipos cohesionados
    cohesioned_teams = len([g for g, zones in solution['team_zones'].items() if zones])
    total_teams = len(data.get('Groups', []))
    if total_teams > 0:
        print(f"👥 Equipos con cohesión total: {cohesioned_teams}/{total_teams} ({100*cohesioned_teams/total_teams:.1f}%)")
    
    # Cumplimiento de restricciones fuertes
    total_employees = len(data.get('Employees', []))
    if total_employees > 0:
        min_2_days = sum(1 for emp, days in solution['employee_schedule'].items() if len(days) >= 2)
        print(f"📅 Empleados con ≥2 días: {min_2_days}/{total_employees} ({100*min_2_days/total_employees:.1f}%)")
    
    teams_meeting = sum(1 for g, days in solution['team_meetings'].items() if len(days) >= 1)
    if total_teams > 0:
        print(f"🤝 Equipos con reunión semanal: {teams_meeting}/{total_teams} ({100*teams_meeting/total_teams:.1f}%)")


# Ejemplo de uso
if __name__ == "__main__":
    # Crear una instancia de prueba pequeña
    test_data = {
        "Employees": ["E1", "E2", "E3", "E4", "E5", "E6"],
        "Desks": ["D1", "D2", "D3", "D4", "D5", "D6"],
        "Days": ["L", "Ma", "Mi", "J", "V"],
        "Groups": ["G1", "G2"],
        "Zones": ["Z1", "Z2"],
        "Desks_Z": {
            "Z1": ["D1", "D2", "D3"],
            "Z2": ["D4", "D5", "D6"]
        },
        "Desks_E": {
            "E1": ["D1", "D2"],
            "E2": ["D2", "D3"],
            "E3": ["D1", "D3"],
            "E4": ["D4", "D5"],
            "E5": ["D5", "D6"],
            "E6": ["D4", "D6"]
        },
        "Employees_G": {
            "G1": ["E1", "E2", "E3"],
            "G2": ["E4", "E5", "E6"]
        },
        "Days_E": {
            "E1": ["L", "Mi", "V"],
            "E2": ["Ma", "J"],
            "E3": ["L", "Ma", "Mi"],
            "E4": ["Mi", "J", "V"],
            "E5": ["L", "J"],
            "E6": ["Ma", "V"]
        }
    }
    
    # Resolver con método lexicográfico
    solution = solve_work_assignment_lexicographic(test_data, verbose=True)
    
    if solution:
        print_lexicographic_solution(solution, test_data)
        
        # Guardar solución
        with open('lexicographic_solution.json', 'w') as f:
            json.dump(solution, f, indent=2)
        print("\nSolución guardada en 'lexicographic_solution.json'")