import streamlit as st
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import os
import tempfile
import base64
from datetime import datetime
import zipfile
import io
import subprocess
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
import time

# ==================== КОНФИГУРАЦИЯ TESSERACT И ОПТИМИЗАЦИЯ ====================
TESSERACT_CONFIG_FAST = '--oem 1 --psm 3 -c tessedit_do_invert=0'

def setup_tesseract():
    possible_paths = [
        '/usr/bin/tesseract',
        '/usr/local/bin/tesseract',
        '/bin/tesseract',
        '/nix/store/*/bin/tesseract',
    ]

    for path in possible_paths:
        if os.path.exists(path):
            return path

    try:
        result = subprocess.run(['which', 'tesseract'],
                                capture_output=True,
                                text=True)
        if result.returncode == 0:
            return result.stdout.strip()
    except:
        pass

    return None

tesseract_path = setup_tesseract()
if tesseract_path:
    pytesseract.pytesseract.tesseract_cmd = tesseract_path
    st.session_state.tesseract_available = True
    st.session_state.tesseract_path = tesseract_path
else:
    st.session_state.tesseract_available = False
    st.session_state.tesseract_path = None

st.set_page_config(page_title="📄 PDF OCR Extractor", 
                   page_icon="https://cdn1.ozone.ru/s3/common-image-storage/bx/char_cat-box-four_m.png",
                   layout="wide",
                   initial_sidebar_state="expanded")

