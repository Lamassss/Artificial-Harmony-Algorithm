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
user_files_uploaded = False

def process_uploaded_files(files):
    """Обрабатываем загруженные файлы"""
    global current_samples_dir, user_files_uploaded
    
    try:
        # Создаем временную директорию для пользовательских файлов
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
        user_files_uploaded = True
        
        # Проверяем, есть ли аудиофайлы
        audio_files = list(temp_dir.glob("*.wav")) + list(temp_dir.glob("*.mp3")) + \
                     list(temp_dir.glob("*.flac")) + list(temp_dir.glob("*.aiff"))
        
        if audio_files:
            return f"✅ Успешно загружено {file_count} файлов. Найдено {len(audio_files)} аудиофайлов."
        else:
            user_files_uploaded = False
            return "⚠️ Файлы загружены, но не найдено аудиофайлов (.wav, .mp3, .flac, .aiff)"
            
    except Exception as e:
        user_files_uploaded = False
        return f"❌ Ошибка при обработке файлов: {str(e)}"

def init_mixer(target_bpm, current_key, use_experimental):
    """Инициализация миксера"""
    global current_mixer, current_samples_dir, user_files_uploaded
    
    if not user_files_uploaded or current_samples_dir is None:
        return None, "❌ Сначала загрузите аудиофайлы в разделе 'Загрузка семплов'"
    
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
            return None, f"❌ Не найдено аудиофайлов в загруженных файлах"
        
        return current_mixer, f"✅ Миксер готов. Проанализировано {len(samples)} семплов"
        
    except Exception as e:
        return None, f"❌ Ошибка инициализации: {str(e)}"

def generate_mix(num_layers, target_bpm, current_key, use_experimental, progress=gr.Progress()):
    """Основная функция генерации микса"""
    global current_mixer
    
    if not user_files_uploaded:
        return None, "❌ Сначала загрузите аудиофайлы в разделе 'Загрузка семплов'"
    
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

def reset_upload():
    """Сброс состояния загрузки"""
    global user_files_uploaded, current_samples_dir, current_mixer
    user_files_uploaded = False
    current_samples_dir = None
    current_mixer = None
    return "🔄 Состояние сброшено. Загрузите новые файлы."

# Создаем интерфейс Gradio (без параметра theme, который вызывает ошибку)
with gr.Blocks(title="AI Музыкальный Миксер") as demo:
    gr.Markdown("# 🎵 AI Музыкальный Миксер")
    gr.Markdown("""
    ### Загрузите свои аудиосемплы, чтобы сгенерировать уникальный музыкальный микс!
    
    **Поддерживаемые форматы:** .wav, .mp3, .flac, .aiff, .zip (архив с семплами)
    
    **Как использовать:**
    1. Загрузите файлы ниже
    2. Настройте параметры микса
    3. Нажмите "Сгенерировать микс"
    """)
    
    with gr.Row():
        with gr.Column(scale=1):
            # Секция загрузки файлов (обязательная)
            gr.Markdown("## 📤 Шаг 1: Загрузка семплов")
            gr.Markdown("Загрузите один или несколько аудиофайлов или ZIP-архив")
            
            file_upload = gr.File(
                label="Выберите файлы",
                file_types=[".wav", ".mp3", ".flac", ".aiff", ".zip"],
                file_count="multiple",
                interactive=True
            )
            
            upload_status = gr.Textbox(
                label="Статус загрузки",
                value="❌ Файлы не загружены",
                interactive=False
            )
            
            with gr.Row():
                upload_btn = gr.Button("📁 Загрузить и проанализировать", variant="primary")
                reset_btn = gr.Button("🔄 Сбросить", variant="secondary")
            
            upload_btn.click(
                process_uploaded_files,
                inputs=[file_upload],
                outputs=[upload_status]
            )
            
            reset_btn.click(
                reset_upload,
                inputs=[],
                outputs=[upload_status]
            )
            
            gr.Markdown("---")
            
            # Настройки микса (доступны только после загрузки)
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
            
            # Информация о ключах
            with gr.Accordion("ℹ️ Что такое Camelot ключи?", open=False):
                gr.Markdown("""
                **Camelot Wheel System** - система для гармоничного микширования:
                - **A** - мажорные тональности (1A-12A)
                - **B** - минорные тональности (1B-12B)
                - **Совместимые ключи**: текущий, параллельный и соседние на "колесе"
                """)
            
            generate_btn = gr.Button(
                "🎵 Сгенерировать микс",
                variant="primary",
                size="lg",
                interactive=True
            )
        
        with gr.Column(scale=2):
            # Секция результата
            gr.Markdown("## 🎧 Шаг 3: Результат")
            
            status_info = gr.Markdown(
                "### Статус: Ожидание загрузки файлов\n"
                "1. 📤 Загрузите семплы\n"
                "2. ⚙️ Настройте параметры\n"
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
    
    # Обработчик генерации
    generate_btn.click(
        generate_mix,
        inputs=[num_layers, target_bpm, current_key, use_experimental],
        outputs=[audio_output, text_output]
    )
    
    # Обновляем статус при загрузке файлов
    def update_status():
        global user_files_uploaded
        if user_files_uploaded:
            return "### Статус: ✅ Файлы загружены\nГотово к генерации микса!"
        else:
            return "### Статус: ❌ Ожидание загрузки файлов\nЗагрузите семплы, чтобы начать"
    
    upload_btn.click(
        update_status,
        inputs=[],
        outputs=[status_info]
    )
    
    # Примеры настроек (без использования примеров файлов)
    gr.Markdown("---")
    gr.Markdown("### 🎛️ Примеры настроек")
    
    with gr.Row():
        with gr.Column():
            gr.Markdown("**Танцевальный микс**")
            gr.Examples(
                examples=[[3, 128, "8A", False]],
                inputs=[num_layers, target_bpm, current_key, use_experimental],
                label=""
            )
        
        with gr.Column():
            gr.Markdown("**Экспериментальный микс**")
            gr.Examples(
                examples=[[4, 140, "5B", True]],
                inputs=[num_layers, target_bpm, current_key, use_experimental],
                label=""
            )
        
        with gr.Column():
            gr.Markdown("**Спокойный микс**")
            gr.Examples(
                examples=[[2, 100, "3A", False]],
                inputs=[num_layers, target_bpm, current_key, use_experimental],
                label=""
            )

if __name__ == "__main__":
    # Запускаем приложение с подробным логированием
    demo.launch(
        server_name="0.0.0.0", 
        server_port=7860, 
        share=False,
        debug=True,
        show_error=True
    )