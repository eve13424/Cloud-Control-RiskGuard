# БЛОК ИМПОРТА БИБЛИОТЕК
import copy  # copy используется для создания независимой копии состояния системы перед изменением.
import csv  # csv используется для сохранения журнала и истории в файлы.
import json  # json используется для сохранения журнала в формате JSONL.
from pathlib import Path  # Path используется для работы с файловыми путями.
from datetime import datetime  # datetime используется для фиксации времени обработки запроса.

import pandas as pd  # pandas используется для табличного представления журнала и истории.
import matplotlib  # matplotlib используется для построения графиков.
matplotlib.use("Agg")  # Agg позволяет сохранять графики без открытия графического окна.
import matplotlib.pyplot as plt  # pyplot используется для построения и сохранения графиков.


# БЛОК ИСХОДНОГО СОСТОЯНИЯ СИСТЕМЫ
INITIAL_STATE = {
    "service_running": True,  # Признак работы защищаемого сервиса.
    "routing_ok": True,  # Признак корректности маршрутизации.
    "cpu_limit": 6,  # Текущий лимит CPU.
    "memory_limit": 12,  # Текущий лимит оперативной памяти.
    "self_healing": True,  # Признак включенного самовосстановления.
    "critical_component_running": True,  # Признак работы критичного компонента.
}


# БЛОК РОЛЕВОЙ МОДЕЛИ ДОСТУПА
role_permissions = {
    "change_resources": ["admin_customer"],  # Изменять ресурсы может только администратор заказчика.
    "change_routing": ["admin_customer", "operator_provider"],  # Маршрутизацию может менять администратор или оператор.
    "disable_self_healing": ["admin_customer"],  # Отключение самовосстановления доступно только администратору.
    "restart_critical_component": ["admin_customer", "operator_provider"],  # Перезапуск доступен администратору и оператору.
    "read_audit": ["admin_customer", "auditor"],  # Читать журнал может администратор и аудитор.
}


# БЛОК ПОЛИТИКИ БЕЗОПАСНОСТИ КОНТЕЙНЕРА
DEFAULT_CRITICAL_ACTIONS = [
    "change_resources",
    "change_routing",
    "disable_self_healing",
    "restart_critical_component",
]

DEFAULT_ALLOWED_ROUTES = [
    "private-cloud-gw",
    "backup-gw",
]

critical_actions = copy.deepcopy(DEFAULT_CRITICAL_ACTIONS)  # Текущий перечень критичных действий.
allowed_routes = copy.deepcopy(DEFAULT_ALLOWED_ROUTES)  # Текущий перечень допустимых маршрутов.

SECURITY_POLICY = {
    "min_cpu_limit": 2,  # Минимально допустимый лимит CPU для сохранения доступности.
    "min_memory_limit": 4,  # Минимально допустимый лимит памяти для сохранения доступности.
}


# БЛОК ГЛОБАЛЬНОГО СОСТОЯНИЯ КОНТЕЙНЕРА
current_state = copy.deepcopy(INITIAL_STATE)  # Текущее состояние системы.
audit_log = []  # Журнал управленческих действий.
history = []  # История изменения состояния системы.


# БЛОК ПРОВЕРКИ ДОСТУПНОСТИ
def check_availability(state):
    """
    Проверяет доступность системы по ключевым параметрам.
    Минимальные значения CPU и RAM берутся из политики безопасности контейнера.
    """

    return (
        state["service_running"]
        and state["routing_ok"]
        and state["self_healing"]
        and state["critical_component_running"]
        and state["cpu_limit"] >= SECURITY_POLICY["min_cpu_limit"]
        and state["memory_limit"] >= SECURITY_POLICY["min_memory_limit"]
    )


# БЛОК ПОЛУЧЕНИЯ ТЕКУЩЕГО СТАТУСА
def get_status(state):
    """
    Формирует словарь текущего состояния системы для вывода в интерфейс.
    """

    return {
        "service_running": state["service_running"],
        "routing_ok": state["routing_ok"],
        "cpu_limit": state["cpu_limit"],
        "memory_limit": state["memory_limit"],
        "self_healing": state["self_healing"],
        "critical_component_running": state["critical_component_running"],
        "available": int(check_availability(state)),
    }