# ==================== СТИЛИ OZON ====================
def apply_ozon_style():
    st.markdown("""
    <style>
        .main, .stApp {
            background-color: #1A1A1A !important;
            color: white !important;
        }
        .main-header {
            font-size: 2.5rem;
            background: linear-gradient(135deg, #005BFF, #FF6B00);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            text-align: center;
            margin-bottom: 1rem;
            font-weight: 800;
        }
        .main-subtitle {
            text-align: center;
            color: #B3B3B3;
            margin-bottom: 2rem;
        }
        .section-header {
            background:  url('https://brandlab.ozon.ru/images/tild6365-6165-4064-b161-626431393363__pattern_bg-1.png');
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            color: white;
            padding: clamp(1rem, 2.5vw, 1.5rem);
            border-radius: clamp(8px, 2vw, 16px);
            margin-bottom: 1rem;
            text-align: center;
            position: relative;
            min-height: 80px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .ozon-card {
            background: #2D2D2D;
            padding: 1.2rem;
            border-radius: 8px;
            border: 1px solid #404040;
            margin: 0.8rem 0;
            color: white;
            transition: all 0.3s ease;
        }
        .ozon-card:hover {
            box-shadow: 0 4px 20px rgba(0, 91, 255, 0.2);
            transform: translateY(-2px);
        }
        .card-header {
            display: flex;
            align-items: center;
            margin-bottom: 0.8rem;
            gap: 0.5rem;
        }
        .card-icon {
            font-size: 1.3em;
            color: #005BFF;
        }
        .card-title {
            margin: 0;
            color: #005BFF;
            font-weight: 600;
        }
        .ozon-status {
            background: #2D2D2D;
            padding: 0.8rem;
            border-radius: 6px;
            margin: 0.5rem 0;
            border-left: 4px solid #005BFF;
            color: white;
        }
        .ozon-status strong {
            color: #005BFF;
        }
        .stButton button {
            background: linear-gradient(135deg, #005BFF, #004ACC);
            color: white;
            border: none;
            padding: 0.6rem 1.2rem;
            border-radius: 8px;
            font-weight: 600;
            transition: all 0.3s ease;
            width: 100%;
        }
        .stButton button:hover {
            background: linear-gradient(135deg, #004ACC, #005BFF);
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(0, 91, 255, 0.2);
        }
        .ozon-sidebar-header {
             background:  url('https://brandlab.ozon.ru/images/tild6365-6165-4064-b161-626431393363__pattern_bg-1.png');
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            color: white;
            padding: clamp(1rem, 2.5vw, 1.5rem);
            border-radius: clamp(8px, 2vw, 16px);
            margin-bottom: 1rem;
            text-align: center;
            position: relative;
            min-height: 80px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .sidebar-title {
            color: white;
            margin: 0;
            font-size: 1.8rem !important;
            font-weight: 900;
        }
        .site-icon {
            width: 60px;
            height: 60px;
            margin-bottom: 10px;
            border-radius: 50%;
            object-fit: cover;
            border: 3px solid white;
        }
        .uploaded-file-info {
            background: #2D2D2D;
            padding: 0.8rem;
            border-radius: 8px;
            margin: 0.5rem 0;
            border-left: 4px solid #005BFF;
        }
        .step-number {
            background: white;           
            color: #005BFF;              
            border-radius: 50%;
            width: 30px;
            height: 30px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            margin-right: 10px;
            font-weight: 700; 
        }
        .stats-card {
            background: linear-gradient(135deg, #005BFF20, #FF6B0020);
            border-radius: 10px;
            padding: 15px;
            margin: 10px 0;
            border: 1px solid #404040;
        }
        .tool-link {
            display: block;
            background: #2D2D2D;
            color: white;
            padding: 12px 15px;
            margin: 8px 0;
            border-radius: 8px;
            text-decoration: none;
            border-left: 4px solid #005BFF;
            transition: all 0.3s ease;
        }
        .tool-link:hover {
            background: #3D3D3D;
            transform: translateX(5px);
            text-decoration: none;
            color: white;
        }
        .footer {
            text-align: center;
            color: #B3B3B3;
            font-size: 0.9rem;
            margin-top: 2rem;
            padding-top: 1rem;
            border-top: 1px solid #404040;
        }
        .heart {
            color: #FF6B00;
            animation: heartbeat 1.5s infinite;
        }
        @keyframes heartbeat {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.1); }
        }
        .status-box {
            padding: 15px;
            border-radius: 10px;
            margin: 15px 0;
        }
        .status-success {
            background: rgba(0, 91, 255, 0.2);
            border: 2px solid #005BFF;
        }
        .status-error {
            background: rgba(255, 107, 0, 0.2);
            border: 2px solid #FF6B00;
        }
        .speed-badge {
            display: inline-block;
            background: linear-gradient(135deg, #00FF88, #00CC66);
            color: white;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 0.8rem;
            font-weight: bold;
            margin-left: 5px;
        }
        .warning-note {
            background: rgba(255, 193, 7, 0.1);
            border: 1px solid #FFC107;
            border-radius: 8px;
            padding: 10px;
            margin: 10px 0;
            color: #FFC107;
            font-size: 0.9rem;
        }
        .main-content-wrapper {
            display: flex;
            flex-direction: column;
            gap: 2rem;
        }
        .main-columns {
            display: flex;
            gap: 2rem;
        }
        .main-columns > div {
            flex: 1;
        }
        @media (max-width: 768px) {
            .main-columns {
                flex-direction: column;
            }
        }
    </style>
    """,
                unsafe_allow_html=True)

apply_ozon_style()

# ==================== ИНИЦИАЛИЗАЦИЯ ====================
if 'processing' not in st.session_state:
    st.session_state.processing = False
if 'result_text' not in st.session_state:
    st.session_state.result_text = ""
if 'total_pages' not in st.session_state:
    st.session_state.total_pages = 0
if 'processed_files' not in st.session_state:
    st.session_state.processed_files = 0
if 'total_pages_processed' not in st.session_state:
    st.session_state.total_pages_processed = 0
if 'processing_time' not in st.session_state:
    st.session_state.processing_time = 0

# ==================== ОПТИМИЗИРОВАННЫЕ ФУНКЦИИ OCR ====================

def process_single_page(args):
    page_num, page, dpi, lang, use_fast_mode = args

    try:
        pix = page.get_pixmap(dpi=dpi)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        if use_fast_mode:
            img = img.convert('L')

        config = TESSERACT_CONFIG_FAST if use_fast_mode else '--oem 1 --psm 3'
        text = pytesseract.image_to_string(img, lang=lang, config=config)
        return page_num, text, None

    except Exception as e:
        return page_num, "", str(e)

