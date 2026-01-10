import flet as ft
from backend import VSTUAuth
import json
import os

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
            v_grades = {}  # Словарь для хранения твоих прогнозов

            # Группируем данные по семестрам
            for item in data.get("statements", []):
                sem = item.get("semesterNumber", "—")
                if sem not in semesters:
                    semesters[sem] = []
                semesters[sem].append(item)

            sorted_nums = sorted(semesters.keys(), reverse=True)
            results_view = ft.Column(spacing=10, scroll="adaptive", expand=True)

            # Верхний индикатор среднего балла
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

            # --- ГЛАВНАЯ ФУНКЦИЯ ОБНОВЛЕНИЯ СПИСКА ---
            def update_semester_view(sem_num):
                results_view.controls.clear()
                subjects = semesters[sem_num]

                # 1. Расчет среднего балла (реальные + прогнозы)
                calc_grades = []
                for s in subjects:
                    s_name = s.get("disciplineName")
                    s_type = s.get("examType")
                    s_key = f"{s_name}_{s_type}"

                    grade_val = str(s.get("grade", ""))
                    if grade_val.isdigit():
                        calc_grades.append(int(grade_val))
                    elif s_key in v_grades:
                        calc_grades.append(v_grades[s_key])

                current_avg = sum(calc_grades) / len(calc_grades) if calc_grades else 0.0
                prog_ring.value = current_avg / 10
                prog_ring.color = ft.Colors.CYAN_ACCENT if current_avg >= 8 else ft.Colors.AMBER_ACCENT
                ring_text.value = f"{current_avg:.2f}"

                # 2. Расчет комбинаций для целевого балла
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

                # Добавляем карточку анализа
                results_view.controls.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Icon(ft.icons.Icons.AUTO_AWESOME, color=ft.Colors.CYAN_ACCENT, size=20),
                                ft.Text("АНАЛИЗ СЕМЕСТРА", weight="bold", size=14, color=ft.Colors.CYAN_ACCENT),
                            ], alignment=ft.MainAxisAlignment.CENTER),
                            ft.Divider(height=1, color=ft.Colors.WHITE24),
                            ft.Text(f"🎯 Для 8.0: {get_combos(8.0)}", size=13, color=ft.Colors.GREY_300),
                            ft.Text(f"🎯 Для 9.0: {get_combos(9.0)}", size=13, color=ft.Colors.GREY_300),
                        ], spacing=8),
                        padding=15, border_radius=15, bgcolor="#1E1E1E",
                        border=ft.Border.all(1, ft.Colors.CYAN_700),
                    )
                )

                # 3. Отрисовка предметов
                # --- 3. ОТРИСОВКА ПРЕДМЕТОВ (РАЗБИТЫЙ ЦИКЛ) ---

                def create_subject_card(s):
                    # Все переменные внутри этой функции изолированы для конкретного предмета
                    name = s.get("disciplineName")
                    stype = s.get("examType")
                    key = f"{name}_{stype}"
                    grade = s.get("grade", "—")
                    is_p = not (str(grade).isdigit() or grade == "зачтено")

                    def set_grade_internal(e):
                        val = e.control.data
                        if val == "clear":
                            v_grades.pop(key, None)
                        else:
                            v_grades[key] = int(val)
                        update_semester_view(sem_num)  # Полный пересчет

                    def show_selector_internal(e):
                        # Заменяем содержимое текущего контейнера на меню выбора
                        e.control.content = ft.Column([
                            ft.ListTile(
                                title=ft.Text(name, size=12, weight="bold"),
                                subtitle=ft.Text("Выберите оценку:", size=10, color=ft.Colors.CYAN_ACCENT)
                            ),
                            ft.Row([
                                ft.IconButton(ft.icons.Icons.CLOSE, data="clear", on_click=set_grade_internal,
                                              icon_color="red"),
                                *[ft.TextButton(str(i), data=i, on_click=set_grade_internal) for i in range(4, 11)]
                            ], wrap=True, alignment=ft.MainAxisAlignment.CENTER)
                        ], spacing=0)
                        e.control.update()

                    # Возвращаем готовый контейнер
                    return ft.Container(
                        content=ft.ListTile(
                            title=ft.Text(name, color=ft.Colors.WHITE if not is_p or v_grades.get(
                                key) else ft.Colors.GREY_400, size=14),
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

                # Теперь цикл просто вызывает функцию для каждого предмета
                for s in subjects:
                    results_view.controls.append(create_subject_card(s))

                page.update()

            # Добавляем все на страницу
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

    creds = load_credentials()
    if creds:
        login_input.value = creds.get("login", "")
        pass_input.value = creds.get("pass", "")
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
            error_text.value = "Неверный логин или пароль"
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