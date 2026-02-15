import os
import time
import requests
from dotenv import load_dotenv
from terminaltables import AsciiTable


load_dotenv()
SUPERJOB_API_KEY = os.getenv("SUPERJOB_SECRET_KEY")

LANGUAGES = ["Python", "Java", "JavaScript", "C++", "C#", "PHP", "Ruby", "Go", "1С"]

SALARY_MULTIPLIER_ONLY_FROM = 1.2
SALARY_MULTIPLIER_ONLY_TO = 0.8


def predict_salary(salary_from, salary_to):
    if salary_from and salary_to:
        return (salary_from + salary_to) / 2
    if salary_from:
        return salary_from * SALARY_MULTIPLIER_ONLY_FROM
    if salary_to:
        return salary_to * SALARY_MULTIPLIER_ONLY_TO
    return None


def predict_rub_salary_hh(vacancy):
    salary = vacancy.get("salary")
    if not salary or salary.get("currency") != "RUR":
        return None
    return predict_salary(salary.get("from"), salary.get("to"))


def predict_rub_salary_sj(vacancy):
    if vacancy.get("currency") != "rub":
        return None
    return predict_salary(vacancy.get("payment_from"), vacancy.get("payment_to"))


def fetch_all_vacancies_list(make_request, extract_items, get_total):

    all_items = []
    page = 0
    total_found = 0
    
    while True:
        response = make_request(page)
        items = extract_items(response)
        
        if page == 0:
            total_found = get_total(response)
            
        all_items.extend(items)
        
        if not items:
            break
        page += 1
        time.sleep(0.3)
    
    return all_items, total_found


def collect_statistics(language, make_request, extract_salary):

    def extract_items(response):
        return response.get("items", []) if "items" in response else response.get("objects", [])

    def get_total(response):
        return response.get("found") or response.get("total", 0)

    all_vacancies, total_found = fetch_all_vacancies_list(
        lambda page: make_request(page),
        extract_items,
        get_total
    )
    
    salaries = []
    for vacancy in all_vacancies:
        salary = extract_salary(vacancy)
        if salary is not None:
            salaries.append(salary)

    if not salaries:
        avg_salary = 0
    else:
        avg_salary = int(sum(salaries) / len(salaries))

    return {
        "vacancies_found": total_found,
        "vacancies_processed": len(salaries),
        "average_salary": avg_salary
    }


def hh_request(language, page):
    url = "https://api.hh.ru/vacancies"
    params = {
        "text": f"ПРОГРАММИСТ {language}",
        "area": 1,
        "period": 30,
        "search_field": "name",
        "per_page": 100,
        "page": page
    }
    return requests.get(url, params=params).json()


def sj_request(language, api_key, page):
    url = "https://api.superjob.ru/2.0/vacancies/"
    headers = {"X-Api-App-Id": api_key}
    params = {
        "town_id": 4,
        "catalogues": 48,
        "keyword": f"программист {language} разработчик {language}",
        "count": 100,
        "page": page
    }
    return requests.get(url, headers=headers, params=params).json()


def get_hh_statistics(language):
    return collect_statistics(
        language,
        lambda page: hh_request(language, page),
        predict_rub_salary_hh
    )


def get_sj_statistics(language, api_key):
    return collect_statistics(
        language,
        lambda page: sj_request(language, api_key, page),
        predict_rub_salary_sj
    )


def print_statistics_table(stats, site_name):
    table_data = [
        ["Язык программирования", "Найдено вакансий", "Обработано вакансий", "Средняя зарплата"]
    ]
    for lang, data in stats.items():
        if data["vacancies_found"] > 0:
            table_data.append([
                lang,
                data["vacancies_found"],
                data["vacancies_processed"],
                data["average_salary"]
            ])
    table = AsciiTable(table_data)
    table.title = f"{site_name} Moscow"
    print(table.table)
    print()


def main():
    print("Сбор статистики с HeadHunter...\n")
    hh_stats = {}
    for lang in LANGUAGES:
        print(f"HeadHunter: {lang}")
        hh_stats[lang] = get_hh_statistics(lang)
        time.sleep(0.5)

    print("\nСбор статистики с SuperJob...\n")
    sj_stats = {}
    for lang in LANGUAGES:
        print(f"SuperJob: {lang}")
        sj_stats[lang] = get_sj_statistics(lang, SUPERJOB_API_KEY)
        time.sleep(0.5)

    print("\n" + "=" * 60)
    print_statistics_table(hh_stats, "HeadHunter")
    print_statistics_table(sj_stats, "SuperJob")


if __name__ == "__main__":
    main()