# БЛОК ПРОВЕРКИ РОЛИ
def role_allowed(action, role):
    """
    Проверяет, имеет ли указанная роль право выполнять выбранное действие.
    """

    return role in role_permissions.get(action, [])


# БЛОК ПРОВЕРКИ ПОЛИТИКИ БЕЗОПАСНОСТИ
def policy_check(state, request_data):
    """
    Проверяет управленческое действие на соответствие политике безопасности.
    Возвращает логическое решение и пояснение.
    """

    action = request_data["action"]

    if action == "change_resources":
        new_cpu = request_data["new_cpu"]
        new_memory = request_data["new_memory"]

        if (
            new_cpu < SECURITY_POLICY["min_cpu_limit"]
            or new_memory < SECURITY_POLICY["min_memory_limit"]
        ):
            return False, "Недопустимые лимиты ресурсов"

        return True, "Ресурсы соответствуют политике доступности"

    if action == "change_routing":
        new_route = request_data["new_route"]

        if new_route not in allowed_routes:
            return False, "Маршрут не входит в допустимый перечень"

        return True, "Маршрут допустим"

    if action == "disable_self_healing":
        return False, "Отключение самовосстановления запрещено политикой безопасности"

    if action == "restart_critical_component":
        return True, "Перезапуск критичного компонента разрешен при сохранении доступности"

    if action == "read_audit":
        return True, "Чтение журнала разрешено"

    return False, "Неизвестная операция"


# БЛОК ПРИМЕНЕНИЯ УПРАВЛЕНЧЕСКОГО ДЕЙСТВИЯ
def apply_action(state, request_data):
    """
    Применяет управленческое действие к копии состояния системы.
    Исходное состояние не изменяется до завершения проверки доступности.
    """

    new_state = copy.deepcopy(state)
    action = request_data["action"]

    if action == "change_resources":
        new_state["cpu_limit"] = request_data["new_cpu"]
        new_state["memory_limit"] = request_data["new_memory"]

    elif action == "change_routing":
        new_state["routing_ok"] = request_data["new_route"] in allowed_routes

    elif action == "disable_self_healing":
        new_state["self_healing"] = False

    elif action == "restart_critical_component":
        new_state["critical_component_running"] = False

        if request_data.get("simulate_failure", False):
            new_state["service_running"] = False
        else:
            new_state["critical_component_running"] = True

    elif action == "read_audit":
        pass

    return new_state


# БЛОК РАСЧЕТА УРОВНЯ РИСКА
def calculate_risk_level(request_data, decision):
    """
    Рассчитывает уровень риска управленческого действия.
    Показатель используется для аудита и продуктового dashboard.
    """

    score = 0

    if request_data["action"] in critical_actions:
        score += 2

    if not request_data.get("approved", False) and request_data["action"] in critical_actions:
        score += 1

    if decision == "deny":
        score += 1

    if decision == "rollback":
        score += 3

    if score >= 4:
        return "Высокий"

    if score >= 2:
        return "Средний"

    return "Низкий"


# БЛОК ОБРАБОТКИ УПРАВЛЕНЧЕСКОГО ЗАПРОСА
def process_request(state, request_data):
    """
    Последовательно обрабатывает управленческий запрос:
    проверяет роль, второе подтверждение, политику безопасности,
    применяет действие, проверяет доступность и формирует решение.
    """

    old_state = copy.deepcopy(state)
    before = get_status(state)

    decision = "deny"
    reason = ""
    recovery = "Не требуется"

    if not role_allowed(request_data["action"], request_data["role"]):
        reason = "Роль не имеет полномочий"

    elif request_data["action"] in critical_actions and not request_data.get("approved", False):
        reason = "Нет второго подтверждения"

    else:
        allowed, message = policy_check(state, request_data)

        if not allowed:
            reason = message
        else:
            changed_state = apply_action(state, request_data)

            if not check_availability(changed_state):
                decision = "rollback"
                reason = "После изменения нарушена доступность"
                recovery = "Выполнен откат к предыдущей конфигурации"
                state = old_state
            else:
                decision = "allow"
                reason = message
                state = changed_state

    after = get_status(state)
    risk_level = calculate_risk_level(request_data, decision)

    log_record = {
        "request_id": request_data["request_id"],
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "actor": request_data["actor"],
        "role": request_data["role"],
        "action": request_data["action"],
        "decision": decision,
        "risk_level": risk_level,
        "reason": reason,
        "approved": int(request_data.get("approved", False)),
        "availability_before": before["available"],
        "availability_after": after["available"],
        "cpu_before": before["cpu_limit"],
        "cpu_after": after["cpu_limit"],
        "memory_before": before["memory_limit"],
        "memory_after": after["memory_limit"],
        "recovery": recovery,
    }

    return state, log_record


