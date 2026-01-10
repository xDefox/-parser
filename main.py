import flet as ft
from backend import VSTUAuth


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
            for item in data.get("statements", []):
                sem = item.get("semesterNumber", "—")
                if sem not in semesters: semesters[sem] = []
                semesters[sem].append(item)

            sorted_nums = sorted(semesters.keys(), reverse=True)
            results_view = ft.Column(spacing=10, scroll="adaptive", expand=True)

            # --- ГЛАВНАЯ ФУНКЦИЯ ОБНОВЛЕНИЯ ЭКРАНА ---
            def update_semester_view(sem_num):
                results_view.controls.clear()
                subjects = semesters[sem_num]

                # 1. Находим все предметы, где УЖЕ есть цифра
                current_grades = []
                for s in subjects:
                    grade_val = str(s.get("grade", ""))
                    if grade_val.isdigit():
                        current_grades.append(int(grade_val))

                # 2. Находим предметы, которые ЕЩЕ НУЖНО сдать (где может быть оценка)
                # Исключаем только обычные зачеты, которые "зачтено/не зачтено"
                pending_subjects = []
                for s in subjects:
                    grade_val = str(s.get("grade", ""))
                    exam_type = str(s.get("examType", "")).lower()

                    # Если оценки нет И это не простой зачет
                    if not grade_val.isdigit() and grade_val != "зачтено":
                        if "зачет" not in exam_type or "дифф" in exam_type:
                            pending_subjects.append(s)

                sum_current = sum(current_grades)
                count_done = len(current_grades)
                count_pending = len(pending_subjects)
                total_count = count_done + count_pending

                sem_avg = sum_current / count_done if count_done > 0 else 0.0

                def get_combinations(target_avg):
                    if total_count == 0: return "Нет оцениваемых предметов"
                    required_sum = target_avg * total_count
                    needed_now = required_sum - sum_current

                    if needed_now <= 0: return "Уже достигнуто! ✅"
                    if count_pending == 0: return "Невозможно (экзаменов больше нет)"

                    avg_req = needed_now / count_pending
                    if avg_req > 10: return f"Недостижимо (нужно {avg_req:.1f})"

                    # Распределяем баллы (твоя идея с перебором)
                    base = int(needed_now // count_pending)
                    remainder = int(needed_now % count_pending)
                    comb = [base + 1] * remainder + [base] * (count_pending - remainder)

                    if base < 4: return "Достаточно сдавать на 4.0 👍"
                    return " + ".join(map(str, sorted(comb, reverse=True)))

                # Формируем карточку анализа
                analysis_text = (
                    f"Средний балл семестра: {sem_avg:.2f}\n"
                    f"Предметов с оценкой: {count_done} из {total_count}\n"
                )

                if count_pending > 0:
                    analysis_text += f"🎯 Цель 8.0: {get_combinations(8.0)}\n"
                    analysis_text += f"🎯 Цель 9.0: {get_combinations(9.0)}"
                else:
                    analysis_text += "Все оценки получены!"

                results_view.controls.append(
                    ft.Container(
                        content=ft.Text(analysis_text, color=ft.Colors.AMBER_ACCENT, weight="bold"),
                        bgcolor=ft.Colors.GREY_900,
                        padding=15,
                        border_radius=10,
                        border=ft.border.all(1, ft.Colors.AMBER_700)
                    )
                )

                # Отрисовка предметов (без изменений)
                for s in subjects:
                    grade = s.get("grade", "—")
                    is_p = not (str(grade).isdigit() or grade == "зачтено")
                    results_view.controls.append(
                        ft.Container(
                            content=ft.ListTile(
                                title=ft.Text(s.get("disciplineName"),
                                              color=ft.Colors.GREY_400 if is_p else ft.Colors.WHITE),
                                subtitle=ft.Text(s.get("examType", "Экзамен")),
                                trailing=ft.Text("?" if is_p else str(grade), size=18, weight="bold",
                                                 color=ft.Colors.GREEN_ACCENT if not is_p else ft.Colors.WHITE),
                            ),
                            bgcolor=ft.Colors.GREY_900,
                            border_radius=10,
                        )
                    )
                page.update()

            # Кнопки семестров
            sem_buttons = ft.Row(
                scroll="auto",
                controls=[
                    ft.FilledTonalButton(
                        f"Сем {n}",
                        on_click=lambda e, num=n: update_semester_view(num)
                    ) for n in sorted_nums
                ]
            )

            avg_total = data.get("average", "0.0")
            page.add(
                ft.Container(
                    content=ft.Column([
                        ft.Text("ОБЩИЙ БАЛЛ", size=12, color=ft.Colors.GREY_500),
                        ft.Text(str(avg_total), size=40, weight="bold", color=ft.Colors.AMBER_ACCENT),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    alignment=ft.alignment.Alignment.CENTER
                ),
                sem_buttons,
                results_view
            )

            # Загружаем первый доступный семестр без генерации Event
            if sorted_nums:
                update_semester_view(sorted_nums[0])

        except Exception as ex:
            print(f"Ошибка в show_grades: {ex}")

    # --- ЭКРАН ВХОДА ---
    login_input = ft.TextField(label="Логин", border_color=ft.Colors.BLUE_400)
    pass_input = ft.TextField(label="Пароль", password=True, can_reveal_password=True)
    error_text = ft.Text("", color=ft.Colors.RED_ACCENT)

    # Заменяем ElevatedButton на FilledButton (современный стандарт)
    login_button = ft.FilledButton(
        "Войти",
        on_click=lambda e: login_click()
    )
    loading_ring = ft.ProgressRing(visible=False, width=20, height=20)

    def login_click():
        error_text.value = ""
        login_button.disabled = True
        loading_ring.visible = True
        page.update()

        print("Запрос к серверу...")
        if auth_service.login(login_input.value, pass_input.value):
            data = auth_service.get_statements()
            if data:
                show_grades(data)
            else:
                error_text.value = "Ошибка получения данных"
                reset_login_state()
        else:
            error_text.value = "Неверный логин или пароль"
            reset_login_state()

    def reset_login_state():
        login_button.disabled = False
        loading_ring.visible = False
        page.update()

    page.add(
        ft.Container(
            content=ft.Column([
                ft.Icon(ft.icons.Icons.SCHOOL, size=50, color=ft.Colors.BLUE_400),
                ft.Text("ВГТУ Зачетка", size=24, weight="bold"),
                ft.Container(height=20),
                login_input,
                pass_input,
                error_text,
                ft.Row([login_button, loading_ring], alignment=ft.MainAxisAlignment.CENTER),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            alignment=ft.alignment.Alignment.CENTER,
            padding=20
        )
    )


# Используем ft.run вместо ft.app
if __name__ == "__main__":
    ft.app(
        target=main)  # Примечание: в версии 0.20+ это всё еще ft.app, но метод run используется в других контекстах. Оставим ft.app для стабильности, если ft.run не подхватится.