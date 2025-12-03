import os
import tempfile
import zipfile
import gradio as gr
from pathlib import Path
import shutil

# Импортируем функции из вашего оригинального кода (их нужно немного адаптировать)
from music_mixer_logic import (
    get_all_samples,
    classify_samples,
    create_multilayer_composition,
    TARGET_BPM,
    CURRENT_KEY,
    EXPERIMENTAL_MODE,
    SAMPLES_DIR
)

# Создаем временную директорию для загрузок пользователя
UPLOAD_DIR = Path(tempfile.mkdtemp())

def process_uploaded_files(files):
    """Обрабатываем загруженные файлы: распаковываем zip или копируем аудиофайлы"""
    samples_dir = UPLOAD_DIR / "user_samples"
    samples_dir.mkdir(exist_ok=True)
    
    # Очищаем предыдущие загрузки
    for item in samples_dir.iterdir():
        if item.is_file():
            item.unlink()
        elif item.is_dir():
            shutil.rmtree(item)
    
    for file in files:
        file_path = Path(file.name)
        
        # Если это zip-архив - распаковываем
        if file_path.suffix.lower() == '.zip':
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(samples_dir)
        else:
            # Иначе копируем аудиофайл
            shutil.copy(file_path, samples_dir / file_path.name)
    
    return str(samples_dir)

def generate_mix(num_layers, target_bpm, current_key, use_experimental, progress=gr.Progress()):
    """Основная функция генерации микса"""
    try:
        progress(0.1, desc="📦 Загрузка семплов...")
        
        # Используем демо-семплы или загруженные пользователем
        if hasattr(generate_mix, 'user_samples_dir') and generate_mix.user_samples_dir:
            samples_dir = generate_mix.user_samples_dir
        else:
            samples_dir = "demo_samples"  # Папка с демо-семплами
        
        # Получаем все семплы
        samples = get_all_samples(samples_dir)
        if not samples:
            return None, "❌ Не найдено аудиофайлов. Загрузите семплы."
        
        progress(0.3, desc="🔍 Анализ семплов...")
        
        # Классифицируем семплы
        categories = classify_samples(samples)
        
        progress(0.6, desc="🎵 Создание микса...")
        
        # Создаем композицию
        layers, composition_info = create_multilayer_composition(
            categories, num_layers, target_bpm, current_key
        )
        
        if not layers:
            return None, "❌ Не удалось создать микс. Попробуйте другие настройки."
        
        progress(0.8, desc="💾 Сохранение результата...")
        
        # Сохраняем микс во временный файл
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            mix_path = tmp_file.name
            # Здесь должен быть код из вашей функции save_current_mix(),
            # который создает и сохраняет аудиофайл
            
            # Временная заглушка - создаем пустой файл
            import wave
            with wave.open(mix_path, 'wb') as wav_file:
                wav_file.setnchannels(2)
                wav_file.setsampwidth(2)
                wav_file.setframerate(44100)
                wav_file.writeframes(b'')
        
        # Формируем описание микса
        description = f"""
        🎶 **Готовый микс!**
        
        **Параметры:**
        • Слоев: {num_layers}
        • BPM: {target_bpm}
        • Ключ: {current_key}
        • Режим: {'Экспериментальный' if use_experimental else 'Стандартный'}
        
        **Состав:**
        """
        
        for layer in composition_info.get('layers', []):
            description += f"\n• {layer['category']}: {Path(layer['sample']).name}"
        
        progress(1.0, desc="✅ Готово!")
        
        return mix_path, description
        
    except Exception as e:
        return None, f"❌ Ошибка: {str(e)}"

def handle_file_upload(files):
    """Обработчик загрузки файлов"""
    if files:
        samples_dir = process_uploaded_files(files)
        generate_mix.user_samples_dir = samples_dir
        return f"✅ Загружено {len(files)} файлов. Теперь можно генерировать микс!"
    return "❌ Файлы не загружены."

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
            
            # Кнопка загрузки
            upload_btn = gr.Button("📁 Загрузить и использовать семплы", variant="secondary")
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
        examples=[[2, 128, "8A", False], [4, 140, "5B", True]],
        inputs=[num_layers, target_bpm, current_key, use_experimental],
        outputs=[audio_output, text_output],
        fn=generate_mix,
        cache_examples=False  # Отключаем кэширование для работы с файлами
    )

# Важный момент: нужно создать папку с демо-семплами
DEMO_SAMPLES_DIR = Path("demo_samples")
DEMO_SAMPLES_DIR.mkdir(exist_ok=True)

# Копируем туда несколько тестовых семплов (если они есть)
# Или создаем минимальный набор

if __name__ == "__main__":
    # Запускаем с публичным доступом
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False)