# БЛОК ДОБАВЛЕНИЯ ЗАПРОСА В ЖУРНАЛ
def submit_request(request_data):
    """
    Обрабатывает запрос, обновляет текущее состояние,
    добавляет запись в журнал и обновляет историю.
    """

    global current_state, audit_log, history

    current_state, record = process_request(current_state, request_data)
    audit_log.append(record)

    status = get_status(current_state)

    history.append({
        "step": request_data["request_id"],
        "available": status["available"],
        "cpu_limit": status["cpu_limit"],
        "memory_limit": status["memory_limit"],
        "risk_level": record["risk_level"],
        "decision": record["decision"],
    })

    save_export_files()

    return record


# БЛОК ДЕМОНСТРАЦИОННЫХ ЗАПРОСОВ
demo_requests = [
    {
        "request_id": 1,
        "actor": "Иманбаева Э.Е.",
        "role": "admin_customer",
        "action": "change_resources",
        "new_cpu": 8,
        "new_memory": 16,
        "approved": True,
    },
    {
        "request_id": 2,
        "actor": "Оператор поставщика",
        "role": "operator_provider",
        "action": "change_routing",
        "new_route": "private-cloud-gw",
        "approved": True,
    },
    {
        "request_id": 3,
        "actor": "Оператор поставщика",
        "role": "operator_provider",
        "action": "disable_self_healing",
        "approved": False,
    },
    {
        "request_id": 4,
        "actor": "Иманбаева Э.Е.",
        "role": "admin_customer",
        "action": "restart_critical_component",
        "approved": False,
    },
    {
        "request_id": 5,
        "actor": "Иманбаева Э.Е.",
        "role": "admin_customer",
        "action": "restart_critical_component",
        "approved": True,
        "simulate_failure": True,
    },
    {
        "request_id": 6,
        "actor": "Аудитор",
        "role": "auditor",
        "action": "read_audit",
        "approved": False,
    },
]


# БЛОК ЗАПУСКА ДЕМО-СЦЕНАРИЯ
def run_demo_requests():
    """
    Выполняет демонстрационный сценарий, показывающий решения allow, deny и rollback.
    """

    if audit_log:
        return

    for request_item in demo_requests:
        submit_request(request_item)


# БЛОК СБРОСА ДАННЫХ
def reset_demo_data():
    """
    Возвращает состояние контейнера к исходным значениям.
    """

    global current_state, audit_log, history

    current_state = copy.deepcopy(INITIAL_STATE)
    audit_log = []
    history = []

    save_export_files()


# БЛОК ФОРМИРОВАНИЯ DATAFRAME
def build_dataframes():
    """
    Формирует таблицы журнала, истории, сводки решений и сводки рисков.
    """

    audit_df = pd.DataFrame(audit_log)
    history_df = pd.DataFrame(history)

    if audit_df.empty:
        summary_df = pd.DataFrame(columns=["decision", "count"])
        risk_df = pd.DataFrame(columns=["risk_level", "count"])
    else:
        summary_df = (
            audit_df.groupby("decision")
            .size()
            .to_frame("count")
            .reset_index()
            .sort_values(by="count", ascending=False)
        )

        risk_df = (
            audit_df.groupby("risk_level")
            .size()
            .to_frame("count")
            .reset_index()
            .sort_values(by="count", ascending=False)
        )

    return audit_df, history_df, summary_df, risk_df


# БЛОК СОХРАНЕНИЯ ЖУРНАЛА И ИСТОРИИ
def save_export_files():
    """
    Сохраняет журнал и историю в файлы CSV и JSONL.
    """

    export_dir = Path("exports")
    export_dir.mkdir(exist_ok=True)

    audit_path_csv = export_dir / "audit_log.csv"
    history_path_csv = export_dir / "history.csv"
    audit_path_jsonl = export_dir / "audit_log.jsonl"

    audit_df = pd.DataFrame(audit_log)
    history_df = pd.DataFrame(history)

    audit_df.to_csv(audit_path_csv, index=False, encoding="utf-8-sig")
    history_df.to_csv(history_path_csv, index=False, encoding="utf-8-sig")

    with open(audit_path_jsonl, "w", encoding="utf-8") as file:
        for row in audit_log:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")


