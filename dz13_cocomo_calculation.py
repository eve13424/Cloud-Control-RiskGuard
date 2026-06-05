op = 101
reuse = 0.15
productivity = 13
hours_per_month = 160

nop = op * (1 - reuse)
effort_pm = nop / productivity
effort_pm_report = round(effort_pm, 2)
effort_hours = effort_pm_report * hours_per_month
duration = 2.5 * (effort_pm_report ** 0.38)

hardware_software = 253000
travel_training = 160000
personnel = 1468350

total_cost = hardware_software + travel_training + personnel

print("Новые объектные точки:", round(nop, 2))
print("Трудоемкость, чел.-мес.:", effort_pm_report)
print("Трудоемкость, чел.-ч.:", round(effort_hours))
print("Длительность проекта, мес.:", round(duration, 2))
print("Общая стоимость проекта:", total_cost)