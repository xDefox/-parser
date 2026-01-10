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

                current_grades = [int(s['grade']) for s in subjects if str(s.get('grade')).isdigit()]
                pending_count = len(
                    [s for s in subjects if not str(s.get('grade')).isdigit() and s.get('grade') != "зачтено"])
                total_count = len(subjects)
                sum_current = sum(current_grades)

                def get_combinations(target_avg):
                    if pending_count == 0: return None
                    # Сколько баллов нужно добрать суммарно
                    needed_sum = int(target_avg * total_count) - sum_current

                    if needed_sum <= 0: return "Цель уже достигнута! ✅"
                    if needed_sum > pending_count * 10: return "Математически невозможно ❌"

                    # Генерируем красивый вариант (равномерный)
                    base = needed_sum // pending_count
                    remainder = needed_sum % pending_count
                    comb = [base + 1] * remainder + [base] * (pending_count - remainder)

                    if any(x > 10 for x in comb): return "Нужны оценки выше 10 ❌"
                    if any(x < 4 for x in comb): return "Хватит даже четверок! 👍"

                    return " + ".join(map(str, sorted(comb, reverse=True)))

                # Формируем блок анализа
                analysis_text = f"Семестровый балл сейчас: {(sum_current / len(current_grades) if current_grades else 0):.2f}\n"

                if pending_count > 0:
                    analysis_text += f"Нужные комбинации для остатка ({pending_count} предм.):\n"
                    analysis_text += f"🎯 Для 8.0: {get_combinations(8.0)}\n"
                    analysis_text += f"🎯 Для 9.0: {get_combinations(9.0)}"
                else:
                    analysis_text += "Все оценки выставлены."

                # Добавляем в интерфейс
                results_view.controls.append(
                    ft.Container(
                        content=ft.Text(analysis_text, color=ft.Colors.AMBER_ACCENT, weight="bold", size=13),
                        bgcolor=ft.Colors.GREY_900,
                        padding=15,
                        border_radius=10,
                        border=ft.border.all(1, ft.Colors.AMBER_700)
                    )
                )

                # Отрисовка списка предметов (оставляем как было)
                for s in subjects:
                    grade = s.get("grade", "—")
                    is_p = not (str(grade).isdigit() or grade == "зачтено")
                    results_view.controls.append(
                        ft.Container(
                            content=ft.ListTile(
                                title=ft.Text(s.get("disciplineName"),
                                              color=ft.Colors.GREY_400 if is_p else ft.Colors.WHITE),
                                subtitle=ft.Text(f"{s.get('examType')}"),
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