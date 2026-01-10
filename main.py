import flet as ft
from backend import VSTUAuth
import json
import os

# Путь к файлу настроек
CONFIG_FILE = "config.json"


def save_credentials(login, password):
    with open(CONFIG_FILE, "w") as f:
        json.dump({"login": login, "pass": password}, f)


def load_credentials():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return None


def clear_credentials():
    if os.path.exists(CONFIG_FILE):
        os.remove(CONFIG_FILE)


def main(page: ft.Page):
    page.title = "ВГТУ Зачетка"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#121212"
    page.window_width = 450
    page.window_height = 800
    page.scroll = "adaptive"

    auth_service = VSTUAuth()

    def show_grades(data):
        try:
            page.clean()
            semesters = {}
            v_grades = {}

            for item in data.get("statements", []):
                sem = item.get("semesterNumber", "—")
                if sem not in semesters:
                    semesters[sem] = []
                semesters[sem].append(item)

            sorted_nums = sorted(semesters.keys(), reverse=True)
            results_view = ft.Column(spacing=10, scroll="adaptive", expand=True)

            prog_ring = ft.ProgressRing(
                value=0.0, stroke_width=10,
                color=ft.Colors.AMBER_ACCENT, bgcolor=ft.Colors.GREY_800,
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

                calc_grades = []
                for s in subjects:
                    name = s.get("disciplineName")
                    grade_val = str(s.get("grade", ""))
                    if grade_val.isdigit():
                        calc_grades.append(int(grade_val))
                    elif name in v_grades:
                        calc_grades.append(v_grades[name])

                current_avg = sum(calc_grades) / len(calc_grades) if calc_grades else 0.0
                prog_ring.value = current_avg / 10
                prog_ring.color = ft.Colors.GREEN_ACCENT if current_avg >= 8 else ft.Colors.AMBER_ACCENT
                ring_text.value = f"{current_avg:.2f}"

                # Логика прогноза (твоя оригинальная)
                real_grades = [int(s['grade']) for s in subjects if str(s.get('grade')).isdigit()]
                pending_ones = [s for s in subjects if
                                not str(s.get('grade')).isdigit() and s.get('grade') != "зачтено" and (
                                            "зачет" not in str(s.get('examType')).lower() or "дифф" in str(
                                        s.get('examType')).lower())]
                sum_real = sum(real_grades)
                p_count = len(pending_ones)
                total_aff = len(real_grades) + p_count

                def get_combos(target):
                    needed = (target * total_aff) - sum_real
                    if needed <= 0: return "Достигнуто! ✅"
                    if p_count == 0: return "—"
                    avg_req = needed / p_count
                    if avg_req > 10: return "Недостижимо"
                    base = int(needed // p_count)
                    rem = int(needed % p_count)
                    return " + ".join(map(str, sorted([base + 1] * rem + [base] * (p_count - rem), reverse=True)))

                results_view.controls.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Text(f"Прогноз семестра: {current_avg:.2f}", weight="bold"),
                            ft.Text(f"🎯 Для 8.0: {get_combos(8.0)}", size=12),
                            ft.Text(f"🎯 Для 9.0: {get_combos(9.0)}", size=12),
                        ]),
                        bgcolor=ft.Colors.GREY_900, padding=15, border_radius=12,
                        border=ft.Border.all(1, ft.Colors.AMBER_700)
                    )
                )

                for s in subjects:
                    name = s.get("disciplineName")
                    grade = s.get("grade", "—")
                    is_p = not (str(grade).isdigit() or grade == "зачтено")
                    v_val = v_grades.get(name)

                    def on_click_item(e, s_name=name):
                        if not is_p: return

                        def set_v(ev):
                            if ev.control.data == "clear":
                                v_grades.pop(s_name, None)
                            else:
                                v_grades[s_name] = ev.control.data
                            page.bottom_sheet.open = False
                            page.update()
                            update_semester_view(sem_num)

                        page.bottom_sheet = ft.BottomSheet(
                            ft.Container(
                                ft.Column([
                                    ft.Text(f"Прогноз: {s_name}", weight="bold"),
                                    ft.Row([
                                        ft.IconButton(ft.icons.Icons.DELETE_OUTLINE, data="clear", on_click=set_v,
                                                      icon_color="red"),
                                        *[ft.TextButton(str(i), data=i, on_click=set_v) for i in range(4, 11)]
                                    ], wrap=True, alignment=ft.MainAxisAlignment.CENTER),
                                ], tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                                padding=20, bgcolor=ft.Colors.GREY_900,
                            )
                        )
                        page.bottom_sheet.open = True
                        page.update()

                    results_view.controls.append(
                        ft.Container(
                            content=ft.ListTile(
                                title=ft.Text(name, color=ft.Colors.WHITE if not is_p or v_val else ft.Colors.GREY_400),
                                subtitle=ft.Text(f"{s.get('examType')} {'(нажми)' if is_p else ''}", size=11),
                                trailing=ft.Text(
                                    str(v_val) + "*" if v_val else ("?" if is_p else str(grade)),
                                    color=ft.Colors.AMBER_ACCENT if v_val else (
                                        ft.Colors.GREEN_ACCENT if not is_p else ft.Colors.WHITE),
                                    size=18, weight="bold"
                                ),
                            ),
                            bgcolor=ft.Colors.GREY_900 if is_p else ft.Colors.BLACK,
                            border_radius=10,
                            on_click=on_click_item
                        )
                    )
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
            if sorted_nums:
                update_semester_view(sorted_nums[0])
        except Exception as ex:
            print(f"Ошибка в show_grades: {ex}")

    # --- ЭКРАН АВТОРИЗАЦИИ ---
    login_input = ft.TextField(label="Логин", border_color=ft.Colors.BLUE_400)
    pass_input = ft.TextField(label="Пароль", password=True, can_reveal_password=True)
    remember_me = ft.Checkbox(label="Запомнить меня", value=False)
    error_text = ft.Text("", color=ft.Colors.RED_ACCENT)
    loading_ring = ft.ProgressRing(visible=False, width=20, height=20)

    # Загружаем из файла
    creds = load_credentials()
    if creds:
        login_input.value = creds["login"]
        pass_input.value = creds["pass"]
        remember_me.value = True

    def login_click(e):
        error_text.value = ""
        login_button.disabled = True
        loading_ring.visible = True
        page.update()

        if auth_service.login(login_input.value, pass_input.value):
            if remember_me.value:
                save_credentials(login_input.value, pass_input.value)
            else:
                clear_credentials()

            data = auth_service.get_statements()
            if data:
                show_grades(data)
            else:
                error_text.value = "Ошибка данных"
                reset_login_state()
        else:
            error_text.value = "Неверный вход"
            reset_login_state()

    def reset_login_state():
        login_button.disabled = False
        loading_ring.visible = False
        page.update()

    login_button = ft.FilledButton("Войти", on_click=login_click)

    page.clean()
    page.add(
        ft.Container(
            content=ft.Column([
                ft.Icon(ft.icons.Icons.SCHOOL, size=50, color=ft.Colors.BLUE_400),
                ft.Text("ВГТУ Зачетка", size=24, weight="bold"),
                ft.Container(height=20),
                login_input,
                pass_input,
                ft.Row([remember_me], alignment=ft.MainAxisAlignment.CENTER),
                error_text,
                ft.Row([login_button, loading_ring], alignment=ft.MainAxisAlignment.CENTER),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            alignment=ft.alignment.Alignment.CENTER,
            padding=20
        )
    )


if __name__ == "__main__":
    ft.app(target=main)