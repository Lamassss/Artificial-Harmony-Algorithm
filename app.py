import os
import tempfile
import zipfile
import gradio as gr
from pathlib import Path
import shutil

# Импортируем класс MusicMixer
from music_mixer_logic import MusicMixer

# Глобальные переменные
current_mixer = None
current_samples_dir = None
DEFAULT_SAMPLES_ZIP = "default_samples.zip"  # Предзагруженный архив

def extract_default_samples():
    """Распаковывает предзагруженный архив с семплами"""
    try:
        if os.path.exists(DEFAULT_SAMPLES_ZIP):
            temp_dir = Path(tempfile.mkdtemp(prefix="default_samples_"))
            with zipfile.ZipFile(DEFAULT_SAMPLES_ZIP, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            return str(temp_dir)
        else:
            # Если архива нет, создаем пустую директорию
            temp_dir = Path(tempfile.mkdtemp(prefix="empty_samples_"))
            return str(temp_dir)
    except Exception as e:
        print(f"Ошибка при распаковке архива: {e}")
        temp_dir = Path(tempfile.mkdtemp(prefix="error_samples_"))
        return str(temp_dir)

def process_uploaded_files(files, use_default_samples):
    """Обрабатываем загруженные файлы"""
    global current_samples_dir
    
    try:
        if use_default_samples:
            # Используем предзагруженные семплы
            current_samples_dir = extract_default_samples()
            
            # Проверяем, есть ли файлы в распакованном архиве
            default_dir = Path(current_samples_dir)
            audio_files = list(default_dir.rglob("*.wav")) + list(default_dir.rglob("*.mp3")) + \
                         list(default_dir.rglob("*.flac")) + list(default_dir.rglob("*.aiff"))
            
            if audio_files:
                return f"✅ Используются предзагруженные семплы. Найдено {len(audio_files)} аудиофайлов."
            else:
                return "⚠️ В предзагруженном архиве не найдено аудиофайлов. Загрузите свои файлы."
        else:
            # Пользователь загружает свои файлы
            if not files:
                return "❌ Файлы не загружены"
            
            temp_dir = Path(tempfile.mkdtemp(prefix="user_samples_"))
            file_count = 0
            
            for file in files:
                file_path = Path(file.name)
                
                # Если это zip-архив - распаковываем
                if file_path.suffix.lower() == '.zip':
                    with zipfile.ZipFile(file_path, 'r') as zip_ref:
                        zip_ref.extractall(temp_dir)
                        extracted = len(zip_ref.namelist())
                        file_count += extracted
                else:
                    # Иначе копируем аудиофайл
                    shutil.copy(file_path, temp_dir / file_path.name)
                    file_count += 1
            
            current_samples_dir = str(temp_dir)
            
            # Проверяем, есть ли аудиофайлы
            audio_files = list(temp_dir.rglob("*.wav")) + list(temp_dir.rglob("*.mp3")) + \
                         list(temp_dir.rglob("*.flac")) + list(temp_dir.rglob("*.aiff"))
            
            if audio_files:
                return f"✅ Загружено {file_count} файлов. Найдено {len(audio_files)} аудиофайлов."
            else:
                return "⚠️ Файлы загружены, но не найдено аудиофайлов (.wav, .mp3, .flac, .aiff)"
                
    except Exception as e:
        return f"❌ Ошибка при обработке файлов: {str(e)}"

def init_mixer(target_bpm, current_key, use_experimental):
    """Инициализация миксера"""
    global current_mixer, current_samples_dir
    
    if current_samples_dir is None:
        # Если ничего не выбрано, используем предзагруженные семплы
        current_samples_dir = extract_default_samples()
    
    try:
        # Проверяем, существует ли директория
        if not os.path.exists(current_samples_dir):
            return None, "❌ Директория с семплами не найдена"
        
        # Создаем миксер
        current_mixer = MusicMixer(
            samples_dir=current_samples_dir,
            target_bpm=target_bpm,
            current_key=current_key,
            experimental_mode=use_experimental
        )
        
        # Проверяем, есть ли семплы
        samples = current_mixer.get_all_samples()
        if not samples:
            return None, f"❌ Не найдено аудиофайлов. Попробуйте загрузить другие файлы."
        
        return current_mixer, f"✅ Миксер готов. Проанализировано {len(samples)} семплов"
        
    except Exception as e:
        return None, f"❌ Ошибка инициализации: {str(e)}"

def generate_mix(num_layers, target_bpm, current_key, use_experimental, progress=gr.Progress()):
    """Основная функция генерации микса"""
    global current_mixer
    
    try:
        progress(0.1, desc="🎵 Инициализация миксера...")
        
        # Инициализируем миксер
        mixer, status = init_mixer(target_bpm, current_key, use_experimental)
        if mixer is None:
            return None, status
        
        current_mixer = mixer
        
        progress(0.4, desc="🎵 Анализ семплов и создание композиции...")
        
        # Генерируем микс
        audio_path, description, composition_info = current_mixer.generate_complete_mix(
            num_layers=num_layers
        )
        
        progress(0.8, desc="💾 Сохранение результата...")
        
        if os.path.exists(audio_path):
            # Читаем файл для проверки
            file_size = os.path.getsize(audio_path)
            if file_size > 0:
                progress(1.0, desc="✅ Готово!")
                return audio_path, description
            else:
                return None, "❌ Ошибка: создан пустой аудиофайл"
        else:
            return None, "❌ Ошибка: аудиофайл не создан"
        
    except Exception as e:
        return None, f"❌ Ошибка при создании микса: {str(e)}"

def cleanup_temp_dirs():
    """Очистка временных директорий"""
    global current_mixer
    if current_mixer:
        current_mixer.cleanup()

# Создаем интерфейс Gradio
with gr.Blocks(title="AI Музыкальный Миксер") as demo:
    gr.Markdown("# 🎵 AI Музыкальный Миксер")
    gr.Markdown("""
    ### Создавайте уникальные музыкальные миксы из семплов!
    
    **Выберите источник семплов:**
    - 🎁 **Использовать предзагруженные семплы** (быстрый старт)
    - 📤 **Загрузить свои семплы** (полный контроль)
    """)
    
    with gr.Row():
        with gr.Column(scale=1):
            # Выбор источника семплов
            gr.Markdown("## 📁 Шаг 1: Выберите источник семплов")
            
            use_default_samples = gr.Checkbox(
                label="🎁 Использовать предзагруженные семплы",
                value=True,
                interactive=True
            )
            
            with gr.Accordion("📤 Загрузить свои семплы (опционально)", open=False):
                file_upload = gr.File(
                    label="Выберите аудиофайлы или ZIP-архив",
                    file_types=[".wav", ".mp3", ".flac", ".aiff", ".zip"],
                    file_count="multiple",
                    interactive=True
                )
            
            upload_status = gr.Textbox(
                label="Статус семплов",
                value="🎁 Готовы предзагруженные семплы. Нажмите 'Загрузить семплы'",
                interactive=False
            )
            
            load_samples_btn = gr.Button("📁 Загрузить семплы", variant="primary")
            
            load_samples_btn.click(
                process_uploaded_files,
                inputs=[file_upload, use_default_samples],
                outputs=[upload_status]
            )
            
            gr.Markdown("---")
            
            # Настройки микса
            gr.Markdown("## ⚙️ Шаг 2: Настройка микса")
            
            num_layers = gr.Slider(
                minimum=1, maximum=8, value=3, step=1,
                label="Количество слоев",
                interactive=True
            )
            
            target_bpm = gr.Slider(
                minimum=80, maximum=180, value=128, step=1,
                label="Целевой BPM (темп)",
                interactive=True
            )
            
            current_key = gr.Dropdown(
                choices=[f"{i}{j}" for i in range(1, 13) for j in ['A', 'B']],
                value="8A",
                label="Музыкальный ключ (Camelot система)",
                interactive=True
            )
            
            use_experimental = gr.Checkbox(
                label="Экспериментальный режим (более необычные сочетания)", 
                value=False,
                interactive=True
            )
            
            generate_btn = gr.Button(
                "🎵 Сгенерировать микс",
                variant="primary",
                size="lg"
            )
        
        with gr.Column(scale=2):
            # Секция результата
            gr.Markdown("## 🎧 Результат")
            
            status_info = gr.Markdown(
                "### Готов к работе!\n"
                "1. 📁 Выберите источник семплов\n"
                "2. ⚙️ Настройте параметры микса\n"
                "3. 🎵 Нажмите 'Сгенерировать микс'"
            )
            
            audio_output = gr.Audio(
                label="Сгенерированный микс",
                type="filepath",
                interactive=False
            )
            
            text_output = gr.Markdown(
                "Здесь появится информация о составе микса..."
            )
            
            # Информация о процессе
            with gr.Accordion("📊 Информация о семплах", open=False):
                sample_info = gr.Markdown("Информация появится после загрузки семплов")
            
            def update_sample_info():
                """Обновляет информацию о загруженных семплах"""
                global current_samples_dir
                if current_samples_dir and os.path.exists(current_samples_dir):
                    dir_path = Path(current_samples_dir)
                    wav_files = list(dir_path.rglob("*.wav"))
                    mp3_files = list(dir_path.rglob("*.mp3"))
                    flac_files = list(dir_path.rglob("*.flac"))
                    aiff_files = list(dir_path.rglob("*.aiff"))
                    
                    total = len(wav_files) + len(mp3_files) + len(flac_files) + len(aiff_files)
                    
                    info_text = f"""
                    **📊 Статистика семплов:**
                    - Всего аудиофайлов: {total}
                    - WAV файлов: {len(wav_files)}
                    - MP3 файлов: {len(mp3_files)}
                    - FLAC файлов: {len(flac_files)}
                    - AIFF файлов: {len(aiff_files)}
                    
                    **📂 Источник:** {dir_path.name}
                    """
                    return info_text
                return "Информация о семплах недоступна"
            
            load_samples_btn.click(
                update_sample_info,
                inputs=[],
                outputs=[sample_info]
            )
    
    # Обработчик генерации
    generate_btn.click(
        generate_mix,
        inputs=[num_layers, target_bpm, current_key, use_experimental],
        outputs=[audio_output, text_output]
    )
    
    # Примеры настроек
    gr.Markdown("---")
    gr.Markdown("### 🚀 Быстрый старт: готовые пресеты")
    
    with gr.Row():
        with gr.Column():
            gr.Markdown("**🎵 Танцевальный микс**")
            gr.Examples(
                examples=[[3, 128, "8A", False]],
                inputs=[num_layers, target_bpm, current_key, use_experimental],
                label=""
            )
        
        with gr.Column():
            gr.Markdown("**🧪 Экспериментальный**")
            gr.Examples(
                examples=[[4, 140, "5B", True]],
                inputs=[num_layers, target_bpm, current_key, use_experimental],
                label=""
            )
        
        with gr.Column():
            gr.Markdown("**😌 Спокойный микс**")
            gr.Examples(
                examples=[[2, 100, "3A", False]],
                inputs=[num_layers, target_bpm, current_key, use_experimental],
                label=""
            )

if __name__ == "__main__":
    # Сначала проверяем наличие предзагруженного архива
    if os.path.exists(DEFAULT_SAMPLES_ZIP):
        print(f"✅ Найден предзагруженный архив: {DEFAULT_SAMPLES_ZIP}")
        print(f"   Размер: {os.path.getsize(DEFAULT_SAMPLES_ZIP) / (1024*1024):.1f} MB")
    else:
        print(f"⚠️  Предзагруженный архив не найден: {DEFAULT_SAMPLES_ZIP}")
        print("   Пользователям нужно будет загрузить свои семплы")
    
    # Запускаем приложение
    demo.launch(
        server_name="0.0.0.0", 
        server_port=7860, 
        share=False,
        debug=False
    )