def extract_text_from_pdf_parallel(pdf_path, dpi=200, lang="rus+eng", use_fast_mode=True, progress_callback=None):
    extracted_text = ""
    page_texts = []

    try:
        pdf = fitz.open(pdf_path)
        total_pages = len(pdf)
        st.session_state.total_pages = total_pages

        tasks = []
        for page_num in range(total_pages):
            page = pdf.load_page(page_num)
            tasks.append((page_num, page, dpi, lang, use_fast_mode))

        page_texts = [""] * total_pages
        extracted_parts = [""] * total_pages

        max_workers = min(3, total_pages)

        completed = 0
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_page = {executor.submit(process_single_page, task): task[0] for task in tasks}

            for future in concurrent.futures.as_completed(future_to_page):
                page_num, text, error = future.result()

                if error:
                    page_texts[page_num] = ""
                    extracted_parts[page_num] = f"\n{'='*50}\n📄 СТРАНИЦА {page_num + 1} - ОШИБКА\n{'='*50}\n\n{error}\n"
                else:
                    page_texts[page_num] = text
                    extracted_parts[page_num] = f"\n{'='*50}\n📄 СТРАНИЦА {page_num + 1}\n{'='*50}\n\n{text}\n"

                completed += 1
                if progress_callback:
                    progress_callback(completed, total_pages)

        pdf.close()
        extracted_text = "".join(extracted_parts)
        return extracted_text, page_texts

    except Exception as e:
        return f"❌ Ошибка при обработке PDF: {e}", []

def extract_text_from_pdf_optimized(pdf_path, dpi=200, lang="rus+eng", use_parallel=True, use_fast_mode=True, progress_bar=None, status_text=None):
    start_time = time.time()

    if use_parallel and st.session_state.total_pages > 1:
        def progress_callback(completed, total):
            if progress_bar:
                progress_bar.progress(completed / total)
            if status_text:
                status_text.text(f"📄 Обработка страницы {completed} из {total}")

        result = extract_text_from_pdf_parallel(pdf_path, dpi, lang, use_fast_mode, progress_callback)
    else:
        extracted_text = ""
        page_texts = []

        try:
            pdf = fitz.open(pdf_path)
            total_pages = len(pdf)
            st.session_state.total_pages = total_pages

            for page_num in range(total_pages):
                if progress_bar:
                    progress_bar.progress((page_num + 1) / total_pages)
                if status_text:
                    status_text.text(f"📄 Обработка страницы {page_num + 1} из {total_pages}")

                try:
                    page = pdf.load_page(page_num)
                    pix = page.get_pixmap(dpi=dpi)
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

                    if use_fast_mode:
                        img = img.convert('L')
                        config = TESSERACT_CONFIG_FAST
                    else:
                        config = '--oem 1 --psm 3'

                    text = pytesseract.image_to_string(img, lang=lang, config=config)
                    page_texts.append(text)
                    extracted_text += f"\n{'='*50}\n📄 СТРАНИЦА {page_num + 1}\n{'='*50}\n\n{text}\n"

                except Exception as page_error:
                    page_texts.append("")
                    extracted_text += f"\n{'='*50}\n📄 СТРАНИЦА {page_num + 1} - ОШИБКА\n{'='*50}\n\n{page_error}\n"
                    continue

            pdf.close()
            result = (extracted_text, page_texts)

        except Exception as e:
            result = (f"❌ Ошибка при обработке PDF: {e}", [])

    st.session_state.processing_time = time.time() - start_time
    return result

def create_zip_archive(page_texts):
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for i, text in enumerate(page_texts):
            filename = f"страница_{i+1:03d}.txt"
            zip_file.writestr(filename, text)
    zip_buffer.seek(0)
    return zip_buffer.getvalue()

