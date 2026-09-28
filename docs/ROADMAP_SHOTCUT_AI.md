# Shotcut AI — Hoja de ruta hacia el editor de vídeo por IA

> **Cómo usar este documento:** es la guía de trabajo del proyecto. Cada sesión con la IA empieza así:
> *"Lee `ROADMAP_SHOTCUT_AI.md` y continúa con la siguiente tarea pendiente."*
> La IA hace **una tarea a la vez**, la prueba, marca su casilla `[x]`, anota lo aprendido en el
> [Registro de avances](#10-registro-de-avances) y se detiene para que el usuario revise.
>
> **Decisión de Fox (28/09/2026):** el trabajo avanza **por entregas con PR** (ver
> [Entregas](#entregas)): cada entrega agrupa varias tareas, se prueba en la app y en el CI y se
> revisa en un PR en `github.com/Foxlith/Shotcut-AI`.

---

## 1. Objetivo

Que una persona pueda **describir en texto el vídeo que quiere** (idea, guion, escenas, estilo,
duración, formato) y que una IA (Claude u otra compatible con MCP) lo **edite como un editor
profesional** dentro de Shotcut AI y entregue un vídeo terminado.

### Ejemplos de lo que debe funcionar al final

- *"Con estos 12 clips de mi viaje, haz un reel vertical de 30 s, ritmo rápido, cortes al compás de
  la música y un título al inicio."*
- *"De esta entrevista de 40 minutos, haz un resumen de 2 minutos con lo más interesante, con
  subtítulos grandes, y quita silencios y muletillas."*
- *"Tutorial: esta grabación de pantalla más la cámara en una esquina, subtítulos, zoom en las partes
  importantes y exporta a YouTube 1080p."*
- *"Guion: Escena 1: amanecer en la ciudad (usa clip_03). Escena 2: presentación del producto con el
  texto 'Nuevo modelo X'…"*. La IA sigue el guion escena por escena.

### Principios

1. **La IA debe ver y oír el material** antes de editar. No se edita a ciegas.
2. **Primero el plan y después la ejecución.** La IA propone un plan revisable y luego lo aplica.
3. **Todo se puede deshacer.** Cada cambio es un paso con nombre `AI: ...` y el proyecto nunca se
   pierde.
4. **La IA revisa su trabajo.** Renderiza un borrador, lo mira y corrige antes de entregar.
5. **Es abierto a cualquier IA.** Todo se expone por MCP con formatos documentados (JSON), sin
   depender de un modelo concreto.
6. **Se mide.** Un conjunto fijo de encargos de prueba indica si cada cambio mejora el resultado.

---

## 2. Estado actual (verificado el 27/09/2026)

| Elemento | Estado |
|---|---|
| Shotcut AI | Versión 26.9.28, en `C:\Users\Fox\Desktop\nuevo\Shotcut-AI-windows-x64 (1)\` |
| Servidor MCP interno | `http://127.0.0.1:9999/mcp`. Se activa en *Settings > AI Agent (MCP)* |
| Puente stdio | `share\shotcut\mcp\shotcut_mcp_bridge.py` (Python). Variables `SHOTCUT_AI_URL` y `SHOTCUT_AI_TIMEOUT` |
| Registro en Claude Code | ✅ Servidor `shotcut-ai` en `~/.claude.json` (alcance de usuario) |
| Prueba de conexión | ✅ 33 herramientas visibles. Se añadieron 3 vídeos a la lista de medios y a la pista V1 |
| Binarios incluidos | `bin\ffmpeg.exe`, `bin\ffprobe.exe`, `bin\melt.exe`, `bin\shotcut.exe` y, desde la Entrega 1, `bin\whisper-cli.exe` |
| Código fuente | ✅ [github.com/Foxlith/Shotcut-AI](https://github.com/Foxlith/Shotcut-AI): *fork* de Shotcut (C++/Qt 6 + MLT 7). Compilación: [build-windows.md](build-windows.md) (workflow *Build Windows (Shotcut AI)* o MSYS2 en local) |
| Servidor de análisis | ✅ Entrega 1: `share\shotcut\mcp\shotcut_analysis.py` (`shotcut-analysis`), ver [ai-analysis.md](ai-analysis.md) |

### Herramientas MCP existentes (33)

- **Consulta:** `get_state`, `get_timeline`, `get_playlist`, `get_frame`, `list_actions`,
  `list_filters`, `get_clip_filters`
- **Reproducción:** `play`, `pause`, `seek`, `step`
- **Historial:** `undo`, `redo`, `run_action`
- **Medios y proyecto:** `open_media`, `add_to_playlist`, `open_project`, `save_project`
- **Edición de clips:** `append_clip`, `insert_clip`, `overwrite_clip`, `split_clip`,
  `remove_clip`, `move_clip`, `trim_clip`, `set_fade`, `select_clips`
- **Pistas:** `add_track`, `set_track`
- **Filtros:** `add_filter`, `set_filter_param`, `set_filter_enabled`, `remove_filter`

### Problemas detectados en las pruebas

- [x] **Respuestas muy largas.** Cada clip repite su ruta absoluta varias veces (`resource`), lo que
      gasta mucho contexto en proyectos grandes.
      → Entrega 1: los datos van una sola vez (antes iban también en `structuredContent`), cada archivo
      tiene un id (`"media": "m1"`) con su ruta una vez en la tabla `media`, `get_timeline` acepta
      `track` y `detail`, y los clips solo llevan nombre si difiere del archivo.
- [x] **Perfil incoherente.** `get_state` devolvió `"PAL 4:3 DV or DVD"` con 1920x1080 a 25 fps en
      un proyecto vacío.
      → Entrega 1: MLT conservaba la descripción del perfil por defecto mientras el modo automático
      adapta el tamaño. Ahora la descripción sale de los valores (`"1920x1080, 25 fps, 16:9"`), con
      `video_mode` y `adapts_to_first_clip`.
- [x] **Rutas en Windows.** La app de Claude usa carpetas virtualizadas (`AppData\Roaming` redirigido a
      `AppData\Local\Packages\...\LocalCache`). Shotcut necesita la ruta real.
      → Entrega 1: Shotcut AI busca la copia privada del paquete (primero los de Claude) al abrir,
      añadir o insertar archivos; si no está, el error explica la causa.
- [x] **Dos procesos `shotcut.exe`** al abrir la aplicación. Hay que confirmar si es normal (por
      ejemplo, un proceso auxiliar) o si hay doble instancia.
      → Es normal: el proceso padre es el *watchdog* de arranque de Shotcut (`src/main.cpp`), que abre
      la app como hijo y la relanza con otro backend gráfico si se cuelga al arrancar.

---

## 3. Arquitectura propuesta

```
 Usuario: "quiero un reel de 30 s…"  (+ guion / escenas / estilo)
                     │
                     ▼
 ┌─────────────────────────────────────────────┐
 │  IA (Claude u otra)  + Skill "editor-video"  │  ← reglas de edición y estilos
 └─────────────────────────────────────────────┘
        │ MCP                          │ MCP
        ▼                              ▼
 ┌──────────────────────┐    ┌────────────────────────────┐
 │ shotcut-ai (existe)  │    │ shotcut-analysis (nuevo)   │
 │ edición en vivo      │    │ Python: ffmpeg, Whisper,   │
 │ + apply_edit_plan    │    │ detección de escenas, audio│
 │ + render/export      │    │ hojas de miniaturas        │
 └──────────────────────┘    └────────────────────────────┘
        │                              │
        ▼                              ▼
   Shotcut AI (MLT)            Caché de análisis (.json por archivo)
```

**Decisión de diseño recomendada:** el **análisis** de medios va en un **servidor MCP aparte en
Python** (`shotcut-analysis`), así no hace falta recompilar Shotcut para iterar. La **aplicación del
plan** y la **exportación** van dentro de Shotcut AI (en el código C++/Qt), o como alternativa en
Python generando un `.mlt` y abriéndolo con `open_project`. Esa decisión se toma en la Fase 2.

**Decisiones tomadas (28/09/2026):**
- `shotcut-analysis` usa **solo la biblioteca estándar de Python** y los programas del zip (`ffmpeg`,
  `ffprobe`, `whisper-cli`) en lugar de PySceneDetect, faster-whisper o librosa: no hay que instalar
  nada y funciona sin internet. Viene en el zip, junto al puente.
- La transcripción usa **whisper.cpp**, el mismo motor y los mismos modelos que *Subtitles > Speech to
  Text* de Shotcut. Añadirlo al zip recupera además esa función de Shotcut, que faltaba.
- **2.3 decidido:** el EditPlan se aplica **dentro de Shotcut AI (C++)**. Con `.mlt` + `open_project`
  se reemplazaría el proyecto y se perdería el historial de deshacer, y el plan debe deshacerse con un
  solo `undo`.
- Todo va en el repositorio `Foxlith/Shotcut-AI`: este roadmap en `docs/`, los servidores en
  `scripts/` y, más adelante, la Skill, los estilos y los evals en `ai/`.

---

## 4. Fases y tareas

> Cada tarea tiene **criterios de aceptación**. No se marca `[x]` hasta cumplirlos y probarlos
> contra Shotcut AI en ejecución.

### Fase 0 — Preparación del entorno

- [x] **0.1** Localizar el código fuente de Shotcut AI y documentar cómo compilarlo en Windows.
  - *Acepta si:* hay un comando documentado que produce un `shotcut.exe` funcional.
  - ✅ [build-windows.md](build-windows.md): el workflow de GitHub Actions o MSYS2 en local.
- [x] **0.2** Crear la carpeta de trabajo del proyecto (`shotcut-ai-tools/`) con git, un README y este
      roadmap dentro.
  - ✅ Decisión de Fox: dentro del repositorio `Shotcut-AI` (`docs/`, `scripts/`, `tests/media/`).
- [ ] **0.3** Crear una carpeta `muestras/` con medios de prueba reales y variados: entrevista con
      voz, clips de viaje, grabación de pantalla, música con ritmo claro.
  - *Acepta si:* hay al menos 10 archivos y cubren video, audio e imagen.
  - Parcial: `tests/media/make_samples.py` genera medios de contenido conocido para las pruebas
    automáticas. El material real lo aporta Fox en `muestras/` (fuera de git, ya en `.gitignore`).
- [x] **0.4** Script `sc.py` para llamar herramientas MCP desde la terminal (ya existe un prototipo)
      y guardarlo en el repositorio.
  - ✅ `scripts/sc.py` (Shotcut AI por HTTP o, con `--analysis`, el servidor de análisis).
- [x] **0.5** Arreglar los *Problemas detectados* de la sección 2 o registrar un issue para cada uno.
  - ✅ Los cuatro, en la Entrega 1.

### Fase 1 — Percepción: que la IA vea y oiga (servidor `shotcut-analysis`)

- [x] **1.1** Esqueleto del servidor MCP en Python (stdio) registrado en Claude Code.
  - ✅ `scripts/shotcut_analysis.py` (11 herramientas); *Copy MCP Configuration* lo registra en los 4
    clientes. Guía: [ai-analysis.md](ai-analysis.md).
- [x] **1.2** `probe_media(path)`: duración, resolución, fps, códecs, pistas de audio y rotación, con
      `ffprobe`.
- [x] **1.3** `detect_scenes(path)`: lista de cortes de escena con tiempos (PySceneDetect o `scdet`
      de ffmpeg).
  - *Acepta si:* sobre un vídeo de prueba con cortes conocidos, detecta al menos el 90 % con un error
    de ±2 fotogramas.
  - ✅ Puntuación de escena de ffmpeg. Encuentra el 100 % de los cortes, en el fotograma exacto
    (`tests/live_analysis_smoke.py`).
- [x] **1.4** `contact_sheet(path, n=12)`: una sola imagen con N fotogramas y su marca de tiempo. Es la
      forma barata de "ver" un clip.
  - ✅ También un fotograma por escena (`scenes: true`) o en tiempos concretos.
- [ ] **1.5** `transcribe(path, lang="es")`: transcripción con tiempos por palabra y por frase
      (faster-whisper).
  - *Acepta si:* una entrevista de 5 min se transcribe en menos de 2 min en esta PC y los tiempos
    cuadran al reproducirla en Shotcut.
  - Implementado con whisper.cpp (frases, palabras, SRT). Probado en el CI de Windows con un modelo
    real y la muestra de voz de whisper.cpp. **Falta medirlo en el PC de Fox** con una entrevista de
    5 min.
- [x] **1.6** `analyze_audio(path)`: silencios, volumen (LUFS), picos y **pulsos/beats** de la
      música (librosa o aubio).
  - ✅ ebur128 y silencedetect de ffmpeg, y un detector de tempo propio. En las pruebas acierta de 60 a
    160 BPM, con beats a ±10 ms; por encima de ~165 BPM puede dar la mitad.
- [x] **1.7** `describe_clip(path)`: un resumen combinado (escenas + miniaturas + transcripción +
      audio) en JSON compacto, **con caché** en `.analysis/<hash>.json` para no repetir el trabajo.
  - ✅ La caché va en `%LOCALAPPDATA%\Meltytech\Shotcut\analysis` en lugar de junto a los medios, así
    no ensucia tus carpetas y funciona con carpetas de solo lectura.
- [x] **1.8** `analyze_folder(path)`: analiza una carpeta completa y devuelve un índice del material.

### Entregas

Orden de trabajo acordado el 28/09/2026: las primitivas de acabado van antes que el EditPlan, que las
usa.

| Entrega | Tareas | Estado |
|---|---|---|
| **Entrega 1** | Fase 0 + Fase 1 (y los 4 problemas de la sección 2) | ✅ PR en revisión |
| Entrega 2 | 3.1 exportar (YouTube 1080p/4K y borrador), 3.2 transiciones, 3.3 títulos, 3.5 volumen y normalización, 3.9 marcadores | Pendiente |
| Entrega 3 | Fase 2: EditPlan v1, validador, `apply_edit_plan` (un *undo*), `export_edit_plan`, `dry_run` | Pendiente |
| Entrega 4 | Fase 4 + 3.4 subtítulos, 3.6 velocidad, 3.7 reencuadre (9:16), 3.8 color, *ducking* | Pendiente |
| Entrega 5 | Fase 5: brief, Skill `editor-video`, estilos, plugin de Claude Code; voz local (Piper) | Pendiente |
| Entrega 6 | Fase 6: encargos de prueba, *runner* y rúbrica | Pendiente |

### Fase 2 — Plan de edición (formato declarativo)

- [ ] **2.1** Definir el esquema **EditPlan v1** en JSON Schema (ver [sección 5](#5-borrador-del-formato-editplan-v1)).
- [ ] **2.2** Validador: comprueba que las rutas existen, que las entradas y salidas caben en la
      duración y que las pistas son coherentes. Devuelve errores claros que la IA pueda corregir.
- [ ] **2.3** Decidir dónde se aplica el plan: dentro de Shotcut (C++, nueva herramienta
      `apply_edit_plan`) o en Python (plan → `.mlt` → `open_project`). Documentar la decisión y el
      porqué.
- [ ] **2.4** Implementar `apply_edit_plan(plan)` como **un solo paso deshacible**.
  - *Acepta si:* un plan con 3 pistas, 10 clips, 2 textos y música se aplica, se ve bien en la línea
    de tiempo y un solo `undo` lo revierte.
- [ ] **2.5** `export_edit_plan()`: lee el proyecto actual y lo convierte en EditPlan (ida y vuelta).
- [ ] **2.6** Modo **simulación** (`dry_run: true`): muestra qué haría sin tocar el proyecto.

### Fase 3 — Herramientas de acabado profesional

- [ ] **3.1** **Exportar/renderizar** con perfiles: `youtube_1080p`, `youtube_4k`, `reel_9x16`,
      `borrador_rapido` (baja resolución). Debe informar del progreso y del archivo final.
- [ ] **3.2** **Transiciones** entre clips: fundido cruzado, barrido y corte seco, con duración.
- [ ] **3.3** **Textos y títulos** con estilo: fuente, tamaño, color, posición, fondo, animación de
      entrada y salida.
- [ ] **3.4** **Subtítulos** a partir de la transcripción (Fase 1.5), con estilos (clásico, "reel"
      con palabra resaltada).
- [ ] **3.5** **Audio:** volumen por clip y por pista, *ducking* (bajar la música cuando hay voz) y
      normalización a −14 LUFS para redes.
- [ ] **3.6** **Velocidad:** cámara lenta, acelerado y rampa de velocidad.
- [ ] **3.7** **Encuadre y reencuadre:** convertir 16:9 a 9:16 siguiendo al sujeto, zoom/*Ken Burns*,
      imagen dentro de imagen.
- [ ] **3.8** **Color:** LUTs y ajustes básicos (exposición, contraste, saturación, temperatura).
- [ ] **3.9** **Marcadores** en la línea de tiempo, para que la IA y el usuario anoten momentos.

### Fase 4 — Bucle de revisión: la IA verifica su trabajo

- [ ] **4.1** `render_preview(range?)`: borrador rápido en baja resolución de todo o de un tramo.
- [ ] **4.2** `review_timeline()`: hoja de miniaturas de la línea de tiempo con los puntos de corte
      marcados, más un informe de audio (silencios inesperados, saturación, niveles).
- [ ] **4.3** Lista de comprobación automática: sin huecos negros no deseados, sin clips
      superpuestos por error, textos dentro de la zona segura, duración objetivo cumplida y audio
      sin saturar.
- [ ] **4.4** Flujo en el Skill: *planificar → aplicar → previsualizar → revisar → corregir* (máximo
      N iteraciones) → entregar.

### Fase 5 — Del texto al vídeo: guion, escenas y estilos

- [ ] **5.1** Formato de **Brief** (lo que escribe el usuario): objetivo, público, duración, formato,
      tono, guion o escenas, material disponible y restricciones. Ver [sección 6](#6-borrador-del-formato-brief).
- [ ] **5.2** **Skill `editor-video`** para Claude Code (`SKILL.md`): cómo leer un brief, analizar el
      material, elegir tomas, construir el EditPlan, revisar y entregar. Incluye reglas de oficio
      (ver [sección 7](#7-reglas-de-oficio-para-el-skill)).
- [ ] **5.3** **Estilos** como archivos reutilizables (`estilos/*.json` + descripción): `reel_dinamico`,
      `vlog`, `tutorial`, `entrevista`, `trailer`, `corporativo`. Cada uno define ritmo, transiciones,
      tipografía, subtítulos y tratamiento de audio.
- [ ] **5.4** **Asignación de escenas a material:** a partir del guion, buscar en el índice (Fase 1.8)
      los clips que mejor encajan con cada escena, usando transcripción y descripciones visuales.
- [ ] **5.5** (Opcional) **Generación de recursos** cuando falte material: voz en off (TTS), música,
      imágenes o vídeo generados. Cada generador como un MCP aparte y sustituible.
- [ ] **5.6** Empaquetar todo como **plugin de Claude Code** (MCP + Skill + estilos) instalable con un
      comando.

### Fase 6 — Calidad y evaluación

- [ ] **6.1** Conjunto de **15–20 encargos de prueba** en `evals/` (brief + material + criterios de
      éxito).
- [ ] **6.2** Script que ejecuta los encargos y guarda los resultados (plan, render y tiempo).
- [ ] **6.3** Rúbrica de puntuación: cumple la duración, respeta el guion, cortes limpios, audio
      correcto, subtítulos sincronizados y estética del estilo.
- [ ] **6.4** Probar con otras IAs compatibles con MCP para confirmar que el sistema no depende de un
      solo modelo.

---

## 5. Borrador del formato EditPlan v1

```json
{
  "version": 1,
  "project": {
    "width": 1080, "height": 1920, "fps": 30,
    "target_duration": 30
  },
  "media": {
    "c1": { "path": "muestras/playa.mp4" },
    "c2": { "path": "muestras/atardecer.mp4" },
    "m1": { "path": "muestras/musica.mp3" }
  },
  "tracks": [
    {
      "id": "V1", "type": "video",
      "items": [
        { "media": "c1", "in": 3.2, "out": 6.0, "transition_in": { "type": "cut" } },
        { "media": "c2", "in": 10.0, "out": 13.5,
          "transition_in": { "type": "crossfade", "duration": 0.5 },
          "filters": [ { "id": "brightness", "params": { "level": 1.1 } } ] }
      ]
    },
    {
      "id": "T1", "type": "text",
      "items": [
        { "text": "Verano 2026", "start": 0.0, "end": 2.5,
          "style": "titulo_grande", "position": "center" }
      ]
    },
    {
      "id": "A1", "type": "audio",
      "items": [
        { "media": "m1", "in": 0, "out": 30, "volume_db": -6,
          "duck_under": "V1", "fade_in": 1.0, "fade_out": 2.0 }
      ]
    }
  ],
  "subtitles": { "source": "transcript", "style": "reel_palabra_resaltada" },
  "markers": [ { "time": 12.0, "note": "clímax: sincronizar con el beat" } ],
  "export": { "profile": "reel_9x16", "path": "salidas/reel_verano.mp4" }
}
```

**Reglas:** los tiempos están en segundos; `in` y `out` son relativos al archivo de origen. Los
items de vídeo y audio se colocan en secuencia salvo que tengan `start` explícito, y los textos
siempre llevan `start` y `end`.

---

## 6. Borrador del formato Brief

```markdown
# Brief: Reel de verano

- **Objetivo:** mostrar el viaje a la playa, emocionante y rápido
- **Público:** seguidores de Instagram
- **Formato:** 9:16, 1080x1920, 30 s
- **Estilo:** reel_dinamico
- **Música:** muestras/musica.mp3 (cortar al beat)
- **Material:** carpeta muestras/viaje/

## Escenas
1. (0–3 s) Llegada: toma amplia de la playa. Título "Verano 2026".
2. (3–15 s) Actividades: cortes rápidos de 1 s, al ritmo.
3. (15–25 s) Momentos lentos: atardecer, cámara lenta.
4. (25–30 s) Cierre: logo + "Sígueme para más".

## Restricciones
- No usar clips movidos o desenfocados
- Subtítulos no (no hay voz)
```

---

## 7. Reglas de oficio para el Skill

Puntos de partida que el Skill `editor-video` debe aplicar salvo que el brief diga otra cosa:

- **Cortar en acción o en pausa natural**, nunca a mitad de palabra. Usar la transcripción.
- **Cortes al beat** en estilos musicales; cambios de plano cada 1–2 s en reels y cada 3–6 s en vlogs.
- **Los primeros 2 segundos deciden:** empezar por la toma más fuerte.
- **Quitar silencios de más de 0,7 s y muletillas** en contenido hablado (configurable).
- **Evitar dos planos casi iguales seguidos** (salto de eje o *jump cut* involuntario).
- **Zona segura:** textos y subtítulos lejos de los bordes, y en 9:16 lejos de la zona de botones de
  la app.
- **Audio:** voz a −14 LUFS aproximadamente, música de 12 a 18 dB por debajo de la voz, sin
  saturación y con fundidos de audio de al menos 2 fotogramas en cada corte.
- **Transiciones con moderación:** corte seco por defecto; fundidos solo con intención (paso de
  tiempo o cambio de tono).
- **Siempre previsualizar y revisar** antes de decir "terminado".

---

## 8. Forma de trabajo con la IA

1. **Una tarea por sesión o por bloque:** la IA lee este archivo, toma la primera casilla `[ ]` de la
   fase actual y la explica en 2–3 líneas antes de empezar.
2. **Probar contra Shotcut real:** Shotcut AI abierto con el servidor MCP activo; la IA lo verifica
   con `get_state` antes de editar.
3. **No tocar proyectos del usuario sin avisar:** para pruebas usar un proyecto nuevo o una copia, y
   guardar antes de cambios grandes.
4. **Commit por tarea** en git con un mensaje claro.
5. **Actualizar este documento:** marcar `[x]`, añadir notas al registro y, si surge trabajo nuevo,
   añadirlo como tarea en la fase que corresponda.
6. **Detenerse al terminar cada tarea** y mostrar el resultado (captura, JSON o vídeo) para que el
   usuario lo apruebe.

---

## 9. Preguntas abiertas

- [x] ¿Dónde está el **código fuente** de Shotcut AI? ¿Es un *fork* de Shotcut (C++/Qt)? ¿Quién lo
      mantiene?
      → `github.com/Foxlith/Shotcut-AI`, *fork* de Shotcut en C++/Qt 6 + MLT 7. Lo mantiene Fox con
      Claude (fases y entregas en `plan.md` y `agent.md`).
- [x] ¿El servidor MCP interno se puede ampliar fácilmente con herramientas nuevas en C++?
      → Sí: se registra la herramienta en `src/ai/aitools.cpp` (nombre, esquema JSON y función). Si va
      dentro de `edit()`, es un paso *AI: …* de deshacer; las pruebas exigen documentarla en
      `docs/ai-mcp.md`.
- [ ] ¿Qué **GPU** tiene esta PC? Afecta a la velocidad de Whisper y del análisis visual.
      → whisper.cpp usa Vulkan (NVIDIA, AMD o Intel) si la hay, y si no la CPU. Solo cambia la
      velocidad; queda por medir en el PC de Fox.
- [x] ¿Se quiere que funcione **sin internet** (todo local) o se aceptan servicios en la nube?
      → Todo local (decisión de Fox). Solo se descargan una vez los modelos de Whisper.
- [x] ¿Formatos de destino prioritarios: YouTube, Reels/TikTok u otros?
      → YouTube 16:9 primero (1080p y 4K). El 9:16 y el 1:1 vienen con el reencuadre (Entrega 4).
- [ ] ¿Idiomas prioritarios para transcripción y subtítulos: español, inglés u otros?
      → Por defecto se detecta el idioma, así que español e inglés funcionan; `language` lo fija.
- [ ] ¿Se quiere publicar el proyecto como código abierto?

---

## 10. Registro de avances

| Fecha | Tarea | Resultado / notas |
|---|---|---|
| 27/09/2026 | Conexión MCP | `shotcut-ai` registrado en `~/.claude.json`; puente probado; 33 herramientas |
| 27/09/2026 | Prueba en vivo | 3 vídeos generados con ffmpeg, añadidos a la lista de medios y a V1 (13 s). Funciona |
| 28/09/2026 | Decisiones | Por entregas con PR; todo en `Shotcut-AI`; todo local; YouTube 16:9 primero; EditPlan en C++ |
| 28/09/2026 | Entrega 1 (Fase 0) | `docs/build-windows.md`, `scripts/sc.py`, muestras sintéticas y los 4 problemas de la sección 2 resueltos |
| 28/09/2026 | Entrega 1 (Fase 1) | `shotcut-analysis` con 11 herramientas. En pruebas: cortes al fotograma exacto, silencios a ±0,1 s, tempo ±2 BPM, volumen ±1 dB. `whisper-cli` en el zip (vuelve *Speech to Text*) |
