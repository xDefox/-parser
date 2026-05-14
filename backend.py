import requests
import urllib.parse
import json

class VSTUAuth:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
        })

    def login(self, username, password):
        base_url = "https://auth.vstu.by/login"
        auth_url = "https://auth.vstu.by/login?redirectUrl="

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Referer": "https://auth.vstu.by/login",
            "Origin": "https://auth.vstu.by"
        }

        try:
            self.session.cookies.clear()
            self.session.get(base_url, headers=headers)

            payload = {"username": username, "password": password}
            response = self.session.post(auth_url, data=payload, headers=headers, allow_redirects=True)

            cookies = self.session.cookies.get_dict()
            print(f"Куки: {cookies.keys()}")

            raw_token = cookies.get("token")

            if raw_token:
                decoded_token = urllib.parse.unquote(raw_token)

                try:
                    token_json = json.loads(decoded_token)
                    access_token = token_json.get("access_token")

                    if access_token:
                        self.session.headers.update({
                            "Authorization": f"Bearer {access_token}"
                        })
                        print("Авторизация успешна!")
                        return True
                except json.JSONDecodeError:
                    self.session.headers.update({
                        "Authorization": f"Bearer {decoded_token}"
                    })
                    return True

            print(f"Токен не найден. Статус: {response.status_code}")
            return False

        except Exception as e:
            print(f"Ошибка входа: {e}")
            return False

    def get_statements(self):
        url = "https://student.vstu.by/api/v1/student/account/statements?studentId=undefined&semester=-1&selectPractisesParam=false"
        try:
            response = self.session.get(url)
            print(f"Оценки статус: {response.status_code}")
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Ошибка: {response.text[:200]}")
                return None
        except Exception as e:
            print(f"Ошибка запроса: {e}")
            return None