# ==================== ОСНОВНОЙ ИНТЕРФЕЙС ====================
def main():

    # Яндекс.Метрика
    metrika_code = """
    <script>
        (function(m,e,t,r,i,k,a){m[i]=m[i]||function(){(m[i].a=m[i].a||[]).push(arguments)};
        m[i].l=1*new Date();
        k=e.createElement(t),a=e.getElementsByTagName(t)[0],k.async=1,k.src=r,a.parentNode.insertBefore(k,a)})
        (window, document, "script", "https://mc.yandex.ru/metrika/tag.js", "ym");

        ym(105749221, "init", {
            clickmap:true,
            trackLinks:true,
            accurateTrackBounce:true,
            webvisor:true
        });
        ym(105749221,'reachGoal','extraction_started')
        ym(105749221,'reachGoal','extraction_success')
        ym(105749221,'reachGoal','download_clicked')
    </script>
    <noscript><div><img src="https://mc.yandex.ru/watch/105749221" style="position:absolute; left:-9999px;" alt="" /></div></noscript>
    """
    st.markdown(metrika_code, unsafe_allow_html=True)

    with st.sidebar:
        st.markdown('''
        <div class="ozon-sidebar-header">
            <h1 class="sidebar-title">Информация</h1>

        </div>
        ''',
                    unsafe_allow_html=True)

        st.markdown('''
        <div class="ozon-card">
            <div class="card-header">
                <span class="card-icon">⚡</span>
                <h3 class="card-title">Настройки скорости</h3>
            </div>
        </div>
        ''',
                    unsafe_allow_html=True)

        speed_mode = st.selectbox(
            "Режим обработки",
            [
                "⚡ Максимальная скорость (200 DPI)",
                "⚖️ Сбалансированный (250 DPI)", 
                "🎯 Максимальная точность (300 DPI)"
            ],
            index=0,
            help="Быстрый режим работает в 2-3 раза быстрее"
        )

        if "Максимальная скорость" in speed_mode:
            dpi = 200
            use_fast_mode = True
            speed_badge = "<span class='speed-badge'>3x быстрее</span>"
        elif "Сбалансированный" in speed_mode:
            dpi = 250
            use_fast_mode = True
            speed_badge = "<span class='speed-badge'>2x быстрее</span>"
        else:
            dpi = 300
            use_fast_mode = False
            speed_badge = ""

        use_parallel = st.checkbox(
            "Параллельная обработка", 
            value=True,
            help="Ускоряет обработку в 2-4 раза (рекомендуется для 2+ страниц)"
        )

        language = st.selectbox("Язык распознавания",
                                ["rus+eng", "rus", "eng", "fra", "deu", "spa"],
                                index=0)

        st.markdown(f'''
        <div class="ozon-card">
            <div class="card-header">
                <span class="card-icon">📊</span>
                <h3 class="card-title">Статистика</h3>
            </div>
            <div class="ozon-status">
                <strong>Обработано файлов:</strong> {st.session_state.processed_files}<br>
                <strong>Всего страниц:</strong> {st.session_state.total_pages_processed}<br>
                <strong>Последняя обработка:</strong> {st.session_state.processing_time:.1f}с
            </div>
        </div>
        ''',
                    unsafe_allow_html=True)

        with st.expander("⚠️ Ограничения бесплатного хостинга"):
            st.markdown("""
            **На бесплатном хостинге:**
            
             • Ограниченная вычислительная мощность
            
             • Нет гарантии стабильной скорости

             • Обработка может быть медленнее локальной

            **Рекомендации:**
            
             • Используйте режим "Максимальная скорость"
            
             • Обрабатывайте документы по частям
            
             • Для больших файлов используйте локальную версию
            """)

        st.markdown('''
        <div class="ozon-card">
            <div class="card-header">
                <span class="card-icon">🔗</span>
                <h3 class="card-title">Другие инструменты</h3>
            </div>
            <div style="margin-top: 10px;">
                <a href="https://extractor-sku-by-mroshchupkin.streamlit.app/" target="_blank" class="tool-link">
                    🛍️ <strong>Extractor SKU</strong>
                </a>
                <a href="https://brand-detected-by-mroshchupkin.streamlit.app/" target="_blank" class="tool-link">
                    🏷️ <strong>Brand Detector</strong>
                </a>
            </div>
        </div>
        ''',
                    unsafe_allow_html=True)

        st.markdown('''
        <div class="footer">
            With <span class="heart">❤️</span> by mroshchupkin and DS<br>
            <small>Powered by Tesseract OCR</small>
        </div>
        ''',
                    unsafe_allow_html=True)

    return dpi, language, use_parallel, use_fast_mode, speed_badge

