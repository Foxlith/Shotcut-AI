# Análisis de medios para la IA (`shotcut-analysis`)

`shotcut-analysis` es el segundo servidor MCP de Shotcut AI. Con él la IA **ve y oye el material antes de editar**: sabe qué hay en cada archivo, dónde están los cortes de escena, cómo suena, qué se dice y dónde caen los beats de la música. Se usa junto al servidor `shotcut-ai`, que es el que edita el proyecto (ver [ai-mcp.md](ai-mcp.md)).

- **Todo en tu equipo:** usa los programas que ya vienen con Shotcut AI (`ffmpeg`, `ffprobe` y `whisper-cli`, en `bin\`). Nada sale del equipo. Solo los modelos de Whisper se descargan una vez.
- **Sin instalar nada más:** es un script de Python (`share\shotcut\mcp\shotcut_analysis.py`) que solo usa la biblioteca estándar. Necesita **Python 3.8 o posterior**, igual que el puente.
- **No hace falta tener Shotcut AI abierto** para analizar; sí para editar con `shotcut-ai`.

## Conectar tu IA

La forma más rápida: *Settings > AI Agent (MCP) > Copy MCP Configuration*. La configuración copiada ya incluye los dos servidores (`shotcut-ai` y `shotcut-analysis`) con las rutas de tu instalación.

A mano, con la ruta de tu carpeta de Shotcut AI:

**Claude Code** (en una terminal):

```
claude mcp add --scope user shotcut-analysis python "C:\ruta\a\Shotcut-AI\share\shotcut\mcp\shotcut_analysis.py"
```

**OpenCode** (`opencode.json`, dentro de `"mcp"`):

```json
"shotcut-analysis": {
  "type": "local",
  "command": ["python", "C:\\ruta\\a\\Shotcut-AI\\share\\shotcut\\mcp\\shotcut_analysis.py"],
  "enabled": true
}
```

**Claude Desktop** (`claude_desktop_config.json`) y **Antigravity** (`mcp_config.json`), dentro de `"mcpServers"`:

```json
"shotcut-analysis": {
  "command": "python",
  "args": ["C:\\ruta\\a\\Shotcut-AI\\share\\shotcut\\mcp\\shotcut_analysis.py"]
}
```

Después de cambiar la configuración, reinicia el cliente.

## Modelos de Whisper (voz a texto)

`transcribe` usa whisper.cpp con un modelo de Whisper. Hay dos formas de conseguir uno:

- Pídeselo a la IA: *«descarga el modelo base»*. Llamará a `download_model`.
- O en Shotcut AI: *Subtitles > Speech to Text*, que usa los mismos modelos y la misma carpeta (`%LOCALAPPDATA%\Meltytech\Shotcut\extensions\whispermodel`).

| Modelo | Tamaño | Para qué |
|---|---|---|
| **base** | 148 MB | Buen punto de partida; rápido. |
| **small-q5_1** | 190 MB | Más preciso en español; recomendado para entrevistas. |
| **tiny-q5_1** | 32 MB | Pruebas rápidas; menos preciso. |
| **medium-q5_0**, **large-v3-q5_0** | 539 MB, 1080 MB | Máxima precisión; lento sin GPU. |

Si no se indica modelo, `transcribe` usa el elegido en *Speech to Text* o el mejor descargado (hasta `small`). Con una GPU compatible con Vulkan (NVIDIA, AMD o Intel) whisper.cpp va más rápido; si la GPU falla, repite sin ella.

## Herramientas

| Herramienta | Qué hace |
|---|---|
| `check_setup` | Dónde están ffmpeg, ffprobe, whisper-cli, los modelos y la caché; qué modelos se pueden descargar y qué trabajos siguen en marcha. |
| `probe_media` | Datos técnicos de un archivo: tipo (vídeo, audio, imagen), duración, tamaño, fps, códecs, rotación y pistas de audio. |
| `describe_clip` | Resumen compacto para elegir tomas: datos técnicos, escenas, volumen, silencios, tempo de la música y, si ya está o se pide, la voz. |
| `detect_scenes` | Cortes de un vídeo (tiempo y fuerza de 0 a 1) y las escenas entre ellos. |
| `contact_sheet` | Una sola imagen con varios fotogramas del vídeo y su tiempo encima: la forma barata de «ver» un clip. |
| `analyze_audio` | Volumen integrado (LUFS), rango, pico real, silencios y, en música, el tempo y los beats para cortar al ritmo. |
| `transcribe` | La voz con tiempos: frases y, si se pide, cada palabra con su inicio y fin. Escribe también un archivo SRT. |
| `analyze_folder` | Índice de una carpeta de material: tipo, duración y (por defecto) escenas, volumen y tempo de cada archivo. |
| `download_model` | Descarga un modelo de Whisper a la carpeta que usa Shotcut AI. |
| `get_jobs` | Estado y progreso de los trabajos largos y, para uno, su resultado. |
| `cancel_job` | Detiene un trabajo en marcha. |

## Cómo trabaja

- **Tiempos:** en segundos desde el inicio del archivo. Son los mismos que los puntos de entrada y salida (`in`/`out`) de un clip en Shotcut AI, así que un corte de escena en 4,4 s se usa directamente para recortar el clip.
- **Trabajos largos:** transcribir o analizar carpetas puede tardar. Cada llamada espera hasta `wait` segundos (20 por defecto). Si no ha terminado, responde con un id de trabajo (`j3`…). La IA puede llamar a la misma herramienta más tarde o a `get_jobs`.
- **Caché:** cada análisis se guarda por archivo (ruta, tamaño y fecha) en `%LOCALAPPDATA%\Meltytech\Shotcut\analysis`. Repetir una pregunta es instantáneo, y si el archivo cambia se analiza de nuevo.
- **Respuestas cortas:** las palabras se envían solo con `words: true` y como listas `[inicio, fin, texto, probabilidad]`. Con `start`/`end` se pide un tramo de la transcripción, los silencios o los beats.
- **Errores útiles:** un argumento mal escrito, un archivo que no existe o un modelo que falta devuelven un mensaje que la IA puede leer para corregirse.

### Ejemplos de peticiones

- «Analiza la carpeta `C:\Videos\viaje` y dime qué tomas tengo.»
- «Enséñame una hoja de miniaturas de `playa.mp4`, una por escena.»
- «Transcribe la entrevista y quita los silencios de más de 0,7 segundos.»
- «¿A qué tempo va `musica.mp3`? Pon los cortes en los beats.»

## Precisión y límites

- **Escenas:** detecta cortes secos. Los fundidos largos pueden no aparecer; bajando `threshold` (por ejemplo a 0.2) aparecen cortes más suaves.
- **Tempo y beats:** de 60 a 200 BPM, en los primeros 10 minutos. En ritmos muy rápidos (más de ~165 BPM) puede dar la mitad (los beats caen entonces uno sí y uno no, pero siguen alineados).
- **Transcripción:** la calidad depende del modelo. Los tiempos por palabra son aproximados (±0,1–0,2 s); para cortar entre palabras conviene dejar un pequeño margen.
- **Hoja de miniaturas:** si ffmpeg no encuentra fuentes, las imágenes llegan sin el tiempo encima; los tiempos siguen en la respuesta.

## Variables de entorno (opcional)

- `SHOTCUT_FFMPEG`, `SHOTCUT_FFPROBE`, `SHOTCUT_WHISPER`: otros programas.
- `SHOTCUT_WHISPER_MODEL`: un modelo concreto (archivo `.bin`).
- `SHOTCUT_WHISPER_MODELS`: otra carpeta de modelos.
- `SHOTCUT_ANALYSIS_CACHE`: otra carpeta de caché.

## Problemas comunes

- **«ffmpeg was not found»:** usa el script de la carpeta de Shotcut AI (`share\shotcut\mcp\`); busca los programas en `bin\` a su lado. Pide a la IA `check_setup` para ver qué encuentra.
- **«whisper-cli was not found»:** necesitas el zip de Shotcut AI de la Entrega 1 o posterior (trae `bin\whisper-cli.exe`).
- **«No Whisper model is installed»:** descarga uno (ver arriba).
- **La transcripción va lenta:** usa un modelo más pequeño (`base`) o una GPU con Vulkan.

## Pruebas

- `tests/test_phase9_ai_analysis_verification.py` (en `python tests/run_e2e_tests.py --fast`): el servidor de extremo a extremo con ffmpeg, ffprobe y whisper-cli simulados (`tests/media/fake_*.py`), el tempo con audio generado en la prueba y los arreglos de Shotcut AI.
- `tests/live_analysis_smoke.py`: con los programas de verdad y medios de contenido conocido (`tests/media/make_samples.py`). Comprueba cortes con un margen de 2 fotogramas, silencios de 0,1 s, tempo de 2 BPM y volumen de 1 dB. El build de Windows lo ejecuta con el zip, un modelo descargado por el propio servidor y la muestra de voz de whisper.cpp.
- `scripts/sc.py --analysis call <herramienta> nombre=valor…`: probar a mano desde una terminal.
