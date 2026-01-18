#!/usr/bin/env python3
"""
PDF Constructor API для генерации документов Intesa Sanpaolo
Поддерживает: contratto, garanzia, carta
"""

from io import BytesIO
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

def format_money(amount: float) -> str:
    """Форматирование суммы БЕЗ знака € (он уже есть в HTML)"""
    return f"{amount:,.2f}".replace(',', ' ')


def format_date() -> str:
    """Получение текущей даты в итальянском формате"""
    return datetime.now().strftime("%d/%m/%Y")


def monthly_payment(amount: float, months: int, annual_rate: float) -> float:
    """Аннуитетный расчёт ежемесячного платежа"""
    r = (annual_rate / 100) / 12
    if r == 0:
        return round(amount / months, 2)
    num = amount * r * (1 + r) ** months
    den = (1 + r) ** months - 1
    return round(num / den, 2)

def calculate_amortization_schedule(amount: float, months: int, annual_rate: float):
    """Рассчитывает план погашения"""
    monthly_rate = (annual_rate / 100) / 12
    payment = monthly_payment(amount, months, annual_rate)
    
    schedule = []
    balance = amount
    total_interest = 0
    
    for i in range(1, months + 1):
        interest = round(balance * monthly_rate, 2)
        principal = round(payment - interest, 2)
        
        # Корректировка последнего платежа
        if i == months:
            # В последнем месяце гасим весь остаток
            principal = balance
            payment = principal + interest
        
        balance = round(balance - principal, 2)
        # Избегаем отрицательного баланса из-за округления
        if balance < 0:
            balance = 0.0
            
        total_interest += interest
        
        schedule.append({
            'month': i,
            'payment': payment,
            'interest': interest,
            'principal': principal,
            'balance': balance
        })
        
    return schedule, total_interest

def generate_signatures_table() -> str:
    """
    Генерирует две наложенные друг на друга таблицы:
    1. Таблица с подписями (по рядам)
    2. Таблица с печатью (смещена на 3 клетки вправо и вниз)
    Изображения встраиваются как base64 для гарантированной загрузки
    """
    import os
    import base64
    
    # Получаем абсолютные пути к изображениям
    base_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
    
    def image_to_base64(filename):
        """Конвертирует изображение в base64 data URI"""
        img_path = os.path.join(base_dir, filename)
        if os.path.exists(img_path):
            with open(img_path, 'rb') as f:
                img_data = f.read()
                img_base64 = base64.b64encode(img_data).decode('utf-8')
                # Определяем MIME тип по расширению
                mime_type = 'image/png' if filename.endswith('.png') else 'image/jpeg'
                return f"data:{mime_type};base64,{img_base64}"
        return None
    
    # Конвертируем изображения в base64
    sing_2_data = image_to_base64('sing_2.png')
    sing_1_data = image_to_base64('sing_1.png')
    seal_data = image_to_base64('seal.png')
    
    # Проверяем, что все изображения загружены
    if not all([sing_2_data, sing_1_data, seal_data]):
        print("⚠️  Не все изображения найдены для таблицы подписей!")
        return ''
    
    # Таблица с подписями (базовая, по рядам)
    signatures_table = f'''
<table class="signatures-table-base">
<tr>
<td style="width: 33.33%;">
<img src="{sing_1_data}" alt="Подпись 1" style="display: block; width: auto; height: auto; max-width: 100mm; max-height: 40mm; margin: 0 auto;" />
</td>
<td style="width: 33.33%;">
<img src="{sing_2_data}" alt="Подпись 2" style="display: block; width: auto; height: auto; max-width: 100mm; max-height: 40mm; margin: 0 auto;" />
</td>
<td style="width: 33.33%;">
</td>
</tr>
</table>
'''
    
    # Таблица с печатью (наложенная, смещена на 3 клетки)
    seal_table = f'''
<table class="signatures-table-overlay">
<tr>
<td style="width: 33.33%;">
<img src="{seal_data}" alt="Печать" style="display: block; width: auto; height: auto; max-width: 150mm; max-height: 65mm; margin: 0 auto;" />
</td>
<td style="width: 33.33%;">
</td>
<td style="width: 33.33%;">
</td>
</tr>
</table>
'''
    
    # Обертка для наложения таблиц
    table_html = f'''
<div class="signatures-tables-wrapper">
{signatures_table}
{seal_table}
</div>
'''
    print("✅ Две наложенные таблицы созданы (подписи и печать)")
    return table_html

def generate_contratto_pdf(data: dict) -> BytesIO:
    """
    API функция для генерации PDF договора
    
    Args:
        data (dict): Словарь с данными {
            'name': str - ФИО клиента,
            'amount': float - Сумма кредита,
            'duration': int - Срок в месяцах, 
            'tan': float - TAN процентная ставка,
            'taeg': float - TAEG эффективная ставка,
            'payment': float - Ежемесячный платеж (опционально, будет рассчитан)
        }
    
    Returns:
        BytesIO: PDF файл в памяти
    """
    # Рассчитываем платеж если не задан
    if 'payment' not in data:
        data['payment'] = monthly_payment(data['amount'], data['duration'], data['tan'])
    
    # Генерируем таблицу с подписями и печатью
    signatures_html = generate_signatures_table()
    data['signatures_table'] = signatures_html

    html = fix_html_layout('contratto')
    return _generate_pdf_with_images(html, 'contratto', data)


def generate_garanzia_pdf(name: str) -> BytesIO:
    """
    API функция для генерации PDF гарантийного письма
    
    Args:
        name (str): ФИО клиента
        
    Returns:
        BytesIO: PDF файл в памяти
    """
    html = fix_html_layout('garanzia')
    return _generate_pdf_with_images(html, 'garanzia', {'name': name})


def generate_carta_pdf(data: dict) -> BytesIO:
    """
    API функция для генерации PDF письма о карте

    Args:
        data (dict): Словарь с данными {
            'name': str - ФИО клиента,
            'amount': float - Сумма кредита,
            'duration': int - Срок в месяцах,
            'tan': float - TAN процентная ставка,
            'payment': float - Ежемесячный платеж (опционально, будет рассчитан)
        }

    Returns:
        BytesIO: PDF файл в памяти
    """
    # Рассчитываем платеж если не задан
    if 'payment' not in data:
        data['payment'] = monthly_payment(data['amount'], data['duration'], data['tan'])

    html = fix_html_layout('carta')
    return _generate_pdf_with_images(html, 'carta', data)


def generate_approvazione_pdf(data: dict) -> BytesIO:
    """
    API функция для генерации PDF письма об одобрении кредита

    Args:
        data (dict): Словарь с данными {
            'name': str - ФИО клиента,
            'amount': float - Сумма кредита,
            'tan': float - TAN процентная ставка
        }

    Returns:
        BytesIO: PDF файл в памяти
    """
    html = fix_html_layout('approvazione')
    return _generate_pdf_with_images(html, 'approvazione', data)