# БЛОК ПОСТРОЕНИЯ ГРАФИКОВ
def save_charts(static_dir):
    """
    Строит и сохраняет графики для dashboard.
    """

    static_path = Path(static_dir)
    static_path.mkdir(parents=True, exist_ok=True)

    audit_df, history_df, summary_df, risk_df = build_dataframes()

    # График количества решений контейнера.
    plt.figure(figsize=(8, 5))
    if not summary_df.empty:
        plt.bar(summary_df["decision"], summary_df["count"])
    plt.title("Количество решений контейнера")
    plt.xlabel("Тип решения")
    plt.ylabel("Число запросов")
    plt.grid(axis="y", linestyle="--", alpha=0.4)
    plt.tight_layout()
    plt.savefig(static_path / "chart_decisions.png")
    plt.close()

    # График доступности системы по шагам.
    plt.figure(figsize=(8, 5))
    if not history_df.empty:
        plt.plot(history_df["step"], history_df["available"], marker="o")
    plt.title("Доступность системы по шагам")
    plt.xlabel("Шаг")
    plt.ylabel("Доступность")
    plt.yticks([0, 1])
    plt.grid(linestyle="--", alpha=0.4)
    plt.tight_layout()
    plt.savefig(static_path / "chart_availability.png")
    plt.close()

    # График изменения ресурсов.
    plt.figure(figsize=(8, 5))
    if not history_df.empty:
        plt.plot(history_df["step"], history_df["cpu_limit"], marker="o", label="CPU")
        plt.plot(history_df["step"], history_df["memory_limit"], marker="s", label="RAM")
    plt.title("Изменение лимитов ресурсов")
    plt.xlabel("Шаг")
    plt.ylabel("Значение")
    plt.legend()
    plt.grid(linestyle="--", alpha=0.4)
    plt.tight_layout()
    plt.savefig(static_path / "chart_resources.png")
    plt.close()

    # График распределения операций по уровню риска.
    plt.figure(figsize=(8, 5))
    if not risk_df.empty:
        plt.bar(risk_df["risk_level"], risk_df["count"])
    plt.title("Распределение операций по уровню риска")
    plt.xlabel("Уровень риска")
    plt.ylabel("Число операций")
    plt.grid(axis="y", linestyle="--", alpha=0.4)
    plt.tight_layout()
    plt.savefig(static_path / "chart_risk.png")
    plt.close()


# БЛОК РАСЧЕТА KPI
def build_kpi():
    """
    Рассчитывает показатели dashboard: количество решений и операций высокого риска.
    """

    audit_df, _, _, _ = build_dataframes()

    if audit_df.empty:
        return {
            "allow_count": 0,
            "deny_count": 0,
            "rollback_count": 0,
            "high_risk_count": 0,
        }

    return {
        "allow_count": int((audit_df["decision"] == "allow").sum()),
        "deny_count": int((audit_df["decision"] == "deny").sum()),
        "rollback_count": int((audit_df["decision"] == "rollback").sum()),
        "high_risk_count": int((audit_df["risk_level"] == "Высокий").sum()),
    }

# БЛОК ФОРМИРОВАНИЯ КОНТЕКСТА ДЛЯ ИНТЕРФЕЙСА
def get_dashboard_context(static_dir):
    """
    Формирует данные для передачи в HTML-шаблон dashboard.
    """

    save_charts(static_dir)

    audit_df, history_df, summary_df, risk_df = build_dataframes()
    status = get_status(current_state)
    kpi = build_kpi()

    roles = sorted(list({role for role_list in role_permissions.values() for role in role_list}))

    return {
        "system_status": status,
        "audit_rows": audit_df.to_dict(orient="records"),
        "history_rows": history_df.to_dict(orient="records"),
        "summary_rows": summary_df.to_dict(orient="records"),
        "risk_rows": risk_df.to_dict(orient="records"),
        "roles": roles,
        "actions": list(role_permissions.keys()),
        "routes": allowed_routes,
        "kpi": kpi,
        "chart_version": datetime.now().strftime("%Y%m%d%H%M%S"),
    }