# ==================== ОСНОВНАЯ ЛОГИКА ====================
def run_app():
    dpi, language, use_parallel, use_fast_mode, speed_badge = main()

    # Заголовок сайта
    st.markdown('<div style="display: flex; align-items: center; justify-content: center; gap: 12px;"><img src="https://cdn1.ozone.ru/s3/common-image-storage/bx/char_cat-box-four_m.png" alt="Коробка Ozon" style="height: 80px; width: 80px; object-fit: contain;"><h1 style="color: #005BFF; font-size: 2.5rem; text-align: center; font-weight: 800; margin: 0; line-height: 1;">Text Extractor PDF OCR </h1></div>', unsafe_allow_html=True)

    st.markdown(
        '<p class="main-subtitle">Извлечение текста из отсканированных PDF файлов</p>',
        unsafe_allow_html=True)

    speed_info = ""
    if dpi == 200:
        speed_info = "⚡ **Режим:** Максимальная скорость (200 DPI)"
    elif dpi == 250:
        speed_info = "⚖️ **Режим:** Сбалансированный (250 DPI)"
    else:
        speed_info = "🎯 **Режим:** Максимальная точность (300 DPI)"

    if use_parallel:
        speed_info += " | **Параллельная обработка:** включена"

    st.info(speed_info)

    if not st.session_state.tesseract_available:
        st.error("""
        ## ⚠️ Tesseract не установлен!

        **Для установки в Replit:**

        1. Откройте **Shell** (терминал) в Replit
        2. Выполните команду:
        ```bash
        apt-get update
        apt-get install -y tesseract-ocr tesseract-ocr-rus tesseract-ocr-eng
        ```
        3. Перезапустите приложение (нажмите Stop → Run)
        """)
        st.stop()

    # Две колонки для блоков "Загрузка" и "Результаты"
    col1, col2 = st.columns(2)

    with col1:
        st.markdown('''
        <div class="section-header">
            <span class="step-number">1</span> Загрузка PDF файла
        </div>
        ''',
                    unsafe_allow_html=True)

        uploaded_file = st.file_uploader("Выберите PDF файл", type=['pdf'])

        if uploaded_file:
            # Определяем реальное количество страниц
            real_page_count = 0
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                    tmp.write(uploaded_file.getvalue())
                    tmp_path = tmp.name

                pdf = fitz.open(tmp_path)
                real_page_count = len(pdf)
                pdf.close()
                os.unlink(tmp_path)

            except:
                # Если не получилось определить, используем приблизительную оценку
                real_page_count = max(1, uploaded_file.size // 100000)  # Более точная оценка

            # Время обработки на хостинге (дольше чем локально)
            estimated_time = real_page_count * (5 if dpi == 200 else 7 if dpi == 250 else 10)

            file_info = f"""
            **📎 Файл:** {uploaded_file.name}<br>
            **📊 Размер:** {uploaded_file.size/1024:.1f} KB<br>
            **📄 Количество страниц:** {real_page_count}
            """

            st.markdown(f'<div class="uploaded-file-info">{file_info}</div>',
                        unsafe_allow_html=True)

            # Предупреждение о времени
            st.markdown(f'''
            <div class="warning-note">
                ⚠️ **На бесплатном хостинге:**<br>
                • Примерное время обработки: ~{estimated_time} секунд<br>
                • Фактическое время может отличаться из-за ограничений хостинга<br>
                • Для больших файлов рекомендуется локальная обработка
            </div>
            ''', unsafe_allow_html=True)

            if st.button("🚀 Начать обработку OCR", use_container_width=True):
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                    tmp.write(uploaded_file.getvalue())
                    pdf_path = tmp.name

                try:
                    progress_bar = st.progress(0)
                    status_text = st.empty()

                    status_text.text("🔄 Начинаю обработку на хостинге...")

                    extracted_text, page_texts = extract_text_from_pdf_optimized(
                        pdf_path,
                        dpi=dpi,
                        lang=language,
                        use_parallel=use_parallel,
                        use_fast_mode=use_fast_mode,
                        progress_bar=progress_bar,
                        status_text=status_text)

                    st.session_state.processed_files += 1
                    st.session_state.total_pages_processed += len(page_texts)
                    st.session_state.result_text = extracted_text
                    st.session_state.page_texts = page_texts

                    progress_bar.empty()

                    status_text.text(f"✅ Обработка завершена за {st.session_state.processing_time:.1f} секунд")

                    if st.session_state.processing_time > 30:
                        st.warning(f"""
                        ⏱️ **Длительная обработка:** {st.session_state.processing_time:.1f} секунд

                        Это связано с ограничениями бесплатного хостинга. 
                        Локально такая обработка заняла бы примерно {st.session_state.processing_time/3:.1f} секунд.
                        """)
                    else:
                        st.success(
                            f"✅ Распознано {len(page_texts)} страниц за {st.session_state.processing_time:.1f} секунд"
                        )

                except Exception as e:
                    st.error(f"❌ Ошибка: {e}")
                finally:
                    if os.path.exists(pdf_path):
                        os.unlink(pdf_path)

    with col2:
        st.markdown('''
        <div class="section-header">
            <span class="step-number">2</span> Результаты
        </div>
        ''',
                    unsafe_allow_html=True)

        if st.session_state.result_text:
            total_chars = len(st.session_state.result_text)
            total_words = len(st.session_state.result_text.split())

            st.markdown(f'''
            <div class="stats-card">
                <h4>📊 Статистика обработки:</h4>
                <strong>📄 Страниц:</strong> {st.session_state.total_pages}<br>
                <strong>⏱️ Время:</strong> {st.session_state.processing_time:.1f} сек<br>
                <strong>🔤 Символов:</strong> {total_chars:,}<br>
                <strong>📝 Слов:</strong> {total_words:,}<br>
                <strong>⚡ DPI:</strong> {dpi}<br>
                <strong>🌐 Язык:</strong> {language}
            </div>
            ''',
                        unsafe_allow_html=True)

            st.markdown('''
            <div class="section-header">
                <span class="step-number">3</span> Скачать результат
            </div>
            ''',
                        unsafe_allow_html=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_name = uploaded_file.name.replace('.pdf', '')

            full_filename = f"{base_name}_текст_{timestamp}.txt"
            b64_full = base64.b64encode(
                st.session_state.result_text.encode()).decode()
            st.markdown(f'''
            <a href="data:text/plain;base64,{b64_full}" download="{full_filename}" style="text-decoration: none;">
                <button style="background: linear-gradient(135deg, #005BFF, #004ACC); color: white; border: none; padding: 10px; border-radius: 8px; width: 100%; margin: 5px 0; cursor: pointer;">
                    📥 Скачать полный текст
                </button>
            </a>
            ''',
                        unsafe_allow_html=True)

            if hasattr(st.session_state, 'page_texts'):
                zip_data = create_zip_archive(st.session_state.page_texts)
                zip_filename = f"{base_name}_страницы_{timestamp}.zip"
                b64_zip = base64.b64encode(zip_data).decode()
                st.markdown(f'''
                <a href="data:application/zip;base64,{b64_zip}" download="{zip_filename}" style="text-decoration: none;">
                    <button style="background: linear-gradient(135deg, #FF6B00, #FF8C00); color: white; border: none; padding: 10px; border-radius: 8px; width: 100%; margin: 5px 0; cursor: pointer;">
                        📦 Скачать по страницам (ZIP)
                    </button>
                </a>
                ''',
                            unsafe_allow_html=True)

            with st.expander("👁️ Предпросмотр текста"):
                preview = st.session_state.result_text[:2000] + "..." if len(
                    st.session_state.result_text
                ) > 2000 else st.session_state.result_text
                st.text_area("",
                             preview,
                             height=300,
                             label_visibility="collapsed")

if __name__ == "__main__":
    run_app()