import flet as ft
from backend import VSTUAuth


def main(page: ft.Page):
    # Настройки страницы
    page.title = "ВГТУ Зачетка"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#121212"
    page.window_width = 450
    page.window_height = 800
    page.scroll = "adaptive"
    page.padding = 20

    auth_service = VSTUAuth()

    # --- ЭКРАН ОЦЕНОК ---
    def show_grades(data):
        page.clean()

        avg_val = data.get("average", "0.0")

        # Шапка со средним баллом
        avg_card = ft.Container(
            content=ft.Column([
                ft.Text("СРЕДНИЙ БАЛЛ", size=14, color=ft.Colors.GREY_500, weight="bold"),
                ft.Text(str(avg_val), size=48, weight="bold", color=ft.Colors.AMBER_ACCENT),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=30,
            alignment=ft.alignment.Alignment.CENTER,
        )

        # Группировка данных по семестрам
        semesters = {}
        for item in data.get("statements", []):
            sem = item.get("semesterNumber", "—")
            if sem not in semesters:
                semesters[sem] = []
            semesters[sem].append(item)

        # Основной список контента
        content_list = ft.Column(spacing=15)
        content_list.controls.append(avg_card)
        content_list.controls.append(ft.Divider(height=1, color=ft.Colors.GREY_800))

        # Отрисовка семестров
        for sem_num in sorted(semesters.keys(), reverse=True):
            content_list.controls.append(
                ft.Container(
                    content=ft.Text(f"СЕМЕСТР {sem_num}", size=20, weight="bold", color=ft.Colors.BLUE_200),
                    margin=ft.margin.only(top=20, bottom=5)
                )
            )

            for subject in semesters[sem_num]:
                grade = subject.get("grade", "—")

                # Логика цвета оценки
                grade_color = ft.Colors.WHITE
                if grade == "зачтено":
                    grade_color = ft.Colors.CYAN_400
                elif str(grade).isdigit() and int(grade) >= 8:
                    grade_color = ft.Colors.GREEN_ACCENT
                elif str(grade).isdigit() and int(grade) < 4:
                    grade_color = ft.Colors.RED_ACCENT

                content_list.controls.append(
                    ft.Container(
                        content=ft.ListTile(
                            title=ft.Text(subject.get("disciplineName"), weight="w500"),
                            subtitle=ft.Text(f"{subject.get('examType', 'Экзамен')}", size=12),
                            trailing=ft.Text(str(grade), size=18, weight="bold", color=grade_color),
                        ),
                        bgcolor=ft.Colors.GREY_900,
                        border_radius=10,
                        padding=ft.padding.only(right=10)
                    )
                )

        page.add(content_list)
        page.update()

    # --- ЭКРАН ВХОДА ---
    login_input = ft.TextField(
        label="Номер билета (Логин)",
        border_color=ft.Colors.BLUE_400,
        prefix_icon=ft.icons.Icons.PERSON
    )
    pass_input = ft.TextField(
        label="Пароль",
        password=True,
        can_reveal_password=True,
        prefix_icon=ft.icons.Icons.PERSON
    )
    error_text = ft.Text("", color=ft.Colors.RED_ACCENT)
    login_button = ft.ElevatedButton(
        "Войти в личный кабинет",
        on_click=lambda e: login_click(),
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))
    )
    loading_ring = ft.ProgressRing(visible=False, width=20, height=20)

    def login_click():
        # Показываем загрузку
        error_text.value = ""
        login_button.disabled = True
        loading_ring.visible = True
        page.update()

        # Вызываем бэкенд
        if auth_service.login(login_input.value, pass_input.value):
            data = auth_service.get_statements()
            if data:
                show_grades(data)
            else:
                error_text.value = "Ошибка: не удалось получить список оценок."
                login_button.disabled = False
                loading_ring.visible = False
                page.update()
        else:
            error_text.value = "Неверный логин или пароль"
            login_button.disabled = False
            loading_ring.visible = False
            page.update()

    # Добавляем элементы входа на страницу
    login_container = ft.Container(
        content=ft.Column([
            ft.Icon(ft.icons.Icons.SCHOOL, size=50, color=ft.Colors.BLUE_400),
            ft.Text("Моя Зачетка ВГТУ", size=24, weight="bold"),
            ft.Text("Введите данные для синхронизации", color=ft.Colors.GREY_500),

            login_input,
            pass_input,
            error_text,
            ft.Row([login_button, loading_ring], alignment=ft.MainAxisAlignment.CENTER),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        padding=20,
        alignment=ft.alignment.Alignment.CENTER,
    )

    page.add(login_container)
    page.update()


# Запуск приложения
if __name__ == "__main__":
    ft.app(target=main)