# БЛОК ИМПОРТА МОДУЛЕЙ DJANGO И СЛУЖЕБНЫХ КОМПОНЕНТОВ
from pathlib import Path  # Path используется для формирования пути к папке статических файлов.
from django.contrib import messages  # messages используется для вывода результата обработки запроса пользователю.
from django.shortcuts import render, redirect  # render и redirect используются для отображения страницы и перенаправления.
from .services import guard_logic  # guard_logic содержит вычислительную логику контейнера безопасности.
from django.views.decorators.csrf import csrf_exempt  # csrf_exempt отключает CSRF-проверку для учебного запуска в Replit Preview.


# БЛОК ГЛАВНОГО ПРЕДСТАВЛЕНИЯ ВЕБ-ПАНЕЛИ
@csrf_exempt
def index(request):
    """
    Главное представление management_panel.
    Отвечает за отображение веб-панели, обработку формы управленческого запроса,
    передачу данных в вычислительный модуль и обновление dashboard.
    """

    # Формируем путь к папке статических файлов приложения, куда сохраняются графики.
    static_dir = Path(__file__).resolve().parent / "static" / "management_panel"

    # При первом открытии страницы запускается демонстрационный сценарий,
    # чтобы dashboard сразу содержал журнал, историю и графики.
    if not guard_logic.audit_log:
        guard_logic.run_demo_requests()

    # БЛОК ОБРАБОТКИ POST-ЗАПРОСА ИЗ ФОРМЫ
    if request.method == "POST":
        try:
            # Получаем основные параметры управленческого запроса из HTML-формы.
            action = request.POST.get("action")
            role = request.POST.get("role")
            actor = request.POST.get("actor", "").strip() or "Неизвестный пользователь"

            # Формируем словарь payload, который передается в вычислительный модуль.
            payload = {
                "request_id": len(guard_logic.audit_log) + 1,
                "actor": actor,
                "role": role,
                "action": action,
                "approved": request.POST.get("approved") == "on",
                "simulate_failure": request.POST.get("simulate_failure") == "on",
            }

            # Для действия изменения ресурсов дополнительно передаются CPU и RAM.
            if action == "change_resources":
                payload["new_cpu"] = int(request.POST.get("new_cpu") or 6)
                payload["new_memory"] = int(request.POST.get("new_memory") or 12)

            # Для действия изменения маршрутизации передается новый маршрут.
            elif action == "change_routing":
                payload["new_route"] = request.POST.get("new_route")

            # Передаем запрос в контейнер безопасности.
            record = guard_logic.submit_request(payload)

            # Показываем пользователю результат обработки запроса.
            messages.success(
                request,
                f"Запрос обработан. Решение: {record['decision']}. "
                f"Риск: {record['risk_level']}. Причина: {record['reason']}"
            )

            return redirect("index")

        except Exception as error:
            # Если при обработке формы возникла ошибка, выводим ее в интерфейс.
            messages.error(request, f"Ошибка обработки запроса: {error}")
            return redirect("index")

    # БЛОК ФОРМИРОВАНИЯ ДАННЫХ ДЛЯ ИНТЕРФЕЙСА
    context = guard_logic.get_dashboard_context(static_dir)

    # Отображаем HTML-шаблон панели управления.
    return render(request, "management_panel/index.html", context)

# БЛОК АДМИНИСТРАТИВНОЙ СТРАНИЦЫ
@csrf_exempt
def admin_console(request):
    """
    Административная страница контейнера безопасности.
    Позволяет просматривать и изменять политику контроля управленческих действий.
    """

    static_dir = Path(__file__).resolve().parent / "static" / "management_panel"

    if not guard_logic.audit_log:
        guard_logic.run_demo_requests()

    if request.method == "POST":
        form_action = request.POST.get("form_action")

        if form_action == "update_policy":
            guard_logic.update_security_policy(
                min_cpu_limit=request.POST.get("min_cpu_limit") or 2,
                min_memory_limit=request.POST.get("min_memory_limit") or 4,
                allowed_routes_text=request.POST.get("allowed_routes") or "",
                critical_actions_selected=request.POST.getlist("critical_actions"),
            )

            messages.success(request, "Политика безопасности контейнера обновлена.")
            return redirect("admin_console")

        if form_action == "reset_policy":
            guard_logic.reset_security_policy()
            messages.info(request, "Политика безопасности возвращена к исходным значениям.")
            return redirect("admin_console")

    context = guard_logic.get_admin_context(static_dir)

    return render(request, "management_panel/admin_console.html", context)

# БЛОК СБРОСА ДЕМОНСТРАЦИОННОГО СЦЕНАРИЯ
@csrf_exempt
def reset_demo(request):
    """
    Представление сбрасывает состояние контейнера безопасности
    и заново выполняет демонстрационный сценарий.
    """

    guard_logic.reset_demo_data()  # Очищает состояние, журнал и историю.
    guard_logic.run_demo_requests()  # Повторно выполняет демонстрационные запросы.

    messages.info(request, "Демонстрационный сценарий выполнен заново.")
    return redirect("index")