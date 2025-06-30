import pulp
import json
from collections import defaultdict
import multiprocessing

def solve_work_assignment(data_file, verbose=True, time_limit=300):
    """
    Resuelve el problema de asignación de puestos de trabajo para estrategia híbrida
    usando el modelo planteado en las imágenes.

    Args:
        data_file: Archivo JSON con los datos o diccionario con los datos
        verbose: Si mostrar información durante la resolución
        time_limit: Límite de tiempo en segundos
    """
    
    # Cargar datos
    if isinstance(data_file, str):
        with open(data_file, 'r') as f:
            data = json.load(f)
    else:
        data = data_file
    
    # Conjuntos
    E = data['Employees']  # Empleados
    D = data['Desks']      # Escritorios
    T = data['Days']       # Días (L, Ma, Mi, J, V)
    G = data['Groups']     # Grupos
    Z = data['Zones']      # Zonas
    
    # Indexados
    D_z = data['Desks_Z']        # Escritorios por zona
    D_e = data['Desks_E']        # Escritorios aptos para empleado
    E_g = data['Employees_G']    # Empleados por grupo
    T_e = data['Days_E']         # Días preferidos por empleado
    
    if verbose:
        print(f"Instancia: {len(E)} empleados, {len(D)} escritorios, {len(G)} grupos")
        print(f"Promedio escritorios por empleado: {sum(len(desks) for desks in D_e.values()) / len(E):.1f}")
        print(f"Promedio días disponibles por empleado: {sum(len(days) for days in T_e.values()) / len(E):.1f}")
    
    # Crear modelo
    model = pulp.LpProblem("Work_Assignment", pulp.LpMaximize)
    
    # Variables de decisión
    # X_ij = 1 si empleado i va en el día j
    X = {}
    for i in E:
        for j in T:
            X[i, j] = pulp.LpVariable(f"X_{i}_{j}", cat='Binary')
    
    # Y_ikj = 1 si empleado i está en escritorio k en el día j
    Y = {}
    for i in E:
        for k in D:
            for j in T:
                Y[i, k, j] = pulp.LpVariable(f"Y_{i}_{k}_{j}", cat='Binary')
    
    # Z_gj = 1 si todo el grupo g está en el día j
    Z_var = {}
    for g in G:
        for j in T:
            Z_var[g, j] = pulp.LpVariable(f"Z_{g}_{j}", cat='Binary')
    
    # Función objetivo: Maximizar satisfacción de empleados (días trabajados en días preferidos)
    model += pulp.lpSum(X[i, j] for i in E for j in T if j in T_e.get(i, T))
    
    # Restricciones

    # 1. Los equipos deben coincidir al menos un día a la semana
    # sum(Z_gj) >= 1 para todo g en G
    for g in G:
        model += pulp.lpSum(Z_var[g, j] for j in T) >= 1, f"Team_Meeting_{g}"

    # 2. Z_gj <= X_ij para todo i en E_g, todo j en T
    for g in G:
        for j in T:
            for i in E_g[g]:
                model += Z_var[g, j] <= X[i, j], f"Team_Consistency_{g}_{i}_{j}"

    # 3. Un empleado debe estar en un escritorio si va en un día
    # sum(Y_ikj) = X_ij para todo i en E, todo j en T
    for i in E:
        for j in T:
            model += pulp.lpSum(Y[i, k, j] for k in D_e[i]) == X[i, j], f"Desk_Assignment_{i}_{j}"

    # 4. Un escritorio no puede ser usado por más de un empleado en un día
    # sum(Y_ikj) <= 1 para todo k en D, todo j en T
    for k in D:
        for j in T:
            model += pulp.lpSum(Y[i, k, j] for i in E if k in D_e[i]) <= 1, f"Desk_Capacity_{k}_{j}"



    # 5. Restricción de días preferidos (relajada como incentivo)
    # Esta restricción se puede implementar como penalización en la función objetivo
    # o como restricción suave

    # Restricción de número mínimo/máximo de días por empleado
    # Basado en el análisis: la mayoría trabaja 2-3 días
    # for i in E:
    #     available_days = len(T_e.get(i, T))
    #     # Determinar días mínimos y máximos basado en disponibilidad
    #     if available_days == 1:
    #         min_days, max_days = 1, 1
    #     elif available_days == 2:
    #         min_days, max_days = 2, 2
    #     elif available_days >= 3:
    #         min_days, max_days = 2, min(3, available_days)
    #     else:
    #         min_days, max_days = 0, 0

    #     if max_days > 0:
    #         model += pulp.lpSum(X[i, j] for j in T) >= min_days, f"Min_Days_{i}"
    #         model += pulp.lpSum(X[i, j] for j in T) <= max_days, f"Max_Days_{i}"

    # # 7. Solo puede ir en días disponibles
    # for i in E:
    #     if i in T_e:
    #         for j in T:
    #             if j not in T_e[i]:
    #                 model += X[i, j] == 0, f"Available_Days_{i}_{j}"
    #     # Si no está en T_e, asumimos que puede ir cualquier día

    # 8. Solo puede usar escritorios compatibles
    for i in E:
        for k in D:
            if k not in D_e[i]:
                for j in T:
                    model += Y[i, k, j] == 0, f"Compatible_Desk_{i}_{k}_{j}"

    # 9. En el día que vaya todo un grupo, todos deben estar en la misma zona
    # Primero, para cada empleado y día, necesitamos saber en qué zona está
    W = {}  # Variable auxiliar para tracking de zona por empleado
    for i in E:
        for j in T:
            for z in Z:
                W[i, z, j] = pulp.LpVariable(f"W_{i}_{z}_{j}", cat='Binary')
                # W_izj = 1 si el empleado i está en la zona z el día j
                model += pulp.lpSum(Y[i, k, j] for k in D_z[z] if k in D_e[i]) == W[i, z, j], f"Zone_Track_{i}_{z}_{j}"

    # Cuando un grupo se reúne (Z_gj = 1), todos deben estar en la misma zona
    for g in G:
        for j in T:
            for z in Z:
                # Si el grupo g se reúne el día j, todos sus miembros deben estar en la misma zona
                for i in E_g[g]:
                    model += W[i, z, j] >= Z_var[g, j] - pulp.lpSum(W[i2, z2, j] for i2 in E_g[g] for z2 in Z if z2 != z), f"Same_Zone_{g}_{j}_{i}_{z}"

    # 10. No debe haber empleados solos del grupo que se reúne
    for g in G:
        for j in T:
            for z in Z:
                # Contar empleados del grupo g en zona z día j
                N_gzj = pulp.lpSum(W[i, z, j] for i in E_g[g])

                # Si el grupo se reúne, no puede haber exactamente 1 empleado del grupo en esta zona
                # Esto se logra con: si Z_var[g,j] = 1, entonces N_gzj != 1
                # Linealización: N_gzj >= 2 * S_gzj y N_gzj <= len(E_g[g]) * (1 - S_gzj) + S_gzj
                # donde S_gzj = 1 si hay al menos un empleado del grupo en la zona

                S_gzj = pulp.LpVariable(f"HasAny_{g}_{z}_{j}", cat='Binary')

                # S_gzj = 1 si N_gzj >= 1 (hay al menos un empleado del grupo)
                model += N_gzj <= len(E_g[g]) * S_gzj, f"HasAny_upper_{g}_{z}_{j}"
                model += N_gzj >= S_gzj, f"HasAny_lower_{g}_{z}_{j}"

                # Si el grupo se reúne Y hay empleados del grupo en la zona, debe haber al menos 2
                # Equivalente a: Z_var[g,j] = 1 AND S_gzj = 1 => N_gzj >= 2
                # Linealización: N_gzj >= 2 - 2*(1 - Z_var[g,j]) - 2*(1 - S_gzj)
                #               = N_gzj >= 2*Z_var[g,j] + 2*S_gzj - 2
                model += N_gzj >= 2 * (Z_var[g, j] + S_gzj - 1), f"AtLeastTwo_{g}_{z}_{j}"

    # Resolver el modelo
    if verbose:
        print("Resolviendo el modelo...")
    
    # Configurar solver con parámetros optimizados
    solver = pulp.GUROBI_CMD(
        msg=1 if verbose else 0,
        timeLimit=time_limit,
        gapRel=0.01,    # Gap de optimalidad del 1%
        threads=max(1, multiprocessing.cpu_count()),
    )
    
    model.solve(solver)

    # Verificar estado de la solución
    if verbose:
        print(f"Estado: {pulp.LpStatus[model.status]}")
        print(f"Valor objetivo: {pulp.value(model.objective)}")
        
        # Estadísticas adicionales
        total_possible = sum(len(T_e.get(i, T)) for i in E)
        assigned = pulp.value(model.objective) if model.status == 1 else 0
        print(f"Utilización: {assigned}/{total_possible} ({100*assigned/total_possible:.1f}%)")

    # Extraer solución
    solution = {
        'status': pulp.LpStatus[model.status],
        'objective_value': pulp.value(model.objective),
        'employee_schedule': {},
        'desk_assignments': {},
        'team_meetings': {}
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

def print_solution(solution):
    """Imprime la solución de manera legible"""
    print("\n" + "="*60)
    print("SOLUCIÓN DEL PROBLEMA DE ASIGNACIÓN")
    print("="*60)

    print(f"\nEstado: {solution['status']}")
    print(f"Empleados asignados (total días): {solution['objective_value']}")

    print("\n" + "-"*40)
    print("HORARIOS DE EMPLEADOS")
    print("-"*40)
    for emp, days in solution['employee_schedule'].items():
        if days:
            print(f"{emp}: {', '.join(days)}")

    print("\n" + "-"*40)
    print("ASIGNACIÓN DE ESCRITORIOS")
    print("-"*40)
    for emp, assignments in solution['desk_assignments'].items():
        if assignments:
            for day, desk in assignments.items():
                print(f"{emp} - {day}: {desk}")

    print("\n" + "-"*40)
    print("REUNIONES DE EQUIPO")
    print("-"*40)
    for group, days in solution['team_meetings'].items():
        if days:
            print(f"{group}: {', '.join(days)}")

# Ejemplo de uso
if __name__ == "__main__":
    # Resolver con la instancia proporcionada
    try:
        # Cargar datos
        with open('instance9.json', 'r') as f:
            data = json.load(f)

        solution = solve_work_assignment(data)
        print_solution(solution)

        # Guardar solución en archivo
        with open('solution_instance9.json', 'w') as f:
            json.dump(solution, f, indent=2)
        print(f"\nSolución guardada en 'solution_instance9.json'")

        # Análisis adicional de la solución
        analyze_solution(solution, data)

    except FileNotFoundError:
        print("Archivo 'instance9.json' no encontrado.")
    except Exception as e:
        print(f"Error al resolver: {e}")
        print("Asegúrate de tener Gurobi instalado y configurado correctamente")

def analyze_solution(solution, data):
    """Analiza la calidad de la solución obtenida"""
    print("\n" + "="*60)
    print("ANÁLISIS DE LA SOLUCIÓN")
    print("="*60)

    if solution['status'] != 'Optimal':
        print(f"⚠️ Solución no óptima: {solution['status']}")
        return

    # Contar empleados asignados
    assigned_employees = len([emp for emp, days in solution['employee_schedule'].items() if days])
    total_employees = len(solution['employee_schedule'])

    print(f"📊 Empleados asignados: {assigned_employees}/{total_employees} ({100*assigned_employees/total_employees:.1f}%)")

    # Distribución de días trabajados
    day_distribution = {}
    for emp, days in solution['employee_schedule'].items():
        num_days = len(days)
        day_distribution[num_days] = day_distribution.get(num_days, 0) + 1

    print(f"📅 Distribución de días trabajados:")
    for days in sorted(day_distribution.keys()):
        print(f"   {days} días: {day_distribution[days]} empleados")

    # Equipos con reuniones programadas
    teams_with_meetings = len([team for team, days in solution['team_meetings'].items() if days])
    total_teams = len(solution['team_meetings'])

    print(f"👥 Equipos con reuniones: {teams_with_meetings}/{total_teams} ({100*teams_with_meetings/total_teams:.1f}%)")

    # Análisis de satisfacción de empleados
    print(f"\n😊 Análisis de satisfacción de empleados:")
    total_days_worked = 0
    preferred_days_worked = 0
    
    for emp, days in solution['employee_schedule'].items():
        total_days_worked += len(days)
        preferred_days = data['Days_E'].get(emp, data['Days'])
        for day in days:
            if day in preferred_days:
                preferred_days_worked += 1
    
    satisfaction_rate = (preferred_days_worked / total_days_worked * 100) if total_days_worked > 0 else 0
    print(f"   Días trabajados en días preferidos: {preferred_days_worked}/{total_days_worked} ({satisfaction_rate:.1f}%)")
    
    # Análisis de zonas por equipo
    print("\n📍 Análisis de zonas por equipo en días de reunión:")

    # Crear un mapeo de escritorio a zona usando los datos originales
    desk_to_zone = {}
    for zone, desks in data['Desks_Z'].items():
        for desk in desks:
            desk_to_zone[desk] = zone

    for team, meeting_days in solution['team_meetings'].items():
        if meeting_days:  # Si el equipo tiene días de reunión
            print(f"\nEquipo {team}:")
            for day in meeting_days:
                print(f"  Día {day}:")
                # Recolectar las zonas de todos los miembros del equipo
                team_zones = {}
                for emp in data['Employees_G'][team]:
                    if day in solution['desk_assignments'].get(emp, {}):
                        desk = solution['desk_assignments'][emp][day]
                        zone = desk_to_zone[desk]
                        team_zones[zone] = team_zones.get(zone, []) + [emp]

                # Mostrar distribución por zonas
                for zone, employees in team_zones.items():
                    print(f"    Zona {zone}: {len(employees)} empleados ({', '.join(employees)})")

                # Verificar si todos están en la misma zona
                if len(team_zones) == 1:
                    print(f"    ✅ Todo el equipo está en la misma zona")
                else:
                    print(f"    ⚠️ El equipo está disperso en {len(team_zones)} zonas diferentes")