def _generate_pdf_with_images(html: str, template_name: str, data: dict) -> BytesIO:
    """Внутренняя функция для генерации PDF с изображениями"""
    try:
        from weasyprint import HTML
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from PyPDF2 import PdfReader, PdfWriter
        from PIL import Image
        
        # Заменяем XXX на реальные данные для contratto, carta, garanzia и approvazione
        if template_name in ['contratto', 'carta', 'garanzia', 'approvazione']:
            
            # СПЕЦИАЛЬНАЯ ЛОГИКА ДЛЯ CONTRATTO (Таблица амортизации)
            if template_name == 'contratto':
                # 1. Генерируем таблицу
                schedule, total_interest = calculate_amortization_schedule(
                    data['amount'], 
                    data['duration'], 
                    data['tan']
                )
                
                # Формируем HTML таблицы
                # Используем стили из документа (c18 - table, c7 - row, c4/c5 - cells)
                
                monthly_rate_val = (data['tan'] / 100) / 12
                total_payments = data['payment'] * data['duration'] # Примерно (с учетом округлений в таблице может отличаться)
                total_payments_exact = sum(item['payment'] for item in schedule)
                overpayment = total_payments_exact - data['amount']
                
                # Блок с итогами перед таблицей
                summary_html = f"""
                <p class="c2"><span class="c3">Tasso mensile: {monthly_rate_val:.10f}</span></p>
                <p class="c2"><span class="c3">Rata mensile: € {format_money(data['payment'])}</span></p>
                <p class="c2"><span class="c3">Importo totale pagamenti: € {format_money(total_payments_exact)}</span></p>
                <p class="c2"><span class="c3">Importo interessi totali: € {format_money(overpayment)}</span></p>
                <br>
                """
                
                table_html = """
                <table class="c18" style="width: 100%;">
                <tr class="c7" style="background-color: #b7b7b7;">
                    <td class="c4" style="text-align: center;"><p class="c15"><span class="c6 c11">Mese</span></p></td>
                    <td class="c4" style="text-align: center;"><p class="c15"><span class="c6 c11">Pagamento</span></p></td>
                    <td class="c4" style="text-align: center;"><p class="c15"><span class="c6 c11">Interessi</span></p></td>
                    <td class="c4" style="text-align: center;"><p class="c15"><span class="c6 c11">Importo del prestito</span></p></td>
                    <td class="c4" style="text-align: center;"><p class="c15"><span class="c6 c11">Saldo residuo</span></p></td>
                </tr>
                """
                
                for row in schedule:
                    table_html += f"""
                    <tr class="c7">
                        <td class="c5" style="text-align: center;"><p class="c15"><span class="c3">{row['month']}</span></p></td>
                        <td class="c5" style="text-align: right;"><p class="c2"><span class="c3">€ {format_money(row['payment'])}</span></p></td>
                        <td class="c5" style="text-align: right;"><p class="c2"><span class="c3">€ {format_money(row['interest'])}</span></p></td>
                        <td class="c5" style="text-align: right;"><p class="c2"><span class="c3">€ {format_money(row['principal'])}</span></p></td>
                        <td class="c5" style="text-align: right;"><p class="c2"><span class="c3">€ {format_money(row['balance'])}</span></p></td>
                    </tr>
                    """
                
                table_html += "</table>"
                
                # Вставляем таблицу вместо плейсхолдера
                if '<!-- AMORTIZATION_TABLE_PLACEHOLDER -->' in html:
                    html = html.replace('<!-- AMORTIZATION_TABLE_PLACEHOLDER -->', summary_html + table_html)
                else:
                    print("⚠️ Плейсхолдер для таблицы не найден, таблица не добавлена!")

            replacements = []
            if template_name in ('contratto',):
                replacements = [
                    ('XXX', data['name']),  # имя клиента (первое "Cliente: XXX")
                    ('XXX', format_money(data['amount'])),  # Importo del credito
                    ('XXX', f"{data['tan']:.2f}%"),  # TAN
                    ('XXX', f"{data['taeg']:.2f}%"),  # TAEG
                    ('XXX', f"{data['duration']} mesi"),  # Durata del credito
                    ('XXX', format_money(data['payment'])),  # Rata mensile
                    ('11/06/2025', format_date()),  # дата
                    ('XXX', data['name']),  # имя клиента в таблице подписей (второе "Cliente: XXX")
                    ('<!-- SIGNATURES_TABLE_PLACEHOLDER -->', data.get('signatures_table', '')),
                ]
            elif template_name == 'carta':
                replacements = [
                    ('XXX', data['name']),  # имя клиента
                    ('XXX', format_money(data['amount'])),  # сумма кредита
                    ('XXX', f"{data['tan']:.2f}%"),  # TAN
                    ('XXX', f"{data['duration']} mes"),  # срок
                    ('XXX', format_money(data['payment'])),  # платеж
                ]
            elif template_name == 'garanzia':
                replacements = [
                    ('XXX', data['name']),  # имя клиента
                ]
            elif template_name == 'approvazione':
                replacements = [
                    ('XXX', data['name']),  # имя клиента
                    ('XXX', format_money(data['amount'])),  # сумма кредита
                    ('XXX', f"{data['tan']:.2f}%"),  # TAN
                ]
            
            for old, new in replacements:
                html = html.replace(old, new, 1)  # заменяем по одному
        
        # Конвертируем HTML в PDF
        pdf_bytes = HTML(string=html).write_pdf()
        
        # НАКЛАДЫВАЕМ ИЗОБРАЖЕНИЯ ЧЕРЕЗ REPORTLAB
        return _add_images_to_pdf(pdf_bytes, template_name)
            
    except Exception as e:
        print(f"Ошибка генерации PDF: {e}")
        raise