# БЛОК ПОЛУЧЕНИЯ ТЕКУЩЕЙ ПОЛИТИКИ БЕЗОПАСНОСТИ
def get_policy_snapshot():
    """
    Возвращает текущие параметры политики безопасности контейнера.
    Используется административной страницей для отображения настроек.
    """

    return {
        "min_cpu_limit": SECURITY_POLICY["min_cpu_limit"],
        "min_memory_limit": SECURITY_POLICY["min_memory_limit"],
        "allowed_routes": allowed_routes,
        "critical_actions": critical_actions,
    }


# БЛОК ОБНОВЛЕНИЯ ПОЛИТИКИ БЕЗОПАСНОСТИ
def update_security_policy(min_cpu_limit, min_memory_limit, allowed_routes_text, critical_actions_selected):
    """
    Обновляет параметры политики безопасности контейнера:
    минимальные лимиты ресурсов, допустимые маршруты и перечень критичных действий.
    """

    min_cpu_limit = int(min_cpu_limit)
    min_memory_limit = int(min_memory_limit)

    if min_cpu_limit < 1:
        min_cpu_limit = 1

    if min_memory_limit < 1:
        min_memory_limit = 1

    routes = [
        route.strip()
        for route in allowed_routes_text.replace(",", "\n").splitlines()
        if route.strip()
    ]

    if not routes:
        routes = copy.deepcopy(DEFAULT_ALLOWED_ROUTES)

    selected_actions = critical_actions_selected or copy.deepcopy(DEFAULT_CRITICAL_ACTIONS)

    SECURITY_POLICY["min_cpu_limit"] = min_cpu_limit
    SECURITY_POLICY["min_memory_limit"] = min_memory_limit

    allowed_routes.clear()
    allowed_routes.extend(routes)

    critical_actions.clear()
    critical_actions.extend(selected_actions)

    save_export_files()


# БЛОК СБРОСА ПОЛИТИКИ БЕЗОПАСНОСТИ
def reset_security_policy():
    """
    Возвращает политику безопасности контейнера к исходным значениям.
    """

    SECURITY_POLICY["min_cpu_limit"] = 2
    SECURITY_POLICY["min_memory_limit"] = 4

    allowed_routes.clear()
    allowed_routes.extend(copy.deepcopy(DEFAULT_ALLOWED_ROUTES))

    critical_actions.clear()
    critical_actions.extend(copy.deepcopy(DEFAULT_CRITICAL_ACTIONS))

    save_export_files()


# БЛОК ФОРМИРОВАНИЯ ДАННЫХ ДЛЯ АДМИНИСТРАТИВНОЙ ПАНЕЛИ
def get_admin_context(static_dir):
    """
    Формирует данные для административной страницы контейнера безопасности.
    Административная панель используется для настройки политики контроля:
    лимитов ресурсов, допустимых маршрутов и критичных действий.
    """

    save_charts(static_dir)

    audit_df, history_df, summary_df, risk_df = build_dataframes()
    status = get_status(current_state)
    kpi = build_kpi()
    policy = get_policy_snapshot()

    roles_matrix = []

    for action, roles in role_permissions.items():
        roles_matrix.append({
            "action": action,
            "roles": ", ".join(roles),
            "is_critical": action in critical_actions,
        })

    export_dir = Path("exports")
    export_files = []

    for file_name in ["audit_log.csv", "audit_log.jsonl", "history.csv"]:
        file_path = export_dir / file_name

        export_files.append({
            "name": file_name,
            "exists": file_path.exists(),
            "size": file_path.stat().st_size if file_path.exists() else 0,
        })

    return {
        "system_status": status,
        "kpi": kpi,
        "security_policy": policy,
        "routes_text": "\n".join(allowed_routes),
        "roles_matrix": roles_matrix,
        "summary_rows": summary_df.to_dict(orient="records"),
        "risk_rows": risk_df.to_dict(orient="records"),
        "export_files": export_files,
        "audit_count": len(audit_log),
        "history_count": len(history),
        "chart_version": datetime.now().strftime("%Y%m%d%H%M%S"),
    }
