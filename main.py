import flet as ft
from backend import VSTUAuth
import json
import os

CONFIG_FILE = "config.json"


def get_stipend_status(avg_grade):
    if avg_grade >= 9.0:
        return "💰 Повышенная стипендия (9-10)", ft.Colors.CYAN_ACCENT
    elif avg_grade >= 8.0:
        return "💰 Повышенная стипендия (8-9)", ft.Colors.GREEN_ACCENT
    elif avg_grade >= 6.0:
        return "✅ Стипендия (6-8)", ft.Colors.BLUE_GREY_200
    elif avg_grade >= 5.0:
        return "✅ Минимальная стипендия (5-6)", ft.Colors.AMBER_100
    else:
        return "⚠️ Без стипендии (ниже 5.0)", ft.Colors.RED_ACCENT


def save_credentials(login, password, data=None):
    payload = {"login": login, "pass": password}
    if data:
        payload["last_data"] = data
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)


def load_credentials():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def main(page: ft.Page):
    page.title = "ВГТУ Зачетка"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#121212"
    page.window_width = 450
    page.window_height = 800
    page.scroll = "adaptive"

    auth_service = VSTUAuth()
    creds = load_credentials()

    def show_grades(data, is_offline=False):
        try:
            page.clean()
            if is_offline:
                page.appbar = ft.AppBar(
                    title=ft.Text("Оффлайн режим (кэш)"),
                    bgcolor="#1E1E1E"
                )

            semesters = {}
            v_grades = {}  # Твоя система прогнозов

            for item in data.get("statements", []):
                sem = item.get("semesterNumber", "—")
                if sem not in semesters:
                    semesters[sem] = []
                semesters[sem].append(item)

            sorted_nums = sorted(semesters.keys(), reverse=True)
            results_view = ft.Column(spacing=10, scroll="adaptive", expand=True)

            prog_ring = ft.ProgressRing(
                value=0.0, stroke_width=10,
                color=ft.Colors.CYAN_ACCENT, bgcolor=ft.Colors.GREY_800,
                width=100, height=100
            )
            ring_text = ft.Text("0.0", size=20, weight="bold")

            ring_container = ft.Container(
                content=ft.Stack([
                    prog_ring,
                    ft.Container(content=ring_text, alignment=ft.alignment.Alignment.CENTER, width=100, height=100)
                ]),
                alignment=ft.alignment.Alignment.CENTER,
                margin=ft.Margin(0, 10, 0, 10)
            )

            def update_semester_view(sem_num):
                results_view.controls.clear()
                subjects = semesters[sem_num]

                combined_grades = []
                actually_pending = []

                for s in subjects:
                    s_name = s.get("disciplineName")
                    s_type = s.get("examType")
                    s_key = f"{s_name}_{s_type}"
                    grade_val = str(s.get("grade", ""))

                    if grade_val.isdigit():
                        combined_grades.append(int(grade_val))
                    elif s_key in v_grades:
                        combined_grades.append(v_grades[s_key])
                    elif "зачет" not in str(s_type).lower() or "дифф" in str(s_type).lower():
                        actually_pending.append(s)

                current_avg = sum(combined_grades) / len(combined_grades) if combined_grades else 0.0
                prog_ring.value = current_avg / 10
                prog_ring.color = ft.Colors.CYAN_ACCENT if current_avg >= 8 else ft.Colors.AMBER_ACCENT
                ring_text.value = f"{current_avg:.2f}"

                stipend_text, stipend_color = get_stipend_status(current_avg)

                sum_current = sum(combined_grades)
                count_total = len(combined_grades) + len(actually_pending)

                def get_combos(target):
                    needed = (target * count_total) - sum_current
                    remaining_slots = len(actually_pending)
                    if needed <= 0: return "Достигнуто! ✅"
                    if remaining_slots == 0: return "—"
                    avg_req = needed / remaining_slots
                    if avg_req > 10: return "Недостижимо"
                    base = int(needed // remaining_slots)
                    rem = int(needed % remaining_slots)
                    return " + ".join(
                        map(str, sorted([base + 1] * rem + [base] * (remaining_slots - rem), reverse=True)))

                results_view.controls.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Icon(ft.icons.Icons.AUTO_AWESOME, color=ft.Colors.CYAN_ACCENT, size=20),
                                ft.Text("АНАЛИЗ И СТИПЕНДИЯ", weight="bold", size=14, color=ft.Colors.CYAN_ACCENT),
                            ], alignment=ft.MainAxisAlignment.CENTER),
                            ft.Divider(height=1, color=ft.Colors.WHITE24),
                            ft.Row([
                                ft.Icon(ft.icons.Icons.PAYMENT, color=stipend_color, size=18),
                                ft.Text(stipend_text, color=stipend_color, weight="bold", size=14),
                            ], alignment=ft.MainAxisAlignment.CENTER),
                            ft.Text(f"🎯 Для 8.0: {get_combos(8.0)}", size=13, color=ft.Colors.GREY_300),
                            ft.Text(f"🎯 Для 9.0: {get_combos(9.0)}", size=13, color=ft.Colors.GREY_300),
                        ], spacing=8),
                        padding=15, border_radius=15, bgcolor="#1E1E1E",
                        border=ft.Border.all(1, ft.Colors.CYAN_700),
                    )
                )

                def set_grade_internal(e, key):
                    val = e.control.data
                    if val == "clear":
                        v_grades.pop(key, None)
                    else:
                        v_grades[key] = int(val)
                    update_semester_view(sem_num)

                def create_subject_card(s):
                    name = s.get("disciplineName")
                    stype = s.get("examType")
                    key = f"{name}_{stype}"
                    grade = s.get("grade", "—")
                    is_p = not (str(grade).isdigit() or grade == "зачтено")

                    def show_selector_internal(e):
                        e.control.content = ft.Column([
                            ft.ListTile(title=ft.Text(name, size=12, weight="bold"),
                                        subtitle=ft.Text("Оценка:", size=10)),
                            ft.Row([
                                ft.IconButton(ft.icons.Icons.CLOSE, data="clear",
                                              on_click=lambda ev: set_grade_internal(ev, key), icon_color="red"),
                                *[ft.TextButton(str(i), data=i, on_click=lambda ev: set_grade_internal(ev, key)) for i
                                  in range(4, 11)]
                            ], wrap=True, alignment=ft.MainAxisAlignment.CENTER)
                        ])
                        e.control.update()

                    return ft.Container(
                        content=ft.ListTile(
                            title=ft.Text(name, size=14, color=ft.Colors.WHITE if not is_p or v_grades.get(
                                key) else ft.Colors.GREY_400),
                            subtitle=ft.Text(stype, size=11, color=ft.Colors.GREY_500),
                            trailing=ft.Text(
                                f"{v_grades.get(key)}*" if v_grades.get(key) else ("?" if is_p else str(grade)),
                                color=ft.Colors.CYAN_ACCENT if v_grades.get(key) else (
                                    ft.Colors.GREEN_ACCENT if not is_p else ft.Colors.WHITE70),
                                size=18, weight="bold"
                            ),
                        ),
                        bgcolor="#1A1A1A" if is_p else ft.Colors.BLACK,
                        border_radius=12,
                        on_click=show_selector_internal if is_p else None
                    )

                for s in subjects:
                    results_view.controls.append(create_subject_card(s))
                page.update()

            avg_all = data.get("average", "0.0")
            page.add(
                ft.Column([
                    ft.Container(
                        content=ft.Column([
                            ft.Text("ОБЩИЙ БАЛЛ", size=10, color=ft.Colors.GREY_500),
                            ft.Text(str(avg_all), size=30, weight="bold", color=ft.Colors.AMBER_ACCENT),
                            ring_container,
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        alignment=ft.alignment.Alignment.CENTER
                    ),
                    ft.Row([
                        ft.FilledTonalButton(f"Сем {n}", on_click=lambda e, num=n: update_semester_view(num))
                        for n in sorted_nums
                    ], scroll="auto"),
                    results_view
                ], expand=True)
            )
            if sorted_nums: update_semester_view(sorted_nums[0])
        except Exception as ex:
            print(f"Error: {ex}")

    # --- ЭКРАН ВХОДА ---
    login_input = ft.TextField(label="Логин", value=creds.get("login", "") if creds else "",
                               border_color=ft.Colors.BLUE_400)
    pass_input = ft.TextField(label="Пароль", password=True, value=creds.get("pass", "") if creds else "",
                              can_reveal_password=True)
    remember_me = ft.Checkbox(label="Запомнить меня", value=True if creds else False)
    error_text = ft.Text("", color=ft.Colors.RED_ACCENT)
    loading_ring = ft.ProgressRing(visible=False, width=20, height=20)

    def login_click(e):
        error_text.value = ""
        login_button.disabled = True
        loading_ring.visible = True
        page.update()

        l, p = login_input.value, pass_input.value
        try:
            if auth_service.login(l, p):
                data = auth_service.get_statements()
                if data:
                    if remember_me.value: save_credentials(l, p, data)
                    show_grades(data, is_offline=False)
                    return

            # Если не зашло онлайн — пробуем кэш
            if creds and "last_data" in creds:
                page.snack_bar = ft.SnackBar(ft.Text("Вход через кэш"), bgcolor=ft.Colors.ORANGE_800)
                page.snack_bar.open = True
                show_grades(creds["last_data"], is_offline=True)
            else:
                error_text.value = "Ошибка сервера / Нет кэша"
                reset_login_state()
        except:
            if creds and "last_data" in creds:
                show_grades(creds["last_data"], is_offline=True)
            else:
                error_text.value = "Ошибка сети"
                reset_login_state()

    def reset_login_state():
        login_button.disabled = False
        loading_ring.visible = False
        page.update()

    login_button = ft.FilledButton("Войти", on_click=login_click)

    # Принудительно выводим сначала только экран входа
    page.clean()
    page.add(
        ft.Container(
            content=ft.Column([
                ft.Icon(ft.icons.Icons.SCHOOL, size=50, color=ft.Colors.BLUE_400),
                ft.Text("ВГТУ Зачетка", size=24, weight="bold"),
                ft.Container(height=20),
                login_input, pass_input,
                ft.Row([remember_me], alignment=ft.MainAxisAlignment.CENTER),
                error_text,
                ft.Row([login_button, loading_ring], alignment=ft.MainAxisAlignment.CENTER),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            alignment=ft.alignment.Alignment.CENTER, padding=20
        )
    )


if __name__ == "__main__":
    ft.app(target=main, assets_dir="assets")