def _add_images_to_pdf(pdf_bytes: bytes, template_name: str) -> BytesIO:
    """Добавляет изображения на PDF через ReportLab"""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from PyPDF2 import PdfReader, PdfWriter
        from PIL import Image
        
        # Создаем overlay с изображениями
        overlay_buffer = BytesIO()
        overlay_canvas = canvas.Canvas(overlay_buffer, pagesize=A4)
        
        # Размер ячейки для расчета сдвигов
        cell_width_mm = 210/25  # 8.4mm
        cell_height_mm = 297/35  # 8.49mm
        
        # Читаем исходный PDF чтобы знать количество страниц
        base_pdf_reader = PdfReader(BytesIO(pdf_bytes))
        num_pages = len(base_pdf_reader.pages)
        
        if template_name == 'garanzia':
            # ЛОГИКА ДЛЯ GARANZIA (без изменений)
            # Добавляем company.png в центр 27-й клетки с уменьшением в 1.92 раза + сдвиг вправо на 5 клеток
            company_img = Image.open("company.png")
            company_width_mm = company_img.width * 0.264583  # пиксели в мм (96 DPI)
            company_height_mm = company_img.height * 0.264583
            
            # Уменьшаем в 1.33 раза (было 1.6, увеличиваем еще на 20%) + увеличиваем на 15%
            company_scaled_width = (company_width_mm / 1.33) * 1.15
            company_scaled_height = (company_height_mm / 1.33) * 1.15
            
            # Клетка 27 = строка 1, колонка 1 + сдвиг на 5 клеток вправо
            row_27 = (27 - 1) // 25  # строка 1
            col_27 = (27 - 1) % 25   # колонка 1
            
            # Центр клетки 27 + смещение на 5 клеток вправо + 1.25 клетки правее + 1 клетка вправо + 1/3 клетки вправо - 1.5 клетки левее - 1 клетка левее - 1/3 клетки левее + 1/2 клетки вправо
            x_27_center = (col_27 + 5 + 0.5 + 1.25 + 1 + 1/3 - 1.5 - 1.0 - 1/3 + 0.5) * cell_width_mm * mm
            y_27_center = (297 - (row_27 + 0.5 + 1 - 1/3 + 1.0 - 1/3 - 0.25) * cell_height_mm) * mm  # на 1 клетку вниз + 1/3 клетки вниз + 1 клетка вниз - 1/3 клетки вверх - 1/4 клетки вверх
            
            # Смещаем на половину размера изображения для центрирования
            x_27 = x_27_center - (company_scaled_width * mm / 2)
            y_27 = y_27_center - (company_scaled_height * mm / 2)
            
            # Рисуем company.png
            overlay_canvas.drawImage("company.png", x_27, y_27, 
                                   width=company_scaled_width*mm, height=company_scaled_height*mm,
                                   mask='auto', preserveAspectRatio=True)
            
            # Добавляем logo.png как в contratto
            logo_img = Image.open("logo.png")
            logo_width_mm = logo_img.width * 0.264583
            logo_height_mm = logo_img.height * 0.264583
            
            logo_scaled_width = logo_width_mm / 9  # такое же масштабирование как в contratto
            logo_scaled_height = logo_height_mm / 9
            
            # Используем клетку 71 как в contratto для logo.png
            row_71 = (71 - 1) // 25
            col_71 = (71 - 1) % 25
            
            x_71 = (col_71 - 2 + 4 - 2.0) * cell_width_mm * mm  # на 2.0 клетки влево как в contratto
            y_71 = (297 - (row_71 * cell_height_mm + cell_height_mm) - 0.25 * cell_height_mm - 1 * cell_height_mm) * mm  # на 1 клетку вниз как в contratto
            
            overlay_canvas.drawImage("logo.png", x_71, y_71, 
                                   width=logo_scaled_width*mm, height=logo_scaled_height*mm,
                                   mask='auto', preserveAspectRatio=True)
            
            # Добавляем seal.png в центр 590-й клетки с уменьшением в 5 раз
            seal_img = Image.open("seal.png")
            seal_width_mm = seal_img.width * 0.264583
            seal_height_mm = seal_img.height * 0.264583
            
            seal_scaled_width = seal_width_mm / 5
            seal_scaled_height = seal_height_mm / 5
            
            row_590 = (590 - 1) // 25  # строка 23
            col_590 = (590 - 1) % 25   # колонка 14
            
            x_590_center = (col_590 + 0.5) * cell_width_mm * mm
            y_590_center = (297 - (row_590 + 0.5 + 2) * cell_height_mm) * mm  # на 2 клетки вниз
            
            x_590 = x_590_center - (seal_scaled_width * mm / 2)
            y_590 = y_590_center - (seal_scaled_height * mm / 2)
            
            overlay_canvas.drawImage("seal.png", x_590, y_590, 
                                   width=seal_scaled_width*mm, height=seal_scaled_height*mm,
                                   mask='auto', preserveAspectRatio=True)
            
            # Добавляем sing_1.png в центр 593-й клетки с уменьшением в 5 раз
            sing1_img = Image.open("sing_1.png")
            sing1_width_mm = sing1_img.width * 0.264583
            sing1_height_mm = sing1_img.height * 0.264583
            
            sing1_scaled_width = sing1_width_mm / 5
            sing1_scaled_height = sing1_height_mm / 5
            
            row_593 = (593 - 1) // 25  # строка 23
            col_593 = (593 - 1) % 25   # колонка 17
            
            x_593_center = (col_593 + 0.5 - 6) * cell_width_mm * mm  # на 6 клеток влево
            y_593_center = (297 - (row_593 + 0.5 + 2) * cell_height_mm) * mm  # на 2 клетки вниз
            
            x_593 = x_593_center - (sing1_scaled_width * mm / 2)
            y_593 = y_593_center - (sing1_scaled_height * mm / 2)
            
            overlay_canvas.drawImage("sing_1.png", x_593, y_593, 
                                   width=sing1_scaled_width*mm, height=sing1_scaled_height*mm,
                                   mask='auto', preserveAspectRatio=True)
            
            overlay_canvas.save()
            print("🖼️ Добавлены изображения для garanzia")

        elif template_name in ['carta', 'approvazione']:
            # ЛОГИКА ДЛЯ CARTA/APPROVAZIONE (без изменений)
            # Добавляем company.png как в contratto
            img = Image.open("company.png")
            img_width_mm = img.width * 0.264583
            img_height_mm = img.height * 0.264583

            scaled_width = (img_width_mm / 2) * 1.44  # +44% как в contratto
            scaled_height = (img_height_mm / 2) * 1.44

            row_52 = (52 - 1) // 25 + 1  # строка 3
            col_52 = (52 - 1) % 25 + 1   # колонка 2

            x_52 = (col_52 * cell_width_mm - 0.5 * cell_width_mm - (1/6) * cell_width_mm + 0.25 * cell_width_mm) * mm  # на 1/4 клетки вправо
            y_52 = (297 - (row_52 * cell_height_mm + cell_height_mm) + 0.5 * cell_height_mm + 0.25 * cell_height_mm - 1 * cell_height_mm + 1 * cell_height_mm) * mm  # на 1.5 клетки вверх

            overlay_canvas.drawImage("company.png", x_52, y_52,
                                   width=scaled_width*mm, height=scaled_height*mm,
                                   mask='auto', preserveAspectRatio=True)

            # Добавляем logo.png только для carta (как в contratto)
            if template_name == 'carta':
                logo_img = Image.open("logo.png")
                logo_width_mm = logo_img.width * 0.264583
                logo_height_mm = logo_img.height * 0.264583

                logo_scaled_width = logo_width_mm / 9  # такое же масштабирование как в contratto
                logo_scaled_height = logo_height_mm / 9

                # Используем клетку 71 как в contratto для logo.png
                row_71 = (71 - 1) // 25
                col_71 = (71 - 1) % 25

                x_71 = (col_71 - 2 + 4 - 2.0) * cell_width_mm * mm  # на 2.0 клетки влево как в contratto
                y_71 = (297 - (row_71 * cell_height_mm + cell_height_mm) - 0.25 * cell_height_mm - 1 * cell_height_mm) * mm  # на 1 клетку вниз как в contratto

                overlay_canvas.drawImage("logo.png", x_71, y_71,
                                       width=logo_scaled_width*mm, height=logo_scaled_height*mm,
                                       mask='auto', preserveAspectRatio=True)

            # Добавляем seal.png в центр 767-й клетки (590 + 7*25 + 2)
            seal_img = Image.open("seal.png")
            seal_width_mm = seal_img.width * 0.264583
            seal_height_mm = seal_img.height * 0.264583

            seal_scaled_width = seal_width_mm / 5
            seal_scaled_height = seal_height_mm / 5

            row_767 = (775 - 1) // 25
            col_767 = (775 - 1) % 25

            x_767_center = (col_767 + 0.5) * cell_width_mm * mm
            y_767_center = (297 - (row_767 + 0.5) * cell_height_mm) * mm

            x_767 = x_767_center - (seal_scaled_width * mm / 2)
            y_767 = y_767_center - (seal_scaled_height * mm / 2)

            overlay_canvas.drawImage("seal.png", x_767, y_767,
                                   width=seal_scaled_width*mm, height=seal_scaled_height*mm,
                                   mask='auto', preserveAspectRatio=True)

            # Добавляем sing_1.png в центр 770-й клетки (593 + 7*25 + 2)
            sing1_img = Image.open("sing_1.png")
            sing1_width_mm = sing1_img.width * 0.264583
            sing1_height_mm = sing1_img.height * 0.264583

            sing1_scaled_width = sing1_width_mm / 5
            sing1_scaled_height = sing1_height_mm / 5

            row_770 = (770 - 1) // 25
            col_770 = (770 - 1) % 25

            x_770_center = (col_770 + 0.5) * cell_width_mm * mm
            y_770_center = (297 - (row_770 + 0.5) * cell_height_mm) * mm

            x_770 = x_770_center - (sing1_scaled_width * mm / 2)
            y_770 = y_770_center - (sing1_scaled_height * mm / 2)

            overlay_canvas.drawImage("sing_1.png", x_770, y_770,
                                   width=sing1_scaled_width*mm, height=sing1_scaled_height*mm,
                                   mask='auto', preserveAspectRatio=True)

            overlay_canvas.save()
            print(f"🖼️ Добавлены изображения для {template_name}")
        
        elif template_name in ('contratto',):
            # ЛОГИКА ДЛЯ CONTRATTO
            
            # Подготавливаем изображения
            # Company
            img = Image.open("company.png")
            img_width_mm = img.width * 0.264583
            img_height_mm = img.height * 0.264583
            
            scaled_width = (img_width_mm / 2) * 1.44 * 1.3
            scaled_height = (img_height_mm / 2) * 1.44 * 1.3
            
            row_52 = (52 - 1) // 25 + 1
            col_52 = (52 - 1) % 25 + 1
            
            x_52 = (col_52 * cell_width_mm - 0.5 * cell_width_mm - (1/6) * cell_width_mm + 0.25 * cell_width_mm) * mm
            y_52 = (297 - (row_52 * cell_height_mm + cell_height_mm) + 0.5 * cell_height_mm + 0.25 * cell_height_mm - 0.5 * cell_height_mm) * mm
            
            # Logo
            logo_img = Image.open("logo.png")
            logo_width_mm = logo_img.width * 0.264583
            logo_height_mm = logo_img.height * 0.264583
            
            logo_scaled_width = logo_width_mm / 9
            logo_scaled_height = logo_height_mm / 9
            
            row_71 = (71 - 1) // 25
            col_71 = (71 - 1) % 25
            
            x_71 = (col_71 - 2 + 4 - 2.0) * cell_width_mm * mm
            y_71 = (297 - (row_71 * cell_height_mm + cell_height_mm) - 0.25 * cell_height_mm - 1 * cell_height_mm) * mm

            # Генерируем страницы overlay
            for i in range(num_pages):
                # На каждой странице добавляем company и logo (ТОЛЬКО НА ПЕРВЫХ ДВУХ СТРАНИЦАХ: индексы 0 и 1)
                if i < 2: 
                    overlay_canvas.drawImage("company.png", x_52, y_52, 
                                           width=scaled_width*mm, height=scaled_height*mm, 
                                           mask='auto', preserveAspectRatio=True)
                    
                    overlay_canvas.drawImage("logo.png", x_71, y_71, 
                                           width=logo_scaled_width*mm, height=logo_scaled_height*mm,
                                           mask='auto', preserveAspectRatio=True)
                
                # Нумерация страниц
                # Используем координаты из оригинального файла для нумерации
                row_862 = (862 - 1) // 25
                col_862 = (862 - 1) % 25
                x_page_num = (col_862 + 1 + 0.5) * cell_width_mm * mm
                y_page_num = (297 - (row_862 * cell_height_mm + cell_height_mm/2) - 0.25 * cell_height_mm + 0.25 * cell_height_mm) * mm

                overlay_canvas.setFillColorRGB(0, 0, 0)
                overlay_canvas.setFont("Helvetica", 10)
                overlay_canvas.drawString(x_page_num-2, y_page_num-2, str(i + 1))
                
                # Подписи и печати теперь встраиваются через HTML и не требуют добавления здесь
                
                overlay_canvas.showPage()
            
            overlay_canvas.save()
            print("🖼️ Добавлены изображения для contratto через ReportLab API (динамические страницы)")
        
        # Объединяем PDF с overlay
        overlay_buffer.seek(0)
        base_pdf = PdfReader(BytesIO(pdf_bytes))
        overlay_pdf = PdfReader(overlay_buffer)
        
        writer = PdfWriter()
        
        # Накладываем изображения на каждую страницу
        for i, page in enumerate(base_pdf.pages):
            if i < len(overlay_pdf.pages):
                page.merge_page(overlay_pdf.pages[i])
            writer.add_page(page)
        
        # Создаем финальный PDF с изображениями
        final_buffer = BytesIO()
        writer.write(final_buffer)
        final_buffer.seek(0)
        
        print(f"✅ PDF с изображениями создан через API! Размер: {len(final_buffer.getvalue())} байт")
        return final_buffer
        
    except Exception as e:
        print(f"❌ Ошибка наложения изображений через API: {e}")
        # Возвращаем обычный PDF без изображений
        buf = BytesIO(pdf_bytes)
        buf.seek(0)
        return buf


