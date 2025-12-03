import os
import tempfile
import zipfile
import gradio as gr
from pathlib import Path
import shutil

# Импортируем класс MusicMixer вместо отдельных функций
from music_mixer_logic import MusicMixer

# Глобальные переменные для хранения текущего миксера и директории с семплами
current_mixer = None
current_samples_dir = "demo_samples"  # Папка с демо-семплами по умолчанию

def process_uploaded_files(files):
    """Обрабатываем загруженные файлы"""
    global current_samples_dir
    
    temp_dir = Path(tempfile.mkdtemp(prefix="user_samples_"))
    
    for file in files:
        file_path = Path(file.name)
        
        # Если это zip-архив - распаковываем
        if file_path.suffix.lower() == '.zip':
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
        else:
            # Иначе копируем аудиофайл
            shutil.copy(file_path, temp_dir / file_path.name)
    
    current_samples_dir = str(temp_dir)
    return f"✅ Загружено {len(files)} файлов в {temp_dir.name}"

def init_mixer(target_bpm, current_key, use_experimental):
    """Инициализация или обновление миксера"""
    global current_mixer, current_samples_dir
    
    try:
        # Проверяем, существует ли директория с семплами
        if not os.path.exists(current_samples_dir):
            # Пытаемся использовать демо-семплы
            demo_dir = "demo_samples"
            if os.path.exists(demo_dir):
                current_samples_dir = demo_dir
            else:
                return None, "❌ Директория с семплами не найдена"
        
        # Создаем или обновляем миксер
        current_mixer = MusicMixer(
            samples_dir=current_samples_dir,
            target_bpm=target_bpm,
            current_key=current_key,
            experimental_mode=use_experimental
        )
        
        # Проверяем, есть ли семплы
        samples = current_mixer.get_all_samples()
        if not samples:
            return None, f"❌ В директории {current_samples_dir} не найдено аудиофайлов"
        
        return current_mixer, f"✅ Миксер готов. Найдено {len(samples)} семплов"
        
    except Exception as e:
        return None, f"❌ Ошибка инициализации: {str(e)}"

def generate_mix(num_layers, target_bpm, current_key, use_experimental, progress=gr.Progress()):
    """Основная функция генерации микса"""
    global current_mixer
    
    try:
        progress(0.1, desc="🎵 Инициализация миксера...")
        
        # Инициализируем или обновляем миксер
        mixer, status = init_mixer(target_bpm, current_key, use_experimental)
        if mixer is None:
            return None, status
        
        current_mixer = mixer
        
        progress(0.4, desc="🎵 Создание композиции...")
        
        # Генерируем микс
        audio_path, description, composition_info = current_mixer.generate_complete_mix(
            num_layers=num_layers
        )
        
        progress(0.8, desc="💾 Сохранение результата...")
        
        if os.path.exists(audio_path):
            progress(1.0, desc="✅ Готово!")
            return audio_path, description
        else:
            return None, "❌ Ошибка: аудиофайл не создан"
        
    except Exception as e:
        return None, f"❌ Ошибка при создании микса: {str(e)}"

def handle_file_upload(files):
    """Обработчик загрузки файлов"""
    if files:
        return process_uploaded_files(files)
    return "❌ Файлы не загружены"

# Создаем демо-директорию если её нет
DEMO_SAMPLES_DIR = Path("demo_samples")
DEMO_SAMPLES_DIR.mkdir(exist_ok=True)

# Создаем несколько тестовых файлов если директория пуста
if not any(DEMO_SAMPLES_DIR.iterdir()):
    import warnings
    warnings.warn("Демо-директория пуста. Добавьте несколько .wav файлов в папку demo_samples/")

# Создаем интерфейс Gradio
with gr.Blocks(theme=gr.themes.Soft(), title="AI Музыкальный Миксер") as demo:
    gr.Markdown("# 🎵 AI Музыкальный Миксер")
    gr.Markdown("Загрузите семплы или используйте демо-версию для генерации уникальных музыкальных миксов.")
    
    with gr.Row():
        with gr.Column(scale=1):
            # Секция загрузки файлов
            gr.Markdown("## 📤 Загрузите свои семплы")
            file_upload = gr.File(
                label="Выберите аудиофайлы или ZIP-архив",
                file_types=[".wav", ".mp3", ".flac", ".aiff", ".zip"],
                file_count="multiple"
            )
            upload_status = gr.Textbox(label="Статус загрузки", interactive=False)
            
            upload_btn = gr.Button("📁 Загрузить семплы", variant="secondary")
            upload_btn.click(
                handle_file_upload,
                inputs=[file_upload],
                outputs=[upload_status]
            )
            
            gr.Markdown("---")
            
            # Настройки микса
            gr.Markdown("## ⚙️ Настройки микса")
            
            num_layers = gr.Slider(
                minimum=1, maximum=8, value=3, step=1,
                label="Количество слоев"
            )
            
            target_bpm = gr.Slider(
                minimum=80, maximum=180, value=128, step=1,
                label="Целевой BPM"
            )
            
            current_key = gr.Dropdown(
                choices=[f"{i}{j}" for i in range(1, 13) for j in ['A', 'B']],
                value="8A",
                label="Музыкальный ключ (Camelot)"
            )
            
            use_experimental = gr.Checkbox(
                label="Экспериментальный режим", value=False
            )
            
            generate_btn = gr.Button("🎵 Сгенерировать микс", variant="primary", size="lg")
        
        with gr.Column(scale=2):
            # Секция результата
            gr.Markdown("## 🎧 Результат")
            audio_output = gr.Audio(label="Сгенерированный микс", type="filepath")
            text_output = gr.Markdown("Здесь появится описание микса...")
    
    # Обработчик генерации
    generate_btn.click(
        generate_mix,
        inputs=[num_layers, target_bpm, current_key, use_experimental],
        outputs=[audio_output, text_output]
    )
    
    # Демо-пример
    gr.Markdown("---")
    gr.Markdown("### 🚀 Быстрый старт")
    gr.Examples(
        examples=[[3, 128, "8A", False], [4, 140, "5B", True]],
        inputs=[num_layers, target_bpm, current_key, use_experimental],
        outputs=[audio_output, text_output],
        fn=generate_mix,
        label="Попробуйте готовые пресеты:",
        cache_examples=False
    )

if __name__ == "__main__":
    # Проверяем демо-директорию
    demo_files = list(DEMO_SAMPLES_DIR.glob("*.wav")) + list(DEMO_SAMPLES_DIR.glob("*.mp3"))
    if demo_files:
        print(f"✅ Найдено {len(demo_files)} демо-файлов")
    else:
        print("⚠️  Демо-директория пуста. Пользователям нужно загрузить свои семплы.")
    
    # Запускаем приложение
    demo.launch(
        server_name="0.0.0.0", 
        server_port=7860, 
        share=False,
        debug=True  # Включить debug для диагностики
    )