def fix_html_layout(template_name='contratto'):
    """Исправляем HTML для корректного отображения"""
    
    # Читаем оригинальный HTML
    html_file = f'{template_name}.html'
    # Читаем файл
    try:
        with open(html_file, 'r', encoding='utf-8') as f:
            html = f.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"Файл {html_file} не найден")
    
    # Для garanzia - МИНИМАЛЬНАЯ обработка, только @page рамка
    if template_name == 'garanzia':
        # СНАЧАЛА удаляем все изображения из HTML, но добавляем пробел
        import re
        html = re.sub(r'<img[^>]*>', '', html)  # Удаляем все img теги
        html = re.sub(r'<span[^>]*overflow:[^>]*>[^<]*</span>', '<br><br>', html)  # Заменяем span с overflow на пробел
        print("🗑️ Удалены все изображения из HTML, добавлен пробел вместо изображения")
        
        css_fixes = """
    <style>
    @page {
        size: A4;
        margin: 1cm;           /* 1cm отступ от края страницы до текста */
        border: 4pt solid #388e2b;  /* Зелёная рамка вокруг текста */
        padding: 0;            /* Никаких дополнительных отступов */
    }
    
    /* ИСПРАВЛЯЕМ ОТСТУПЫ BODY - ставим 2см слева и справа */
    .c8 {
        padding: 0 2cm !important;  /* 2см слева и справа для текста */
        max-width: none !important;  /* Убираем ограничение ширины */
    }
    
    /* УСТАНАВЛИВАЕМ МЕЖСТРОЧНЫЙ ИНТЕРВАЛ 1.25 - ПЕРЕОПРЕДЕЛЯЕМ ВСЕ КЛАССЫ */
    .c5, .c6, .c7, .c0, .c1, .c2, .c3, .c4, .c11,
    body, p, div, span, li, ul, ol,
    .title, .subtitle, h1, h2, h3, h4, h5, h6 {
        line-height: 1.25 !important;
    }
    
    /* ТОЛЬКО контроль количества страниц */
    * {
        page-break-after: avoid !important;
        page-break-inside: avoid !important;
        page-break-before: avoid !important;
    }
    
    @page:nth(2) {
        display: none !important;
    }
    </style>
    """
        # Вставляем CSS ПЕРЕД закрывающим </head>
        html = html.replace('</head>', f'{css_fixes}</head>')
        print("✅ Для garanzia добавлена только @page рамка - исходная структура сохранена")
        return html
    
    # Добавляем CSS для правильной разметки (НЕ для garanzia - уже обработана выше)
    elif template_name in ['carta', 'approvazione']:
        # Для carta - СТРОГО 1 СТРАНИЦА с компактной версткой
        css_fixes = """
    <style>
    @page {
        size: A4;
        margin: 1cm;  /* Отступ как в garanzia */
        border: 2pt solid #388e2b;  /* Зелёная рамка (на 2pt тоньше чем garanzia) */
        padding: 0;  /* Отступ как в garanzia */
    }
    
    body {
        font-family: "Roboto Mono", monospace;
        font-size: 9pt;  /* Уменьшаем размер шрифта для компактности */
        line-height: 1.0;  /* Компактная высота строки */
        margin: 0;
        padding: 0 0cm;  /* 2см отступы слева и справа как в garanzia */
        overflow: hidden;  /* Предотвращаем выход за границы */
    }
    
    /* СТРОГИЙ КОНТРОЛЬ: ТОЛЬКО 1 СТРАНИЦА для carta */
    * {
        page-break-after: avoid !important;
        page-break-inside: avoid !important;
        page-break-before: avoid !important;
        overflow: hidden !important;  /* Обрезаем контент если он не помещается */
    }
    
    /* Запрещаем создание страниц после 1-й */
    @page:nth(2) {
        display: none !important;
    }
    
    /* УБИРАЕМ ВСЕ рамки элементов - используем только @page рамку КАК В ДРУГИХ ШАБЛОНАХ */
    .c12, .c9, .c20, .c22, .c8 {
        border: none !important;
        padding: 2pt !important;
        margin: 0 !important;
        width: 100% !important;
        max-width: none !important;
    }
    
    /* Основной контейнер документа - компактный */
    .c12 {
        max-width: none !important;
        padding: 0 !important;
        margin: 0 !important;
        width: 100% !important;
        height: auto !important;
        overflow: hidden !important;
        border: none !important;  /* Убираем только лишние рамки, НЕ .c8 */
    }
    
    /* Параграфы с минимальными отступами */
    .c6, .c0, .c2, .c3 {
        margin: 1pt 0 !important;  /* Минимальные отступы */
        padding: 0 !important;
        text-align: left !important;
        width: 100% !important;
        line-height: 1.0 !important;
        overflow: hidden !important;
    }
    
    /* Таблицы компактные */
    table {
        margin: 1pt 0 !important;
        padding: 0 !important;
        width: 100% !important;
        font-size: 9pt !important;
        border-collapse: collapse !important;
    }
    
    td, th {
        padding: 1pt !important;
        margin: 0 !important;
        font-size: 9pt !important;
        line-height: 1.0 !important;
    }
    
    /* Убираем красное выделение и фоны */
    .c15, .c1, .c16, .c6 {
        background-color: transparent !important;
        background: none !important;
    }
    
    /* Списки компактные */
    ul, ol, li {
        margin: 0 !important;
        padding: 0 !important;
        line-height: 1.0 !important;
    }
    
    /* Заголовки компактные */
    h1, h2, h3, h4, h5, h6 {
        margin: 2pt 0 !important;
        padding: 0 !important;
        font-size: 10pt !important;
        line-height: 1.0 !important;
    }
    
    /* СЕТКА ДЛЯ ПОЗИЦИОНИРОВАНИЯ ИЗОБРАЖЕНИЙ 25x35 - КАК В ДРУГИХ ШАБЛОНАХ */
    .grid-overlay {
        position: absolute;
        top: 0;
        left: 0;
        width: 210mm;  /* Полная ширина A4 */
        height: 297mm; /* Полная высота A4 */
        pointer-events: none;
        z-index: 1000;
        opacity: 0; /* 0% прозрачности - невидимая */
    }
    
    .grid-cell {
        position: absolute;
        border: none;
        background-color: transparent;
        display: none;
        font-size: 6pt;
        font-weight: bold;
        color: transparent;
        font-family: Arial, sans-serif;
        box-sizing: border-box;
    }
    
    </style>
    """
    else:
        # Для contratto (и других многостраничных)
        css_fixes = """
    <style>
    @page {
        size: A4;
        margin: 1cm;  /* Отступ как в garanzia */
        border: 4pt solid #388e2b;  /* Зелёная рамка */
        padding: 0;  /* Отступ как в garanzia */
    }
    
    body {
        font-family: "Roboto Mono", monospace;
        font-size: 10pt;  /* Возвращаем нормальный размер шрифта */
        line-height: 1.0;  /* Нормальная высота строки */
        margin: 0;
        padding: 0 2cm;  /* 2см отступы слева и справа как в garanzia */
    }
    
    /* КРИТИЧНО: Убираем ВСЕ рамки из элементов, оставляем только @page */
    .c20 {
        border: none !important;
        padding: 3mm !important;  /* Нормальные отступы */
        margin: 0 !important;
    }
    
    /* РАЗРЕШАЕМ РАЗРЫВ СТРАНИЦ */
    * {
        page-break-after: auto !important;
        page-break-inside: auto !important;
    }
    
    /* ИСПРАВЛЯЕМ ПРОБЛЕМУ С РАЗРЫВОМ - переопределяем только c7 */
    .c7 {
        height: auto !important;
    }
    
    .page-break {
        page-break-before: always !important;
        page-break-after: avoid !important;
        height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    
    /* ВОССТАНАВЛИВАЕМ НОРМАЛЬНЫЕ ОТСТУПЫ В ТЕКСТЕ */
    p {
        margin: 2pt 0 !important;  /* Нормальные отступы между параграфами */
        padding: 0 !important;
        line-height: 1.0 !important;
    }
    
    div {
        margin: 0 !important;
        padding: 0 !important;
    }
    
    table {
        margin: 3pt 0 !important;  /* Нормальные отступы для таблиц */
        font-size: 10pt !important;  /* Нормальный размер шрифта */
    }
    
    /* Убираем Google Docs стили */
    .c22 {
        max-width: none !important;
        padding: 0 !important;
        margin: 0 !important;
        border: none !important;
    }
    
    .c14, .c25 {
        margin-left: 0 !important;
    }
    
    /* НОРМАЛЬНЫЕ ЗАГОЛОВКИ С ОТСТУПАМИ */
    .c15 {
        font-size: 14pt !important;  /* Возвращаем нормальный размер */
        margin: 4pt 0 !important;    /* Нормальные отступы */
        font-weight: 700 !important;
    }
    
    .c10 {
        font-size: 12pt !important;  /* Возвращаем нормальный размер */
        margin: 3pt 0 !important;    /* Нормальные отступы */
        font-weight: 700 !important;
    }
    
    /* ТОЛЬКО пустые элементы делаем невидимыми - НЕ ТРОГАЕМ текстовые! */
    .c6:empty {
        height: 0pt !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    
    /* Нормальные отступы для списков */
    .c3 {
        margin: 1pt 0 !important;
    }
    
    /* УБИРАЕМ КРАСНОЕ ВЫДЕЛЕНИЕ ТЕКСТА */
    .c1, .c16 {
        background-color: transparent !important;
        background: none !important;
    }
    
    /* ТАБЛИЦА С ПОДПИСЯМИ И ПЕЧАТЬЮ - динамически в конце документа */
    .signatures-table-base {
        width: 100% !important;
        border-collapse: collapse !important;
        border: none !important;
        background: transparent !important;
        position: relative !important;
    }
    
    .signatures-table-base td {
        border: none !important;
        padding: 10pt !important;
        background: transparent !important;
        vertical-align: bottom !important;
        text-align: center !important;
    }
    
    /* НАЛОЖЕННАЯ ТАБЛИЦА С ПЕЧАТЬЮ (смещена на 3 клетки вправо и 2 клетки вверх) */
    .signatures-table-overlay {
        width: 100% !important;
        border-collapse: collapse !important;
        border: none !important;
        background: transparent !important;
        position: absolute !important;
        top: -16.98mm !important;  /* 2 клетки вверх (2 * 8.49mm) */
        left: 25.2mm !important;  /* 3 клетки вправо (3 * 8.4mm) */
        z-index: 10 !important;
    }
    
    .signatures-table-overlay td {
        border: none !important;
        padding: 10pt !important;
        background: transparent !important;
        vertical-align: bottom !important;
        text-align: center !important;
    }
    
    /* ОБЕРТКА ДЛЯ НАЛОЖЕННЫХ ТАБЛИЦ */
    .signatures-tables-wrapper {
        position: relative !important;
        width: 100% !important;
        margin-top: 15pt !important;
        margin-bottom: 10pt !important;
        page-break-inside: avoid !important;
    }

    /* СЕТКА ДЛЯ ПОЗИЦИОНИРОВАНИЯ ИЗОБРАЖЕНИЙ 25x35 - НА КАЖДОЙ СТРАНИЦЕ */
    .grid-overlay {
        position: absolute;
        top: 0;
        left: 0;
        width: 210mm;  /* Полная ширина A4 */
        height: 297mm; /* Полная высота A4 */
        pointer-events: none;
        z-index: 1000;
        opacity: 0; /* 0% прозрачности - невидимая */
    }
    
    /* Сетка для каждой страницы отдельно */
    .page-grid {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100vh;
        pointer-events: none;
        z-index: 1000;
        opacity: 0.3;
    }
    
    .grid-cell {
        position: absolute;
        border: none;
        background-color: transparent;
        display: none;
        font-size: 6pt;
        font-weight: bold;
        color: transparent;
        font-family: Arial, sans-serif;
        box-sizing: border-box;
    }
    
    /* Позиционирование относительно сетки */
    .positioned-image {
        position: absolute;
        z-index: 500;
    }
    
    </style>
    """
    
    # Вставляем CSS ПЕРЕД закрывающим </head>, чтобы наши правила шли ПОСЛЕ исходных
    # и имели приоритет каскада (last-wins)
    html = html.replace('</head>', f'{css_fixes}</head>')
    
    # НЕ НУЖНО - используем @page рамку как в других шаблонах
    
    # КРИТИЧНО: СНАЧАЛА убираем старые изображения, ПОТОМ добавляем новые!
    import re
    
    # Очистка HTML в зависимости от шаблона
    if template_name in ('contratto',):
        # 1. ПОЛНОСТЬЮ убираем блок с 3 изображениями между разделами
        middle_images_pattern = r'<p class="c3"><span style="overflow: hidden[^>]*><img alt="" src="images/image1\.png"[^>]*></span><span style="overflow: hidden[^>]*><img alt="" src="images/image2\.png"[^>]*></span><span style="overflow: hidden[^>]*><img alt="" src="images/image4\.png"[^>]*></span></p>'
        html = re.sub(middle_images_pattern, '', html)
    
        # 2. Убираем ВСЕ пустые div и параграфы в конце
        html = re.sub(r'<div><p class="c6 c18"><span class="c7 c23"></span></p></div>$', '', html)
        html = re.sub(r'<p class="c3 c6"><span class="c7 c12"></span></p>$', '', html)
        html = re.sub(r'<p class="c6 c24"><span class="c7 c12"></span></p>$', '', html)
        
        # 3. Убираем избыточные пустые строки между разделами (НЕ в тексте!)
        html = re.sub(r'(<p class="c3 c6"><span class="c7 c12"></span></p>\s*){2,}', '<p class="c3 c6"><span class="c7 c12"></span></p>', html)
        html = re.sub(r'(<p class="c24 c6"><span class="c7 c12"></span></p>\s*)+', '', html)
        
        # 4. Убираем лишние высоты из таблиц
        html = html.replace('class="c13"', 'class="c13" style="height: auto !important;"')
        html = html.replace('class="c19"', 'class="c19" style="height: auto !important;"')
        
    elif template_name == 'garanzia':
        # Для garanzia НЕ УДАЛЯЕМ НИЧЕГО - сохраняем исходную структуру
        print("✅ Для garanzia сохранена исходная HTML структура без изменений")
    elif template_name in ['carta', 'approvazione']:
        # Убираем ВСЕ изображения из carta - они создают лишние страницы
        # Убираем логотип в начале
        logo_pattern = r'<p class="c12"><span style="overflow: hidden[^>]*><img alt="" src="images/image1\.png"[^>]*></span></p>'
        html = re.sub(logo_pattern, '', html)
        
        # Убираем изображения в тексте (печать и подпись)
        seal_pattern = r'<span style="overflow: hidden[^>]*><img alt="" src="images/image2\.png"[^>]*></span>'
        html = re.sub(seal_pattern, '', html)
        
        signature_pattern = r'<span style="overflow: hidden[^>]*><img alt="" src="images/image3\.png"[^>]*></span>'
        html = re.sub(signature_pattern, '', html)
        
        # Убираем ВСЕ пустые div и параграфы которые создают лишние страницы
        html = re.sub(r'<div><p class="c6 c18"><span class="c7 c23"></span></p></div>', '', html)
        html = re.sub(r'<p class="c3 c6"><span class="c7 c12"></span></p>', '', html)
        html = re.sub(r'<p class="c6 c24"><span class="c7 c12"></span></p>', '', html)
        html = re.sub(r'<p class="c6"><span class="c7"></span></p>', '', html)
        
        # Убираем избыточные пустые строки между разделами
        html = re.sub(r'(<p class="c3 c6"><span class="c7 c12"></span></p>\s*){2,}', '', html)
        html = re.sub(r'(<p class="c24 c6"><span class="c7 c12"></span></p>\s*)+', '', html)
        
        # Убираем лишние высоты из таблиц - принудительно делаем auto
        html = html.replace('class="c13"', 'class="c13" style="height: auto !important;"')
        html = html.replace('class="c19"', 'class="c19" style="height: auto !important;"')
        html = html.replace('class="c5"', 'class="c5" style="height: auto !important;"')
        html = html.replace('class="c9"', 'class="c9" style="height: auto !important;"')
        
        # КРИТИЧНО: Убираем всё что может создать вторую страницу в конце документа
        # Ищем закрывающий тег body и убираем всё лишнее перед ним
        body_end = html.rfind('</body>')
        if body_end != -1:
            # Находим последний значимый контент перед </body>
            content_before_body = html[:body_end].rstrip()
            # Убираем trailing пустые параграфы и divs
            content_before_body = re.sub(r'(<p[^>]*><span[^>]*></span></p>\s*)+$', '', content_before_body)
            content_before_body = re.sub(r'(<div[^>]*></div>\s*)+$', '', content_before_body)
            html = content_before_body + '\n</body></html>'
        
        print("🗑️ Удалены все изображения из carta для предотвращения лишних страниц")
        print("🗑️ Убраны пустые элементы в конце документа для строгого контроля 1 страницы")

    
    # Общая очистка ТОЛЬКО для contratto и carta
    if template_name != 'garanzia':
        # Убираем лишние высоты из таблиц
        html = html.replace('class="c5"', 'class="c5" style="height: auto !important;"')
        html = html.replace('class="c9"', 'class="c9" style="height: auto !important;"')
    else:
        print("🚫 Для garanzia пропускаем общую очистку таблиц - сохраняем исходные стили")
    
    # УНИВЕРСАЛЬНЫЙ АНАЛИЗАТОР И УДАЛИТЕЛЬ ПРОБЛЕМНЫХ ЭЛЕМЕНТОВ
    def analyze_and_fix_problematic_elements(html_content):
        """
        Универсальный анализатор, находящий и исправляющий элементы, создающие лишние страницы:
        1. Элементы с огромными высотами (>500pt)
        2. Элементы с красными/оранжевыми рамками
        3. Таблицы с фиксированными высотами строк
        """
        print("🔍 Анализируем HTML на предмет проблемных элементов...")
        
        # 1. НАХОДИМ И ИСПРАВЛЯЕМ ОГРОМНЫЕ ВЫСОТЫ (>500pt)
        height_pattern = r'\.([a-zA-Z0-9_-]+)\{[^}]*height:\s*([0-9]+(?:\.[0-9]+)?)pt[^}]*\}'
        matches = re.findall(height_pattern, html_content)
        
        fixed_heights = []
        for class_name, height_value in matches:
            height_pt = float(height_value)
            if height_pt > 500:  # Больше 500pt = проблема
                old_pattern = f'.{class_name}{{height:{height_value}pt}}'
                new_pattern = f'.{class_name}{{height:auto;}}'
                html_content = html_content.replace(old_pattern, new_pattern)
                fixed_heights.append(f"{class_name}({height_value}pt)")
        
        if fixed_heights:
            print(f"📏 Исправлены огромные высоты: {', '.join(fixed_heights)}")
        
        # 2. НАХОДИМ И УБИРАЕМ СТАРЫЕ РАМКИ #e2001a (встроенные из HTML)
        # Это нужно чтобы избежать двойных рамок с @page
        red_border_pattern = r'\.([a-zA-Z0-9_-]+)\{[^}]*border[^}]*#e2001a[^}]*\}'
        red_border_matches = re.findall(red_border_pattern, html_content, re.IGNORECASE)
        
        removed_red_borders = []
        for class_name in red_border_matches:
            # Заменяем весь CSS класса на простой без рамки
            old_class_pattern = rf'\.{re.escape(class_name)}\{{[^}}]+\}}'
            new_class_css = f'.{class_name}{{border:none !important; padding:5pt;}}'
            html_content = re.sub(old_class_pattern, new_class_css, html_content)
            removed_red_borders.append(class_name)
        
        if removed_red_borders:
            print(f"🎨 Убраны встроенные старые рамки #e2001a: {', '.join(removed_red_borders)}")
        # 3. НАХОДИМ И ИСПРАВЛЯЕМ ТАБЛИЦЫ С ФИКСИРОВАННЫМИ ВЫСОТАМИ СТРОК
        # Ищем tr с классами, имеющими большие высоты
        tr_pattern = r'<tr\s+class="([^"]*)"[^>]*>'
        tr_matches = re.findall(tr_pattern, html_content)
        
        fixed_rows = []
        for tr_class in set(tr_matches):  # Убираем дубли
            # Проверяем, есть ли у этого класса большая высота в CSS
            css_pattern = rf'\.{re.escape(tr_class)}\{{[^}}]*height:\s*([0-9]+(?:\.[0-9]+)?)pt[^}}]*\}}'
            css_match = re.search(css_pattern, html_content)
            if css_match:
                height_value = float(css_match.group(1))
                if height_value > 300:  # Строки таблиц больше 300pt = проблема
                    old_css = css_match.group(0)
                    new_css = f'.{tr_class}{{height:auto;}}'
                    html_content = html_content.replace(old_css, new_css)
                    fixed_rows.append(f"{tr_class}({height_value}pt)")
        
        if fixed_rows:
            print(f"📋 Исправлены высоты строк таблиц: {', '.join(fixed_rows)}")
        
        if not fixed_heights and not removed_red_borders and not fixed_rows:
            print("✅ Проблемных элементов не найдено")
        
        return html_content
    
    # Применяем универсальный анализатор ТОЛЬКО для contratto и carta
    if template_name != 'garanzia':
        html = analyze_and_fix_problematic_elements(html)
    else:
        print("🚫 Для garanzia пропускаем универсальный анализатор - сохраняем исходный HTML")
    
    # ТЕСТИРУЕМ ОЧИСТКУ ПО ЧАСТЯМ - ШАГ 4: ОТКЛЮЧАЕМ ВСЮ АГРЕССИВНУЮ ОЧИСТКУ
    
    if template_name != 'garanzia':
        print("🗑️ Удалены: блок изображений между разделами")
        print("📄 Разрывы страниц разрешены (кроме carta)")
        print("🤖 ПРИМЕНЕН: Универсальный анализатор проблемных элементов")
    else:
        print("🚫 Для garanzia все модификации отключены - используется исходный HTML")
    
    # ГЕНЕРИРУЕМ СЕТКУ 25x35 ДЛЯ ПОЗИЦИОНИРОВАНИЯ
    def generate_grid():
        """Генерирует HTML сетку 25x35 с нумерацией для A4"""
        grid_html = '<div class="grid-overlay">\n'
        
        # Размеры страницы A4 в миллиметрах
        page_width_mm = 210  # A4 ширина
        page_height_mm = 297  # A4 высота
        
        cell_width_mm = page_width_mm / 25  # 8.4mm на ячейку
        cell_height_mm = page_height_mm / 35  # 8.49mm на ячейку
        
        cell_number = 1
        
        for row in range(35):
            for col in range(25):
                x_mm = col * cell_width_mm
                y_mm = row * cell_height_mm
                
                grid_html += f'''    <div class="grid-cell" style="
                    left: {x_mm:.1f}mm; 
                    top: {y_mm:.1f}mm; 
                    width: {cell_width_mm:.1f}mm; 
                    height: {cell_height_mm:.1f}mm;">
                    {cell_number}
                </div>\n'''
                
                cell_number += 1
        
        grid_html += '</div>\n'
        return grid_html
    
    
    # Добавляем сетку в body (для contratto, carta и approvazione)
    if template_name in ['contratto', 'carta', 'approvazione']:
        grid_overlay = generate_grid()
        if template_name in ('contratto',):
            html = html.replace('<body class="c22 doc-content">', f'<body class="c22 doc-content">\n{grid_overlay}')
        elif template_name in ['carta', 'approvazione']:
            # Для carta и approvazione ищем правильный body тег
            html = html.replace('<body class="c9 doc-content">', f'<body class="c9 doc-content">\n{grid_overlay}')
        print("🔢 Добавлена сетка позиционирования 25x35")
        print("📋 Изображения будут добавлены через ReportLab поверх PDF")
    elif template_name == 'garanzia':
        print("🚫 Для garanzia НЕ добавляем сетку - сохраняем чистый HTML")
        print("📋 Изображения будут добавлены ТОЛЬКО через ReportLab поверх PDF")
    else:
        print("📋 Простой PDF без сетки и изображений")
    
    # НЕ СОХРАНЯЕМ исправленный HTML - не нужен
    
    print(f"✅ HTML обработан в памяти (файл не сохраняется)")
    print("🔧 Рамка зафиксирована через @page - будет на каждой странице!")
    
    return html


def main():
    """Функция для тестирования PDF конструктора"""
    import sys
    
    # Определяем какой шаблон обрабатывать
    template = sys.argv[1] if len(sys.argv) > 1 else 'contratto'
    
    print(f"🧪 Тестируем PDF конструктор для {template} через API...")
    
    # Тестовые данные
    test_data = {
        'name': 'Mario Rossi',
        'amount': 15000.0,
        'tan': 7.86,
        'taeg': 8.30, 
        'duration': 36,
        'payment': monthly_payment(15000.0, 36, 7.86)
    }
    
    try:
        if template in ('contratto',):
            buf = generate_contratto_pdf(test_data)
            filename = f'test_contratto.pdf'
        elif template == 'garanzia':
            buf = generate_garanzia_pdf(test_data['name'])
            filename = f'test_garanzia.pdf'
        elif template == 'carta':
            buf = generate_carta_pdf(test_data)
            filename = f'test_carta.pdf'
        elif template == 'approvazione':
            buf = generate_approvazione_pdf(test_data)
            filename = f'test_approvazione.pdf'
        else:
            print(f"❌ Неизвестный тип документа: {template}")
            return
        
        # Сохраняем тестовый PDF
        with open(filename, 'wb') as f:
            f.write(buf.read())
            
        print(f"✅ PDF создан через API! Файл сохранен как {filename}")
        print(f"📊 Данные: {test_data}")
        
    except Exception as e:
        print(f"❌ Ошибка тестирования API: {e}")


if __name__ == '__main__':
    main()
